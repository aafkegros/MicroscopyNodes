from typing import Annotated, Optional, Tuple, List, Dict, Any
from pydantic import BaseModel, Field, PrivateAttr, field_validator, model_validator, ConfigDict
import numpy as np
from cmap import Color, Colormap
from .handle_blender_structs.min_keys import min_keys
import dask.array as da

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


class ChannelDataModel(BaseModel):
    # allow arbitrary types to parse dask arrays - might remove
    model_config = ConfigDict(arbitrary_types_allowed=True, populate_by_name=True)

    source: str  #for logging
    source_axes_order: Annotated[str, Field(pattern=r"^[tcxyz]*$")]
    source_data: da.Array = Field(alias="data") # lazy link to source data

    ix: int # channel index in the source_data
    affine: List[List[float]] | None = None #transforms into unit space
    name: str | None = None
    unit: float #the data-unit in meters, affine transform maps into this
    frame_start: int = None
    frame_end: int = None

    min_rescale_xyz: Tuple[float, float, float] = (1.0, 1.0, 1.0)
    _data_cache: da.Array | None = PrivateAttr(default=None)

    @field_validator("min_rescale_xyz")
    def validate_min_rescale_xyz(cls, v):
        if any(value < 1 for value in v):
            raise ValueError("min_rescale_xyz values must be greater than or equal to 1.")
        return tuple(float(value) for value in v)

    @property
    def data(self):
        channel_axis = self.channel_axis
        if channel_axis is None:
            return self.source_data
        if self._data_cache is None:
            self._data_cache = da.take(
                self.source_data,
                indices=self.ix,
                axis=channel_axis,
            )
        return self._data_cache

    @data.setter
    def data(self, value):
        self.source_data = value
        self.source_axes_order = self.axes_order
        self._data_cache = None

    @property
    def axes_order(self):
        return self.source_axes_order.replace("c", "")

    @property
    def channel_axis(self):
        if self.source_axes_order is None or "c" not in self.source_axes_order:
            return None
        return self.source_axes_order.find("c")

    @property
    def data_shape(self):
        shape = tuple(self.source_data.shape)
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
        return self.source_data.dtype

    @field_validator("source_data")
    def validate_data_shape(cls, v, info):
        if v is not None:
            source_axes_order = info.data.get("source_axes_order")
            if source_axes_order is not None and v.ndim != len(source_axes_order):
                raise ValueError(f"data.ndim ({v.ndim}) does not match source_axes_order length ({len(source_axes_order)})")
        return v

    @field_validator('affine', mode='before')
    def default_affine(cls, v):
        if v is None:
            return np.eye(4).tolist()
        return v

    @field_validator('affine')
    def validate_affine(cls, v):
        a = np.asarray(v, dtype=float)
        if a.shape != (4, 4):
            raise ValueError('Affine must be 4×4.')
        return a.tolist()

    @field_validator("frame_start", "frame_end")
    def validate_frame_bounds(cls, v, info):
        return v

    @model_validator(mode="after")
    def validate_frame_order(self):
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
    model_config = ConfigDict(json_encoders={Colormap: Colormap.as_dict})

    ix: int = 0 
    name: str | None = None
    volume: bool = True
    surface: bool = False
    labelmask: bool = False
    emission: bool = True
    cmap: Colormap | None = None
    surf_resolution: int = 0

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

    @field_validator("cmap", mode="before")
    def validate_cmap(cls, v):
        if isinstance(v, Colormap):
            return v
        return Colormap(v)


class ChannelModel(BaseModel):
    data_options: Annotated[List[ChannelDataModel], Field(min_length=1)]
    data_option_ix: int = 0
    viz: ChannelVizModel
    cache_path: str
    force_remaking_files: bool = False
    metadata: Dict[min_keys, Any] = Field(default_factory=dict) # runtime assessed
    file_constructors: Dict[min_keys, List[Dict[str, Any]]] = Field(default_factory=dict) # local file paths to load from

    def __init__(self, **data):
        if "data" in data:
            if "data_options" in data:
                raise ValueError("Use either data or data_options, not both")
            data_value = data.pop("data")
            data["data_options"] = data_value if isinstance(data_value, list) else [data_value]
            data.setdefault("data_option_ix", 0)
        super().__init__(**data)

    @model_validator(mode="after")
    def validate_selected_scale(self):
        if self.data_option_ix < 0 or self.data_option_ix >= len(self.data_options):
            raise ValueError("data_option_ix out of bounds")
        return self

    @property
    def data(self):
        return self.data_options[self.data_option_ix]

    @data.setter
    def data(self, value):
        if not isinstance(value, ChannelDataModel):
            value = ChannelDataModel.model_validate(value)
        self.data_options = [value]
        self.data_option_ix = 0

    @property
    def selected_scale(self):
        return self.data_option_ix

    @selected_scale.setter
    def selected_scale(self, value):
        value = int(value)
        if value < 0 or value >= len(self.data_options):
            raise ValueError("selected_scale out of bounds")
        self.data_option_ix = value

    @property
    def identifier(self):
        return f"ch_id{self.data.ix}"

    @property
    def name(self):
        return self.viz.name

class DatasetModel(BaseModel):
    channels: Annotated[List[ChannelModel], Field(min_length=1)]

    name : Optional[str] 
    output_unit: float = 1e-2 
    relative_loc: Tuple[float, float, float] = (-0.5, -0.5, 0) # world origin in /bbox

    # These two are only to make the px -> cm work, this entire mode will be deprecated
    explicit_scale: float | None = None 
    axis_unit_scale: float = 1.0 # axis-label units per dataset coordinate unit

    local_files_exist: bool = False

    @property
    def scale(self):
        if self.explicit_scale is not None:
            return self.explicit_scale
        return self.channels[0].data.unit / self.output_unit

    @property
    def unit_label(self):
        if self.explicit_scale is not None:
            if not np.isclose(float(self.axis_unit_scale), 1.0):
                unit_label = self._unit_label_from_value(self.channels[0].data.unit)
                if unit_label is not None:
                    return unit_label
            return "px"

        unit_label = self._unit_label_from_value(self.output_unit)
        if unit_label is not None:
            return unit_label
        return "unit"

    def _unit_label_from_value(self, unit_value):
        labels = {
            1e-10: "Å",
            1e-9: "nm",
            1e-6: "µm",
            1e-3: "mm",
            1.0: "m",
        }
        for value, label in labels.items():
            if np.isclose(float(unit_value), value):
                return label
        return None

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
        mins, _, extent = self.intermediate_bbox
        return np.array(self.relative_loc, dtype=float) * extent - mins

    @property
    def dataset_center_world(self):
        _, _, extent = self.intermediate_bbox
        return (np.array(self.relative_loc, dtype=float) + 0.5) * extent

    @model_validator(mode="after")
    def set_defaults(self):
        if not self.name:
            self.name = 'Microscopy Dataset'
        return self

    def make_local_files(self):
        from .io.factories import DataIOFactory

        try:
            for ch in self.channels:
                for min_type in (min_keys.VOLUME, min_keys.SURFACE, min_keys.LABELMASK):
                    load = getattr(ch.viz, min_type.name.lower(), False)
                    if not load:
                        continue
                    data_io = DataIOFactory(min_type)
                    file_constructors = data_io.make_local_files(ch)
                    ch.file_constructors[min_type] = file_constructors
                    ch.metadata[min_type] = data_io.get_metadata(file_constructors)
            self.local_files_exist = True
            return {"ok": True, "error": ""}
        except Exception as e:
            return {"ok": False, "error": str(e)}
