import bpy
import mathutils
import os

from bpy.types      import PropertyGroup
from bpy.props      import (EnumProperty,
                            FloatProperty,
                            FloatVectorProperty,
                            IntProperty,
                            StringProperty,
                            BoolProperty,
                            PointerProperty,
                            CollectionProperty)


from ..utilities.notifications  import display_notification

# Update functions
def update_paint_color_ui(self, context):
    updated_color = context.scene.vrt.paint_color_ui
    context.view_layer['VRT_paint_color'] = tuple(mathutils.Vector(updated_color) - mathutils.Vector((0.5, 0.5, 0.5)))


def update_use_parallax_ui(self, context):
     use_parallax = context.scene.vrt.use_parallax_ui
     context.view_layer['VRT_disable_parallax'] = bool(not use_parallax)

def update_export_path_ui(self, context):
    if context.scene.vrt.export_directory != os.path.abspath(context.scene.vrt.export_directory):
        context.scene.vrt.export_directory = os.path.abspath(context.scene.vrt.export_directory)


# Collection properties
class VRT_Section(PropertyGroup):
    """Holder for VRT section properties"""
    def get_name(self):
        return self.get("name", "Section")

    def set_name(self, value):
        oldname = self.get("name", "Section")
        scene_objs = bpy.context.scene.objects
        for obj in scene_objs:
            if not 'SECTION' in obj:
                continue
            if obj['SECTION'] == oldname:
                obj['SECTION'] = value
        self["name"] = value

    name: StringProperty(
        default="Section",
        get=get_name,
        set=set_name
    ) # type: ignore

class VRT_Fracture(PropertyGroup):
    """Holder for VRT fracture properties"""

    name: StringProperty(
        name="Name",
        default="Fracture 1"
    ) # type: ignore
    group_id: StringProperty(
        name="Group ID",
        default="fracture_01"
    ) # type: ignore


# Main class
class VRT_Scene(PropertyGroup):
    """Holder for VRT Scene properties"""

    version: IntProperty(
        default=1
    ) # type: ignore
    
    paint_color_ui: FloatVectorProperty(
        name='Paint Color',
        description="Change display color of colorable VRAGE materials",
        size=3,
        default=(0.5, 0.5, 0.5),
        subtype='COLOR',
        soft_min=0.0,
        soft_max=1.0,
        step=3,
        precision=6,
        update=update_paint_color_ui
        ) # type: ignore

    use_parallax_ui: BoolProperty(
        name="Toggle Parallax",
        description="Enable VRAGE material parallax occlusion mapping",
        default=True,
        update=update_use_parallax_ui
    ) # type: ignore

    fractures_list: CollectionProperty(
        type=VRT_Fracture
        ) # type: ignore

    fractures_list_active_index: IntProperty() # type: ignore

    sections_list: CollectionProperty(
        type=VRT_Section
        ) # type: ignore

    sections_list_active_index: IntProperty() # type: ignore

    export_name: StringProperty(
        name="Block Base Name",
        description='Base name of block to export (e.g. "CargoContainer")'
    ) # type: ignore

    export_directory: StringProperty(
        name="Quick Export Directory",
        description='Root directory for exporting model. (parent directory of "NonFractured", "Fractured"...)',
        subtype='DIR_PATH',
        update = update_export_path_ui
    ) # type: ignore

    export_variant: EnumProperty(
        items=[
            ('NON_FRACTURED', "Non-fractured", "Export as undamaged, base variant"),
            ('FRACTURED', "Fractured", "Export as fractured variant"),
            ('DEFORMED', "Deformed", "Export as deformed fractured variant"),
            ('NONE', "None", "Export directly into selected directory, without variant suffix")
            ],
        name="Export Variant",
        description="Variant of the block to export. Selects subdirectory in root directory"
    ) # type: ignore

    export_limit: EnumProperty(
        items=[
            ('SELECTED_OBJECTS', "Selected Objets", "Export only selected objects"),
            ('ACTIVE_COLLECTION', "Active Collection", "Export only the currently active collection"),
            ('VISIBLE_OBJECTS', "Visible Objets", "Export all visible objects") 
        ],
        name="Limit to",
        description="Limit which objects to export"
    ) # type: ignore