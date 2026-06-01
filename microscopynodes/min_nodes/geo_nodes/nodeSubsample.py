import bpy
from nodebpy import TreeBuilder, geometry as g
from nodebpy.builder import CustomGeometryGroup
from nodebpy.types import InputFloat, InputInteger


GROUP_NAME = "Subsampled active grid positions"


class SubsampledActiveGridPositions(CustomGeometryGroup):
    _name = GROUP_NAME

    def __init__(
        self,
        grid: InputFloat = 0.0,
        resolution_x: InputInteger = 20,
        resolution_y: InputInteger = 20,
        resolution_z: InputInteger = 10,
    ):
        super().__init__(
            **{
                "Grid": grid,
                "Resolution X": resolution_x,
                "Resolution Y": resolution_y,
                "Resolution Z": resolution_z,
            }
        )

    def _build_group(self, tree):
        _build_subsampled_active_grid_positions(tree)


def _build_subsampled_active_grid_positions(tree):
    tree.tree.show_modifier_manage_panel = True

    grid = tree.inputs.float(
        "Grid",
        hide_value=True,
        structure_type="GRID",
    )
    resolution_x = tree.inputs.integer(
        "Resolution X",
        20,
        min_value=1,
    )
    resolution_y = tree.inputs.integer(
        "Resolution Y",
        20,
        min_value=1,
    )
    resolution_z = tree.inputs.integer(
        "Resolution Z",
        10,
        min_value=1,
    )
    geometry = tree.outputs.geometry("Geometry")

    volume = g.StoreNamedGrid.float(
        name="",
        grid=grid,
    ).o.volume
    bounds = g.BoundingBox(
        geometry=volume,
        use_radius=False,
    )
    topology = g.CubeGridTopology(
        bounds_min=bounds.o.min,
        bounds_max=bounds.o.max,
        resolution_x=resolution_x,
        resolution_y=resolution_y,
        resolution_z=resolution_z,
    ).o.topology

    active_grid = g.Compare(
        a=grid,
        b=0.0001,
        operation="GREATER_THAN",
        data_type="FLOAT",
    ).node.outputs["Result"]
    position = g.Position().o.position
    sampled_active = g.SampleGrid.boolean(
        grid=active_grid,
        position=position,
        interpolation="Nearest Neighbor",
    ).o.value
    active_topology = g.BooleanMath.l_and(
        sampled_active,
        topology,
    ).o.boolean
    points_grid = g.BooleanMath.l_not(
        g.PruneGrid.boolean(
            grid=active_topology,
        ).o.grid,
    ).o.boolean

    points = g.GridToPoints.boolean(
        points_grid,
    )
    active_points = g.DeleteGeometry(
        geometry=points.o.points,
        selection=points.o.value,
    ).o.geometry
    bounds_size = g.VectorMath.subtract(
        bounds.o.max,
        bounds.o.min,
    ).o.vector
    normalized_position = g.VectorMath.divide(
        g.VectorMath.subtract(
            position,
            bounds.o.min,
        ).o.vector,
        bounds_size,
    ).o.vector
    g.SetPosition(
        geometry=active_points,
        position=normalized_position,
    ).o.geometry >> geometry


def subsampled_active_grid_positions_node_group():
    node_group = bpy.data.node_groups.get(GROUP_NAME)
    if node_group:
        return node_group

    with TreeBuilder.geometry(GROUP_NAME) as tree:
        _build_subsampled_active_grid_positions(tree)

    return tree.tree
