from .arrayloading import ArrayLoader
import tifffile

class TifLoader(ArrayLoader):
    suffixes = ['.tif', '.TIF', '.tiff', '.TIFF']

    def set_unit_and_axes_order(self, input_file):
        with tifffile.TiffFile(input_file) as ifstif:
            self._set_axes_order(ifstif.series[0].axes.lower().replace('s', 'c').replace('q','z'))
            try:
                self._set_unit(self.parse_unit(dict(ifstif.imagej_metadata)['unit']))
            except:
                self._set_unit("")
        return

    def fill_array_options(self, input_file):
        # uses self.add_option() to fill out a list of all native arrays
        xy_size = self._xy_size(input_file)
        z_size = self._z_size(input_file)
        shape = tifffile.TiffFile(input_file).series[0].shape
        self.add_option(xy_size=xy_size, z_size=z_size, shape=shape)
        return

    def load_array(self, input_file, array_option):
        with tifffile.TiffFile(input_file) as ifstif:
            return ifstif.asarray()

    def _xy_size(self, input_file):
        try:
            return tifffile.TiffFile(input_file).pages[0].tags['XResolution'].value[1]/ifstif.pages[0].tags['XResolution'].value[0]
        except:
            return 1.0

    def _z_size(self, input_file):
        try:
            return dict(tifffile.TiffFile(input_file).imagej_metadata)['spacing']
        except:
            return 1.0

