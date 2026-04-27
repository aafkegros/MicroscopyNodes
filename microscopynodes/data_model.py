from typing import Annotated, Optional, Tuple, List, Dict, Any
from pydantic import BaseModel, Field, field_validator, model_validator, ConfigDict
import numpy as np
from .handle_blender_structs.props import min_keys
import dask.array as da
from .io.factories import DataIOFactory

# class ChannelTransform(BaseModel)
#     affine: 
#     


class ChannelModel(BaseModel):
    # allow arbitrary types to parse dask arrays - might remove
    model_config = ConfigDict(arbitrary_types_allowed=True)

    name : str

    dataset_resolution: int # currently static resolution identifier 
    cache_path: str

    ix: int # channel index in the original array
    data: da.Array # Maybe make this optional again for if the link to the data is lost?
    axes_order: Annotated[str, Field(pattern=r"^[txyz]*$")] # removes channel axis
    affine: List[List[float]] | None = None #transforms into unit space
    unit: float #the data-unit in meters, affine transform maps into this
    metadata: Dict[min_keys, Any] = Field(default_factory=dict) # runtime assessed
    file_constructors: Dict[min_keys, List[Dict[str, Any]]] = Field(default_factory=dict)
    
    frame_start: int = None
    frame_end: int = None

    visible_as : Dict[min_keys, bool] #maybe change this later

    emission: bool 
    # DISPLAY RGBA space(0-1 normalized rgb)
    cmap: Annotated[list[Tuple[float, float, float, float]], Field(min_length=1, max_length=32)] #RGBA
    cmap_is_linear: bool = True

    source: str  #for logging
    surf_resolution: int 
    force_remaking_files: bool = False

    @property
    def identifier(self):
        return f"ch_id{self.ix}"

    # should implement transforms for Zarr RFC-5, will then turn to floats
    @property
    def intrinsic_bbox(self) -> Tuple[Tuple[float, float], Tuple[float, float], Tuple[float, float]]:
        upper_bound = [self.data.shape[self.axes_order.find(dim)] if dim in self.axes_order else 1 for dim in 'xyz']
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
    
    @field_validator("data")
    def validate_data_shape(cls, v, info):
        if v is not None:
            axes_order = info.data.get("axes_order")
            if axes_order is not None and v.ndim != len(axes_order):
                raise ValueError(f"data.ndim ({v.ndim}) does not match axes_order length ({len(axes_order)}, note that channelConfig data is single-channel without channel axis)")
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
        data = info.data.get("data")
        axes = info.data.get("axes_order")

        if data is None or axes is None:
            return v

        if v is None:
            return v

        if "t" not in axes:
            return 0

        tdim = data.shape[axes.index("t")]

        if v < 0 or v >= tdim:
            raise ValueError(f"frame index {v} out of bounds for t axis length {tdim}")

        return v

    @model_validator(mode="after")
    def validate_frame_order(self):
        if "t" not in self.axes_order:
            self.frame_start = 0
            self.frame_end = 0
        if 't' in self.axes_order and self.frame_start is None:
            self.frame_start = 0
        if 't' in self.axes_order and self.frame_end is None:
            self.frame_end = self.data.shape[self.axes_order.find('t')]-1 
        if "t" in self.axes_order and self.frame_start > self.frame_end:
            raise ValueError("frame_start must not exceed frame_end")
        return self

class DatasetModel(BaseModel):
    channels: Annotated[List[ChannelModel], Field(min_length=1)]

    name : Optional[str] 
    output_unit: float = 1e-2 
    explicit_scale: float | None = None # this is only to make px -> cm work
    relative_loc: Tuple[float, float, float] = (-0.5, -0.5, 0) # world origin in /bbox

    local_files_exist: bool = False

    # only for updates
    update_settings: bool = True
    update_data: bool = True
    
    exception : Optional[str] = ""

    @property
    def scale(self):
        if self.explicit_scale is not None:
            return self.explicit_scale
        return self.channels[0].unit / self.output_unit

    @property
    def unit_label(self):
        if self.explicit_scale is not None:
            return "px"

        labels = {
            1e-10: "Å",
            1e-9: "nm",
            1e-6: "µm",
            1e-3: "mm",
            1.0: "m",
        }
        unit_value = float(self.output_unit)
        for value, label in labels.items():
            if np.isclose(unit_value, value):
                return label
        return "unit"

    @field_validator("channels")
    def no_duplicate_channel_names(cls, channels):
        names = [ch.name for ch in channels]
        if len(names) != len(set(names)):
            raise ValueError("No duplicate channel names allowed")
        return channels

    # TODO this doesnt have to be here and could be parsed in gn    
    @field_validator("channels")
    def no_different_units(cls, channels):
        units = [ch.unit for ch in channels]
        if len(set(units)) != 1:
            raise ValueError("All channel units need to currently be the same")
        return channels

    @property
    def intermediate_bbox(self):
        # this is pre-loc and output transform, in channel units
        bbs = [ch.transformed_bbox for ch in self.channels]
        mins = [min(b[i][0] for b in bbs) for i in range(3)]
        maxs = [max(b[i][1] for b in bbs) for i in range(3)]
        mins = np.array(mins, dtype=float)
        maxs = np.array(maxs, dtype=float)
        return mins, maxs, maxs - mins

    @property
    def final_bbox(self):
        mins, _, extent_unit = self.intermediate_bbox
        extent_world = extent_unit * float(self.scale)
        relative_loc = np.array(self.relative_loc, dtype=float)
        mins_world = (mins + (relative_loc + np.array([0.5, 0.5, 0.0])) * extent_unit) * float(self.scale)
        maxs_world = mins_world + extent_world
        return mins_world, maxs_world, extent_world

    @property
    def final_center(self):
        mins, _, extent_unit = self.intermediate_bbox
        relative_loc = np.array(self.relative_loc, dtype=float)
        return (mins + (relative_loc + 0.5) * extent_unit) * float(self.scale)

    @model_validator(mode="after")
    def set_defaults(self):
        if not self.name:
            self.name = 'Microscopy Dataset'
        return self

    def make_local_files(self):
        try:
            for ch in self.channels:
                for min_type, load in ch.visible_as.items():
                    if not load:
                        continue
                    data_io = DataIOFactory(min_type)
                    file_constructors = data_io.make_local_files(ch)
                    ch.file_constructors[min_type] = file_constructors
                    ch.metadata[min_type] = data_io.get_metadata(file_constructors)
            self.local_files_exist = True
        except Exception as e:
            self.exception = str(e)
        return self
