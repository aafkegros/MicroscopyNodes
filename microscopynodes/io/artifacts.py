from pathlib import Path
from typing import Any, Dict, List

import numpy as np
from pydantic import BaseModel, Field, field_serializer


def _json_safe(value):
    if isinstance(value, np.ndarray):
        return value.tolist()
    if isinstance(value, np.generic):
        return value.item()
    if isinstance(value, dict):
        return {str(key): _json_safe(item) for key, item in value.items()}
    if isinstance(value, (list, tuple)):
        return [_json_safe(item) for item in value]
    return value


class ChannelFilesModel(BaseModel):
    constructors: List[Dict[str, Any]] = Field(default_factory=list)
    metadata: Dict[str, Any] = Field(default_factory=dict)

    @field_serializer("metadata", when_used="json")
    def serialize_metadata(self, metadata):
        return _json_safe(metadata)


class GeneratedChannelFilesModel(BaseModel):
    volume: ChannelFilesModel = Field(default_factory=ChannelFilesModel)
    surface: ChannelFilesModel = Field(default_factory=ChannelFilesModel)
    labelmask: ChannelFilesModel = Field(default_factory=ChannelFilesModel)

    def for_type(self, min_type):
        return getattr(self, min_type.name.lower())


def write_mask(cache_path, mask):
    mask = np.asarray(mask, dtype=bool)
    if mask.ndim != 3:
        raise ValueError("mask must be a three-dimensional boolean array")
    mask_path = Path(cache_path) / "visibility_mask.npy"
    mask_path.parent.mkdir(parents=True, exist_ok=True)
    temporary_path = mask_path.with_suffix(".tmp.npy")
    np.save(temporary_path, mask, allow_pickle=False)
    temporary_path.replace(mask_path)
    return str(mask_path), mask
