import os
from pathlib import Path
from urllib.parse import unquote_to_bytes

import dask.array as da
import tifffile
import zarr


def open_source_array(source, internal_path=None):
    source = str(source)
    suffix = Path(source).suffix.lower()
    if suffix in {".tif", ".tiff"}:
        return da.from_zarr(tifffile.imread(source, aszarr=True))
    if suffix == ".zarr" or ".zarr" in source:
        group = _open_zarr_group(source)
        array = group[internal_path] if internal_path else group
        return da.from_zarr(array)
    raise ValueError(f"Could not infer array loader from source path: {source}")


def _open_zarr_group(uri):
    if uri.startswith("file:"):
        uri = os.fsdecode(unquote_to_bytes(uri))
    store = _s3_store(uri) if uri.startswith("s3://") else uri
    return zarr.open_group(store, mode="r")


def _s3_store(uri):
    import s3fs

    return s3fs.S3Map(root=uri, s3=s3fs.S3FileSystem(anon=True), check=False)
