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

def cmap_submenu_class(category, namespace=None):

    def draw(self, context):
        if self.namespace is None:
            for namespace in cmap_namespaces(self.category):
                self.layout.menu(cmap_bl(self.category, namespace)[0], text=cmap_bl(category, namespace)[1])
        else:
            for cmap in cmaps(self.category, self.namespace):
                op_ = self.layout.operator( "microscopynodes.add_lut", text=cmap)
                op_.cmap_name = cmap
#            menu_items.get_submenu("utils").menu(self.layout, context)
    
    cls_elements = {
            'bl_idname': cmap_bl(category, namespace)[0],
            'bl_label': cmap_bl(category, namespace)[1],
            'category' : category,
            'namespace' : namespace,
            'draw' : draw
        }

    # Dynamically create classes for cmap submenus
    menu_class = type(
        cmap_bl(category, namespace)[0], 
        (bpy.types.Menu,),  
        cls_elements
    )
    return menu_class

def cmap_namespaces(categories):
    return list({cmap_name.split(':')[0] for cmap_name in cmap.Catalog().unique_keys(categories=categories, prefer_short_names=False)})

def cmaps(category, namespace):
    return list({cmap_name.split(':')[1] for cmap_name in cmap.Catalog().unique_keys(categories=[category], prefer_short_names=False) if cmap_name.split(':')[0] == namespace})


def cmap_bl(category, namespace=None, name=None):
    # Returns bl_idname, bl_label
    if name is not None: 
        return f"MIN_MT_{category.upper()}_{namespace.upper()}_{name.upper()}", name
    if namespace is not None: 
        return f"MIN_MT_{category.upper()}_{namespace.upper()}", namespace
    return f"MIN_MT_{category.upper()}", category


def cmap_catalog():
    for category in CMAP_CATEGORIES:
        for cmap_name in cmap.Catalog().unique_keys(categories=[category], prefer_short_names=False):
            yield category, cmap_name.split(':')[0],  cmap_name.split(':')[1]

def draw_category_menus(self, context, op):
    for category in CMAP_CATEGORIES:
        self.layout.menu(cmap_bl(category)[0], text=cmap_bl(category)[1].capitalize(), icon=CMAP_CATEGORIES[category])
    self.layout.operator(op, text="Single Color", icon="MESH_PLANE")
    self.layout.operator(op, text="From Fiji LUT...", icon="FILE")



CLASSES = [cmap_submenu_class(category) for category in CMAP_CATEGORIES]
for category in CMAP_CATEGORIES:
    CLASSES.extend([cmap_submenu_class(category, namespace) for namespace in cmap_namespaces(categories=category)])


def register():
    bpy.types.NODE_MT_add.append(MIN_add_shader_node_menu)
    for op in CLASSES:
        try:
            bpy.utils.register_class(op)
        except Exception as e:
            print(op, e)
            pass

if __name__ == "__main__":
    register()
    

    # The menu can also be called from scripts
#    bpy.ops.wm.call_menu(name="MIN_MT_CMAPS")
