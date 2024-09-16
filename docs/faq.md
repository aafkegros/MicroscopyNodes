Frequently asked questions. If yours is not in here, don't be afraid to open an [issue](https://github.com/oanegros/MicroscopyNodes/issues)!

<details>
  <summary>How is data transformed on load?</summary>
The data is scaled to 0.02 blender-meter per pixel on an initial load and centered in x and y. If you reload an image with a differently scaled version, it will adapt itself to the initial scale. You can check the size in pixels, blender meters and micrometers in the `Axes` object.
</details>


<details>
  <summary>I do not see my surfaces?</summary>
Try adjusting the threshold in the Surface Geometry Nodes modifier, the visibility of the Surfaces object, or the visibility of each channel in the Geometry Nodes modifier.
</details>


<details>
  <summary>I do not see my volumes?</summary>
Try adjusting the threshold in the materials, the visibility of the Volumes object, or the visibility of each channel in the Geometry Nodes modifier. If the emission of the channel was off, make sure there is enough light in the scene to reflect (often done with increasing background intensity).
</details>

<details>
  <summary>Why does my volume consist of multiple blocks?</summary>
Currently, Blender cannot handle volumes that are over 2048 pixels in any axis, so Microscopy Nodes chunks this type of data to smaller blocks. This should still be fully equal data (floating-point datasets may suffer from incorrect normalization), channel chunks are offset to avoid Blender rendering bugs.
</details>

