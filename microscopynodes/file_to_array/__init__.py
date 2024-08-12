from .tif import TifLoader
from .zarr import ZarrLoader

ARRAYLOADERS = [TifLoader(), ZarrLoader()]

