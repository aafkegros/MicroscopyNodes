import bpy, bpy_types
from ..handle_blender_structs import *
import numpy as np


def ChannelObjectFactory(min_key, obj):
    if min_key == min_keys.VOLUME:
        from .load_volume import VolumeObject
        return VolumeObject(obj)
    elif min_key == min_keys.SURFACE:
        from .load_surfaces import SurfaceObject
        return SurfaceObject(obj)
    elif min_key == min_keys.LABELMASK:
        from .load_labelmask import LabelmaskObject
        return LabelmaskObject(obj)

def DataIOFactory(min_key):
    if min_key == min_keys.VOLUME:
        from .load_volume import VolumeIO
        return VolumeIO()
    elif min_key == min_keys.SURFACE:
        from .load_surfaces import SurfaceIO
        return SurfaceIO()
    elif min_key == min_keys.LABELMASK:
        from .load_labelmask import LabelmaskIO
        return LabelmaskIO()

class DataIO():
    min_type = min_keys.NONE

    def export_ch(self, ch, axes_order, remake, cache_dir):
        # return paths to local files with metadata in list of dcts
        return []
    
    def import_data(self, ch, scale):
        # return collection, metadata
        return None, None


class ChannelObject():
    min_type = min_keys.NONE
    obj = None
    gn_mod = None
    node_group = None

    def __init__(self, obj):
        if obj is None:
            obj = self.init_obj()
        self.obj = obj
        self.gn_mod = get_min_gn(obj)
        self.node_group =self.gn_mod.node_group


    def init_obj(self):
        if self.min_type == min_keys.VOLUME: # makes the icon show up
            bpy.ops.object.volume_add(align='WORLD', location=(0, 0, 0), scale=(1, 1, 1))
        else:
            bpy.ops.mesh.primitive_cube_add()
        obj = bpy.context.view_layer.objects.active
        name = self.min_type.name.lower()
        obj.name = name

        bpy.ops.object.modifier_add(type='NODES')

        node_group = bpy.data.node_groups.new(name, 'GeometryNodeTree')  
        obj.modifiers[-1].node_group = node_group
        obj.modifiers[-1].name = f"[Microscopy Nodes {name}]"
        node_group.interface.new_socket(name='Geometry', in_out="OUTPUT",socket_type='NodeSocketGeometry')

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

    def update_ch_data(self, ch):
        if self.min_type in ch['collections'] and not self.ch_present(ch): 
            self.append_channel_to_holder(ch)
            
        loadnode = self.node_group.nodes[f"channel_load_{ch['identifier']}"]
        loadnode.label = ch['name']
        if loadnode.parent is not None:
            loadnode.parent.label = f"{ch['name']} data"
        clear_collection(loadnode.inputs[0].default_value)
        loadnode.inputs[0].default_value = ch['collections'][self.min_type]
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
        
        if out_node.location[0] - 1200 < in_node.location[0]: # make sure there is enough space
            out_node.location[0] = in_node.location[0]+1200

        # add switch socket
        socket = new_socket(self.node_group, ch, 'NodeSocketBool', min_type="SWITCH")
        node_socket = in_node.outputs.get(socket.name)

        # make new channel
        min_y_loc = in_node.location[1] + 300
        for node in self.node_group.nodes:
            if node.name not in [in_node.name, out_node.name, joingeo.name]:
                min_y_loc = min(min_y_loc, node.location[1])
        in_ch, out_ch = self.channel_nodes(in_node.location[0] + 400, min_y_loc - 300, ch)

        self.node_group.links.new(node_socket, in_ch)
        self.node_group.links.new(out_ch, joingeo.inputs[-1])
        return

    def channel_nodes(self, x, y, ch):
        nodes = self.node_group.nodes
        links = self.node_group.links
        interface = self.node_group.interface
        
        loadnode = nodes.new('GeometryNodeCollectionInfo')
        loadnode.location = (x , y + 100)
        loadnode.hide = True
        loadnode.label = ch['name']
        loadnode.transform_space='RELATIVE'

        # reload-func:
        loadnode.name = f"channel_load_{ch['identifier']}"
        
        switch = nodes.new('GeometryNodeSwitch')      
        switch.location = (x, y + 50)  
        switch.input_type = 'GEOMETRY'
        links.new(loadnode.outputs.get('Instances'), switch.inputs.get("True"))
        switch.hide = True
        switch.label = "Include channel"
        
        dataframe = nodes.new('NodeFrame')
        loadnode.parent = dataframe
        switch.parent = dataframe
        dataframe.label = f"{ch['name']} data"
        dataframe.name = f"dataframe_{ch['identifier']}"

        reroutes = [switch] 
        for x_, y_ in [(220, 40), (0, -150), (850,0), (0, 150)]:
            x += x_
            y += y_
            reroutes.append(nodes.new('NodeReroute'))
            reroutes[-1].location= (x, y)
            links.new(reroutes[-2].outputs[0], reroutes[-1].inputs[0])
        
        x += 50
        
        editframe = nodes.new('NodeFrame')
        reroutes[2].parent = editframe
        reroutes[2].name = f"edit_in_{ch['identifier']}"
        reroutes[3].parent = editframe
        reroutes[3].name = f"edit_out_{ch['identifier']}"
        editframe.label = f"edit geometry"
        editframe.name = f"editframe_{ch['identifier']}"
        
        setmat = nodes.new('GeometryNodeSetMaterial')
        setmat.name = f"set_material_{ch['identifier']}"
        setmat.inputs.get('Material').default_value = self.add_material(ch)
        links.new(reroutes[-1].outputs[0], setmat.inputs.get('Geometry'))
        setmat.location = (x, y)
        setmat.hide= True
        return switch.inputs.get("Switch"), setmat.outputs[0]


    def set_parent_and_slicer(self, parent, slice_cube, ch):
        self.obj.parent = parent
        for mat in self.obj.data.materials:
            if mat.node_tree.nodes.get("Slice Cube") is None:
                node_handling.insert_slicing(mat.node_tree, slice_cube)
        if self.min_type in ch['collections']:
            for obj in ch['collections'][self.min_type].all_objects:
                obj.parent = parent