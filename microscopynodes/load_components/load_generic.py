import bpy
from ..handle_blender_structs import *
import numpy as np
from .. import min_nodes
from databpy.nodes import append_from_blend

def ChannelObjectFactory(min_key, obj, scale):
    if min_key == min_keys.VOLUME:
        from .load_volume import VolumeObject
        return VolumeObject(obj, scale)
    elif min_key == min_keys.SURFACE:
        from .load_surfaces import SurfaceObject
        return SurfaceObject(obj, scale)
    elif min_key == min_keys.LABELMASK:
        from .load_labelmask import LabelmaskObject
        return LabelmaskObject(obj, scale)

def DataIOFactory(min_key):
    if min_key == min_keys.VOLUME or min_key == min_keys.SURFACE:
        from .load_volume import VolumeIO
        return VolumeIO()
    elif min_key == min_keys.LABELMASK:
        from .load_labelmask import LabelmaskIO
        return LabelmaskIO()

class DataIO():
    min_type = min_keys.NONE

    def generate_file_constructors(self, ch, cache_dir):
        return []

    def export_ch(self, ch, file_constructors, remake):
        # return paths to local files with metadata in list of dcts
        return []

    def get_metadata(self, file_constructors):
        return {}

class ChannelObject():
    min_type = min_keys.NONE
    obj = None
    gn_mod = None
    node_group = None
    import_node_name = ""

    def __init__(self, obj, scale):
        if obj is None:
            obj = self.init_obj(scale)
        self.obj = obj
        self.gn_mod = get_min_gn(obj)
        self.node_group =self.gn_mod.node_group


    def init_obj(self, scale):
        if self.min_type == min_keys.VOLUME: # makes the icon show up
            bpy.ops.object.volume_add(align='WORLD', location=(0, 0, 0), scale=(1, 1, 1))
        else:
            bpy.ops.mesh.primitive_cube_add()
        obj = bpy.context.view_layer.objects.active
        name = self.min_type.name.lower()
        obj.name = name
        obj.scale = scale

        bpy.ops.object.modifier_add(type='NODES')

        node_group = bpy.data.node_groups.new(name, 'GeometryNodeTree')  
        obj.modifiers[-1].node_group = node_group
        obj.modifiers[-1].name = f"[Microscopy Nodes {name}]"
        node_group.interface.new_socket(name="Frame", in_out="INPUT",socket_type='NodeSocketInt')
        node_group.interface.new_socket(name='Geometry', in_out="OUTPUT",socket_type='NodeSocketGeometry')
        node_group.interface.items_tree[-1].default_attribute_name = "[frame]"

        inputnode = node_group.nodes.new('NodeGroupInput')
        inputnode.location = (-900, 0)
        outnode = node_group.nodes.new('NodeGroupOutput')
        outnode.location = (800, -100)

        for dim in range(3):
            obj.lock_location[dim] = True
            obj.lock_rotation[dim] = True
            obj.lock_scale[dim] = True
        return obj

    def add_material(self, ch):
        mat = bpy.data.materials.new(f"{ch['name']} {self.min_type.name.lower()}")
        self.obj.data.materials.append(mat)
        return mat

    def update_ch_data(self, ch, file_constructors):
        if not self.ch_present(ch): 
            self.append_channel_to_holder(ch)
        importnode = self.node_group.nodes[f"channel_load_{ch['identifier']}"]
        self.update_import_node(importnode, file_constructors, ch)  
        return

    def update_ch_settings(self, ch):
        if not self.ch_present(ch): 
            return

        for ix, socket in enumerate(self.node_group.interface.items_tree):
            if isinstance(socket, bpy.types.NodeTreeInterfaceSocket) and ch['identifier'] in socket.default_attribute_name:
                set_name_socket(socket, ch['name'])
        
        self.update_gn(ch)
        for mat in self.obj.data.materials:
            if any([ch['identifier'] in node.name for node in mat.node_tree.nodes]):
                self.update_material(mat, ch)

        socket = get_socket(self.node_group, ch, min_type="SWITCH")
        if socket is not None:
            self.gn_mod[socket.identifier] = bool(ch[self.min_type])
        
        
        # frame_socket, socket_ix = get_socket_by_name('[frame]', return_ix=True)
        # keyframes = get_keyframes(self.gn_mod, '["Socket_0"]')
        # if len(keyframes) == 2:
        #     if keyframe

        setattr(self.gn_mod, '["Socket_0"]', 0)
        self.gn_mod.keyframe_insert(data_path='["Socket_0"]', frame=0)
        setattr(self.gn_mod, '["Socket_0"]', bpy.context.scene.MiN_load_end_frame-bpy.context.scene.MiN_load_start_frame)
        self.gn_mod.keyframe_insert(data_path='["Socket_0"]', frame=bpy.context.scene.MiN_load_end_frame-bpy.context.scene.MiN_load_start_frame)
        return
    

    def import_node(self, ch):
        import_node = self.node_group.nodes.new("GeometryNodeGroup")  # type: ignore
        node_group = bpy.data.node_groups.get(self.import_node_name)
        if node_group:
            import_node.node_tree = node_group
        else: 
            import_node.node_tree = append_from_blend(self.import_node_name, filepath='/Users/oanegros/Documents/werk/tif2bpy/microscopynodes/min_nodes/min_nodes.blend/NodeTree',link=False)
        import_node.location = (-600, 0)

        for input_field in import_node.inputs: 
            if input_field.name not in ['Include', 'Normalized', 'Frame']:
                input_field.hide = True
        return import_node


    def update_import_node(self, import_node, file_constructors, ch):
        if import_node.inputs.get('original_path') == "":
            import_node.inputs.get('original_path').default_value = ch['dataset_path']
            self.node_group.links.new(self.node_group.nodes['Group Input'].outputs['Frame'], import_node.inputs['Frame'])
        for key,val in file_constructors[0].items():
            if key == 't':
                key = 'Frame'
            if import_node.inputs.get(key) is None:
                continue
            try:
                import_node.inputs.get(key).default_value = int(val)
            except Exception:
                import_node.inputs.get(key).default_value = str(val)
        import_node.label = ch['name']
        return

    def ch_present(self, ch):
        return f"channel_load_{ch['identifier']}" in [node.name for node in self.node_group.nodes]

    def update_material(self, mat, ch):
        return
    
    def update_gn(self, ch):
        return

    def append_channel_to_holder(self, ch):
        # assert that layout is reasonable or make this:
        joingeo, out_node, out_input = get_safe_nodes_last_output(self.node_group, make=True)
        in_node = get_safe_node_input(self.node_group, make=True)
        if joingeo is not None and joingeo.type == "REALIZE_INSTANCES":
            joingeo = joingeo.inputs[0].links[0].from_node
        if joingeo is None or joingeo.type != "JOIN_GEOMETRY":
            joingeo = self.node_group.nodes.new('GeometryNodeJoinGeometry')
            insert_last_node(self.node_group, joingeo, safe=True)
            if self.min_type != min_keys.VOLUME:
                realize = self.node_group.nodes.new('GeometryNodeRealizeInstances')
                insert_last_node(self.node_group, realize, safe=True)

        socket = new_socket(self.node_group, ch, 'NodeSocketBool', min_type="SWITCH")

        if out_node.location[0] - 1200 < in_node.location[0]: # make sure there is enough space
            out_node.location[0] = in_node.location[0]+1200

        # make new channel
        min_y_loc = in_node.location[1] + 300
        for node in self.node_group.nodes:
            if node.name not in [in_node.name, out_node.name, joingeo.name]:
                min_y_loc = min(min_y_loc, node.location[1])
        
        x = in_node.location[0] + 400
        y = min_y_loc - 300
        importnode = self.import_node(ch)
        importnode.location = (x , y+100)
        importnode.name = f"channel_load_{ch['identifier']}"
        
        

        self.channel_nodes(x, y, ch, importnode.outputs[0], joingeo.inputs[-1])

        self.node_group.links.new(in_node.outputs.get('Frame'), importnode.inputs.get("Frame"))
        # add switch socket
        
        node_socket = in_node.outputs.get(socket.name)
        self.node_group.links.new(in_node.outputs.get(socket.name), importnode.inputs.get("Include"))
        return

    def channel_nodes(self, x, y, ch, in_ch, out_ch):
        x += 800
        setmat = self.node_group.nodes.new('GeometryNodeSetMaterial')
        setmat.name = f"set_material_{ch['identifier']}"
        setmat.inputs.get('Material').default_value = self.add_material(ch)
        setmat.location = (x, y)
        
        self.node_group.links.new(in_ch, setmat.inputs.get('Geometry'))
        self.node_group.links.new(setmat.outputs[0], out_ch)
        return setmat.inputs[0] , setmat.outputs[0]


    def set_parent_and_slicer(self, parent, slice_cube, ch):
        self.obj.parent = parent
        for mat in self.obj.data.materials:
            if mat.node_tree.nodes.get("Slice Cube") is None:
                node_handling.insert_slicing(mat.node_tree, slice_cube)
        if self.min_type in ch['collections']:
            for obj in ch['collections'][self.min_type].all_objects:
                obj.parent = parent
            