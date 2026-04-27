import bpy
from ..handle_blender_structs import *
from ..min_nodes.shader_nodes import add_shaders_node, channel_index_node, slice_cube_node_group
from databpy import BlenderObject
import numpy as np
from ..min_nodes.geo_nodes.affine_matrix import affine_socket_names


class MiNObject(BlenderObject):
    min_type = None # needs to be of type min_keys

    def __init__(self, obj=None):
        super().__init__(obj) 
        if obj is None:
            obj = self.init_obj()
    
    def init_obj(self):
        bpy.ops.mesh.primitive_cube_add()
        self.object = bpy.context.view_layer.objects.active
        self.object.name = self.min_type.name.lower()

    def set_data(self, dataset_model):
        return

    def set_settings(self, dataset_model):
        return
    
    @property
    def min_gn(self):
        for mod in self.object.modifiers:
            if 'Microscopy Nodes' in mod.name:
                return mod

    @property 
    def node_group(self):
        if self.min_gn is not None:
            return self.min_gn.node_group

    @property
    def gn_mod(self):
        return self.min_gn


class ChannelObject(MiNObject):
    shader_count = 10

    def expand_node_ui(self, node):
        if hasattr(node, "show_options"):
            node.show_options = True
        for socket in getattr(node, "inputs", []):
            if hasattr(socket, "show_expanded"):
                socket.show_expanded = True
        return node

    def init_obj(self):
        if self.min_type == min_keys.VOLUME: # makes the icon show up
            bpy.ops.object.volume_add(align='WORLD', location=(0, 0, 0), scale=(1, 1, 1))
        else:
            bpy.ops.mesh.primitive_cube_add()
        obj = bpy.context.view_layer.objects.active
        name = self.min_type.name.lower()
        obj.name = name
        self.object = obj
        node_group = bpy.data.node_groups.new(name, 'GeometryNodeTree')
        bpy.ops.object.modifier_add(type='NODES')
        obj.modifiers[-1].node_group = node_group
        obj.modifiers[-1].name = f"[Microscopy Nodes {name}]"
        node_group.interface.new_socket(name="Frame", in_out="INPUT",socket_type='NodeSocketInt')
        node_group.interface.new_socket(name='Geometry', in_out="OUTPUT",socket_type='NodeSocketGeometry')
        node_group.interface.items_tree[-1].default_attribute_name = "[frame]"
        self.init_gn()
        for dim in range(3):
            obj.lock_location[dim] = True
            obj.lock_rotation[dim] = True
            obj.lock_scale[dim] = True
        return obj

    def add_material(self, ch):
        material_name = self.material_name()
        if len(self.object.data.materials) > 0 and self.object.data.materials[0] is not None:
            mat = self.object.data.materials[0]
            if mat.name != material_name:
                mat.name = material_name
        else:
            mat = bpy.data.materials.new(material_name)
            if len(self.object.data.materials) == 0:
                self.object.data.materials.append(mat)
            else:
                self.object.data.materials[0] = mat
            self.init_shader(mat)
        set_material = self.node_group.nodes.get("Set Material")
        if set_material is not None and set_material.inputs.get("Material").default_value is None:
            set_material.inputs.get("Material").default_value = mat
        return mat


    def set_data(self, dataset_model):
        self.dataset_name = dataset_model.name
        for ch in dataset_model.channels:
            if not ch.visible_as.get(self.min_type, False):
                continue
            self.update_ch_data(ch)

    def update_ch_data(self, ch):
        file_constructors = ch.file_constructors.get(self.min_type, [])
        if not file_constructors:
            return
        if not self.ch_present(ch):
            self.add_ch_to_gn(ch)
            self.init_channel_shader(self.add_material(ch), ch)
        importnode = self.node_group.nodes[f"channel_load_{ch.identifier}"]
        self.update_import_node(importnode, file_constructors, ch)  
        return

    def set_settings(self, dataset_model):
        self.dataset_name = dataset_model.name
        for ch in dataset_model.channels:
            self.update_ch_settings(ch)
        ch = next((ch for ch in dataset_model.channels if ch.visible_as.get(self.min_type, False)), None)
        if ch is not None:
            self.object.location = dataset_model.channel_object_location
            self.object.rotation_euler = (0.0, 0.0, 0.0)
            self.object.scale = (1.0, 1.0, 1.0)


    def update_ch_settings(self, ch):
        if not self.ch_present(ch): 
            return

        for ix, socket in enumerate(self.node_group.interface.items_tree):
            if isinstance(socket, bpy.types.NodeTreeInterfaceSocket) and ch.identifier in socket.default_attribute_name:
                set_name_socket(socket, ch.name)
        
        self.update_gn(ch)
        mat = self.add_material(ch)
        self.update_material(mat, ch)

        socket = get_socket(self.node_group, ch, min_type="SWITCH")
        if socket is not None:
            self.gn_mod[socket.identifier] = bool(ch.visible_as.get(self.min_type, False))
        return
    

    def update_import_node(self, import_node, file_constructors, ch):
        for key,val in file_constructors[0].items():
            if key == 't':
                key = 'Frame'
            if import_node.inputs.get(key) is None:
                continue
            try:
                import_node.inputs.get(key).default_value = int(val)
            except Exception:
                import_node.inputs.get(key).default_value = str(val)
        import_node.label = ch.name
        self.update_import_affine(import_node, ch)
        return

    def update_import_affine(self, import_node, ch):
        affine = np.array(ch.affine, dtype=float)
        for socket_name, value in zip(affine_socket_names(), affine.reshape(-1)):
            socket = import_node.inputs.get(socket_name)
            if socket is not None:
                socket.default_value = float(value)
        return

    def ch_present(self, ch):
        return f"channel_load_{ch.identifier}" in [node.name for node in self.node_group.nodes]

    def update_material(self, mat, ch):
        return
    
    def update_gn(self, ch):
        return

    def init_shader(self, mat):
        mat.use_nodes = True
        nodes = mat.node_tree.nodes
        links = mat.node_tree.links
        nodes.clear()

        output = nodes.new("ShaderNodeOutputMaterial")
        output.name = "Material Output"
        output.location = (1500, 0)
        output.is_active_output = True

        texcoord = nodes.new("ShaderNodeTexCoord")
        texcoord.name = "Texture Coordinate"
        texcoord.width = 200
        texcoord.location = (770, 140)

        add_shaders = nodes.new("ShaderNodeGroup")
        add_shaders.node_tree = add_shaders_node(self.shader_count)
        add_shaders.name = "Add Shaders"
        add_shaders.width = 100
        add_shaders.location = (620, 0)
        self.expand_node_ui(add_shaders)

        slicecube = nodes.new("ShaderNodeGroup")
        slicecube.node_tree = slice_cube_node_group()
        slicecube.name = "Slice Cube"
        slicecube.width = 250
        slicecube.location = (1070, 0)
        self.expand_node_ui(slicecube)

        links.new(texcoord.outputs.get("Object"), slicecube.inputs.get("Slicing Object"))
        links.new(add_shaders.outputs[0], slicecube.inputs.get("Shader"))
        links.new(slicecube.outputs.get("Shader"), output.inputs[self.shader_output_name()])
        return

    def shader_output_name(self):
        raise NotImplementedError(f"{type(self).__name__} must implement shader_output_name()")

    def shader_y_step(self):
        raise NotImplementedError(f"{type(self).__name__} must implement shader_y_step()")

    def material_name(self):
        dataset_name = getattr(self, "dataset_name", None)
        if not dataset_name and self.object.parent is not None:
            dataset_name = self.object.parent.name
        if not dataset_name:
            dataset_name = self.object.name
        return f"{dataset_name} {self.min_type.name.lower()}"

    def init_channel_shader(self, mat, ch):
        raise NotImplementedError(f"{type(self).__name__} must implement init_channel_shader()")

    def import_node_tree(self):
        raise NotImplementedError(f"{type(self).__name__} must implement import_node_tree()")

    def create_join_node(self):
        raise NotImplementedError(f"{type(self).__name__} must implement create_join_node()")

    def attach_channel_output(self, join_node, ch, out_ch):
        raise NotImplementedError(f"{type(self).__name__} must implement attach_channel_output()")

    def import_output_socket(self, import_node):
        return import_node.outputs[0]

    def init_gn(self):
        node_group = self.node_group
        nodes = node_group.nodes
        links = node_group.links

        nodes.clear()

        inputnode = nodes.new('NodeGroupInput')
        inputnode.location = (-900, 0)

        outputnode = nodes.new('NodeGroupOutput')
        outputnode.location = (1400, -100)

        join_node = self.create_join_node()
        links.new(join_node.outputs[0], outputnode.inputs['Geometry'])
        return

    def add_ch_to_gn(self, ch):
        in_node = self.node_group.nodes.get('Group Input')
        join_node = self.node_group.nodes.get("Join")

        socket = new_socket(self.node_group, ch, 'NodeSocketBool', min_type="SWITCH")

        min_y_loc = in_node.location[1] + 300
        skip_names = {in_node.name, "Group Output", join_node.name, "Set Material"}
        for node in self.node_group.nodes:
            if node.name not in skip_names:
                min_y_loc = min(min_y_loc, node.location[1])

        x = in_node.location[0] + 400
        y = min_y_loc - 300

        import_node = self.import_node(ch)
        import_node.location = (x, y + 100)
        import_node.name = f"channel_load_{ch.identifier}"
        import_node.label = ch.name

        self.node_group.links.new(in_node.outputs.get(socket.name), import_node.inputs.get("Include"))
        out_ch = self.channel_nodes(x, y, ch, self.import_output_socket(import_node))
        self.attach_channel_output(join_node, ch, out_ch)
        return

    def channel_nodes(self, x, y, ch, in_ch):
        return in_ch

    def add_ch_to_shader(self, mat, ch, shader_socket):
        nodes = mat.node_tree.nodes
        links = mat.node_tree.links
        y_offset = -self.shader_y_step() * ch.ix
        add_shaders = nodes["Add Shaders"]

        frame = nodes.new("NodeFrame")
        frame.name = f"[frame_{ch.identifier}]"
        frame.label = ch.name
        frame.use_custom_color = True
        frame.color = (0.0, 0.0, 0.0)
        frame.label_size = 50
        frame.shrink = True

        links.new(shader_socket, add_shaders.inputs[min(ch.ix, self.shader_count - 1)])
        return frame, add_shaders

    def import_node(self, ch):
        import_node = self.node_group.nodes.new("GeometryNodeGroup")
        import_node.node_tree = self.import_node_tree()
        import_node.location = (-600, 0)
        for input_field in import_node.inputs:
            if input_field.name not in ['Include', 'Normalized', 'Frame']:
                input_field.hide = True
        self.node_group.links.new(self.node_group.nodes['Group Input'].outputs['Frame'], import_node.inputs['Frame'])
        return import_node

    def set_parent_and_slicer(self, parent, slice_cube, ch):
        self.object.parent = parent
        self.object.matrix_parent_inverse.identity()
        for mat in self.object.data.materials:
            texcoord = mat.node_tree.nodes.get("Texture Coordinate")
            if texcoord is not None:
                texcoord.object = slice_cube
        for obj in ch.metadata.get("collections", {}).get(self.min_type, []):
            obj.parent = parent
            obj.matrix_parent_inverse.identity()


class MeshChannelObject(ChannelObject):
    def shader_output_name(self):
        return "Surface"

    def shader_y_step(self):
        return 500

    def create_join_node(self):
        join_node = self.node_group.nodes.new('GeometryNodeJoinGeometry')
        join_node.name = "Join"
        join_node.location = (800, -100)
        return join_node

    def attach_channel_output(self, join_node, ch, out_ch):
        self.node_group.links.new(out_ch, join_node.inputs["Geometry"])
        return

    def store_channel_attribute(self, x, y, ch, geometry_socket):
        store_channel = self.node_group.nodes.new("GeometryNodeStoreNamedAttribute")
        store_channel.name = f"STORE_CHANNEL_{ch.identifier}"
        store_channel.location = (x, y)
        store_channel.data_type = 'INT'
        store_channel.domain = 'FACE'
        store_channel.inputs["Selection"].default_value = True
        store_channel.inputs["Name"].default_value = "channel ix"
        store_channel.inputs["Value"].default_value = ch.ix
        self.node_group.links.new(geometry_socket, store_channel.inputs["Geometry"])
        return store_channel.outputs["Geometry"]

    def init_gn(self):
        super().init_gn()
        outputnode = self.node_group.nodes.get('Group Output')
        join_node = self.node_group.nodes.get("Join")

        set_material = self.node_group.nodes.new('GeometryNodeSetMaterial')
        set_material.name = "Set Material"
        set_material.location = (1100, -100)

        self.node_group.links.new(join_node.outputs[0], set_material.inputs['Geometry'])
        self.node_group.links.new(set_material.outputs[0], outputnode.inputs['Geometry'])
        return

    def channel_nodes(self, x, y, ch, in_ch):
        return self.store_channel_attribute(x + 400, y, ch, in_ch)

    def init_shader(self, mat):
        super().init_shader(mat)
        nodes = mat.node_tree.nodes
        nodes["Add Shaders"].location = (980, 0)
        nodes["Texture Coordinate"].location = (1270, 140)
        nodes["Slice Cube"].location = (1570, 0)
        nodes["Material Output"].location = (2050, 0)
        return

    def init_channel_shader(self, mat, ch):
        nodes = mat.node_tree.nodes
        links = mat.node_tree.links
        y_offset = -self.shader_y_step() * ch.ix

        color_lut = nodes.new("ShaderNodeValToRGB")
        color_lut.name = f"[color_lut_{ch.identifier}]"
        color_lut.location = (-20, y_offset - 35)
        color_lut.width = 300
        color_lut.outputs[1].hide = True

        princ = nodes.new("ShaderNodeBsdfPrincipled")
        princ.name = f"[{ch.identifier}] principled"
        princ.location = (390, y_offset - 35)
        princ.inputs.get('Alpha').default_value = 0.8

        channel_index = nodes.new("ShaderNodeGroup")
        channel_index.name = f"[channel_index_{ch.identifier}]"
        channel_index.node_tree = channel_index_node()
        channel_index.label = "Channel index"
        channel_index.location = (710, y_offset - 65)
        channel_index.inputs["Index"].default_value = ch.ix
        self.expand_node_ui(channel_index)

        frame, _ = self.add_ch_to_shader(mat, ch, channel_index.outputs["Shader"])

        color_lut.parent = frame
        princ.parent = frame
        channel_index.parent = frame

        links.new(color_lut.outputs[0], princ.inputs.get('Base Color'))
        links.new(color_lut.outputs[0], princ.inputs[27])
        links.new(princ.outputs[0], channel_index.inputs["Shader"])
        color_lut.inputs[0].default_value = 1.0
        return
