# Microscopy in Blender
This is a project building bioimage support for the open source software blender. This currently exists as the Blender add-on `Microscopy Nodes`, previously named `tif2blender`. This is able to easily load tif files as volumetric objects in Blender. 

Please make some pretty figures with this add-on! 

For usage questions please use the [image.sc forum](https://forum.image.sc/tag/microscopy-nodes) 😁
For issues/bug reports/feature requests please [open an issue](https://github.com/oanegros/MicroscopyNodes/issues).

If you publish with this add-on, please cite [the preprint](https://www.biorxiv.org/content/10.1101/2025.01.09.632153v1):
```
@article {Gros2025.01.09.632153,
	author = {Gros, Oane and Bhickta, Chandni and Lokaj, Granita and Schwab, Yannick and K{\"o}hler, Simone and Banterle, Niccol{\`o}},
	title = {Microscopy Nodes: versatile 3D microscopy visualization with Blender},
	elocation-id = {2025.01.09.632153},
	year = {2025},
	doi = {10.1101/2025.01.09.632153},
	publisher = {Cold Spring Harbor Laboratory},
	URL = {https://www.biorxiv.org/content/early/2025/01/14/2025.01.09.632153},
	eprint = {https://www.biorxiv.org/content/early/2025/01/14/2025.01.09.632153.full.pdf},
	journal = {bioRxiv}
} 
```

## Current Features
Microscopy Nodes supports:

- up to 5D (up to tzcyx in any axis order) tifs and OME-Zarr files can be loaded. 
- Channel interface to define how to load data
- Replacing a pyramidal dataset with it's higher resolution version
- Accurate scale bars
- Load per-index label masks
- Lazy loading of giant files (no data is loaded in RAM outside what's rendered)

### [Get Started!](./new_user.md)
<img src="https://github.com/oanegros/MicroscopyNodes/blob/main/figures/newprettyside.png?raw=true" width="600"/>