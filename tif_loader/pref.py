import bpy
import pathlib
from . import pkg
from bpy.types import AddonPreferences

ADDON_DIR = pathlib.Path(__file__).resolve().parent

bpy.types.Scene.pypi_mirror_provider = bpy.props.StringProperty(
    name = 'pypi_mirror_provider', 
    description = 'PyPI Mirror Provider', 
    options = {'TEXTEDIT_UPDATE','LIBRARY_EDITABLE'}, 
    default = 'Default', 
    subtype = 'NONE', 
    search = pkg.get_pypi_mirror_alias,
    )

def button_install_pkg(layout, name, version, desc = ''):
    layout = layout.row()
    if pkg.is_available(name, version):
        row = layout.row()
        row.label(text=f"{name} version {version} is installed.")
        op = row.operator('mn.install_package', text = f'Reinstall {name}')
        op.package = name
        op.version = version
        op.description = f'Reinstall {name}'
    else:
        row = layout.row(heading = f"Package: {name}")
        col = row.column()
        col.label(text=str(desc))
        col = row.column()
        op = col.operator('mn.install_package', text = f'Install {name}')
        op.package = name
        op.version = version
        op.description = f'Install required python package: {name}'

# Defines the preferences panel for the addon, which shows the buttons for 
# installing and reinstalling the required python packages defined in 'requirements.txt'
class TifLoadPreferences(AddonPreferences):
    bl_idname = __package__

    def draw(self, context):
        layout = self.layout
        layout.label(text = "Install the required packages for Tif Loader.")
        
        col_main = layout.column(heading = '', align = False)
        row_import = col_main.row()
        row_import.prop(bpy.context.scene, 'pypi_mirror_provider',text='Set PyPI Mirror')
        
        pkgs = pkg.get_pkgs()

        for package in pkgs.values():
            row = layout.row()
            button_install_pkg(
                layout = row, 
                name = package.get('name'), 
                version = package.get('version'), 
                desc = package.get('desc')
                )
            