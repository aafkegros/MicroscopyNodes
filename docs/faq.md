# FAQ

Frequently asked questions. If yours is not in here, don't be afraid to open an [issue](https://github.com/oanegros/MicroscopyNodes/issues)!

<details>
  <summary>How is data transformed on load?</summary>
The data is scaled to 0.02 blender-meter per pixel on an initial load and centered in x and y. If you reload an image with a differently scaled version, it will adapt itself to the initial scale. You can check the size in pixels, blender meters and micrometers in the `Axes` object.
</details>




