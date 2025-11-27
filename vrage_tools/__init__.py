'''
VRAGE Tools, Copyright 2025,
Keen Software House s.r.o., Na Petynce 213/23b, Břevnov, 169 00 Praha 6, Czech Republic, Company number: 05264561

Licensed under the Apache License, Version 2.0 (the "License");
you may not use this file except in compliance with the License.
You may obtain a copy of the License at

http://www.apache.org/licenses/LICENSE-2.0

Unless required by applicable law or agreed to in writing, software
(VRAGE Tools) distributed under the License is distributed on an "AS IS" BASIS,
WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
See the License for the specific language governing permissions and
limitations under the License.
'''

bl_info = {
    "name" : "VRAGE Tools",
    "author" : "Keen Software House",
    "description" : "A Blender Add-on to streamline and simplify the creation of 3D assets for Space Engineers 2",
    "blender" : (4, 3, 0),
    "version" : (0, 3, 0),
    "location" : "",
    "warning" : "",
    "category" : "Generic"
}

#region Imports

import bpy
from bpy.app.handlers import persistent

# TODO: We should explicitly import classes instead of wildcards, once we implement everything we need to.
from .operators                     import *
from .preferences                   import *
from .ui                            import *

from .scene.scene                   import *
from .view_layer.view_layer         import *
from .text.text                     import *
from .utilities.documentation_link  import *
from .utilities.notifications       import *
from .utilities.update_check        import *

from .utilities.MSFT_Physics        import MSFT_Physics_register, MSFT_Physics_unregister

# Construction Tool - temporary implementation
from .tmp_construction_stages_tool  import (
	ConstructionPropertySettings,
	OBJECT_PT_construction_panel,
	OBJECT_OT_apply_selected_properties,
	OBJECT_OT_detach_materials,
	OBJECT_OT_select_objects_by_name,
	OBJECT_OT_SetFractureGroupDefault,
	OBJECT_OT_SetFractureGroupHide,
	OBJECT_OT_SetFractureGroupSupport,
	OBJECT_OT_SetFractureGroupFrameCut,
	OBJECT_OT_SetColliderMeshGroups
 )

classes = (
    VRT_AddonPreferences,

    VRT_Section,
    VRT_Fracture,
    VRT_Scene,
    VRT_ViewLayer,
    VRT_Notification,
    VRT_Text,

    VRT_PT_Panel,
    VRT_PT_Panel_subpanel_physics,
    VRT_PT_BlockProperties,
    VRT_UL_fractures,
    VRT_PT_BlockProperties_subpanel_fractures,
    VRT_MT_Menu_subpanel_fractures_more_options,
    VRT_UL_sections,
    VRT_PT_BlockProperties_subpanel_sections,
    VRT_MT_Menu_subpanel_sections_more_options,
    VRT_MT_Menu_subpanel_sections_add_preset,
    VRT_PT_Materials,
    VRT_PT_Export,

    VRT_OT_DummyOperator,
    VRT_OT_ReLinkProjectMaterials,
    VRT_OT_ResetPaintColor,
    VRT_OT_CleanNames,
    VRT_OT_AddRigidBody,
    VRT_OT_ExportCollisions,
    VTR_OT_LinkCollisionsToFracture,
    VTR_OT_SelectLinkedCollisions,
    VTR_OT_UnlinkCollisionsFractureCollisions,
    VRT_OT_ConvexHullFromSelected,
    VTR_OT_fracture_add,
    VTR_OT_fracture_remove,
    VRT_OT_fracture_Assign,
    VRT_OT_fracture_Remove,
    VRT_OT_fracture_Select,
    VRT_OT_fracture_Deselect,
    VRT_OT_fracture_Repopulate_List,
    VRT_OT_section_add,
    VRT_OT_section_add_preset,
    VRT_OT_section_remove,
    VRT_OT_Section_Assign,
    VRT_OT_Section_Remove,
    VRT_OT_Section_Select,
    VRT_OT_Section_Deselect,
    VRT_OT_Section_Repopulate_List,
    VRT_OT_QuickExport,
    VRT_OT_QuickExportCollisions,
    VRT_OT_DocuLink,
    VRT_OT_NotificationDisplay,
    VRT_OT_DeleteNotification,
    VRT_OT_ClearnNotification,

    VRT_OT_GetCurrentVersion,
    VRT_OT_CheckUpdate,
    
    # Construction Tool - temporary implementation
    ConstructionPropertySettings,
	OBJECT_PT_construction_panel,
	OBJECT_OT_apply_selected_properties,
	OBJECT_OT_detach_materials,
	OBJECT_OT_select_objects_by_name,
	OBJECT_OT_SetFractureGroupDefault,
	OBJECT_OT_SetFractureGroupHide,
	OBJECT_OT_SetFractureGroupSupport,
	OBJECT_OT_SetFractureGroupFrameCut,
	OBJECT_OT_SetColliderMeshGroups
)

#region (Un)Register

def register():

    for cls in classes:
        bpy.utils.register_class(cls)

    bpy.types.Scene.vrt = bpy.props.PointerProperty(type=VRT_Scene)
    bpy.types.ViewLayer.vrt = bpy.props.PointerProperty(type=VRT_ViewLayer)
    bpy.types.Text.vrt = bpy.props.PointerProperty(type=VRT_Text)

    MSFT_Physics_register()

    bpy.app.handlers.load_post.append(file_load_handler)
    
    # Construction Tool - temporary implementation
    bpy.types.Scene.construction_props = bpy.props.PointerProperty(type=ConstructionPropertySettings)

def unregister():
    # Construction Tool - temporary implementation
    del bpy.types.Scene.construction_props

    MSFT_Physics_unregister()

    del bpy.types.Text.vrt
    del bpy.types.ViewLayer.vrt
    del bpy.types.Scene.vrt

    for cls in reversed(classes):
        bpy.utils.unregister_class(cls)

    bpy.app.handlers.load_post.remove(file_load_handler)

# We need to wait until we create the gltf2UserExtension to import the gltf2 modules
# Otherwise, it may fail because the gltf2 may not be loaded yet
from .utilities.MSFT_Physics import glTF2ImportUserExtension, glTF2ExportUserExtension


#region Event Handlers

@persistent
def file_load_handler(dummy):
    bpy.ops.scene.vrt_section_repopulate_list('INVOKE_DEFAULT',)
    bpy.context.scene.msft_physics_exporter_props.enabled = False # Disable havok extension. It can mess with glTF imports

    bpy.ops.wm.vrt_check_update('INVOKE_DEFAULT')