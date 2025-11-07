# SPACE FOR PYDANTIC MODELS 

# from typing import List, Union
# from pydantic import BaseModel, field_validator
# import numpy as np


# ColorInputType = Union[str, List[float]]

# class ColorInput(BaseModel):
#     value: ColorInputType

#     @field_validator("value")
#     def validate_color_input(cls, v):
#         # Case 1: named colormap string
#         if isinstance(v, str):
#             if v.lower() not in VALID_CMAPS:
#                 raise ValueError(f"Invalid colormap name '{v}'. Must be one of: {sorted(list(VALID_CMAPS))[:10]}...")
#             return v.lower()

#         # Case 2: numeric list (RGB or LUT)
#         if isinstance(v, list):
#             if not all(isinstance(x, (int, float)) for x in v):
#                 raise ValueError("Color list must contain only numbers")
#             n = len(v)

#             # RGB triplet
#             if n == 3 and all(0.0 <= x <= 1.0 for x in v):
#                 return [float(x) for x in v]

#             # LUT (max 32 entries)
#             if 1 < n <= 32:
#                 return [float(x) for x in v]

#             raise ValueError("List must be either RGB length 3 or up to 32-length LUT of floats")

#         raise TypeError(f"Unsupported color input type: {type(v)}")
