from typing import Annotated, Tuple, List, Dict, Any, Literal
from pydantic import BaseModel, Field, PrivateAttr, field_validator, model_validator
import numpy as np
from cmap import Color, Colormap
from .handle_blender_structs.min_keys import min_keys
from .handle_blender_structs.units import output_scale_for_import_scale, unit_label_from_value, unit_value
from .io.artifacts import GeneratedChannelFilesModel, write_mask

#######
#
# the data model is an intermediate shape that can easily be generated from code, back and forth the input GUI and into local cache files
# This can be handed to the blender_state managers to impact only the state of the tracked variables
# The rest of blender state is left to Blender itself to manage, as i do not want to mirror the entirety of Blender state
#
#######



# subtractive space as derived from https://trygvrad.github.io/multivariate-colormaps-for-n-dimensions/ (not a true implementation)
INIT_COLORS = [
    Color("#008AE4"),
    Color("#4A5B00"),
    Color("#A12352"),
    Color("#D55800"),
    Color("#9061D9"),
    Color("#006C4D"),
    Color("#CF458F"),
    Color("#0093AF"),
]


def _validate_axis_order(value, allowed, field_name):
    if not value:
        raise ValueError(f"{field_name} must not be empty")
    invalid = sorted(set(value) - set(allowed))
    if invalid:
        raise ValueError(f"{field_name} contains unsupported axes: {''.join(invalid)}")
    duplicates = sorted(axis for axis in set(value) if value.count(axis) > 1)
    if duplicates:
        raise ValueError(f"{field_name} contains duplicate axes: {''.join(duplicates)}")
    return value


class ChannelDataModel(BaseModel):
    dataset_resolution: int # currently static resolution identifier 

    ix: int # channel index in the original array used as unique identifier for the dataset TODO abstract this inot the ix in the dataset?
    axes_order: str # removes channel axis - optional later: make xarray?
    source_axes_order: str | None = None
    mask_path: str | None = None
    affine: List[List[float]] = Field(default_factory=lambda: np.eye(4).tolist()) #transforms into unit space
    unit: float #the data-unit in meters, affine transform maps into this
    frame_start: int | None = None
    frame_end: int | None = None

    source: str  # URI of the data
    internal_path: str | None = None # path inside container sources such as zarr
    min_rescale_xyz: Tuple[float, float, float] = (1.0, 1.0, 1.0)
    _source_array_cache: Any = PrivateAttr(default=None)
    _data_cache: Any = PrivateAttr(default=None) # check if necessary?
    _mask_cache: Any = PrivateAttr(default=None)

    @property
    def mask(self):
        if self.mask_path is None:
            return None
        if self._mask_cache is None:
            self._mask_cache = np.load(self.mask_path, allow_pickle=False)
        return self._mask_cache

    @field_validator("min_rescale_xyz")
    def validate_min_rescale_xyz(cls, v):
        if any(value < 1 for value in v):
            raise ValueError("min_rescale_xyz values must be greater than or equal to 1.")
        return tuple(float(value) for value in v)

    @field_validator("axes_order")
    def validate_axes_order(cls, value):
        return _validate_axis_order(value, "txyz", "axes_order")

    @field_validator("source_axes_order")
    def validate_source_axes_order(cls, value):
        if value is None:
            return None
        return _validate_axis_order(value, "tcxyz", "source_axes_order")

    @property
    def data(self):
        channel_axis = self.channel_axis
        if channel_axis is None:
            return self._source_array
        if self._data_cache is None:
            import dask.array as da

            self._data_cache = da.take(
                self._source_array,
                indices=self.ix,
                axis=channel_axis,
            )
        return self._data_cache

    @property
    def _source_array(self):
        if self._source_array_cache is None:
            from .file_to_array.source_array import open_source_array

            data = open_source_array(self.source, self.internal_path)
            data = self._stride_rescale(data)
            self._source_array_cache = data
        return self._source_array_cache

    def _stride_rescale(self, data):
        slices = []
        axes_order = self.source_axes_order or self.axes_order
        for axis in axes_order:
            if axis in "xyz":
                step = int(self.min_rescale_xyz["xyz".find(axis)])
                slices.append(slice(None, None, max(step, 1)))
            else:
                slices.append(slice(None))
        return data[tuple(slices)]

    @property
    def channel_axis(self):
        if self.source_axes_order is None or "c" not in self.source_axes_order:
            return None
        return self.source_axes_order.find("c")

    @property
    def data_shape(self):
        shape = tuple(self._source_array.shape)
        channel_axis = self.channel_axis
        if channel_axis is None:
            return shape
        return tuple(
            dim
            for ix, dim in enumerate(shape)
            if ix != channel_axis
        )

    @property
    def data_dtype(self):
        return self._source_array.dtype

    @field_validator('affine')
    def validate_affine(cls, v):
        a = np.asarray(v, dtype=float)
        if a.shape != (4, 4):
            raise ValueError('Affine must be 4×4.')
        return a.tolist()

    @field_validator("unit", mode="before")
    def parse_unit_scale(cls, v):
        return unit_value(v)

    @model_validator(mode="after")
    def validate_frame_order(self):
        if self.source_axes_order is None:
            self.source_axes_order = self.axes_order
        if self.source_axes_order.replace("c", "") != self.axes_order:
            raise ValueError(
                "source_axes_order without its channel axis must match axes_order"
            )
        if "t" not in self.axes_order:
            self.frame_start = 0
            self.frame_end = 0
        if 't' in self.axes_order and self.frame_start is None:
            self.frame_start = 0
        if 't' in self.axes_order and self.frame_end is None:
            self.frame_end = self.data_shape[self.axes_order.find('t')]-1
        if 't' in self.axes_order:
            tdim = self.data_shape[self.axes_order.find('t')]
            if self.frame_start < 0 or self.frame_start >= tdim:
                raise ValueError(f"frame_start {self.frame_start} out of bounds for t axis length {tdim}")
            if self.frame_end < 0 or self.frame_end >= tdim:
                raise ValueError(f"frame_end {self.frame_end} out of bounds for t axis length {tdim}")
        if "t" in self.axes_order and self.frame_start > self.frame_end:
            raise ValueError("frame_start must not exceed frame_end")
        return self

    # should implement transforms for Zarr RFC-5, will then turn to floats
    @property
    def intrinsic_bbox(self) -> Tuple[Tuple[float, float], Tuple[float, float], Tuple[float, float]]:
        upper_bound = [self.data_shape[self.axes_order.find(dim)] if dim in self.axes_order else 1 for dim in 'xyz']
        return tuple((0.0, float(u)) for u in upper_bound)

    @property
    def affine_matrix(self):
        return np.asarray(self.affine)

    @property
    def transformed_bbox(self):
        xs, ys, zs = self.intrinsic_bbox
        corners = np.array([
            [x, y, z, 1]
            for x in xs for y in ys for z in zs
        ])
        tc = (self.affine_matrix @ corners.T).T[:, :3]
        mins = tc.min(0)
        maxs = tc.max(0)
        return (mins[0], maxs[0]), (mins[1], maxs[1]), (mins[2], maxs[2])


class ChannelVizModel(BaseModel):
    ix: int = 0 
    name: str | None = None
    volume: bool = True
    surface: bool = False
    labelmask: bool = False
    emission: bool = True
    cmap: Colormap | None = None
    surf_resolution: int = 0 # will be deprecated?

    @model_validator(mode="before")
    @classmethod
    def set_ix_defaults(cls, data):
        if data is None:
            data = {}
        if not isinstance(data, dict):
            return data

        data = data.copy()
        ix = int(data.get("ix", 0) or 0)
        if data.get("name") is None:
            data["name"] = f"Channel {ix}"
        if data.get("cmap") is None:
            data["cmap"] = Colormap([INIT_COLORS[ix % len(INIT_COLORS)]])
        return data

class ChannelModel(BaseModel):
    data: ChannelDataModel
    viz: ChannelVizModel
    cache_path: str
    force_remaking_files: bool = False
    generated: GeneratedChannelFilesModel = Field(default_factory=GeneratedChannelFilesModel)

    @property
    def identifier(self):
        return f"ch_id{self.data.ix}"

    @property
    def name(self):
        return self.viz.name

    def files_for(self, min_type):
        return self.generated.for_type(min_type)

    def store_mask(self, mask):
        mask_path, mask = write_mask(self.cache_path, mask)
        self.data.mask_path = mask_path
        self.data._mask_cache = mask

class DatasetModel(BaseModel):
    channels: Annotated[List[ChannelModel], Field(min_length=1)]

    name: str | None = None
    slice_cube_mode: Literal["GEOMETRY", "SHADER"] = "GEOMETRY"

    @property
    def local_files_exist(self):
        for channel in self.channels:
            for min_type in (min_keys.VOLUME, min_keys.SURFACE, min_keys.LABELMASK):
                if getattr(channel.viz, min_type.name.lower(), False):
                    if not channel.files_for(min_type).constructors:
                        return False
        return True

    @property
    def unit_label(self):
        return unit_label_from_value(self.channels[0].data.unit) or "unit"

    @field_validator("channels")
    def no_duplicate_channel_names(cls, channels):
        names = [ch.name for ch in channels]
        if len(names) != len(set(names)):
            raise ValueError("No duplicate channel names allowed")
        return channels

    # TODO this doesnt have to be here and could be parsed in gn    
    @field_validator("channels")
    def no_different_units(cls, channels):
        units = [ch.data.unit for ch in channels]
        if len(set(units)) != 1:
            raise ValueError("All channel units need to currently be the same")
        return channels

    @property
    def intermediate_bbox(self):
        # this is pre-loc and output transform, in channel units
        bbs = [ch.data.transformed_bbox for ch in self.channels]
        mins = [min(b[i][0] for b in bbs) for i in range(3)]
        maxs = [max(b[i][1] for b in bbs) for i in range(3)]
        mins = np.array(mins, dtype=float)
        maxs = np.array(maxs, dtype=float)
        return mins, maxs, maxs - mins
        
    @property
    def dataset_origin_world(self):
        mins, _, _ = self.intermediate_bbox
        return -mins

    @property
    def dataset_center_world(self):
        _, _, extent = self.intermediate_bbox
        return extent / 2.0

    @model_validator(mode="after")
    def set_defaults(self):
        if not self.name:
            self.name = 'Microscopy Dataset'
        return self

class SceneModel(BaseModel):
    output_scale: float # conversion factor for blender scales
    import_transform: Tuple[float, float, float] = (0.5, 0.5, 0.0) # offset from world origin in inferred bbox

    @field_validator("output_scale", mode="before")
    def parse_output_scale(cls, v):
        return cls.output_scale_value(v)

    @field_validator("import_transform", mode="before")
    def parse_import_transform(cls, value):
        if isinstance(value, str):
            return {
                "ZERO": (0.0, 0.0, 0.0),
                "XY_CENTER": (0.5, 0.5, 0.0),
                "XYZ_CENTER": (0.5, 0.5, 0.5),
            }[value]
        return tuple(float(component) for component in value)

    @classmethod
    def output_scale_value(cls, value):
        return output_scale_for_import_scale(value)
