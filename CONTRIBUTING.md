# Building the documentation

Use Python 3.10 or later. Building the documentation does not require installing
Blender or the Microscopy Nodes Python dependencies.

```sh
python3 -m venv .venv-docs
source .venv-docs/bin/activate
make docs-install
make docs-build
# Or preview locally:
make docs-serve
```

Alternatively, use Conda:

```sh
conda create -n microscopy-docs python=3.13 pip -y
conda activate microscopy-docs
make docs-install
make docs-serve
```

`docs-install` installs all documentation dependencies from PyPI, including
`blender-doc-icons[mkdocs]`, with no version restriction. To upgrade an existing
installation, run `python -m pip install --upgrade "blender-doc-icons[mkdocs]"`.

The equivalent pip command is:

```sh
python -m pip install --index-url https://pypi.org/simple/ -r requirements-docs.txt
```

Write icons as `:blender-SCENE_DATA:` (names are case-insensitive). The MkDocs
plugin supplies the SVGs and stylesheet. Our custom `MICROSCOPY_NODES` icon lives
in `docs/custom_icons`; the static grey icons remain for the GitHub README.
The local `docs_macros.py` module only handles YouTube embeds.

For the smaller icon style, use
`<span class="small-icon">:blender-LIGHT:</span>`.
