from utils import *
from sklearn.preprocessing import normalize
from collections import OrderedDict

def loadScene(sceneFile):
    sceneLines = [line.strip() for line in open(sceneFile)]

    numModels = sceneLines[2].split()[1]
    instances = []
    for line in sceneLines:
        parts = line.split()
        if parts[0] == 'newModel':
            modelId = parts[2]
        if parts[0] == 'parentContactPosition':
            parentContactPosition = mathutils.Vector([float(parts[1])*inchToMeter, float(parts[2])*inchToMeter, float(parts[3])*inchToMeter])            
        if parts[0] == 'parentIndex':
            parentIndex = int(parts[1])
        if parts[0] == 'transform':
            transform = mathutils.Matrix([[float(parts[1]), float(parts[2]), float(parts[3]), float(parts[4])], [float(parts[5]), float(parts[6]), float(parts[7]), float(parts[8])], [ float(parts[9]), float(parts[10]), float(parts[11]), float(parts[12])], [float(parts[13]), float(parts[14]), float(parts[15]), float(parts[16])]]).transposed()
            # ipdb.set_trace()
            transform[0][3] = transform[0][3]*inchToMeter
            transform[1][3] = transform[1][3]*inchToMeter
            transform[2][3] = transform[2][3]*inchToMeter
            # ipdb.set_trace()
            
            instances.append([modelId, parentIndex, parentContactPosition, transform])

    return instances


def composeScene(modelInstances, targetIndex):

    bpy.ops.scene.new()
    bpy.context.scene.name = 'Main Scene'
    scene = bpy.context.scene
    scene.unit_settings.system = 'METRIC'
    modelNum = 0
    for instance in modelInstances:
        if modelNum != targetIndex:
            scene.objects.link(instance)
        modelNum = modelNum + 1


    return scene


def importBlenderScenes(instances, completeScene, targetIndex):

    baseDir = '../COLLADA/'
    blenderScenes = []
    modelInstances = []
    modelNum = 0
    for instance in instances:
        modelId = instance[0]

        reg = re.compile('(room[0-9]+)')
        isRoom = reg.match(modelId)

        if completeScene or isRoom:

            transform = instance[3]

            modelPath = baseDir + modelId + '_cleaned.obj'
            print('Importing ' + modelPath )

            # if modelNum != targetIndex:
            bpy.ops.scene.new()
            bpy.context.scene.name = modelId
            scene = bpy.context.scene

            # scene.unit_settings.system = 'METRIC'
            # bpy.utils.collada_import(modelPath)


            bpy.ops.import_scene.obj(filepath=modelPath, split_mode='OFF', use_split_objects=True, use_split_groups=False)
            # ipdb.set_trace()
            sceneGroup = bpy.data.groups.new(modelId)

            scene.update()

            scaleMat = mathutils.Matrix.Scale(inchToMeter, 4)
            # xrotation = mathutils.Matrix.Rotation(-90,4, 'X')

            for mesh in scene.objects:
                if mesh.type == 'MESH':
                    sceneGroup.objects.link(mesh)
                    # ipdb.set_trace()
                    # mesh_transform = mesh.matrix_world
                    # mesh.matrix_world =  transform * mesh.matrix_world
                    mesh.pass_index = 0
                    # mesh.matrix_world[0][3] = mesh.matrix_world[0][3]*inchToMeter
                    # mesh.matrix_world[1][3] = mesh.matrix_world[1][3]*inchToMeter
                    # mesh.matrix_world[2][3] = mesh.matrix_world[2][3]*inchToMeter
                    # mesh.matrix_world = scaleMat * mesh.matrix_world
                     # ipdb.set_trace()
                    # mesh.data.show_double_sided = True

            modelInstance = bpy.data.objects.new(modelId, None)
            modelInstance.dupli_type = 'GROUP'
            modelInstance.dupli_group = sceneGroup
            modelInstance.matrix_world = transform
            modelInstance.pass_index = 0
            modelInstances.append(modelInstance)
            modelNum = modelNum + 1
            # ipdb.set_trace()
            blenderScenes.append(scene)


    return blenderScenes, modelInstances

def loadTargetModels(experimentTeapots):

    teapots = [line.strip() for line in open('teapots.txt')]
    targetModels = []

    baseDir = '../databaseFull/models/'
    targetInstances = []
    blenderTeapots = []
    transformations = []
    modelNum = 0

    selection = [ teapots[i] for i in experimentTeapots]
    for teapot in selection:
        targetGroup = bpy.data.groups.new(teapot)
        fullTeapot = baseDir + teapot + '.obj'
        modelPath = fullTeapot
        bpy.ops.scene.new()
        bpy.context.scene.name = teapot
        scene = bpy.context.scene
        scene.unit_settings.system = 'METRIC'
        print("Importing " + modelPath)
        # bpy.utils.collada_import(modelPath)

        bpy.ops.import_scene.obj(filepath=modelPath, split_mode='OFF', use_split_objects=True, use_split_groups=False)
        scene.update()
        # modifySpecular(scene, 0.3)

        #Rotate the object to the azimuth angle we define as 0.
        # rot = mathutils.Matrix.Rotation(radians(-90), 4, 'X')
        # rot = mathutils.Matrix.Rotation(radians(90), 4, 'Z')
        # rotateMatrixWorld(scene,  rot )
        # rot = mathutils.Matrix.Rotation(radians(90), 4, 'Z')

        matrix_world = mathutils.Matrix.Identity(4)
        minZ, maxZ = modelHeight(scene.objects, mathutils.Matrix.Identity(4))
        minY, maxY = modelDepth(scene.objects, mathutils.Matrix.Identity(4))
        scaleZ = 0.265/(maxZ-minZ)
        scaleY = 0.18/(maxY-minY)
        scale = min(scaleZ, scaleY)
        scaleMat = mathutils.Matrix.Scale(scale, 4)
        for mesh in scene.objects:
            if mesh.type == 'MESH':

                mesh.matrix_world =  scaleMat * mesh.matrix_world

        matrix_world = scaleMat * matrix_world

        rot = mathutils.Matrix.Rotation(radians(90), 4, 'Z') 
        rotateMatrixWorld(scene,  rot )

        matrix_world  = rot * matrix_world

        minZ, maxZ = modelHeight(scene.objects, mathutils.Matrix.Identity(4))

        center = centerOfGeometry(scene.objects, mathutils.Matrix.Identity(4))

        for mesh in scene.objects:
            if mesh.type == 'MESH':
                mesh.matrix_world = mathutils.Matrix.Translation(-center) * mesh.matrix_world

        matrix_world = mathutils.Matrix.Translation(-center) * matrix_world

        minZ, maxZ = modelHeight(scene.objects, mathutils.Matrix.Identity(4))

        for mesh in scene.objects:
            if mesh.type == 'MESH':
                mesh.matrix_world = mathutils.Matrix.Translation(mathutils.Vector((0,0,-minZ))) * mesh.matrix_world

        matrix_world = mathutils.Matrix.Translation(mathutils.Vector((0,0,-minZ))) * matrix_world

        transformations = transformations + [matrix_world]
        for mesh in scene.objects:
            targetGroup.objects.link(mesh)
            mesh.pass_index = 1

        targetInstance = bpy.data.objects.new(teapot, None)
        targetInstance.dupli_type = 'GROUP'
        targetInstance.dupli_group = targetGroup
        targetInstance.pass_index = 1
        targetInstances.append(targetInstance)
        blenderTeapots.append(scene)
    # ipdb.set_trace()
    return blenderTeapots, targetInstances, transformations



def loadSceneBlenderToOpenDR(sceneIdx, loadSavedScene, serializeScene, width, height):
    replaceableScenesFile = '../databaseFull/fields/scene_replaceables.txt'
    sceneLines = [line.strip() for line in open(replaceableScenesFile)]
    sceneLineNums = numpy.arange(len(sceneLines))
    sceneNum =  sceneLineNums[sceneIdx]
    sceneLine = sceneLines[sceneNum]
    sceneParts = sceneLine.split(' ')
    sceneFile = sceneParts[0]
    sceneNumber = int(re.search('.+?scene([0-9]+)\.txt', sceneFile, re.IGNORECASE).groups()[0])
    sceneFileName = re.search('.+?(scene[0-9]+\.txt)', sceneFile, re.IGNORECASE).groups()[0]
    targetIndex = int(sceneParts[1])
    instances = loadScene('../databaseFull/scenes/' + sceneFileName)
    targetParentPosition = instances[targetIndex][2]
    targetParentIndex = instances[targetIndex][1]

    cam = bpy.data.cameras.new("MainCamera")
    camera = bpy.data.objects.new("MainCamera", cam)
    world = bpy.data.worlds.new("MainWorld")

    sceneDicFile = 'data/scene' + str(sceneIdx) + '.pickle'
    sceneDic = {}

    #We can store the OpenDR scene data as a pickle file for much faster loading.

    [blenderScenes, modelInstances] = importBlenderScenes(instances, True, targetIndex)

    targetParentInstance = modelInstances[targetParentIndex]
    targetParentInstance.layers[2] = True

    roomName = ''
    for model in modelInstances:
        reg = re.compile('(room[0-9]+)')
        res = reg.match(model.name)
        if res:
            roomName = res.groups()[0]

    scene = composeScene(modelInstances, targetIndex)

    roomInstance = scene.objects[roomName]
    roomInstance.layers[2] = True
    targetParentInstance.layers[2] = True

    setupScene(scene, targetIndex,roomName, world, camera, width, height, 16, False, False)

    scene.update()

    scene.render.filepath = 'opendr_blender.png'
    if not loadSavedScene:
        # bpy.ops.render.render( write_still=True )
        # ipdb.set_trace()
        # v,f_list, vc, vn, uv, haveTextures_list, textures_list = unpackObjects(teapot)
        v = []
        f_list = []
        vc  = []
        vn  = []
        uv  = []
        haveTextures_list  = []
        textures_list  = []
        print("Unpacking blender data for OpenDR.")
        for modelInstance in scene.objects:
            if modelInstance.dupli_group != None:
                vmod,f_listmod, vcmod, vnmod, uvmod, haveTextures_listmod, textures_listmod = unpackObjects(modelInstance, 0, False, False)
                # gray = np.dot(np.array([0.3, 0.59, 0.11]), vcmod[0].T).T
                # sat = 0.5
                # vcmod[0][:,0] = vcmod[0][:,0] * sat + (1-sat) * gray
                # vcmod[0][:,1] = vcmod[0][:,1] * sat + (1-sat) * gray
                # vcmod[0][:,2] = vcmod[0][:,2] * sat + (1-sat) * gray
                v = v + vmod
                f_list = f_list + f_listmod
                vc = vc + vcmod
                vn = vn + vnmod
                uv = uv + uvmod
                haveTextures_list = haveTextures_list + haveTextures_listmod
                textures_list = textures_list + textures_listmod

        #Serialize
        if serializeScene:
            sceneDic = {'v':v,'f_list':f_list,'vc':vc,'uv':uv,'haveTextures_list':haveTextures_list,'vn':vn,'textures_list': textures_list}
            with open(sceneDicFile, 'wb') as pfile:
                pickle.dump(sceneDic, pfile)

        print("Serialized scene!")
    else:
        with open(sceneDicFile, 'rb') as pfile:
            sceneDic = pickle.load(pfile)
            v = sceneDic['v']
            f_list = sceneDic['f_list']
            vc = sceneDic['vc']
            uv = sceneDic['uv']
            haveTextures_list = sceneDic['haveTextures_list']
            vn = sceneDic['vn']
            textures_list = sceneDic['textures_list']

        print("Loaded serialized scene!")

    return v, f_list, vc, vn, uv, haveTextures_list, textures_list, scene, targetParentPosition

def unpackObjects(target, targetIdx, loadTarget, saveData):
    targetDicFile = 'data/target' + str(targetIdx) + '.pickle'
    targetDic = {}
    if not loadTarget:
        f_list = []
        v = []
        vc = []
        vn = []
        uv = []
        haveTextures = []
        textures_list = []
        vertexMeshIndex = 0
        for mesh in target.dupli_group.objects:
            if mesh.type == 'MESH':
                # mesh.data.validate(verbose=True, clean_customdata=True)
                fmesh, vmesh, vcmesh,  nmesh, uvmesh, haveTexture, textures  = buildData(mesh.data)
                f_list = f_list + [fmesh]
                vc = vc + [vcmesh]
                transf = np.array(np.dot(target.matrix_world, mesh.matrix_world))
                vmesh = np.hstack([vmesh, np.ones([vmesh.shape[0],1])])
                vmesh = ( np.dot(transf , vmesh.T)).T[:,0:3]
                v = v + [vmesh]
                transInvMat = np.linalg.inv(transf).T
                nmesh = np.hstack([nmesh, np.ones([nmesh.shape[0],1])])
                nmesh = (np.dot(transInvMat , nmesh.T)).T[:,0:3]
                vn = vn + [normalize(nmesh, axis=1)]
                uv = uv + [uvmesh]
                haveTextures_list = haveTextures + [haveTexture]
                textures_list = textures_list + [textures]

                vertexMeshIndex = vertexMeshIndex + len(vmesh)
        #Serialize
        if saveData:
            targetDic = {'v':v,'f_list':f_list,'vc':vc,'uv':uv,'haveTextures_list':haveTextures_list,'vn':vn,'textures_list': textures_list}
            with open(targetDicFile, 'wb') as pfile:
                pickle.dump(targetDic, pfile)

            print("Serialized scene!")

    else:
        with open(targetDicFile, 'rb') as pfile:
            targetDic = pickle.load(pfile)
            v = targetDic['v']
            f_list = targetDic['f_list']
            vc = targetDic['vc']
            uv = targetDic['uv']
            haveTextures_list = targetDic['haveTextures_list']
            vn = targetDic['vn']
            textures_list = targetDic['textures_list']
        print("Loaded serialized target!")

    return [v],[f_list],[vc],[vn], [uv], [haveTextures_list], [textures_list]

def buildData (msh):

    lvdic = {} # local dictionary
    lfl = [] # lcoal faces index list
    lvl = [] # local vertex list
    lvcl = []
    lnl = [] # local normal list
    luvl = [] # local uv list
    lvcnt = 0 # local vertices count
    isSmooth = False

    texdic = {} # local dictionary

    msh.calc_tessface()
    # if len(msh.tessfaces) == 0 or msh.tessfaces is None:
    #     msh.calc_tessface()

    textureNames = []
    haveUVs = []

    for i,f in enumerate(msh.polygons):
        isSmooth = f.use_smooth
        tmpfaces = []
        hasUV = False    # true by default, it will be verified below
        texture = None
        texname = None
        if (len(msh.tessface_uv_textures)>0):
            activeUV = msh.tessface_uv_textures.active.data

            if msh.tessface_uv_textures.active.data[i].image is not None:
                # ipdb.set_trace()
                texname = msh.tessface_uv_textures.active.data[i].image.name
                hasUV = True
                texture = texdic.get(texname)
                if (texture is None): # vertex not found
                    # print("Image: " + texname)
                    # print("Clamp x: " + str(msh.tessface_uv_textures.active.data[i].image.use_clamp_x))
                    # print("Clamp y: " + str(msh.tessface_uv_textures.active.data[i].image.use_clamp_y))
                    # print("Tile x: " + str(msh.tessface_uv_textures.active.data[i].image.tiles_x))
                    # print("Tile y: " + str(msh.tessface_uv_textures.active.data[i].image.tiles_y))
                    texture = np.flipud(np.array(msh.tessface_uv_textures.active.data[i].image.pixels).reshape([msh.tessface_uv_textures.active.data[i].image.size[1],msh.tessface_uv_textures.active.data[i].image.size[0],4])[:,:,:3])
                    texdic[texname] = texture
        textureNames = textureNames + [texname]
        haveUVs = haveUVs + [hasUV]


        for j,v in enumerate(f.vertices):

            vec = msh.vertices[v].co

            vec = r3d(vec)

            if (isSmooth):  # use vertex normal
                nor = msh.vertices[v].normal
            else:           # use face normal
                nor = f.normal

            vcolor = msh.materials[f.material_index].diffuse_color[:]
            if vcolor == (0.0,0.0,0.0) and msh.materials[f.material_index].specular_color[:] != (0.0,0.0,0.0):
                vcolor = msh.materials[f.material_index].specular_color[:]
                # print("Using specular!")

            nor = r3d(nor)
            co = (0.0, 0.0)

            if hasUV:
                co = activeUV[i].uv[j]
                co = r2d(co)
                vcolor = (1.0,1.0,1.0)

            key = vec, nor, co
            vinx = lvdic.get(key)

            if (vinx is None): # vertex not found

                lvdic[key] = lvcnt
                lvl.append(vec)
                lnl.append(nor)

                lvcl.append(vcolor)
                luvl.append(co)
                tmpfaces.append(lvcnt)
                lvcnt+=1
            else:
                inx = lvdic[key]
                tmpfaces.append(inx)

        if (len(tmpfaces)==3):
            lfl.append(tmpfaces)
        else:
            lfl.append([tmpfaces[0], tmpfaces[1], tmpfaces[2]])
            lfl.append([tmpfaces[0], tmpfaces[2], tmpfaces[3]])

    # vtx.append(lvdic)
    textures = []
    haveTextures = []
    f_list = []

    orderedtexs = OrderedDict(sorted(texdic.items(), key=lambda t: t[0]))
    for texname, texture in orderedtexs.items():
        fidxs = [lfl[idx] for idx in range(len(lfl)) if textureNames[idx] == texname]
        f_list = f_list + [np.vstack(fidxs)]
        textures = textures + [texture]
        haveTextures = haveTextures + [True]
    try:
        fidxs = [lfl[idx] for idx in range(len(lfl)) if haveUVs[idx] == False]
    except:
        ipdb.set_trace()

    if fidxs != None and fidxs != []:
        f_list = f_list + [np.vstack(fidxs)]
        textures = textures + [None]
        haveTextures = haveTextures + [False]

    #update global lists and dictionaries
    v = np.vstack(lvl)
    vc = np.vstack(lvcl)
    n = np.vstack(lnl)
    uv = np.vstack(luvl)

    return f_list, v, vc, n, uv, haveTextures, textures
