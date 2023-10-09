# MIT License

# Copyright (c) 2023 Oane Gros

# Permission is hereby granted, free of charge, to any person obtaining a copy
# of this software and associated documentation files (the "Software"), to deal
# in the Software without restriction, including without limitation the rights
# to use, copy, modify, merge, publish, distribute, sublicense, and/or sell
# copies of the Software, and to permit persons to whom the Software is
# furnished to do so, subject to the following conditions:

# The above copyright notice and this permission notice shall be included in all
# copies or substantial portions of the Software.

# THE SOFTWARE IS PROVIDED "AS IS", WITHOUT WARRANTY OF ANY KIND, EXPRESS OR
# IMPLIED, INCLUDING BUT NOT LIMITED TO THE WARRANTIES OF MERCHANTABILITY,
# FITNESS FOR A PARTICULAR PURPOSE AND NONINFRINGEMENT. IN NO EVENT SHALL THE
# AUTHORS OR COPYRIGHT HOLDERS BE LIABLE FOR ANY CLAIM, DAMAGES OR OTHER
# LIABILITY, WHETHER IN AN ACTION OF CONTRACT, TORT OR OTHERWISE, ARISING FROM,
# OUT OF OR IN CONNECTION WITH THE SOFTWARE OR THE USE OR OTHER DEALINGS IN THE
# SOFTWARE.
import bpy

from bpy.props import (StringProperty, FloatProperty,
                        PointerProperty,
                        )

from bpy.types import (Panel,
                        Operator,
                        AddonPreferences,
                        PropertyGroup,
                        )

import subprocess
from pathlib import Path
import os
import pip
import numpy as np
try:
    import tifffile
except:
    pip.main(['install', 'tifffile'])
    import tifffile




# note that this will write a dynamically linked vdb file, so rerunning the script on a file with the same name
# in the same folder, but with different data, will change the previously loaded data.

def make_and_load_vdb(imgdata, x_ix, y_ix, z_ix, axes_order, tif):
    # unpacks z stack into x/y slices in tmp tif files
    # calls zstacker, which assembles this into a vdb
    # deletes tmp files
    # returns the added volume object blender pointer
    # TODO redo x and y orientation from axes_order; rewrite with pyopenvdb
    tmpfiles = []
    zax =  axes_order.find('z')
    for z in range(imgdata.shape[zax]):
        fname = tif.parents[0] / f"tmp_zstacker/{z:04}.tif"
        plane = imgdata.take(indices=z,axis=zax)
        # if axes_order.find('x') > axes_order.find('y'):
        #     plane = plane.T
        tifffile.imwrite(fname, plane)
        tmpfiles.append(fname)
    identifier = str(x_ix)+str(y_ix)+str(z_ix)

    subprocess.run(" ".join([zstacker_path, "-t 1 -z", str(z_scale/xy_scale) ,str(tif.parents[0] / "tmp_zstacker"),  str(tif.with_name(tif.stem + identifier +".vdb"))]), shell=True)

    for tmpfile in tmpfiles:
        tmpfile.unlink()
    
    bpy.ops.object.volume_import(filepath=str(tif.with_name(tif.stem + identifier +".vdb")), align='WORLD', location=(0, 0, 0))
    return bpy.context.view_layer.objects.active

def load_tif(input_file, zstacker_path, xy_scale, z_scale, axes_order):

    tif = Path(input_file)

    with tifffile.TiffFile(input_file) as ifstif:
        imgdata = ifstif.asarray()
        print(imgdata.shape)
        imgdata = np.moveaxis(imgdata, 1,2)
        print(imgdata.shape)
        metadata = dict(ifstif.imagej_metadata)


    (tif.parents[0] / "tmp_zstacker/").mkdir(exist_ok=True)

    # 2048 is maximum grid size for Eevee rendering, so grids are split for multiple
    n_splits = [(dim // 2048)+ 1 for dim in imgdata.shape]
    arrays = [imgdata]


    # Loops over all axes and splits based on length
    # reassembles in negative coordinates, parents all to a parent at (half_x, half_y, bottom) that is then translated to (0,0,0)
    volumes =[]
    a_chunks = np.array_split(imgdata, n_splits[0], axis=0)
    for a_ix, a_chunk in enumerate(a_chunks):
        b_chunks = np.array_split(a_chunk, n_splits[1], axis=1)
        for b_ix, b_chunk in enumerate(b_chunks):
            c_chunks = np.array_split(b_chunk, n_splits[2], axis=2)
            for c_ix, c_chunk in enumerate(reversed(c_chunks)):
                vol = make_and_load_vdb(c_chunk, a_ix, b_ix, c_ix, axes_order, tif)
                bbox = np.array([c_chunk.shape[2],c_chunk.shape[1],c_chunk.shape[0]*(z_scale/xy_scale)])
                scale = np.ones(3)*0.02
                vol.scale = scale
                print(c_ix, b_ix, a_ix)
                offset = np.array([-c_ix-1,-b_ix-1,-a_ix-1])
                
                vol.location = tuple(offset*bbox*scale)
                volumes.append(vol)


    # recenter x, y, keep z at bottom
    center = np.array([0.5,0.5,1]) * np.array([c_chunk.shape[2] * (-len(c_chunks)), c_chunk.shape[1] * (-len(b_chunks)), c_chunk.shape[0] * (-len(a_chunks)*(z_scale/xy_scale))])
    empty = bpy.ops.object.empty_add(location=tuple(center*0.02))

    empty = bpy.context.object
    empty.name = str(tif.name) + " container" 

    for vol in volumes:
        vol.parent = empty
        vol.matrix_parent_inverse = empty.matrix_world.inverted()

    empty.location = (0,0,0)

    print('done')
    return




# ------------------------------------------------------------------------
#    Scene Properties
# ------------------------------------------------------------------------

class MyProperties(PropertyGroup):

    path_zstack : StringProperty(
        name="",
        description="Zstacker executable",
        default="",
        maxlen=1024,
        subtype='FILE_PATH')

    path_tif : StringProperty(
        name="",
        description="RGB tif file",
        default="",
        maxlen=1024,
        subtype='FILE_PATH')
    
    axes_order : StringProperty(
        name="",
        description="axes order (only z is used currently)",
        default="zyx",
        maxlen=6)
    
    xy_size : FloatProperty(
        name="",
        description="xy physical pixel size in micrometer",
        default=1.0)
    
    z_size : FloatProperty(
        name="",
        description="z physical pixel size in micrometer",
        default=1.0)


class TifLoadOperator(bpy.types.Operator):
    bl_idname = "tiftool.load"
    bl_label = "Load TIF"

    def execute(self, context):
        print("Hello World")
        return {'FINISHED'}



class TIFLoadPanel(bpy.types.Panel):
    bl_idname = "SCENE_PT_zstackpanel"
    bl_label = "zstacker wrapper"
    # bl_space_type = "VIEW_3D"   
    # bl_region_type = "UI"
    # bl_category = "Tools"
    bl_space_type = 'PROPERTIES'
    bl_region_type = 'WINDOW'
    bl_context = "scene"

    def draw(self, context):
        layout = self.layout
        scn = context.scene
        col = layout.column(align=True)
        col.label(text="RGB .tif file:")
        col.prop(scn.tiftool, "path_tif", text="")
        col.label(text="zstacker executable:")
        col.prop(scn.tiftool, "path_zstack", text="")

        split = layout.split()
        col = split.column()
        col.label(text="xy pixel size (µm):")
        col.prop(scn.tiftool, "xy_size")


        col = split.column(align=True)
        col.label(text="z pixel size (µm):")
        col.prop(scn.tiftool, "z_size")
        
        col = layout.column(align=True)
        col.label(text="axis order:")
        col.prop(scn.tiftool, "axes_order")
        
#        layout.label(text="Big Button:")
        layout.operator("tiftool.load")


# ------------------------------------------------------------------------
#    Registration
# ------------------------------------------------------------------------

classes = (
    MyProperties,
    TIFLoadPanel,
    TifLoadOperator
)

def register():
    from bpy.utils import register_class
    for cls in classes:
        register_class(cls)

    bpy.types.Scene.tiftool = PointerProperty(type=MyProperties)

def unregister():
    from bpy.utils import unregister_class
    for cls in reversed(classes):
        unregister_class(cls)
    del bpy.types.Scene.tiftool


if __name__ == "__main__":
    register()

#if __name__ == "__main__":
#    register()
