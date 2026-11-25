import numpy as np
import pytest
import tifffile

from microscopynodes.file_to_array.tif import TifLoader


def test_tiff_reads_x_and_y_resolution_independently(tmp_path):
    path = tmp_path / "anisotropic.tif"
    tifffile.imwrite(path, np.zeros((8, 16), dtype=np.uint8), resolution=(4, 2))

    [dataset] = TifLoader().native_options(path)
    [channel] = dataset.channels

    assert np.diag(channel.data.affine_matrix)[:3] == pytest.approx([0.25, 0.5, 1.0])
