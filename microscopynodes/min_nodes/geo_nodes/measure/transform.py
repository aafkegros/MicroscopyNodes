from nodebpy import geometry as g


def mesh_in_holder_space(mesh, holder, mesh_parented_by_holder):
    holder_transform = g.ObjectInfo(
        object=holder,
        transform_space="RELATIVE",
    ).o.transform
    local_mesh = g.TransformGeometry(
        geometry=mesh,
        mode="Matrix",
        transform=g.InvertMatrix(matrix=holder_transform).o.matrix,
    ).o.geometry
    return (
        g.Switch.geometry(
            switch=mesh_parented_by_holder,
            false=local_mesh,
            true=mesh,
        ).o.output,
        holder_transform,
    )


def mesh_from_holder_space(mesh, holder_transform, mesh_parented_by_holder):
    transformed_mesh = g.TransformGeometry(
        geometry=mesh,
        mode="Matrix",
        transform=holder_transform,
    ).o.geometry
    return g.Switch.geometry(
        switch=mesh_parented_by_holder,
        false=transformed_mesh,
        true=mesh,
    ).o.output
