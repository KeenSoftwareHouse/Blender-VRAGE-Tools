import bpy

from .utilities.easybpy import *
from .functions.fn_operators import *
from .functions.fn_ui import refresh_ui
from .preferences import get_preferences

from bpy.types import Context, Operator

class VRT_OT_DummyOperator(Operator):
    bl_idname = "scene.vrt_do_nothing"
    bl_label = "Do Nothing"
    bl_description = "This operator does nothing"
    bl_options = {'REGISTER', 'INTERNAL'}

    def execute(self, context):
        return {'FINISHED'}

class VRT_OT_ReLinkProjectMaterials(Operator):
    bl_idname = "scene.vrt_relink_project_materials"
    bl_label = "Re-link VRAGE Project Materials"
    bl_description = "Link materials from asset library, delete unused materials slots and purge unused data"

    @classmethod
    def poll(cls, context):
        cls.poll_message_set("Asset library not set in add-on preferences")
        prefs = get_preferences()
        invalid_lib_names = ("", "0", 0, "None", None) # don't know which one of these works but it's good enough
        return (not prefs.project_asset_lib in invalid_lib_names)

    def execute(self, context):
        op_fix_vrage_project_materials(self, context)
        return {'FINISHED'}

class VRT_OT_ResetPaintColor(Operator):
    bl_idname = "scene.vrt_reset_paint_color"
    bl_label = "Reset Paint Color"
    bl_description = "Reset VRAGE material paint color to Default"
    bl_options = {"REGISTER", "UNDO", "INTERNAL"}

    def execute(self, context):
        context.scene.vrt.paint_color_ui = (0.5, 0.5, 0.5)
        return {'FINISHED'}

class VRT_OT_CleanNames(Operator):
    bl_idname = "scene.vrt_clean_names"
    bl_label = "Clean Names"
    bl_description = "Clean names of selected objects, removing .001, etc. suffix"
    bl_options = {'REGISTER', 'UNDO'}

    def execute(self, context):
        objs = get_selected_objects()

        if len(objs) == 0:
            self.report({'WARNING'}, "Nothing selected")
            return {'CANCELLED'}

        clean_names(objs)

        return {'FINISHED'}

#region Collisions
class VRT_OT_AddRigidBody(Operator):
    bl_idname = "scene.vrt_add_rigid_body"
    bl_label = "Add Rigid Body"
    bl_description = "Add preset rigid body to selected objects"
    bl_options = {'REGISTER', 'UNDO'}

    def execute(self, context):
        objs = get_selected_objects()

        if len(objs) == 0:
            self.report({'WARNING'}, "Nothing selected")
            return {'CANCELLED'}

        for obj in objs:
            set_active_object(obj)

            # Add a rigid body physics type if not already present
            if not obj.rigid_body:
                bpy.ops.rigidbody.object_add()

            # Set the rigid body type to passive
            obj.rigid_body.type = 'PASSIVE'

        return {'FINISHED'}

class VRT_OT_ExportCollisions(Operator):
    bl_idname = "scene.vrt_export_collisions"
    bl_label = "Export Collisions"
    bl_description = "Apply scale to selected Objects and open exporter dialogue with preset settings"
    bl_options = {'REGISTER', 'UNDO'}

    @classmethod
    def poll(cls, context):
        is_object_mode = context.mode == 'OBJECT'

        poll_message = ""
        if not is_object_mode:
            poll_message = "Mode is not set to 'Object Mode'. "
        cls.poll_message_set(poll_message)
        return is_object_mode

    def execute(self, context):
        objs = get_selected_objects()
        # clean_names(objs) # remove duplicate suffixes

        # apply scale
        bpy.ops.object.transform_apply(
            location=False,
            rotation=False,
            scale=True,
            properties=True,
            isolate_users=True
            )

        # Invoke glTF export
        context.scene.msft_physics_exporter_props.enabled = True # Enable havok extention
        export_gltf_physics_invoke()
        return {'FINISHED'}

class VTR_OT_LinkCollisionsToFracture(Operator):
    bl_idname = "scene.vrt_link_collisions_to_fracture"
    bl_label = "Link Collisions to Fracture"
    bl_description = "Link selected colliders to active fracture object"
    bl_options = {'REGISTER', 'UNDO'}

    def execute(self, context):
        selected_objs = get_selected_objects()
        active_obj = get_active_object()

        if len(selected_objs) < 2:
            self.report({'WARNING'}, "Select two or more objects")
            return {'CANCELLED'}

        success = collision_custom_prop(self, context, selected_objs, active_obj)
        if not success:
            self.report({'ERROR'}, "Some colliders share the same base name. Colliders must each have a unique base name")
            return {'CANCELLED'}
        refresh_ui(self, context)
        self.report({'INFO'}, "Done")
        return {'FINISHED'}

class VTR_OT_SelectLinkedCollisions(Operator):
    bl_idname = "scene.vrt_select_linked_fracture_collisions"
    bl_label = "Select Linked Collisions"
    bl_description = "Select colliders that are linked to active fracture object"
    bl_options = {'REGISTER', 'UNDO'}

    def execute(self, context):
        obj = get_selected_objects()

        # check that 1 object is selected
        if not len(obj) == 1:
            self.report(type={'WARNING'}, message="Select one object")
            return {'CANCELLED'}
        obj = obj[0]

        # check that object has collision attribs
        if not 'group' in obj.keys():
            self.report(type={'WARNING'}, message="Object has no linked collisions")
            return {'CANCELLED'}

        deselect_all_objects()
        for coll in obj['group'].split("|"):
            # Find objects which share the same root name
            matching_objs = []
            for obj in context.view_layer.objects:
                # Name matches
                if obj.name == coll:
                    matching_objs.append(obj)
                # Name partially matches
                elif obj.name[:-4] == coll:
                    # make sure last 4 chars are duplicate suffix
                    if obj.name[-4] == "." and obj.name[-3:].isdigit():
                        matching_objs.append(obj)

            select_objects(matching_objs)
        return {'FINISHED'}

class VTR_OT_UnlinkCollisionsFractureCollisions(Operator):
    bl_idname = "scene.vrt_unlink_fracture_collisions"
    bl_label = "Unlink Collisions from Fracture"
    bl_description = "Unlink all colliders from active fracture object"
    bl_options = {'REGISTER', 'UNDO'}

    def execute(self, context):
        objs = get_selected_objects()
        for obj in objs:
            if 'group' in obj.keys():
                del obj['group']
            if 'ColliderMeshGroups' in obj.keys():
                del obj['ColliderMeshGroups']
        refresh_ui(self, context)
        return {'FINISHED'}

class VRT_OT_ConvexHullFromSelected(Operator):
    bl_idname = "object.vrt_convex_hull_from_selected"
    bl_label = "Generate Convex Hull from Selected"
    bl_description = (
                    "Generate a new object that is a convex hull of selected objects. \n"
                    + "Add a Rigid Body and Decimate, Displace modifiers to it"
                    )
    bl_options = {'REGISTER', 'UNDO'}

    @classmethod
    def poll(cls, context):
        cls.poll_message_set("No meshes selected")
        objs = context.selected_objects
        return len(objs) > 0 and 'MESH' in [o.type for o in objs]

    def execute(self, context):
        convex_hull_from_selected()
        return {'FINISHED'}

#endregion
#region Fractures
class VTR_OT_fracture_add(bpy.types.Operator):
    bl_idname = "scene.vrt_fracture_add"
    bl_label = "Add Fracture"
    bl_description = "Add a new fracture to the end of list"
    bl_options = {"REGISTER", "UNDO", "INTERNAL"}

    @classmethod
    def poll(cls, context):
        cls.poll_message_set("VRAGE 3 does not support more than 15 fractures per block")
        fractures = context.scene.vrt.fractures_list
        return len(fractures) < 15  # Engine maximum supported fractures

    def execute(self, context):
        scene = context.scene
        fractures = scene.vrt.fractures_list

        new_index = len(fractures) + 1
        new_fracture = fractures.add()
        new_fracture.name = f"Fracture {new_index}"
        new_fracture.group_id = f"fracture_{new_index:02d}"

        scene.vrt.fractures_list_active_index = len(fractures) - 1
        return {'FINISHED'}
    
    def invoke(self, context, _):
        return self.execute(context)

class VTR_OT_fracture_remove(bpy.types.Operator):
    bl_idname = "scene.vrt_fracture_remove"
    bl_label = "Remove Fracture"
    bl_description = "Remove the last fracture from the end of list"
    bl_options = {"REGISTER", "UNDO", "INTERNAL"}

    @classmethod
    def poll(cls, context):
        cls.poll_message_set("Scene has no fractures")
        fractures = context.scene.vrt.fractures_list
        return len(fractures) > 0

    def execute(self, context):
        scene = context.scene
        fractures = scene.vrt.fractures_list

        scene_objs = context.scene.objects
        for obj in scene_objs:
            if 'ColliderMeshGroups' in obj:
                if obj['ColliderMeshGroups'] == fractures[len(fractures) - 1].group_id:
                    del obj['ColliderMeshGroups']
            if 'group' in obj:
                if obj['group'] == fractures[len(fractures) - 1].group_id:
                    del obj['group']
            if 'FractureGroupName' in obj:
                if obj['FractureGroupName'] == fractures[len(fractures) - 1].group_id:
                    del obj['FractureGroupName']

        fractures.remove(len(fractures) - 1)
        scene.vrt.fractures_list_active_index = max(0, len(fractures) - 1)

        refresh_ui(self, context)
        return {'FINISHED'}

class VRT_OT_fracture_Assign(Operator):
    bl_idname = "object.vrt_fracture_assign"
    bl_label = "Assign"
    bl_description = "Assign the selected objects to the active fracture"
    bl_options = {"REGISTER", "UNDO", "INTERNAL"}

    def execute(self, context):
        fractures_list = bpy.context.scene.vrt.fractures_list
        active_fracture_index = bpy.context.scene.vrt.fractures_list_active_index

        if len(fractures_list) == 0:
            self.report({'WARNING'},message="No active fracture!")
            return {'CANCELLED'}

        objs = get_selected_objects()
        for obj in objs:
            obj['ColliderMeshGroups'] = fractures_list[active_fracture_index].group_id
            obj['group'] = fractures_list[active_fracture_index].group_id
            obj['FractureGroupName'] = fractures_list[active_fracture_index].group_id

        refresh_ui(self, context)
        return {'FINISHED'}
    
class VRT_OT_fracture_Remove(Operator):
    bl_idname = "object.vrt_fracture_remove"
    bl_label = "Remove"
    bl_description = "Remove the selected objects from the active fracture"
    bl_options = {"REGISTER", "UNDO", "INTERNAL"}

    def execute(self, context):
        fractures_list = bpy.context.scene.vrt.fractures_list
        active_fracture_index = bpy.context.scene.vrt.fractures_list_active_index

        objs = get_selected_objects()
        for obj in objs:
            if 'ColliderMeshGroups' in obj:
                if obj['ColliderMeshGroups'] == fractures_list[active_fracture_index].group_id:
                    del obj['ColliderMeshGroups']
            if 'group' in obj:
                if obj['group'] == fractures_list[active_fracture_index].group_id:
                    del obj['group']
            if 'FractureGroupName' in obj:
                if obj['FractureGroupName'] == fractures_list[active_fracture_index].group_id:
                    del obj['FractureGroupName']

        refresh_ui(self, context)
        return {'FINISHED'}

class VRT_OT_fracture_Select(Operator):
    bl_idname = "object.vrt_fracture_select"
    bl_label = "Select"
    bl_description = "Select all objects from the active fracture"
    bl_options = {"REGISTER", "UNDO", "INTERNAL"}

    def execute(self, context):
        fractures_list = bpy.context.scene.vrt.fractures_list
        active_fracture_index = bpy.context.scene.vrt.fractures_list_active_index

        objs = bpy.context.view_layer.objects
        for obj in objs:
            if 'ColliderMeshGroups' in obj:
                if obj['ColliderMeshGroups'] == fractures_list[active_fracture_index].group_id:
                    select_object(obj)
            elif 'group' in obj:
                if obj['group'] == fractures_list[active_fracture_index].group_id:
                    select_object(obj)
            elif 'FractureGroupName' in obj:
                if obj['FractureGroupName'] == fractures_list[active_fracture_index].group_id:
                    select_object(obj)

        return {'FINISHED'}

class VRT_OT_fracture_Deselect(Operator):
    bl_idname = "object.vrt_fracture_deselect"
    bl_label = "Deselect"
    bl_description = "Deselect all objects from the active fracture"
    bl_options = {"REGISTER", "UNDO", "INTERNAL"}

    def execute(self, context):
        fractures_list = bpy.context.scene.vrt.fractures_list
        active_fracture_index = bpy.context.scene.vrt.fractures_list_active_index

        objs = bpy.context.view_layer.objects
        for obj in objs:
            if 'ColliderMeshGroups' in obj:
                if obj['ColliderMeshGroups'] == fractures_list[active_fracture_index].group_id:
                    deselect_object(obj)
            elif 'group' in obj:
                if obj['group'] == fractures_list[active_fracture_index].group_id:
                    deselect_object(obj)
            elif 'FractureGroupName' in obj:
                if obj['FractureGroupName'] == fractures_list[active_fracture_index].group_id:
                    deselect_object(obj)

        return {'FINISHED'}

class VRT_OT_fracture_Repopulate_List(Operator):
    bl_idname = "scene.vrt_fracture_repopulate_list"
    bl_label = "Repopulate"
    bl_description = "Repopulate fractures list with existing scene items"
    bl_options = {"REGISTER", "UNDO"}

    def execute(self, context):
        fractures_list = context.scene.vrt.fractures_list
        fracture_ids = [a.group_id for a in fractures_list]
        scene_objs = context.scene.objects
        fracture_objects = []
        
        for obj in scene_objs:
            fracture_id = None
            if 'ColliderMeshGroups' in obj:
                fracture_id = obj['ColliderMeshGroups']
            elif 'group' in obj:
                fracture_id = obj['group']
            elif 'FractureGroupName' in obj:
                fracture_id = obj['FractureGroupName']
            else:
                continue
            if not fracture_id in fracture_ids:
                fracture_ids.append(fracture_id)
            fracture_objects.append(obj)

        if len(fracture_ids) > 15:
            self.report({'ERROR'}, message="Number of fractures in Scene exceeds 15. Re-assign fractures manually")
        n = min(len(fracture_ids), 15) - len(fractures_list)
        if n > 0:
            while n > 0:
                bpy.ops.scene.vrt_fracture_add('INVOKE_DEFAULT',)
                n -= 1
        
        has_non_standard_name = False
        for obj in fracture_objects:
            fracture_id = None
            if 'ColliderMeshGroups' in obj:
                fracture_id = obj['ColliderMeshGroups']
            elif 'group' in obj:
                fracture_id = obj['group']
            elif 'FractureGroupName' in obj:
                fracture_id = obj['FractureGroupName']
            number = str(fracture_id).replace("fracture_", "")
            if number.isdigit():
                if int(number) <= 15:
                    continue
            has_non_standard_name = True
        if has_non_standard_name:
            self.report({'ERROR'}, message="Some fracture group ids don't follow the 'fracture_01' format. Re-assign fractures manually")
        
        refresh_ui(self, context)
        return {'FINISHED'}
    
    def invoke(self, context, _):
        return self.execute(context)

#region Sections
class VRT_OT_section_add(Operator):
    bl_idname = "scene.vrt_section_add"
    bl_label = "Add Section"
    bl_description = "Add a new section group to the scene"
    bl_options = {"REGISTER", "UNDO", "INTERNAL"}

    def execute(self, context):
        my_list = context.scene.vrt.sections_list
        active_index = context.scene.vrt.sections_list_active_index

        to_index = min(len(my_list), active_index + 1)

        my_list.add()
        my_list.move(len(my_list) - 1, to_index)
        context.scene.vrt.sections_list_active_index = to_index

        refresh_ui(self, context)
        return {'FINISHED'}
    
class VRT_OT_section_add_preset(Operator):
    bl_idname = "scene.vrt_section_add_preset"
    bl_label = "Add Section preset"
    bl_description = "Add a new section group preset to the scene"
    bl_options = {"REGISTER", "UNDO", "INTERNAL"}

    section_name: bpy.props.StringProperty(name="Section") # type: ignore

    def execute(self, context):
        my_list = context.scene.vrt.sections_list
        active_index = context.scene.vrt.sections_list_active_index

        to_index = min(len(my_list), active_index + 1)

        my_list.add()
        my_list.move(len(my_list) - 1, to_index)
        context.scene.vrt.sections_list_active_index = to_index
        my_list[to_index].name = self.section_name

        refresh_ui(self, context)
        return {'FINISHED'}

class VRT_OT_section_remove(Operator):
    bl_idname = "scene.vrt_section_remove"
    bl_label = "Remove active Section"
    bl_description = "Delete the active section group from the scene"
    bl_options = {"REGISTER", "UNDO", "INTERNAL"}

    @classmethod
    def poll(cls, context):
        cls.poll_message_set('Scene has no section groups')
        return len(context.scene.vrt.sections_list) > 0

    def execute(self, context):
        my_list = context.scene.vrt.sections_list
        active_index = context.scene.vrt.sections_list_active_index

        section_name = my_list[active_index].name

        my_list.remove(active_index)
        to_index = min(active_index, len(my_list) - 1)
        context.scene.vrt.sections_list_active_index = to_index

        # If given section name is no longer in sections list
        if not section_name in [s.name for s in my_list]:
            scene_objs = context.scene.objects
            for obj in scene_objs:
                if not 'SECTION' in obj:
                    continue
                if obj['SECTION'] == section_name:
                    del obj['SECTION']

        refresh_ui(self, context)
        return {'FINISHED'}

class VRT_OT_Section_Assign(Operator):
    bl_idname = "object.vrt_section_assign"
    bl_label = "Assign"
    bl_description = "Assign the selected objects to the active section group"
    bl_options = {"REGISTER", "UNDO", "INTERNAL"}

    def execute(self, context):
        sections_list = bpy.context.scene.vrt.sections_list
        active_section_index = bpy.context.scene.vrt.sections_list_active_index

        if len(sections_list) == 0:
            self.report({'WARNING'},message="No active section group!")
            return {'CANCELLED'}

        objs = get_selected_objects()
        for obj in objs:
            obj['SECTION'] = sections_list[active_section_index].name

        refresh_ui(self, context)
        return {'FINISHED'}

class VRT_OT_Section_Remove(Operator):
    bl_idname = "object.vrt_section_remove"
    bl_label = "Remove"
    bl_description = "Remove the selected objects from the active section group"
    bl_options = {"REGISTER", "UNDO", "INTERNAL"}

    def execute(self, context):
        sections_list = bpy.context.scene.vrt.sections_list
        active_section_index = bpy.context.scene.vrt.sections_list_active_index

        objs = get_selected_objects()
        for obj in objs:
            if not 'SECTION' in obj:
                continue
            if obj['SECTION'] == sections_list[active_section_index].name:
                del obj['SECTION']

        refresh_ui(self, context)
        return {'FINISHED'}

class VRT_OT_Section_Select(Operator):
    bl_idname = "object.vrt_section_select"
    bl_label = "Select"
    bl_description = "Select all objects from the active section group"
    bl_options = {"REGISTER", "UNDO", "INTERNAL"}

    def execute(self, context):
        sections_list = bpy.context.scene.vrt.sections_list
        active_section_index = bpy.context.scene.vrt.sections_list_active_index

        objs = bpy.context.view_layer.objects
        for obj in objs:
            if not 'SECTION' in obj:
                continue
            if obj['SECTION'] == sections_list[active_section_index].name:
                select_object(obj)

        return {'FINISHED'}

class VRT_OT_Section_Deselect(Operator):
    bl_idname = "object.vrt_section_deselect"
    bl_label = "Deselect"
    bl_description = "Deselect all objects from the active section group"
    bl_options = {"REGISTER", "UNDO", "INTERNAL"}

    def execute(self, context):
        sections_list = bpy.context.scene.vrt.sections_list
        active_section_index = bpy.context.scene.vrt.sections_list_active_index

        objs = bpy.context.view_layer.objects
        for obj in objs:
            if not 'SECTION' in obj:
                continue
            if obj['SECTION'] == sections_list[active_section_index].name:
                deselect_object(obj)

        return {'FINISHED'}

class VRT_OT_Section_Repopulate_List(Operator):
    bl_idname = "scene.vrt_section_repopulate_list"
    bl_label = "Repopulate"
    bl_description = "Repopulate sections list with existing scene items"
    bl_options = {"REGISTER", "UNDO"}

    def execute(self, context):
        sections_list = context.scene.vrt.sections_list
        section_names = [a.name for a in sections_list]
        scene_objs = context.scene.objects
        
        for obj in scene_objs:
            if not 'SECTION' in obj:
                continue
            section_name = obj['SECTION']
            if section_name in section_names:
                continue
            sections_list.add()
            sections_list[-1].name = section_name
            sections_list = context.scene.vrt.sections_list
            section_names = [a.name for a in sections_list]
        
        refresh_ui(self, context)
        return {'FINISHED'}
    
    def invoke(self, context, _):
        return self.execute(context)

#endregion
#region Quick Export
class VRT_OT_QuickExport(Operator):
    bl_idname = "scene.vrt_quick_export"
    bl_label = "Quick Export"
    bl_description = "Export selected objects as this LOD directly into its variant folder under selected directory"
    bl_options = {'REGISTER', 'INTERNAL'}

    export_lod: bpy.props.IntProperty(name="LOD") # type: ignore

    @classmethod
    def poll(cls, context):
        name_set = bool(context.scene.vrt.export_name) # name not ""
        dir_set = bool(context.scene.vrt.export_directory) # path not ""
        if dir_set: # if path is not empty string, check that it's valid
            dir_set = os.path.exists(context.scene.vrt.export_directory)

        if not name_set:
            cls.poll_message_set("Model name not set")
        if not dir_set:
            cls.poll_message_set("Export directory is not valid")
        if not name_set and not dir_set:
            cls.poll_message_set("Model name and export directory is not valid")

        return name_set*dir_set

    # ivoke a confirmation popup
    def invoke(self, context, event):
        return context.window_manager.invoke_confirm(self, event)

    def execute(self, context):
        match context.scene.vrt.export_limit:
            case 'SELECTED_OBJECTS':
                if not get_selected_objects():
                    self.report(type={'WARNING'}, message="Select one or more objects")
                    return {'CANCELLED'}
            case 'ACTIVE_COLLECTION':
                if len(context.collection.all_objects) == 0:
                    self.report(type={'WARNING'}, message="Active collection is empty")
                    return {'CANCELLED'}
            case 'VISIBLE_OBJECTS':
                if len(context.visible_objects) == 0:
                    self.report(type={'WARNING'}, message="No objects visible")
                    return {'CANCELLED'}


        name = context.scene.vrt.export_name
        dir = context.scene.vrt.export_directory
        var = context.scene.vrt.export_variant
        lod = self.export_lod

        filename = f"{name}{get_export_variant_suffix(var)}{get_export_lod_suffix(lod)}"
        filepath = os.path.join(dir, f"{filename}.fbx") # set path to root dir

        if not var == 'NONE': # if a variant is selected
            subdir = get_export_variant_dir(var)
            os.makedirs(name=os.path.join(dir, subdir), exist_ok=True)
            filepath = os.path.join(dir, subdir, f"{filename}.fbx") # overwrite path to include subdir

        export_fbx_quick(filepath)
        self.report({'INFO'}, "Done")
        return {'FINISHED'}

class VRT_OT_QuickExportCollisions(Operator):
    bl_idname = "scene.vrt_quick_export_collisions"
    bl_label = "Export Collisions"
    bl_description = "Apply scale to selected Objects and export selected objects directly into its variant folder under selected directory"
    bl_options = {'REGISTER', 'UNDO'}

    @classmethod
    def poll(cls, context):
        name_set = bool(context.scene.vrt.export_name) # name not ""
        dir_set = bool(context.scene.vrt.export_directory) # path not ""
        if dir_set: # if path is not empty string, check that it's valid
            dir_set = os.path.exists(context.scene.vrt.export_directory)
        physics_installed = True #('MSFT_Physics' in context.preferences.addons.keys())
        is_object_mode = context.mode == 'OBJECT'

        poll_message = ""
        if not name_set:
            poll_message += "Model name not set. "
        if not dir_set:
            poll_message += "Export directory is not valid. "
        if not physics_installed:
            poll_message += "MSFT_Physics module not installed. "
        if not is_object_mode:
            poll_message += "Mode is not set to 'Object Mode'. "
        cls.poll_message_set(poll_message)

        return name_set*dir_set*physics_installed*is_object_mode

    # ivoke a confirmation popup
    def invoke(self, context, event):
        return context.window_manager.invoke_confirm(self, event)

    def execute(self, context):
        objs = None
        match context.scene.vrt.export_limit:
            case 'SELECTED_OBJECTS':
                objs = get_selected_objects()
                if not objs:
                    self.report(type={'WARNING'}, message="Select one or more objects")
                    return {'CANCELLED'}
            case 'ACTIVE_COLLECTION':
                objs = context.collection.all_objects
                if len(objs) == 0:
                    self.report(type={'WARNING'}, message="Active collection is empty")
                    return {'CANCELLED'}
            case 'VISIBLE_OBJECTS':
                objs = context.visible_objects
                if len(objs) == 0:
                    self.report(type={'WARNING'}, message="No objects visible")
                    return {'CANCELLED'}

        deselect_all_objects()
        for obj in objs:
            try:
                select_object(obj)
            except:
                pass
        # apply scale
        bpy.ops.object.transform_apply(
            location=False,
            rotation=False,
            scale=True,
            properties=True,
            isolate_users=True
            )
        bpy.ops.object.origin_set(type='ORIGIN_GEOMETRY')

        # Invoke glTF export
        context.scene.msft_physics_exporter_props.enabled = True # Enable havok extention

        name = context.scene.vrt.export_name
        dir = context.scene.vrt.export_directory
        var = context.scene.vrt.export_variant

        filename = f"{name}{get_export_variant_suffix(var)}"
        filepath = os.path.join(dir, f"{filename}_collision") # set path to root dir

        if not var == 'NONE': # if a variant is selected
            subdir = get_export_variant_dir(var)
            os.makedirs(name=os.path.join(dir, subdir), exist_ok=True)
            filepath = os.path.join(dir, subdir, f"{filename}_collision") # overwrite path to include subdir

        export_gltf_physics_quick(filepath)
        self.report({'INFO'}, "Done")
        return {'FINISHED'}
#endregion