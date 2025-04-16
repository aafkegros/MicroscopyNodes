from .arrayloading import ArrayLoader
from .arrayoptions import add_array_option
import tifffile

class TifLoader(ArrayLoader):
    suffixes = ['.tif', '.TIF', '.tiff', '.TIFF']

    def set_file_globals(self, input_file):
        with tifffile.TiffFile(input_file) as ifstif:
            self._set_axes_order(ifstif.series[0].axes.lower().replace('s', 'c').replace('q','z'))
            if 'unit' in dict(ifstif.imagej_metadata):
                self._set_unit(dict(ifstif.imagej_metadata)['unit'])
        return

    def fill_array_options(self, input_file):
        # uses add_array_option to fill out a list of all native arrays
        xy_size = self._xy_size(input_file)
        z_size = self._z_size(input_file)
        shape = tifffile.TiffFile(input_file).series[0].shape
        add_array_option(xy_size=xy_size, z_size=z_size, shape=shape)
        return

    def load_array(self, input_file, array_option):
        # return tifffile.imread(input_file, aszarr=True) # this can be tried in the future
        with tifffile.TiffFile(input_file) as ifstif:
            return ifstif.asarray()

    def _xy_size(self, input_file):
        try:
            return tifffile.TiffFile(input_file).pages[0].tags['XResolution'].value[1]/tifffile.TiffFile(input_file).pages[0].tags['XResolution'].value[0]
        except Exception as e:
            print(e)
            return 1.0

    def _z_size(self, input_file):
        try:
            return dict(tifffile.TiffFile(input_file).imagej_metadata)['spacing']
        except Exception as e:
            # print(e)
            return 1.0

