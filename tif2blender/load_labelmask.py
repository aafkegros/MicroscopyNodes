import numpy as np
import bpy
import bmesh
from bpy_extras.object_utils import AddObjectHelper, object_data_add
from pathlib import Path
import json, difflib,time
from .collection_handling import *

def labelmask_shader(maskchannel, maxval):
    # do not check whether it exists, so a new load will force making a new mat
    mat = bpy.data.materials.new(f'channel {maskchannel}')
    mat.blend_method = "BLEND"
    mat.use_nodes = True
    nodes = mat.node_tree.nodes
    links = mat.node_tree.links

    if nodes.get("Principled BSDF") is None:
        try: 
            nodes.remove(nodes.get("Principled Volume"))
        except Exception as e:
            print(e)
        princ = nodes.new("ShaderNodeBsdfPrincipled")
        links.new(princ.outputs[0], nodes.get('Material Output').inputs[0])
    
    idnode =  nodes.new("ShaderNodeVertexColor")
    idnode.layer_name = 'object id'
    idnode.location = (-800, 300)
    
    mod = nodes.new("ShaderNodeMath")
    mod.operation = "MODULO"
    mod.location =(-600, 300)
    links.new(idnode.outputs.get('Color'), mod.inputs[0])
    mod.inputs[1].default_value = 10
    
    map_range = nodes.new(type='ShaderNodeMapRange')
    map_range.location = (-450, 300)
    map_range.inputs[1].default_value = 0
    map_range.inputs[2].default_value = 11
    links.new(mod.outputs[0],map_range.inputs[0])
    
    tab10 = nodes.new(type="ShaderNodeValToRGB")
    tab10.location = (-300, 300)
    tab10.label = 'mpl-tab10'
    #    plt.get_cmap('tab10').colors
    cmap = ((0.12156862745098039, 0.4666666666666667, 0.7058823529411765), (1.0, 0.4980392156862745, 0.054901960784313725), (0.17254901960784313, 0.6274509803921569, 0.17254901960784313), (0.8392156862745098, 0.15294117647058825, 0.1568627450980392), (0.5803921568627451, 0.403921568627451, 0.7411764705882353), (0.5490196078431373, 0.33725490196078434, 0.29411764705882354), (0.8901960784313725, 0.4666666666666667, 0.7607843137254902), (0.4980392156862745, 0.4980392156862745, 0.4980392156862745), (0.7372549019607844, 0.7411764705882353, 0.13333333333333333), (0.09019607843137255, 0.7450980392156863, 0.8117647058823529))
    get_color_ramp(tab10, cmap, False)
    tab10.color_ramp.interpolation='CONSTANT'
    links.new(map_range.outputs[0], tab10.inputs.get('Fac'))
    links.new(tab10.outputs[0], nodes.get("Principled BSDF").inputs.get("Base Color"))
    
    
    # make optional linear colormap
    map_range_lin = nodes.new(type='ShaderNodeMapRange')
    map_range_lin.location = (-450, 0)
    map_range_lin.inputs[1].default_value = 0
    map_range_lin.inputs[2].default_value = maxval
    links.new(idnode.outputs.get('Color'),map_range_lin.inputs[0])
    
    vir = nodes.new(type="ShaderNodeValToRGB")
    vir.location = (-300, 0)
    vir.label = 'mpl-viridis'
    #    plt.get_cmap('viridis',32).colors
    cmap = [[0.267004, 0.004874, 0.329415, 1.      ],
       [0.277018, 0.050344, 0.375715, 1.      ],
       [0.282327, 0.094955, 0.417331, 1.      ],
       [0.282884, 0.13592 , 0.453427, 1.      ],
       [0.278012, 0.180367, 0.486697, 1.      ],
       [0.269308, 0.218818, 0.509577, 1.      ],
       [0.257322, 0.25613 , 0.526563, 1.      ],
       [0.243113, 0.292092, 0.538516, 1.      ],
       [0.225863, 0.330805, 0.547314, 1.      ],
       [0.210503, 0.363727, 0.552206, 1.      ],
       [0.19586 , 0.395433, 0.555276, 1.      ],
       [0.182256, 0.426184, 0.55712 , 1.      ],
       [0.168126, 0.459988, 0.558082, 1.      ],
       [0.15627 , 0.489624, 0.557936, 1.      ],
       [0.144759, 0.519093, 0.556572, 1.      ],
       [0.133743, 0.548535, 0.553541, 1.      ],
       [0.123463, 0.581687, 0.547445, 1.      ],
       [0.119423, 0.611141, 0.538982, 1.      ],
       [0.12478 , 0.640461, 0.527068, 1.      ],
       [0.143303, 0.669459, 0.511215, 1.      ],
       [0.180653, 0.701402, 0.488189, 1.      ],
       [0.226397, 0.728888, 0.462789, 1.      ],
       [0.281477, 0.755203, 0.432552, 1.      ],
       [0.344074, 0.780029, 0.397381, 1.      ],
       [0.421908, 0.805774, 0.35191 , 1.      ],
       [0.496615, 0.826376, 0.306377, 1.      ],
       [0.575563, 0.844566, 0.256415, 1.      ],
       [0.657642, 0.860219, 0.203082, 1.      ],
       [0.751884, 0.874951, 0.143228, 1.      ],
       [0.83527 , 0.886029, 0.102646, 1.      ],
       [0.916242, 0.896091, 0.100717, 1.      ],
       [0.993248, 0.906157, 0.143936, 1.      ]]
    get_color_ramp(vir, cmap, True)
    links.new(map_range_lin.outputs[0], vir.inputs.get('Fac'))
    
    return mat

def get_color_ramp(ramp_node, cmap, linear):
    for ix, color in enumerate(cmap):
        if len(ramp_node.color_ramp.elements) <= ix:
            ramp_node.color_ramp.elements.new(ix/(len(cmap)-linear))
        ramp_node.color_ramp.elements[ix].position = ix/(len(cmap)-linear)
        ramp_node.color_ramp.elements[ix].color = (color[0],color[1],color[2],1)
    return

def gn_oid_tree(oid, ch):
    node_group = bpy.data.node_groups.get(f"object id {oid}, {ch}")
    if node_group:
        return node_group
    node_group= bpy.data.node_groups.new(type = 'GeometryNodeTree', name =f"object id {oid}")
    links = node_group.links
    nodes = node_group.nodes
    interface = node_group.interface
    interface.new_socket("Geometry", in_out="INPUT",socket_type='NodeSocketGeometry')
    group_input = node_group.nodes.new("NodeGroupInput")
    group_input.location = (-400, 0)
    
    oidnode = nodes.new('FunctionNodeInputInt')
    oidnode.integer = oid
    oidnode.label = 'object id'
    oidnode.location = (-100, -200)
    
    chnode = nodes.new('FunctionNodeInputInt')
    chnode.integer = ch
    chnode.label = 'channel'
    chnode.location = (-100, -400)

    store =  node_group.nodes.new("GeometryNodeStoreNamedAttribute")
    store.data_type = 'FLOAT_COLOR'
    store.domain = 'CORNER'
    store.location =(150, 0)
    store.inputs.get("Name").default_value = "object id"
    links.new(group_input.outputs.get('Geometry'), store.inputs[0])
    links.new(oidnode.outputs[0], store.inputs.get("Value"))

    store2 =  node_group.nodes.new("GeometryNodeStoreNamedAttribute")
    store2.data_type = 'FLOAT_COLOR'
    store2.domain = 'CORNER'
    store2.location =(350, 0)
    store2.inputs.get("Name").default_value = "channel"
    links.new(store.outputs[0], store2.inputs[0])
    links.new(chnode.outputs[0], store2.inputs.get("Value"))

    interface.new_socket("Geometry", in_out="OUTPUT",socket_type='NodeSocketGeometry')
    group_output = node_group.nodes.new("NodeGroupOutput")
    group_output.location = (500, 0)
    links.new(store2.outputs[0], group_output.inputs[0])
    return node_group
    

def node_group_shared(maskchannel):
    node_group= bpy.data.node_groups.new(type = 'GeometryNodeTree', name = f"channel {maskchannel}")
    links = node_group.links
    nodes = node_group.nodes
    interface = node_group.interface
    interface.new_socket("Geometry", in_out="INPUT",socket_type='NodeSocketGeometry')
    group_input = node_group.nodes.new("NodeGroupInput")
    group_input.location = (-250, 0)

    interface.new_socket("Geometry", in_out="OUTPUT",socket_type='NodeSocketGeometry')
    group_output = node_group.nodes.new("NodeGroupOutput")
    group_output.location = (250, 0)
    links.new(group_input.outputs[0], group_output.inputs[0])
    return node_group


def dissolve(obj, obj_id):
    m = obj.data
    bm = bmesh.new()
    bm.from_mesh(m)
    bmesh.ops.dissolve_limit(bm, angle_limit=0.0872665, verts=bm.verts, edges=bm.edges)
    bm.to_mesh(m)
    bm.free()
    m.update()
    return

def abcfname(channel, timestep):
    return str(Path(bpy.context.scene.T2B_cache_dir) / f"mask_ch{channel}_t_{timestep:04}.abc")
def jsonfname(channel):
    return str(Path(bpy.context.scene.T2B_cache_dir) / f"mask_locs_ch{channel}.json")

def export_alembic_and_loc(mask, maskchannel, scale):
    from skimage.measure import marching_cubes
    from scipy.ndimage import find_objects
    axes_order = bpy.context.scene.axes_order.replace("c","")
    mask= np.moveaxis(mask, [axes_order.find('t'), axes_order.find('x'),axes_order.find('y'),axes_order.find('z')],[0,1,2,3])
    new_order = 'txyz'

    tmp_collection = collection_activate('tmp')
    objnames = {} # register objnames as dict at start value : name
    locations = {} 

    for timestep in range(0,mask.shape[0]):
        bpy.ops.object.select_all(action='DESELECT')
        if timestep == 0:
            print( np.unique(mask), 'hey')
            for obj_id_val in np.unique(mask)[1:]: #skip zero, register all objects with new names, need to be present in first frame
                objname=f"ch{maskchannel}_obj{obj_id_val}_" 
                bpy.ops.mesh.primitive_cube_add()
                obj=bpy.context.view_layer.objects.active
                obj.name = objname
                obj.data.name = objname
                obj.scale = scale
                objnames[obj_id_val] = obj.name
                locations[obj.name]={}
                locations[obj.name][0] = {'x':-1,'y':-1,'z':-1}

        for obj_id, objslice in enumerate(find_objects(mask[timestep])):
            if objslice is None:
                continue
            obj_id_val = obj_id + 1
            objarray = np.pad(mask[timestep][objslice], 1, constant_values=0)
            verts, faces, normals, values = marching_cubes(objarray==obj_id+1, step_size=1)
#            obj = get_obj_by_id(fname, obj_id_val)
            
            obj = bpy.data.objects.get(objnames[obj_id_val])
            # print(objnames[obj_id_val], obj)
            mesh = obj.data
            mesh.clear_geometry()
            mesh.from_pydata(verts,[], faces)
            bpy.ops.object.mode_set(mode = 'OBJECT')

            loc = np.array([objslice[0].start, objslice[1].start, objslice[2].start]) *scale
            obj.location = loc
            # locations[obj.name]({"timestep": timestep,"location":loc})
            locations[obj.name][timestep] = {'x':loc[0],'y':loc[1],'z':loc[2]}

            dissolve(obj, obj_id)
        

        for obj in tmp_collection.all_objects: 
            # if obj.name in objnames.values():
            obj.select_set(True)
        

        fname = abcfname(maskchannel, timestep)
        if Path(fname).exists() and bpy.context.scene.TL_remake:
            Path(fname).unlink() # this may fix an issue with subsequent loads
        bpy.ops.wm.alembic_export(filepath=fname,
                        visible_objects_only=False,
                        selected=True,
                        vcolors = True,
                        flatten=True,
                        orcos=True,
                        export_custom_properties=True,
                        start = 0,
                        end = 1,
                        evaluation_mode = "RENDER",
                        )
        for obj in tmp_collection.all_objects: 
            # if obj.name in objnames.values():
            obj.data.clear_geometry()

    for objname in objnames.values():
        obj.select_set(True)
    bpy.ops.object.delete(use_global=False)
    bpy.data.collections.remove(tmp_collection)
    with open(jsonfname(maskchannel), 'w') as fp:
        json.dump(locations, fp, indent=4)
    return 

def import_abc_and_loc(maskchannel, maxval):
    mask_objs = []
    parentcoll, parentlcoll = get_current_collection()
    channel_collection, _ = make_subcollection(f"channel {maskchannel} labelmask")
    bpy.ops.wm.alembic_import(filepath=abcfname(maskchannel, 0), is_sequence=True)

    gn_labelmask = node_group_shared(maskchannel)
    shader_labelmask = labelmask_shader(maskchannel,maxval + 1)

    with open(jsonfname(maskchannel), 'r') as fp:
        locations = json.load(fp)

    locnames_newnames = {}
    for obj in channel_collection.all_objects: # for blender renaming
        oid = int(obj.name.split('_')[1].strip('obj'))
        ch = int(obj.name.split('_')[0].strip('ch'))
        locnames_newnames[(oid, ch)] = obj

    for objname in locations:
        print(locnames_newnames.keys(), objname, locations.keys())
        oid = int(objname.split('_')[1].strip('obj'))
        ch = int(objname.split('_')[0].strip('ch'))
        obj = locnames_newnames[(oid, ch)]   
        print(objname, obj.name)
        mask_objs.append(obj)
        for time, loc in locations[objname].items():
            obj.location = (loc['x'], loc['y'], loc['z'])
            obj.keyframe_insert(data_path="location", frame=int(time))
        obj.modifiers.new(type='NODES', name=f'object id + channel {oid}')
        obj.modifiers[-1].node_group = gn_oid_tree(oid, ch)
        
        obj.modifiers.new(type='NODES', name='shared modifier')
        obj.modifiers[-1].node_group = gn_labelmask
        obj.data.materials.append(shader_labelmask)

    collection_activate(parentcoll, parentlcoll)
    return mask_objs, channel_collection, shader_labelmask

def load_labelmask(mask_arrays, scale):
    mask_objs = []
    mask_colls, mask_shaders = [], []
    locations = {}
    
    for maskchannel, mask in mask_arrays.items():
        if not Path(abcfname(maskchannel,0)).exists() or bpy.context.scene.TL_remake:
            export_alembic_and_loc(mask, maskchannel, scale)
        
        
        objs, coll, shader = import_abc_and_loc(maskchannel, np.max(mask))
        
        
        mask_objs.extend(objs)
        mask_colls.append(coll)
        mask_shaders.append(shader)

        
    return mask_objs, mask_colls, mask_shaders



