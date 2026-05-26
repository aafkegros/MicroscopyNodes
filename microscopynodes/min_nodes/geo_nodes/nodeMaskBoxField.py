from nodebpy import geometry as g
from nodebpy.builder import CustomGeometryGroup
from nodebpy.types import InputBoolean, InputObject


class ClipFieldToBox(CustomGeometryGroup):
    _name = "Clip Field to Box"

    def __init__(
        self,
        box_object: InputObject = ...,
        invert: InputBoolean = False,
    ):
        super().__init__(
            **{
                "Box Object": box_object,
                "Invert": invert,
            }
        )

    def _build_group(self, tree):
        box = tree.inputs.object("Box Object", optional_label=True)
        invert = tree.inputs.boolean("Invert")
        masked = tree.outputs.boolean("Clipped Field")

        local_pos = (
            g.InvertMatrix(
                matrix=g.ObjectInfo(
                    object=box,
                    transform_space="RELATIVE",
                ).o.transform
            ).o.matrix
            @ g.Position()
            * 0.5
        )

        result = (
            (abs(local_pos.x) < 0.5)
            & (abs(local_pos.y) < 0.5)
            & (abs(local_pos.z) < 0.5)
        )

        (result != invert) >> masked
