# 1. First Use

## **Installing Microscopy Nodes**

{{ youtube("BFMX0Dk5rIw", 360, 200) }}

1. Open Blender.
2. Navigate to `Edit > Preferences`.
3. In the Add-ons tab, search for `Microscopy Nodes`.
4. Click **Install** to download and enable the add-on.


## **Blender Interface Overview**
The Blender interface is very flexible and can be reconfigured in many ways. While this is a powerful feature, it also means that explaining the basics can be a bit technical, and some of the terms are Blender **jargon**. To make things easier, here is a quick overview of some **key terms** and where to find common functions.

Further information and navigation can be found in the {{ svg("Blender") }} [Blender Manual](https://docs.blender.org/manual/en/latest/editors/3dview/navigate/index.html)

![alt text](../figures/tutorials/Fig1.png)

The Blender interface always contains: 

1. {{ svg("topbar") }}	**Top bar**: contains the main menus and selection of the tabs, or  {{ svg("workspace") }} workspaces (e.g. Layout, Shading, Geometry Nodes).
2. {{ svg("workspace") }} **Workspace**: Reconfigurable workspace. Contains different areas depending on the selection in the  {{ svg("topbar") }} topbar.
3. {{ svg("statusbar") }} **Status bar**: contains shortcuts suggestions

But it can be configured much more with **workspaces** {{ svg("workspace") }}. Currently we're in the **Layout** workspace.

## Layout Workspace 

The **Layout** workspace {{ svg("workspace") }}  (by default selected in the {{ svg("topbar") }} *topbar*) is our main workspace, made for assembling and seeing your 3D scene. This contains multiple elements with Blender-specific names:

![alt text](<../figures/tutorials/Fig 2.png>)

1. {{ svg("view3d") }} **3D Viewport**: Main 3D interaction area. 
1. {{ svg("outliner") }} **Outliner**: Tree view of all objects in the *scene*. This is the easiest place to *select* objects.
2. {{ svg("properties") }} **Properties Editor**: Edit properties of the scene and the selected object. Under {{ svg("scene_data") }} you can find *Microscopy Nodes*.
3. {{ svg("time") }} **Timeline**: For animation.

With Microscopy Nodes, we also use the [Shading]() workspace, and for advanced users, the [Geometry Nodes]() and [Scripting]() workspaces.

## The 3D Viewport

Annotated on the right in the image are widgets you can drag to **rotate** (axes), {{ svg("view_zoom") }} **scale** and {{ svg("view_pan") }} **move** the view.

Mouse navigation is possible and configurable in the {{ svg("blender") }} [Preferences](https://docs.blender.org/manual/en/latest/editors/preferences/input.html). This depends on which input device you use (2-button mouse, 3-button mouse, touchpad).

### The `View` menu
 
![alt text](../figures/view3d_viewmenu.png){: style="height:200px"}

At the top of the {{ svg("view3d") }} 3D viewport, there is a dropdown menu called `View` - this has shortcuts and other tools to align the view. 

For example, if you lose all the objects in the scene, you can select an object in the {{ svg("outliner") }} outliner in the top right, and use the menu `View > Frame Selected` (or just `View > Frame All`) to see your scene again.

## The outliner

![alt text](../figures/outliner.png)

The {{ svg("outliner") }} outliner lists all {{ svg("outliner_collection") }} collections and objects in the scene. Here you can **select** objects more easily.

This also provides an interface for **visibility** in the {{ svg("hide_off") }}/{{ svg("hide_on") }} 3D viewport, and in the {{ svg("restrict_render_off") }}/{{ svg("restrict_render_on") }} final render. If objects are not visible, they are also not loaded into RAM, so it can speed up Blender to limit visibility.

## Manipulating Objects

Annotated on the left in the image are widgets you can drag to **select**, **move**, **rotate** and **scale** objects. The transform widgets spawn a *gizmo*: a mouse-clickable interaction interface:
![transform gizmos](<../figures/tutorials/Screenshot 2025-07-02 at 15.55.29.png>)

Transforms can also be done with hotkeys: `G` for grab/move, `R` for rotate, `S` for scale. The transformation can be locked to an axis with the `X`, `Y` or`Z` key.

### Adding an object

At the top of the 3D viewport is an `Add` menu, from which you can add different primitive objects, such as a camera or lights. This is also findable under the key combination `Shift + A`

To add microscopy data, there is a [separate loading window](./2_loading_data.md).

### Deleting objects

You can select any object in the {{ svg("view3d") }} viewport or {{ svg("outliner") }} outliner, and delete it by `Right Mouse Button > Delete Object` or pressing `X` and confirming.

For deleting all objects in the scene, it is fastest to press `A` to select all objects and `X` to delete them. 

In the {{ svg("outliner") }} **outliner**, an entire group can be deleted at once with  `Right Mouse Button > Delete Hierarchy`


## **Viewport rendering**

In the top right of the viewport you can change the way the contents are shown. 

{{ svg("microscopy_nodes") }} Microscopy Nodes volume data will only be visible in **Material Preview** and **Rendered** mode.

![alt text](../figures/tutorials/editors_3dview_display_shading.png)

From left to right:

1.	{{ svg("shading_wire") }} **Wireframe** : Only the object skeleton, *No volumetric data shown.*
2.	{{ svg("shading_solid") }} **Solid Mode**: Only the external surfaces are drawn 
3.	{{ svg("shading_texture") }} **Material Preview**: Is meant for previewing your scene without full calculations. Defaults to [EEVEE](./rendering.md#eevee). May be a fast view, but will be slow to open with microscopy data, and is data-dependent. 
4.	{{ svg("shading_rendered") }} **Rendered**: Shows the scene as it will appear in the final render. By default, Microscopy Nodes sets this to be in [Cycles](./rendering.md#cycles). Often the best way to view microscopy data.

## **Further UI instruction (video)** 

<div class="yt-lazy" data-id="enTid4aDC0Q" style="width:560px; height:315px;">
  <div class="yt-thumbnail" style="background-image: url('https://img.youtube.com/vi/enTid4aDC0Q/hqdefault.jpg');">
    <div class="yt-play-button"></div>
    <div class="yt-overlay-text">
      Click to load video from YouTube.
      <br />
      By clicking, you agree to YouTube’s privacy policy.
    </div>
  </div>
</div>