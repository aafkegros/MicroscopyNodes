# Rendering

There are a lot of extra parameters that can be adjusted to optimize rendering in Blender. All of these are explained in the {{ svg("blender") }} [Blender manual](https://docs.blender.org/manual/en/latest/render/cycles/render_settings/index.html). Some, however, are especially useful to know for microscopy data or for new users. These are covered here.

## Render Engines

There are two major render engines in Blender. **EEVEE**, a [rasterized](https://en.wikipedia.org/wiki/Rasterisation) render engine, and **Cycles** a [ray-traced](https://en.wikipedia.org/wiki/Ray_tracing_(graphics)) engine. 

### EEVEE

**EEVEE** is a render engine that is made to be fast, and powerful. It is less optimized for {{ svg("volume") }} volumetric data, especially for dense/scattering volumes. Currently, it can only handle volume data < 4 GiB.

However, it is still very strong, is usually able to combine semi-transparent masks and volumes, and is often faster, especially for rendering emissive time-lapses. 

It may take longer to open an EEVEE interface with volumes, and for larger data it can be slower in general than Cycles.


### Cycles

**Cycles** is the ray-traced render engine, slower than EEVEE as it calculates light bouncing. This is best for scattering, and can be faster with bigger data. 


## Render Settings

The {{ svg("scene") }} render settings can be found in the {{ svg("properties") }} properties.

### Samples

The number of samples is a metric for how much time the rendering algorithm takes to make an image. Lower samples mean more noise, but quicker render times, a high number of samples makes nicer images, but takes more time.

### Volume scattering (Cycles)

The amount of scattering in a volume is very important for the visualization of {{ svg("light") }} dense/scattering volumes. These are not as important in emissive {{ svg("outliner_ob_light") }} volumes.

This is only well-defined in a raytracer, so this is only available in Cycles. These can significantly affect performance.

This can be controlled with two parameters:

- Volumes > Max Steps
  > The depth of traversal through the volume
- Light Paths > Max Bounces > Volume 
  > Total amount of volume scattering events

In addition, the `Volumes > Step Rate` can be changed, but only if artefacts show up. This can often also be helped by downscaling the volume (through the [holder](./3_objects.md#holder)).

### General scattering (Cycles)

The number of light bounces can be relevant also outside of the volumes. Especially for `Light Paths > Max Bounces > Transparent` and `Light Paths > Max Bounces > Total`. This is relevant to avoid black artefacting when overlaying many (semi-)transparent meshes. 


### Transparent background

This can be found under Film > Transparent. Note that a transparent background can and will still be able to light a scene, if the {{ svg("world") }} background color is not black.

### Color Management

The `Color Management > View Transform` is set by default to `Standard` after loading with Microscopy Nodes, doing no postprocessing of colors in the final image. The default of Blender is `AgX`. This postprocesses the colors in the image to make them look more 'real'/'better', and has multiple **Looks** (high contrast, punchy etc) to choose from.

## Output settings

The {{ svg("output") }} output settings can be found in the {{ svg("properties") }} properties.

### Time

The timing of output can be changed. The **Frame Rate** for output videos and previews can be changed under `Format > Frame Rate`.

**Time Stretching**, under `Frame Range`, is the best way to offset Blender-frame rate from your volume's frame rate. Stretching time here allows e.g. more frames of camera movement per timeframe of your biological sample.

{{ youtube("jcERgoBI1b8", 280, 158) }}

### Output location and format

Under {{ svg("output") }} > Output, the output file location and format can be defined. Here it is useful to note that if the format is set to `PNG`, as default, you would still have to compile the frames to video later.

Optionally, you can set the output format to `FFMPEG Video`, which will output a full video when you render an animation. This does limit your capacity to edit the video encoding and you cannot stop the render e.g. halfway and still retain the first half of the output.