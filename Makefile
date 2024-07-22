test:
	python -m pip install .
	pytest -v


version := $(shell grep version pyproject.toml | grep -o -E "\b[0-9]+\.[0-9]+\.[0-9]+\b")

template:
	mkdir microscopynodes/assets
	mkdir microscopynodes/assets/template
	cd microscopynodes/assets/template && zip -r microscopynodes.zip ../../../microscopynodes

# git clean -dfX
release:
	git clean -dfX
	make template
	zip -r microscopynodes_$(version).zip microscopynodes -x *pycache* *.blend1 "microscopynodes/assets/template/microscopynodes/*"
