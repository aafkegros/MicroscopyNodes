test:
	poetry install 
	pytest -vx

version := $(shell grep version pyproject.toml | grep -o -E "\b[0-9]+\.[0-9]+\.[0-9]+\b")

template:
	cd tif2blender/assets/template && zip -r tif2blender.zip ../../../tif2blender

# git clean -dfX
release:
	
	make template
	zip -r tif2blender_$(version).zip tif2blender -x *pycache* *.blend1 "tif2blender/assets/template/tif2blender/*"
