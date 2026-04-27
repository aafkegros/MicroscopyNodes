import glob
import os
from pathlib import Path
import re
import subprocess
import sys
from dataclasses import dataclass
from typing import List, Union
# import bpy

import tomlkit
import tomllib

toml_path = "microscopynodes/blender_manifest.toml"
whl_path = "./microscopynodes/wheels"
pyproject_path = Path("pyproject.toml")
blender_path =r"/Applications/Blender_5a.app/Contents/MacOS/Blender"
blender_path = "/Users/oanegros/Documents/blenderBuilds/stable/blender-5.0.0-macos-arm64+stable.a37564c4df7a/Blender/Blender.app/Contents/MacOS/Blender"
# permanent_whls = ["./microscopynodes/wheels/asciitree-0.3.4.dev1-py3-none-any.whl"]

@dataclass
class Platform:
    pypi_suffix: str
    metadata: str


# tags for blender metadata
# platforms = ["windows-x64", "macos-arm64", "linux-x64", "windows-arm64", "macos-x64"]


windows_x64 = Platform(pypi_suffix="win_amd64", metadata="windows-x64")
linux_x64 = Platform(pypi_suffix="manylinux2014_x86_64", metadata="linux-x64")
macos_arm = Platform(pypi_suffix="macosx_12_0_arm64", metadata="macos-arm64")
macos_intel = Platform(pypi_suffix="macosx_10_16_x86_64", metadata="macos-x64")

EXCLUDED_POETRY_PACKAGES = {"python", "bpy"}


def _pyproject() -> dict:
    with pyproject_path.open("rb") as f:
        return tomllib.load(f)


def python_download_version() -> str:
    deps = _pyproject()["tool"]["poetry"]["dependencies"]
    python_spec = deps["python"]
    match = re.search(r"(\d+)\.(\d+)", python_spec)
    if match is None:
        raise ValueError(f"Could not parse python version from {python_spec!r}")
    return f"{match.group(1)}.{match.group(2)}"


def runtime_packages() -> List[str]:
    deps = _pyproject()["tool"]["poetry"]["dependencies"]
    packages: List[str] = []
    for name, spec in deps.items():
        if name in EXCLUDED_POETRY_PACKAGES:
            continue
        if isinstance(spec, str):
            if spec.strip() == "*":
                packages.append(name)
            else:
                packages.append(f"{name}{spec}")
        else:
            raise ValueError(
                f"Unsupported dependency spec for {name!r}: {spec!r}. "
                "build.py currently expects string versions in [tool.poetry.dependencies]."
            )
    return packages

# this is deprecated - for non buildable wheels, will remove in the future
nodeps_packages = [ 
]

build_platforms = [
    # windows_x64,
    # linux_x64,
    macos_arm,
    # macos_intel,
]


def run_python(args: str):
    python = os.path.realpath(sys.executable)
    subprocess.run([python] + args.split(" "))


def remove_whls():
    for whl_file in glob.glob(os.path.join(whl_path, "*.whl")):
        # if whl_file not in permanent_whls:
        os.remove(whl_file)
    # exit()


def download_whls(
    platforms: Union[Platform, List[Platform]],
    required_packages: List[str] | None = None,
    python_version: str | None = None,
    clean: bool = True,
):
    if required_packages is None:
        required_packages_from_pyproject = runtime_packages()
    else:
        required_packages_from_pyproject = required_packages
    if python_version is None:
        python_version = python_download_version()

    if isinstance(platforms, Platform):
        platforms = [platforms]

    if clean:
        remove_whls()

    for platform in platforms:
        print(required_packages_from_pyproject, nodeps_packages, f"-m pip download {' '.join(required_packages_from_pyproject)} --dest ./microscopynodes/wheels --only-binary=:all: --python-version={python_version} --platform={platform.pypi_suffix}")
        run_python(
            f"-m pip download {' '.join(required_packages_from_pyproject)} --dest ./microscopynodes/wheels --only-binary=:all: --python-version={python_version} --platform={platform.pypi_suffix}"
        )
        # run_python(
        #     f"-m pip download {' '.join(nodeps_packages)} --dest ./microscopynodes/wheels --python-version={python_version} --platform={platform.pypi_suffix} --no-deps"
        # )

def update_toml_whls(platforms):
    # Define the path for wheel files
    wheels_dir = "microscopynodes/wheels"
    wheel_files = glob.glob(f"{wheels_dir}/*.whl")
    wheel_files.sort()

    # Packages to remove
    packages_to_remove = {
        "numpy"
    }

    # Filter out unwanted wheel files
    to_remove = []
    to_keep = []
    for whl in wheel_files:
        if any(pkg in whl for pkg in packages_to_remove):
            to_remove.append(whl)
        else:
            to_keep.append(whl)

    # Remove the unwanted wheel files from the filesystem
    for whl in to_remove:
        # if whl not in permanent_whls:
        os.remove(whl)

    # Load the TOML file
    with open(toml_path, "r") as file:
        manifest = tomlkit.parse(file.read())

    # Update the wheels list with the remaining wheel files
    manifest["wheels"] = [f"./wheels/{os.path.basename(whl)}" for whl in to_keep]

    # Simplify platform handling
    if not isinstance(platforms, list):
        platforms = [platforms]
    manifest["platforms"] = [p.metadata for p in platforms]

    # Write the updated TOML file
    with open(toml_path, "w") as file:
        file.write(
            tomlkit.dumps(manifest)
            .replace('["', '[\n\t"')
            .replace("\\\\", "/")
            .replace('", "', '",\n\t"')
            .replace('"]', '",\n]')
        )


def clean_files(suffix: str = ".blend1") -> None:
    pattern_to_remove = f"microscopynodes/**/*{suffix}"
    for blend1_file in glob.glob(pattern_to_remove, recursive=True):
        os.remove(blend1_file)


def build_extension(split: bool = True) -> None:
    for suffix in [".blend1", ".MNSession"]:
        clean_files(suffix=suffix)

    if split:
        subprocess.run(
            f"{blender_path} --command extension build"
            " --split-platforms --source-dir microscopynodes --output-dir .".split(" ")
        )
    else:
        subprocess.run(
            f"{blender_path} --command extension build "
            "--source-dir microscopynodes --output-dir .".split(" ")
        )


def build(platform) -> None:
    download_whls(platform)
    update_toml_whls(platform)
    build_extension()


def main():
    # for platform in build_platforms:
    #     build(platform)
    build(build_platforms)


if __name__ == "__main__":
    main()
