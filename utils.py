#!/usr/bin/env python3.4m
 
import bpy
import bpy_extras
import numpy
import mathutils
from math import radians
import h5py
import scipy.io

import sys
import io
import os
import pickle
import ipdb
import re

inchToMeter = 0.0254

def loadData():
    #data
    # fdata = h5py.File('../data/data-all-flipped-cropped-512.mat','r')
    # data = fdata["data"]

    data = scipy.io.loadmat('../data/data-all-flipped-cropped-512-scipy.mat')['data']

    images = h5py.File('../data/images-all-flipped-cropped-512-color.mat','r')
    # images = f["images"]
    # imgs = numpy.array(images)
    # N = imgs.shape[0]
    # imgs = imgs.transpose(0,2,3,1)

    # f = h5py.File('../data/all-flipped-cropped-512-crossval6div2_py-experiment.mat')
    # experiments = f["experiments_data"]

    # f = h5py.File('../data/all-flipped-cropped-512-crossval6div2_py-experiment.mat')
    experiments = scipy.io.loadmat('../data/all-flipped-cropped-512-crossval6all2-experiment.mat')

    return data, images, experiments['experiments_data']

def loadGroundTruth(rendersDir):
    lines = [line.strip() for line in open(rendersDir + 'groundtruth.txt')]
    groundTruthLines = []
    imageFiles = []
    segmentFiles = []
    segmentSingleFiles = []
    unoccludedFiles = []
    prefixes = []
    for instance in lines:
        parts = instance.split(' ')
        framestr = '{0:04d}'.format(int(parts[4]))
        prefix = ''
        az = float(parts[0])
        objAz = float(parts[1])
        el = float(parts[2])
        objIndex = int(parts[3])
        frame = int(parts[4])
        sceneNum = int(parts[5])
        targetIndex = int(parts[6])

        spoutPosX = int(float(parts[7]))
        spoutPosY = int(float(parts[8]))
        handlePosX = int(float(parts[9]))
        handlePosY = int(float(parts[10]))
        tipPosX = int(float(parts[11]))
        tipPosY = int(float(parts[12]))
        spoutOccluded = int(float(parts[13]))
        handleOccluded = int(float(parts[14]))
        tipOccluded = int(float(parts[15]))

        if len(parts) == 17:
            prefix = parts[16]
        outfilename = "render" + prefix + "_obj" + str(objIndex) + "_scene" + str(sceneNum) + '_target' + str(targetIndex) + '_' + framestr
        outfilenamesingle = "render" + prefix + "_obj" + str(objIndex) + "_scene" + str(sceneNum) + '_target' + str(targetIndex) + '_single_' + framestr
        outfilenameunoccluded = "render" + prefix + "_obj" + str(objIndex) + "_scene" + str(sceneNum) + '_target' + str(targetIndex) + '_unoccluded' + framestr
        imageFile = rendersDir + "images/" +  outfilename + ".png"
        segmentFile =  rendersDir + "images/" +  outfilename + "_segment.png"
        segmentFileSingle =  rendersDir + "images/" +  outfilenamesingle + "_segment.png"
        unoccludedFile =  rendersDir + "images/" +  outfilenameunoccluded + ".png"
        if os.path.isfile(imageFile):
            imageFiles = imageFiles + [imageFile]
            segmentFiles = segmentFiles + [segmentFile]
            segmentSingleFiles = segmentSingleFiles + [segmentFileSingle]
            unoccludedFiles = unoccludedFiles + [unoccludedFile]
            prefixes = prefixes + [prefix]
            groundTruthLines = groundTruthLines + [[az, objAz, el, objIndex, frame, 0.0, sceneNum, targetIndex, spoutPosX, spoutPosY, handlePosX, handlePosY, tipPosX, tipPosY, spoutOccluded, handleOccluded, tipOccluded]]

    # groundTruth = numpy.zeros([len(groundTruthLines), 5])
    groundTruth = numpy.array(groundTruthLines)

    # groundTruth = numpy.hstack((groundTruth,numpy.zeros((groundTruth.shape[0],1))))

    lines = [line.strip() for line in open(rendersDir + 'occlusions.txt')]

    for instance in lines:
        parts = instance.split(' ')
        prefix = ''
        try:
            index = numpy.where((groundTruth[:, 3] == int(parts[0])) & (groundTruth[:, 4] == int(parts[1])) & (groundTruth[:,6] == int(parts[2])) & (groundTruth[:,7] == int(parts[3])) & (eqPrefixes))[0][0]
            groundTruth[index, 5] = float(parts[4])
        except:
            print("Problem!")


 
    return groundTruth, imageFiles, segmentFiles, segmentSingleFiles, unoccludedFiles, prefixes

def modifySpecular(scene, delta):
    for model in scene.objects:
        if model.type == 'MESH':
            for mat in model.data.materials:
                mat.specular_shader = 'PHONG'
                mat.specular_intensity = mat.specular_intensity + delta
                mat.specular_hardness = mat.specular_hardness / 4.0


def makeMaterial(name, diffuse, specular, alpha):
    mat = bpy.data.materials.new(name)
    mat.diffuse_color = diffuse
    mat.diffuse_shader = 'LAMBERT' 
    mat.diffuse_intensity = 1.0 
    mat.specular_color = specular
    mat.specular_shader = 'COOKTORR'
    mat.specular_intensity = 0.5
    mat.alpha = alpha
    mat.ambient = 1
    return mat
 

def setMaterial(ob, mat):
    me = ob.data
    me.materials.append(mat)

def look_at(obj_camera, point):
    loc_camera = obj_camera.location

    direction = point - loc_camera
    # point the cameras '-Z' and use its 'Y' as up
    rot_quat = direction.to_track_quat('-Z', 'Y')

    # assume we're using euler rotation
    obj_camera.rotation_euler = rot_quat.to_euler()


def modelHeight(objects, transform):
    maxZ = -999999;
    minZ = 99999;
    for model in objects:
        if model.type == 'MESH':
            for v in model.data.vertices:
                if (transform * model.matrix_world * v.co).z > maxZ:
                    maxZ = (transform * model.matrix_world * v.co).z
                if (transform * model.matrix_world * v.co).z < minZ:
                    minZ = (transform * model.matrix_world * v.co).z


    return minZ, maxZ

def modelDepth(objects, transform):
    maxY = -999999;
    minY = 99999;
    for model in objects:
        if model.type == 'MESH':
            for v in model.data.vertices:
                if (transform * model.matrix_world * v.co).y > maxY:
                    maxY = (transform * model.matrix_world * v.co).y
                if (transform * model.matrix_world * v.co).y < minY:
                    minY = (transform * model.matrix_world * v.co).y


    return minY, maxY


def modelWidth(objects, transform):
    maxX = -999999;
    minX = 99999;
    for model in objects:
        if model.type == 'MESH':
            for v in model.data.vertices:
                if (transform * model.matrix_world * v.co).x > maxX:
                    maxX = (transform * model.matrix_world * v.co).x
                if (transform * model.matrix_world * v.co).x < minX:
                    minX = (transform * model.matrix_world * v.co).x


    return minX, maxX


def centerOfGeometry(objects, transform):
    center = mathutils.Vector((0.0,0.0,0.0))
    numVertices = 0.0
    for model in objects:
        if model.type == 'MESH':
            numVertices = numVertices + len(model.data.vertices)
            for v in model.data.vertices:
                center = center + (transform * model.matrix_world * v.co)


    return center/numVertices

def setEulerRotation(scene, eulerVectorRotation):
    for model in scene.objects:
        if model.type == 'MESH':
            model.rotation_euler = eulerVectorRotation

    scene.update()

def rotateMatrixWorld(scene, rotationMat):
    for model in scene.objects:
        if model.type == 'MESH':
            model.matrix_world = rotationMat * model.matrix_world

    scene.update()  


def AutoNodeOff():
    mats = bpy.data.materials
    for cmat in mats:
        cmat.use_nodes=False

def AutoNode():
    mats = bpy.data.materials
    for cmat in mats:
        #print(cmat.name)
        cmat.use_nodes=True
        TreeNodes=cmat.node_tree
        links = TreeNodes.links
    
        shader=''
        for n in TreeNodes.nodes:
    
            if n.type == 'ShaderNodeTexImage' or n.type == 'RGBTOBW':
                TreeNodes.nodes.remove(n)

            if n.type == 'OUTPUT_MATERIAL':
                shout = n       
                        
            if n.type == 'BACKGROUND':
                shader=n              
            if n.type == 'BSDF_DIFFUSE':
                shader=n  
            if n.type == 'BSDF_GLOSSY':
                shader=n              
            if n.type == 'BSDF_GLASS':
                shader=n  
            if n.type == 'BSDF_TRANSLUCENT':
                shader=n     
            if n.type == 'BSDF_TRANSPARENT':
                shader=n   
            if n.type == 'BSDF_VELVET':
                shader=n     
            if n.type == 'EMISSION':
                shader=n 
            if n.type == 'HOLDOUT':
                shader=n   

        if cmat.raytrace_mirror.use and cmat.raytrace_mirror.reflect_factor>0.001:
            print("MIRROR")
            if shader:
                if not shader.type == 'BSDF_GLOSSY':
                    print("MAKE MIRROR SHADER NODE")
                    TreeNodes.nodes.remove(shader)
                    shader = TreeNodes.nodes.new('BSDF_GLOSSY')    # RGB node
                    shader.location = 0,450
                    #print(shader.glossy)
                    links.new(shader.outputs[0],shout.inputs[0]) 
                        
        if not shader:
            shader = TreeNodes.nodes.new('BSDF_DIFFUSE')    # RGB node
            shader.location = 0,450
             
            shout = TreeNodes.nodes.new('OUTPUT_MATERIAL')
            shout.location = 200,400          
            links.new(shader.outputs[0],shout.inputs[0])                
                   
                   
                   
        if shader:                         
            textures = cmat.texture_slots
            for tex in textures:
                                
                if tex:
                    if tex.texture.type=='IMAGE':
                         
                        img = tex.texture.image
                        #print(img.name)  
                        shtext = TreeNodes.nodes.new('ShaderNodeTexImage')
          
                        shtext.location = -200,400 
        
                        shtext.image=img
        
                        if tex.use_map_color_diffuse:
                            links.new(shtext.outputs[0],shader.inputs[0]) 
    
                        if tex.use_map_normal:
                            t = TreeNodes.nodes.new('RGBTOBW')
                            t.location = -0,300 
                            links.new(t.outputs[0],shout.inputs[2]) 
                            links.new(shtext.outputs[0],t.inputs[0]) 



def cameraLookingInsideRoom(cameraAzimuth):
    if cameraAzimuth > 270 and cameraAzimuth < 90:
        return True
    return False

def deleteInstance(instance):

    for mesh in instance.dupli_group.objects:
        mesh.user_clear()
        bpy.data.objects.remove(mesh)

    instance.dupli_group.user_clear()
    bpy.data.groups.remove(instance.dupli_group)
    instance.user_clear()
    bpy.data.objects.remove(instance)

def setupScene(scene, targetIndex, roomName, world, distance, camera, width, height, numSamples, useCycles, useGPU):
    if useCycles:
        #Switch Engine to Cycles
        scene.render.engine = 'CYCLES'
        if useGPU:
            bpy.context.scene.cycles.device = 'GPU'
            bpy.context.user_preferences.system.compute_device_type = 'CUDA'
            bpy.context.user_preferences.system.compute_device = 'CUDA_MULTI_0'

        AutoNode()
        # bpy.context.scene.render.engine = 'BLENDER_RENDER'

        cycles = bpy.context.scene.cycles

        cycles.samples = 1024
        cycles.max_bounces = 36
        cycles.min_bounces = 4
        cycles.caustics_reflective = True
        cycles.caustics_refractive = True
        cycles.diffuse_bounces = 36
        cycles.glossy_bounces = 12
        cycles.transmission_bounces = 12
        cycles.volume_bounces = 12
        cycles.transparent_min_bounces = 4
        cycles.transparent_max_bounces = 12

    scene.render.image_settings.compression = 0
    scene.render.resolution_x = width #perhaps set resolution in code
    scene.render.resolution_y = height
    scene.render.resolution_percentage = 100

    scene.camera = camera
    camera.up_axis = 'Y'
    camera.data.angle = 60 * 180 / numpy.pi
    camera.data.clip_start = 0.01
    camera.data.clip_end = 10

    # center = centerOfGeometry(modelInstances[targetIndex].dupli_group.objects, modelInstances[targetIndex].matrix_world)
    # # center = mathutils.Vector((0,0,0))
    # # center = instances[targetIndex][1]
    #
    # originalLoc = mathutils.Vector((0,-distance , 0))
    # elevation = 45.0
    # azimuth = 0
    #
    # elevationRot = mathutils.Matrix.Rotation(radians(-elevation), 4, 'X')
    # azimuthRot = mathutils.Matrix.Rotation(radians(-azimuth), 4, 'Z')
    # location = center + azimuthRot * elevationRot * originalLoc
    # camera.location = location

    # lamp_data2 = bpy.data.lamps.new(name="LampBotData", type='POINT')
    # lamp2 = bpy.data.objects.new(name="LampBot", object_data=lamp_data2)
    # lamp2.location = targetParentPosition + mathutils.Vector((0,0,1.5))
    # lamp2.data.energy = 0.00010
    # # lamp.data.size = 0.25
    # lamp2.data.use_diffuse = True
    # lamp2.data.use_specular = True
    # # scene.objects.link(lamp2)
        

        # # toggle lamps
        # if obj.type == 'LAMP':
        #     obj.cycles_visibility.camera = not obj.cycles_visibility.camera

    roomInstance = scene.objects[roomName]

    ceilMinX, ceilMaxX = modelWidth(roomInstance.dupli_group.objects, roomInstance.matrix_world)
    ceilWidth = (ceilMaxX - ceilMinX)
    ceilMinY, ceilMaxY = modelDepth(roomInstance.dupli_group.objects, roomInstance.matrix_world)
    ceilDepth = (ceilMaxY - ceilMinY) 
    ceilMinZ, ceilMaxZ = modelHeight(roomInstance.dupli_group.objects, roomInstance.matrix_world)
    ceilPos =  mathutils.Vector(((ceilMaxX + ceilMinX) / 2.0, (ceilMaxY + ceilMinY) / 2.0 , ceilMaxZ))

    numLights = int(numpy.floor((ceilWidth-0.2)/1.15))
    lightInterval = ceilWidth/numLights

    for light in range(numLights):
        lightXPos = light*lightInterval + lightInterval/2.0
        lamp_data = bpy.data.lamps.new(name="Rect", type='AREA')
        lamp = bpy.data.objects.new(name="Rect", object_data=lamp_data)
        lamp.data.size = 0.15
        lamp.data.size_y = ceilDepth - 0.2
        lamp.data.shape = 'RECTANGLE'
        lamp.location = mathutils.Vector((ceilPos.x - ceilWidth/2.0 + lightXPos, ceilPos.y, ceilMaxZ))
        lamp.data.energy = 0.0025
        # if not useCycles:
        #     lamp.data.energy = 0.0015

        if useCycles:
            lamp.data.cycles.use_multiple_importance_sampling = True
            lamp.data.use_nodes = True
            lamp.data.node_tree.nodes['Emission'].inputs[1].default_value = 5
        scene.objects.link(lamp)
        lamp.layers[1] = True
        lamp.layers[2] = True

    scene.world = world
    scene.world.light_settings.distance = 0.1

    if not useCycles:
        scene.render.use_raytrace = False
        scene.render.use_shadows = False

        # scene.view_settings.exposure = 5
        # scene.view_settings.gamma = 0.5
        scene.world.light_settings.use_ambient_occlusion = True
        scene.world.light_settings.ao_blend_type = 'ADD'
        scene.world.light_settings.use_indirect_light = True
        scene.world.light_settings.indirect_bounces = 1
        scene.world.light_settings.use_cache = True

        scene.world.light_settings.ao_factor = 1
        scene.world.light_settings.indirect_factor = 1
        scene.world.light_settings.gather_method = 'APPROXIMATE'

    world.light_settings.use_environment_light = False
    world.light_settings.environment_energy = 0.0
    world.horizon_color = mathutils.Color((0.0,0.0,0.0))
    # world.light_settings.samples = 20

    # world.light_settings.use_ambient_occlusion = False
    #
    # world.light_settings.ao_factor = 1
    # world.exposure = 1.1
    # world.light_settings.use_indirect_light = True

    # scene.sequencer_colorspace_settings.name = 'Linear'
    scene.update()

    bpy.ops.scene.render_layer_add()
    bpy.ops.scene.render_layer_add()

    camera.layers[1] = True
    scene.render.layers[0].use_pass_object_index = True
    scene.render.layers[1].use_pass_object_index = True
    scene.render.layers[1].use_pass_combined = True

    camera.layers[2] = True

    scene.layers[1] = False
    scene.layers[2] = False
    scene.layers[0] = True
    scene.render.layers[0].use = True
    scene.render.layers[1].use = False
    scene.render.layers[2].use = False

def targetSceneCollision(target, scene):

    for sceneInstance in scene.objects:
        if sceneInstance.type == 'EMPTY' and sceneInstance != target and sceneInstance.name != roomName and sceneInstance != targetParentInstance:
            if instancesIntersect(teapot, sceneInstance):
                return True

    return False


def view_plane(camd, winx, winy, xasp, yasp):
    #/* fields rendering */
    ycor = yasp / xasp
    use_fields = False
    if (use_fields):
      ycor *= 2

    def BKE_camera_sensor_size(p_sensor_fit, sensor_x, sensor_y):
        #/* sensor size used to fit to. for auto, sensor_x is both x and y. */
        if (p_sensor_fit == 'VERTICAL'):
            return sensor_y;

        return sensor_x;

    if (camd.type == 'ORTHO'):
      #/* orthographic camera */
      #/* scale == 1.0 means exact 1 to 1 mapping */
      pixsize = camd.ortho_scale
    else:
      #/* perspective camera */
      sensor_size = BKE_camera_sensor_size(camd.sensor_fit, camd.sensor_width, camd.sensor_height)
      pixsize = (sensor_size * camd.clip_start) / camd.lens

    #/* determine sensor fit */
    def BKE_camera_sensor_fit(p_sensor_fit, sizex, sizey):
        if (p_sensor_fit == 'AUTO'):
            if (sizex >= sizey):
                return 'HORIZONTAL'
            else:
                return 'VERTICAL'

        return p_sensor_fit

    sensor_fit = BKE_camera_sensor_fit(camd.sensor_fit, xasp * winx, yasp * winy)

    if (sensor_fit == 'HORIZONTAL'):
      viewfac = winx
    else:
      viewfac = ycor * winy

    pixsize /= viewfac

    #/* extra zoom factor */
    pixsize *= 1 #params->zoom

    #/* compute view plane:
    # * fully centered, zbuffer fills in jittered between -.5 and +.5 */
    xmin = -0.5 * winx
    ymin = -0.5 * ycor * winy
    xmax =  0.5 * winx
    ymax =  0.5 * ycor * winy

    #/* lens shift and offset */
    dx = camd.shift_x * viewfac # + winx * params->offsetx
    dy = camd.shift_y * viewfac # + winy * params->offsety

    xmin += dx
    ymin += dy
    xmax += dx
    ymax += dy

    #/* fields offset */
    #if (params->field_second):
    #    if (params->field_odd):
    #        ymin -= 0.5 * ycor
    #        ymax -= 0.5 * ycor
    #    else:
    #        ymin += 0.5 * ycor
    #        ymax += 0.5 * ycor

    #/* the window matrix is used for clipping, and not changed during OSA steps */
    #/* using an offset of +0.5 here would give clip errors on edges */
    xmin *= pixsize
    xmax *= pixsize
    ymin *= pixsize
    ymax *= pixsize

    return xmin, xmax, ymin, ymax


def projection_matrix(camd, scene):
    r = scene.render
    left, right, bottom, top = view_plane(camd, r.resolution_x, r.resolution_y, 1, 1)

    farClip, nearClip = camd.clip_end, camd.clip_start

    Xdelta = right - left
    Ydelta = top - bottom
    Zdelta = farClip - nearClip

    mat = [[0]*4 for i in range(4)]

    mat[0][0] = nearClip * 2 / Xdelta
    mat[1][1] = nearClip * 2 / Ydelta
    mat[2][0] = (right + left) / Xdelta #/* note: negate Z  */
    mat[2][1] = (top + bottom) / Ydelta
    mat[2][2] = -(farClip + nearClip) / Zdelta
    mat[2][3] = -1
    mat[3][2] = (-2 * nearClip * farClip) / Zdelta
    # ipdb.set_trace()
    # return sum([c for c in mat], [])
    projMat = mathutils.Matrix(mat)
    return projMat.transposed()

def image_projection(scene, point):
    p4d = mathutils.Vector.Fill(4, 1)
    p4d.x = point.x
    p4d.y = point.y
    p4d.z = point.z
    projectionMat = projection_matrix(scene.camera.data, scene)
    ipdb.set_trace()
    proj = projectionMat * scene.camera.matrix_world.inverted() * p4d
    return [scene.render.resolution_x*(proj.x/proj.w + 1)/2, scene.render.resolution_y*(proj.y/proj.w + 1)/2]

def image_project(scene, camera, point):
    co_2d = bpy_extras.object_utils.world_to_camera_view(scene, camera, point)

    # print("2D Coords:", co_2d)

    # If you want pixel coords
    render_scale = scene.render.resolution_percentage / 100
    render_size = ( int(scene.render.resolution_x * render_scale), int(scene.render.resolution_y * render_scale))
    return (round(co_2d.x * render_size[0]), round(co_2d.y * render_size[1]))

#Need to verify!
def closestCameraIntersection(scene, point):
    for instance in scene.objects:

        if instance.type == 'EMPTY' and instance.dupli_type == 'GROUP':
            instanceLoc = numpy.array(instance.location)
            camLoc = numpy.array(scene.camera.location)
            pointLoc = numpy.array(point)
            invInstanceTransf = instance.matrix_world.inverted()
            localCamTmp = invInstanceTransf * scene.camera.location
            if numpy.linalg.norm(instanceLoc - camLoc) < numpy.linalg.norm(pointLoc - camLoc) and (instanceLoc - camLoc).dot(pointLoc - camLoc) > 0:
                for mesh in instance.dupli_group.objects:
                    if mesh.type == 'MESH':
                        invMeshTransf = mesh.matrix_world.inverted()
                        localCam = invMeshTransf * localCamTmp
                        localPoint = invMeshTransf * invInstanceTransf * point

                        location, normal, index = mesh.ray_cast(localCam, localPoint)
                        if index != -1:
                            #Success.
                            return True

    return False

def sceneIntersection(scene, point):
    result, object, matrix, location, normal = scene.ray_cast(scene.camera.location, point)

    return result
