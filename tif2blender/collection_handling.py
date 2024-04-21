import bpy

def get_collection(name, supercollections=[], duplicate=False, under_active_coll=False):
    # duplicate is not duplicated-name-safe, so intention is to have types of names with/without duplication (programmer's choice)
    coll = bpy.context.scene.collection
    lcoll = bpy.context.view_layer.layer_collection
    for ix, scoll in enumerate(supercollections):
        coll = coll.children.get(scoll)
        lcoll = lcoll.children[scoll]
    if under_active_coll:
        coll = bpy.context.collection
        lcoll = bpy.context.view_layer.active_layer_collection
    newcoll = coll.children.get(name)
    if duplicate or newcoll is None:
        newcoll = bpy.data.collections.new(name)
        coll.children.link(newcoll)
        name = newcoll.name
    lcoll = lcoll.children[name]
    return newcoll, lcoll

def collection_by_name(name, supercollections=[], duplicate=False):
    coll, lcoll = get_collection(name, supercollections, duplicate, under_active_coll=False)
    collection_activate(coll, lcoll)
    return coll, lcoll

def get_current_collection():
    return bpy.context.collection, bpy.context.view_layer.active_layer_collection

def make_subcollection(name):
    coll, lcoll = get_collection(name, supercollections=[], duplicate=False, under_active_coll=True)
    collection_activate(coll, lcoll)
    return coll, lcoll

def collection_deactivate(name, supercollections=[]):
    coll, lcoll = get_collection(name, supercollections, False)
    lcoll.exclude = True
    coll.hide_render = True
    lcoll.hide_viewport = True
    return coll, lcoll

def collection_activate(coll, lcoll):
    bpy.context.view_layer.active_layer_collection = lcoll
    lcoll.exclude = False
    coll.hide_render = False
    lcoll.hide_viewport = False
