from .arrayloading import ArrayLoader


class TifLoader(ArrayLoader):
    suffix = '.tif'

    def load_array(self, input_file):
        import tifffile
        with tifffile.TiffFile(input_file) as ifstif:
            return ifstif.asarray()

    def changePath(self, context):
        # infers metadata, resets to default if not found
        # the raise gets handled upstream, so only prints to cli, somehow.
        try: 
            import tifffile
            with tifffile.TiffFile(context.scene.MiN_input_file) as ifstif:
                try:
                    context.scene.MiN_axes_order = ifstif.series[0].axes.lower().replace('s', 'c')
                except Exception as e:
                    context.scene.property_unset("MiN_axes_order")
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

    