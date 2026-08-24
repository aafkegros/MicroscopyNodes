# Work with time-series data

If the source axes contain `t`, Microscopy Nodes maps the selected image timepoints onto Blender's {{ svg("time") }} timeline.

## Choose the source range

After entering the dataset path, check the detected axis order and set the start and end timepoints in the {{ svg("microscopy_nodes") }} loading panel. Load only the interval needed for the scene when storage or conversion time matters.

After loading, move through the timeline with the arrow keys or timeline controls. The microscopy data updates with the Blender frame.

## Retime the biological sequence

Select the {{ svg("outliner_ob_empty") }} holder object. Its animated **Frame** property controls which microscopy timepoint is read.

- Move the first or last keyframe with `G` to add a delay.
- Scale the keyframes with `S` to slow down or accelerate the complete sequence.
- Edit the interpolation in Blender's animation editors when a different timing curve is needed.

Retiming this property changes playback without duplicating source frames.

## Create a pause

To hold one biological timepoint while the camera continues moving:

1. Move to the desired Blender frame.
2. Set the holder's **Frame** value to the source timepoint to hold.
3. Hover over the value and press `I` to insert a keyframe.
4. Move later in the Blender timeline.
5. Insert the same source-frame value again.

The data remains fixed between those keyframes, while the {{ svg("view_camera") }} camera and all other animated scene properties remain independent.

## Display elapsed time

Use the Microscopy Nodes **Time Annotation** geometry node to convert the current frame into a formatted label. Set the acquisition period and choose input and output units, for example seconds to minutes.

See [Scale bars, grids, and time labels](./annotation.md) and [Cameras, animation, and output](./creating_output.md).

For tracked label masks, [Split and animate subvolumes](./subvolumes.md) explains how to preserve each object's `oid` while separating regions across time.
