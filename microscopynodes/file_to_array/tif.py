from .arrayloading import ArrayLoader
import tifffile
import bpy

class TifLoader(ArrayLoader):
    suffixes = ['.tif', '.TIF', '.tiff', '.TIFF']

    def load_array(self, input_file):
        with tifffile.TiffFile(input_file) as ifstif:
            return ifstif.asarray()

    def changePath(self, context):
        # infers metadata, resets to default if not found
        # the raise gets handled upstream, so only prints to cli, somehow.
        try: 
            with tifffile.TiffFile(context.scene.MiN_input_file) as ifstif:
                try:
                    context.scene.MiN_axes_order = ifstif.series[0].axes.lower().replace('s', 'c').replace('q','z')
                except Exception as e:
                    context.scene.property_unset("MiN_axes_order")
                try:
                    context.scene.MiN_unit =  self.parse_unit(dict(ifstif.imagej_metadata)['unit'])
                except Exception as e:
                    print(e)
                    context.scene.property_unset("MiN_unit")
                try:
                    context.scene.MiN_xy_size = ifstif.pages[0].tags['XResolution'].value[1]/ifstif.pages[0].tags['XResolution'].value[0]
                except Exception as e:
                    context.scene.property_unset("MiN_xy_size")
                try:
                    context.scene.MiN_z_size = dict(ifstif.imagej_metadata)['spacing']
                except Exception as e:
                    context.scene.property_unset("MiN_z_size")
                try:
                    if 'channels' in dict(ifstif.imagej_metadata):
                        context.scene.MiN_channel_nr = dict(ifstif.imagej_metadata)['channels']
                    else: 
                        context.scene.MiN_channel_nr = 1
                except Exception as e:
                    bpy.context.scene.MiN_channel_nr = 0
        except Exception as e:
            context.scene.property_unset("axes_order")
            context.scene.property_unset("xy_size")
            context.scene.property_unset("z_size")
            raise   
        return

    def shape(self):
        return tifffile.TiffFile(bpy.context.scene.MiN_input_file).series[0].shape