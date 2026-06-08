import bpy
from ..handle_blender_structs.node_handling import expand_node_ui, get_socket, set_modifier_input_socket, set_name_socket
from ..handle_blender_structs.min_keys import min_keys
from ..min_nodes.geo_nodes.combine_channels import join_microscopy_grids_and_meshes_node_group
from ..min_nodes.geo_nodes.nodeMaskGrid import mask_grid_node_group
from ..min_nodes.shader_nodes import add_shaders_node, channel_index_node
from ..ui.preferences import addon_preferences
from databpy import BlenderObject
import numpy as np


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

    def set_holder(self, holder):
        for node in self.node_group.nodes:
            if node.name.startswith("IMPORT_") and node.inputs.get("Holder") is not None:
                node.inputs["Holder"].default_value = holder

    def set_channel_capacity(self, dataset_model):
        pref_buffer = int(getattr(addon_preferences(bpy.context), "extra_channel_slots", 2))
        self.shader_count = max(len(dataset_model.channels) + pref_buffer, 1)
        self.ensure_channel_capacity()

    def ensure_channel_capacity(self):
        if self.object is None or not hasattr(self.object.data, "materials"):
            return
        for mat in self.object.data.materials:
            if mat is None or not mat.use_nodes or mat.node_tree is None:
                continue
            add_shaders = mat.node_tree.nodes.get("Add Shaders")
            if add_shaders is not None:
                add_shaders.node_tree = add_shaders_node(self.shader_count)

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
        self.set_channel_capacity(dataset_model)
        for ch in dataset_model.channels:
            if not getattr(ch.viz, self.min_type.name.lower(), False):
                continue
            self.update_ch_data(ch)

    def update_ch_data(self, ch):
        file_constructors = ch.file_constructors.get(self.min_type, [])
        if not file_constructors:
            return
        if not self.ch_present(ch):
            self.add_ch_to_gn(ch)
            self.init_channel_shader(self.add_material(ch), ch)
        importnode = self.node_group.nodes[f"IMPORT_{ch.identifier}"]
        self.update_import_node(importnode, file_constructors, ch)  
        return

    def set_settings(self, dataset_model):
        self.dataset_name = dataset_model.name
        self.set_channel_capacity(dataset_model)
        for ch in dataset_model.channels:
            self.update_ch_settings(ch)
        ch = next((ch for ch in dataset_model.channels if getattr(ch.viz, self.min_type.name.lower(), False)), None)
        if ch is not None:
            # self.object.location = dataset_model.dataset_origin_world
            self.object.rotation_euler = (0.0, 0.0, 0.0)
            self.object.scale = (1.0, 1.0, 1.0)


    def update_ch_settings(self, ch):
        if not self.ch_present(ch): 
            return

        self.update_channel_bundle_name(ch)
        for ix, socket in enumerate(self.node_group.interface.items_tree):
            if isinstance(socket, bpy.types.NodeTreeInterfaceSocket) and ch.identifier in socket.default_attribute_name:
                set_name_socket(socket, ch.name)
        
        self.update_gn(ch)
        mat = self.add_material(ch)
        self.update_material(mat, ch)

        socket = get_socket(self.node_group, ch, min_type="SWITCH")
        if socket is not None:
            set_modifier_input_socket(
                self.gn_mod,
                socket,
                getattr(ch.viz, self.min_type.name.lower(), False)
            )
        return
    

    def update_import_node(self, import_node, file_constructors, ch):
        for key,val in file_constructors[0].items():
            if key == 't':
                key = 'Frame'
            if import_node.inputs.get(key) is None:
                continue
            if import_node.inputs.get(key).type == "STRING":
                import_node.inputs.get(key).default_value = str(val)
                continue
            try:
                import_node.inputs.get(key).default_value = int(val)
            except Exception:
                import_node.inputs.get(key).default_value = str(val)
        import_node.label = ch.name
        self.update_import_affine(import_node, ch)
        return

    def update_import_affine(self, import_node, ch):
        affine = np.array(ch.data.affine, dtype=float)
        affine_node = self.node_group.nodes.get(f"channel_affine_{ch.identifier}")
        if affine_node is None:
            return
        for row in range(4):
            for column in range(4):
                # Combine Matrix exposes sockets by column, with four row values per column.
                affine_node.inputs[column * 4 + row].default_value = float(affine[row, column])
        return

    def ch_present(self, ch):
        return f"IMPORT_{ch.identifier}" in [node.name for node in self.node_group.nodes]

    def update_material(self, mat, ch):
        return
    
    def update_gn(self, ch):
        return

    def init_shader(self, mat):
        mat.use_nodes = True
        nodes = mat.node_tree.nodes
        nodes.clear()

        output = nodes.new("ShaderNodeOutputMaterial")
        output.name = "Material Output"
        output.location = (1500, 0)
        output.is_active_output = True

        add_shaders = nodes.new("ShaderNodeGroup")
        add_shaders.node_tree = add_shaders_node(self.shader_count)
        add_shaders.name = "Add Shaders"
        add_shaders.width = 100
        add_shaders.location = (620, 0)
        expand_node_ui(add_shaders)
        return

    def material_name(self):
        dataset_name = getattr(self, "dataset_name", None)
        if not dataset_name and self.object.parent is not None:
            dataset_name = self.object.parent.name
        if not dataset_name:
            dataset_name = self.object.name
        return f"{dataset_name} {self.min_type.name.lower()}"

    def init_channel_shader(self, mat, ch):
        raise NotImplementedError(f"{type(self).__name__} must implement init_channel_shader()")

    def init_gn(self):
        node_group = self.node_group
        nodes = node_group.nodes
        links = node_group.links

        nodes.clear()

        inputnode = nodes.new('NodeGroupInput')
        inputnode.location = (-900, 0)

        outputnode = nodes.new('NodeGroupOutput')
        outputnode.location = (1400, -100)
        outputnode.is_active_output = True

        channel_bundle = nodes.new("NodeCombineBundle")
        channel_bundle.name = "Channel Bundle"
        channel_bundle.location = (650, -100)

        join_node = nodes.new("GeometryNodeGroup")
        join_node.node_tree = join_microscopy_grids_and_meshes_node_group()
        join_node.name = "Join"
        join_node.location = (850, -100)

        set_material = nodes.new("GeometryNodeSetMaterial")
        set_material.name = "Set Material"
        set_material.location = (1100, -100)

        links.new(channel_bundle.outputs["Bundle"], join_node.inputs["Channel Bundle"])
        links.new(join_node.outputs["Geometry"], set_material.inputs["Geometry"])
        links.new(set_material.outputs["Geometry"], outputnode.inputs["Geometry"])
        return

    def add_ch_to_gn(self, ch):
        raise NotImplementedError(f"{type(self).__name__} must implement add_ch_to_gn()")

    def next_channel_location(self, in_node, join_node):
        min_y_loc = in_node.location[1] + 300
        skip_names = {
            in_node.name,
            "Group Output",
            "Channel Bundle",
            join_node.name,
            "Set Material",
        }
        for node in self.node_group.nodes:
            if node.name not in skip_names:
                min_y_loc = min(min_y_loc, node.location[1])
        return in_node.location[0] + 400, min_y_loc - 300

    def add_channel_to_bundle(self, ch, socket, data_type):
        combine = self.node_group.nodes["Channel Bundle"]
        item = combine.bundle_items.new(data_type, ch.name)
        combine[f"channel_{ch.identifier}"] = item.name
        bundle_input = combine.inputs[item.name]
        self.node_group.links.new(socket, bundle_input)

    def update_channel_bundle_name(self, ch):
        combine = self.node_group.nodes["Channel Bundle"]
        item_name = combine.get(f"channel_{ch.identifier}")
        if item_name is None:
            return
        item = next(item for item in combine.bundle_items if item.name == item_name)
        item.name = ch.name
        combine[f"channel_{ch.identifier}"] = item.name

        channel_attribute = self.node_group.nodes.get(f"[channel_load_{ch.identifier}]")
        if channel_attribute is not None:
            channel_attribute.attribute_name = ch.name

    def mask_grid_for_slice_cube(self, x, y, ch, grid_socket):
        nodes = self.node_group.nodes
        links = self.node_group.links

        mask_grid = nodes.new("GeometryNodeGroup")
        mask_grid.node_tree = mask_grid_node_group()
        mask_grid.name = f"SLICE_CUBE_{ch.identifier}"
        mask_grid.location = (x + 360, y + 80)
        mask_grid.width = 280
        mask_grid.show_options = False
        if mask_grid.inputs.get("With") is not None:
            mask_grid.inputs["With"].default_value = 'Box'

        links.new(grid_socket, mask_grid.inputs["Grid"])
        return mask_grid.outputs["Masked Grid"]

    def add_ch_to_shader(self, mat, ch, shader_socket):
        nodes = mat.node_tree.nodes
        links = mat.node_tree.links
        y_offset = -self.shader_y_step * ch.data.ix
        add_shaders = nodes["Add Shaders"]

        frame = nodes.new("NodeFrame")
        frame.name = f"[frame_{ch.identifier}]"
        frame.label = ch.name
        frame.use_custom_color = True
        frame.color = (0.0, 0.0, 0.0)
        frame.label_size = 50
        frame.shrink = True

        links.new(shader_socket, add_shaders.inputs[min(ch.data.ix, self.shader_count - 1)])
        return frame, add_shaders

    def set_parent_and_slicer(self, parent, slice_cube, ch):
        self.object.parent = parent
        self.object.matrix_parent_inverse.identity()
        slicer = self.node_group.nodes.get(f"SLICE_CUBE_{ch.identifier}")
        if slicer is not None and slicer.inputs.get("Object") is not None:
            slicer.inputs["Object"].default_value = slice_cube
        for obj in ch.metadata.get("collections", {}).get(self.min_type, []):
            obj.parent = parent
            obj.matrix_parent_inverse.identity()


class MeshChannelObject(ChannelObject):
    shader_y_step = 500

    def init_shader(self, mat):
        super().init_shader(mat)
        nodes = mat.node_tree.nodes
        links = mat.node_tree.links
        nodes["Add Shaders"].location = (980, 0)
        nodes["Material Output"].location = (1400, 0)
        links.new(nodes["Add Shaders"].outputs[0], nodes["Material Output"].inputs["Surface"])
        return

    def init_channel_shader(self, mat, ch):
        nodes = mat.node_tree.nodes
        links = mat.node_tree.links
        y_offset = -self.shader_y_step * ch.data.ix

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
        channel_index.inputs["Index"].default_value = ch.data.ix
        expand_node_ui(channel_index)

        frame, _ = self.add_ch_to_shader(mat, ch, channel_index.outputs["Shader"])

        color_lut.parent = frame
        princ.parent = frame
        channel_index.parent = frame

        links.new(color_lut.outputs[0], princ.inputs.get('Base Color'))
        links.new(color_lut.outputs[0], princ.inputs[27])
        links.new(princ.outputs[0], channel_index.inputs["Shader"])
        color_lut.inputs[0].default_value = 1.0
        return
