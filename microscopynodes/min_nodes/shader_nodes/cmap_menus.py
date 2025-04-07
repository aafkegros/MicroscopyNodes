import bpy


import numpy as np 
import cmap


CMAP_CATEGORIES =  {
    "sequential": "IPO_LINEAR",
    "diverging": "LINCURVE", 
    "cyclic" : "MESH_CIRCLE", 
    "qualitative":"OUTLINER_DATA_POINTCLOUD",
    "miscellaneous":"ADD",
    }

def cmap_submenu_class(op, opname, category, namespace=None):
    def draw(self, context):
        if self.namespace is None:
            for namespace in sorted(cmap_namespaces(self.category)):
                self.layout.menu(cmap_bl(self.category, namespace, opname=opname)[0], text=cmap_bl(category, namespace, opname=opname)[1])
        else:
            for cmap in cmaps(self.category, self.namespace):
                if cmap != 'prinsenvlag': # exclude this colormap, this is a weird fascist dogwhistle
                    op_ = self.layout.operator(op, text=cmap)
                    op_.cmap_name = cmap
#            menu_items.get_submenu("utils").menu(self.layout, context)
    
    cls_elements = {
            'bl_idname': cmap_bl(category, namespace, opname=opname)[0],
            'bl_label': cmap_bl(category, namespace, opname=opname)[1],
            'category' : category,
            'namespace' : namespace,
            'draw' : draw
        }

    # Dynamically create classes for cmap submenus
    menu_class = type(
        cmap_bl(category, namespace, opname=opname)[0], 
        (bpy.types.Menu,),  
        cls_elements
    )
    return menu_class

def cmap_namespaces(categories):
    return list({cmap_name.split(':')[0] for cmap_name in cmap.Catalog().unique_keys(categories=categories, prefer_short_names=False)})

def cmaps(category, namespace):
    return list({cmap_name.split(':')[1] for cmap_name in cmap.Catalog().unique_keys(categories=[category], prefer_short_names=False) if cmap_name.split(':')[0] == namespace})

def cmap_bl(category, namespace=None, name=None, opname=None):
    if name is not None: 
        return f"MIN_MT_{category.upper()}_{namespace.upper()}_{name.upper()}_{opname.upper()}", name
    if namespace is not None: 
        return f"MIN_MT_{category.upper()}_{namespace.upper()}_{opname.upper()}", namespace
    return f"MIN_MT_{category.upper()}_{opname.upper()}", category


def cmap_catalog():
    for category in CMAP_CATEGORIES:
        for cmap_name in cmap.Catalog().unique_keys(categories=[category], prefer_short_names=False):
            yield category, cmap_name.split(':')[0],  cmap_name.split(':')[1]

def draw_category_menus(self, context, op, opname):
    for category in CMAP_CATEGORIES:
        self.layout.menu(cmap_bl(category, opname=opname)[0], text=cmap_bl(category,opname=opname)[1].capitalize(), icon=CMAP_CATEGORIES[category])
    op_ = self.layout.operator(op, text="Single Color", icon="MESH_PLANE")
    op_.cmap_name = 'single_color'


CLASSES = []
for op, opname in [('microscopynodes.add_lut', "ADD"), ('microscopynodes.replace_lut', 'REPLACE')]:
    CLASSES = CLASSES + [cmap_submenu_class(op, opname, category) for category in CMAP_CATEGORIES]
    for category in CMAP_CATEGORIES:
        CLASSES.extend([cmap_submenu_class(op, opname, category, namespace) for namespace in cmap_namespaces(categories=category)])

