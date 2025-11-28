import bpy

from bpy.types import Panel, Menu

from vrage_tools.preferences import get_preferences

from .utilities.documentation_link import display_docu_link
from .assets.section_presets import section_presets

class VRT_PT_Panel(Panel):
    bl_idname = 'VRT_PT_Panel'
    bl_label = 'VRAGE Tools'
    bl_category = 'VRAGE'
    bl_space_type = 'VIEW_3D'
    bl_region_type = 'UI'
    bl_options = {'DEFAULT_CLOSED'}
    bl_order = 0

    @classmethod
    def poll(cls, context):
        return True

    def draw_header(self, context):
        layout = self.layout

    def draw(self, context):
        layout = self.layout

        preferences = get_preferences()
        if preferences.addon_needs_update:
            layout.label(text=preferences.addon_update_message, icon='ERROR')
            layout.separator()

        layout.operator('scene.vrt_relink_project_materials',text="Fix Project Materials", icon='MATERIAL')
        layout.operator("scene.vrt_clean_names", text="Clean Names", icon='SORTALPHA')

        layout.operator("wm.vrt_notification_display", icon='INFO')

class VRT_PT_Panel_subpanel_physics(Panel):
    bl_idname = 'VRT_PT_Panel_subpanel_physics'
    bl_label = "Physics"
    bl_parent_id = 'VRT_PT_Panel'
    bl_space_type = 'VIEW_3D'
    bl_region_type = 'UI'
    bl_options = {'DEFAULT_CLOSED'}
    bl_order = 0

    @classmethod
    def poll(cls, context):
        return True

    def draw_header(self, context):
        layout = self.layout

    def draw(self, context):
        layout = self.layout

        layout.operator('scene.vrt_export_collisions',                  text="Export Collisions",       icon='EXPORT')
        layout.separator()
        layout.operator("scene.vrt_add_rigid_body",                     text="Add Rigid Body",          icon='PHYSICS')
        layout.operator("object.vrt_convex_hull_from_selected",         text="Generate Convex Hull",    icon='MESH_ICOSPHERE')
        # layout.label(text="Fractures:")
        # layout.operator('scene.vrt_link_collisions_to_fracture',        text="Link Collisions",         icon='LINKED')
        # layout.operator('scene.vrt_unlink_fracture_collisions',         text="Unlink Collisions",       icon='UNLINKED')
        # layout.operator('scene.vrt_select_linked_fracture_collisions',  text="Select Linked",           icon='RESTRICT_SELECT_OFF')


class VRT_UL_fractures(bpy.types.UIList): # List item class

    def draw_item(self, context, layout, data, item, icon, active_data, active_propname):
        layout.alignment = 'LEFT'
        row = layout.row()
        row.alignment = 'EXPAND'
        # row.prop(item, "name", text="", emboss=False, icon='GROUP')
        row.label(text=item.name, icon='GROUP')

class VRT_PT_BlockProperties(Panel):
    bl_idname = 'VRT_PT_BlockProperties'
    bl_label = 'Block Properties'
    bl_category = 'VRAGE'
    bl_space_type = 'VIEW_3D'
    bl_region_type = 'UI'
    bl_options = {'DEFAULT_CLOSED'}
    bl_order = 1

    @classmethod
    def poll(cls, context):
        return True

    def draw_header(self, context):
        layout = self.layout

    def draw(self, context):
        layout = self.layout
        layout.prop(context.scene.vrt, "use_experimental_features")

        if context.scene.vrt.use_experimental_features and len(context.scene.vrt.fractures_list) > 0:
            box = layout.box()
            box.alert = True
            box.label(text="Scene contains Fractures", icon='ERROR')
            box.alert = False
            box.label(text="Using experimental features together")
            box.label(text="with Fractures will result in conflicting")
            box.label(text="object properties and Editor errors")

class VRT_PT_BlockProperties_subpanel_fractures(Panel):
    bl_idname = 'VRT_PT_BlockProperties_subpanel_fractures'
    bl_label = "Fractures"
    bl_parent_id = 'VRT_PT_BlockProperties'
    bl_space_type = 'VIEW_3D'
    bl_region_type = 'UI'
    bl_options = {'DEFAULT_CLOSED'}
    bl_order = 0

    @classmethod
    def poll(cls, context):
        return True

    def draw_header(self, context):
        layout = self.layout

    def draw(self, context):
        layout = self.layout

        layout.active = not context.scene.vrt.use_experimental_features
        
        # Fracture UI
        list_owner_path, list_prop_name = "scene.vrt.fractures_list".rsplit('.', 1)
        list_owner = context.path_resolve(list_owner_path)
        index_owner_path, index_prop_name = "scene.vrt.fractures_list_active_index".rsplit('.', 1)
        index_owner = context.path_resolve(index_owner_path)
        row = layout.row()
        row.template_list(
            "VRT_UL_fractures",
            "VRT_fractures_list",
            list_owner, list_prop_name,
            index_owner, index_prop_name,
        )
        col = row.column(align=True)
        col.operator("scene.vrt_fracture_add", icon='ADD', text="")
        col.operator("scene.vrt_fracture_remove", icon='REMOVE', text="")
        col.separator(factor=1.0)
        col.menu('VRT_MT_Menu_subpanel_fractures_more_options', text="", icon='DOWNARROW_HLT')

        # Draw fracture action buttons
        if len(context.scene.vrt.fractures_list) > 0:
            row = layout.row()
            row_left = row.row(align=True)
            row_right = row.row(align=True)

            row_left.operator("object.vrt_fracture_assign")
            row_left.operator("object.vrt_fracture_remove")

            row_right.operator("object.vrt_fracture_select")
            row_right.operator("object.vrt_fracture_deselect")

class VRT_MT_Menu_subpanel_fractures_more_options(Menu):
    bl_idname = 'VRT_MT_Menu_subpanel_fractures_more_options'
    bl_label = "More Options"

    def draw(self, context):
        layout = self.layout
        layout.operator("scene.vrt_fracture_repopulate_list", text="Repopulate List", icon='FILE_REFRESH')

class VRT_UL_sections(bpy.types.UIList): # List item class

    def draw_item(self, context, layout, data, item, icon, active_data, active_propname):
        layout.alignment = 'LEFT'
        row = layout.row()
        row.alignment = 'EXPAND'
        row.prop(item, "name", text="", emboss=False, icon='GROUP')

class VRT_PT_BlockProperties_subpanel_sections(Panel):
    bl_idname = 'VRT_PT_BlockProperties_subpanel_sections'
    bl_label = "Section Groups"
    bl_parent_id = 'VRT_PT_BlockProperties'
    bl_space_type = 'VIEW_3D'
    bl_region_type = 'UI'
    bl_options = {'DEFAULT_CLOSED'}
    bl_order = 1

    @classmethod
    def poll(cls, context):
        return True

    def draw_header(self, context):
        layout = self.layout

    def draw(self, context):
        list_owner_path, list_prop_name = "scene.vrt.sections_list".rsplit('.', 1)
        list_owner = context.path_resolve(list_owner_path)

        index_owner_path, index_prop_name = "scene.vrt.sections_list_active_index".rsplit('.', 1)
        index_owner = context.path_resolve(index_owner_path)

        layout = self.layout

        # Draw Collection list
        row = layout.row()
        row.template_list(
            "VRT_UL_sections",
            "VRT_sections_list",
            list_owner, list_prop_name,
            index_owner, index_prop_name,
        )
        # Draw Collection list buttons
        col = row.column(align=True)
        props = col.operator("scene.vrt_section_add", text="", icon='ADD')
        props = col.operator("scene.vrt_section_remove", text="", icon='REMOVE')
        col.separator(factor=1.0)
        col.menu('VRT_MT_Menu_subpanel_sections_more_options', text="", icon='DOWNARROW_HLT')

        # Draw Section action buttons
        if len(context.scene.vrt.sections_list) > 0:
            row = layout.row()
            row_left = row.row(align=True)
            row_right = row.row(align=True)

            row_left.operator("object.vrt_section_assign")
            row_left.operator("object.vrt_section_remove")

            row_right.operator("object.vrt_section_select")
            row_right.operator("object.vrt_section_deselect")

class VRT_MT_Menu_subpanel_sections_more_options(Menu):
    bl_idname = 'VRT_MT_Menu_subpanel_sections_more_options'
    bl_label = "More Options"

    def draw(self, context):
        layout = self.layout
        layout.operator("scene.vrt_section_repopulate_list", text="Repopulate List", icon='FILE_REFRESH')
        layout.separator()
        layout.menu('VRT_MT_Menu_subpanel_sections_add_preset', icon='ADD')

class VRT_MT_Menu_subpanel_sections_add_preset(Menu):
    bl_idname = 'VRT_MT_Menu_subpanel_sections_add_preset'
    bl_label = "Add Section Preset"

    def draw(self, context):
        layout = self.layout
        row = layout.row()
        for column in section_presets:
            col = row.column()
            for category in column:
                # draw category
                col.label(text = category)
                col.separator(type='LINE')
                # draw items
                for name in column[category]:
                    op = col.operator('scene.vrt_section_add_preset', text=name)
                    op.section_name = name
                col.separator(type='SPACE')



class VRT_PT_Materials(Panel):
    bl_idname = 'VRT_PT_Materials'
    bl_label = 'Materials'
    bl_category = 'VRAGE'
    bl_space_type = 'VIEW_3D'
    bl_region_type = 'UI'
    bl_options = {'DEFAULT_CLOSED'}
    bl_order = 3

    @classmethod
    def poll(cls, context):
        return True

    def draw_header(self, context):
        layout = self.layout

    def draw(self, context):
        layout = self.layout
        layout.use_property_split = True

        row = layout.row(heading='', align=False)
        row.use_property_split = True
        row.alignment = 'EXPAND'
        row.prop(context.scene.vrt, 'paint_color_ui', text='Paint Color')
        row.operator('scene.vrt_reset_paint_color', text='', icon='LOOP_BACK')

        layout.prop(context.scene.vrt, 'use_parallax_ui', text="Parallax")

class VRT_PT_Materials_subpanel_uv(Panel):

    bl_idname = 'VRT_PT_Materials_subpanel_uv'
    bl_label = ""
    bl_parent_id = 'VRT_PT_Materials'
    bl_space_type = 'VIEW_3D'
    bl_region_type = 'UI'
    bl_options = {'DEFAULT_CLOSED'}
    bl_order = 0

    @classmethod
    def poll(cls, context):
        return True

    def draw_header(self, context):
        layout = self.layout

        layout.prop(context.view_layer.vrt, 'use_uv_grid')

    def draw(self, context):
        layout = self.layout

        row = layout.row(align=False, heading="")
        # row.enabled = context.view_layer['VRT_use_uv_grid']

        row.prop(context.view_layer.vrt, 'use_color_grid')


class VRT_PT_Export(Panel):
    bl_idname = 'VRT_PT_Export'
    bl_label = 'Quick Export'
    bl_category = 'VRAGE'
    bl_space_type = 'VIEW_3D'
    bl_region_type = 'UI'
    bl_options = {'DEFAULT_CLOSED'}
    bl_order = 4

    def draw(self, context):
        layout = self.layout

        col = layout.column(align=True)
        col.alignment = 'EXPAND'
        col.prop(context.scene.vrt, "export_name", text="Name")
        col.separator()
        col.prop(context.scene.vrt, "export_directory", text="Directory")
        col.separator()
        col.prop(context.scene.vrt, "export_variant", text="Variant")

        layout.separator()
        layout.label(text="Quick Export:", icon='EXPORT')
        layout.prop(context.scene.vrt, "export_limit")
        grid = layout.grid_flow(row_major=True, columns=2, even_columns=True, even_rows=True, align=True)
        op = grid.operator('scene.vrt_quick_export', text="LOD 0"); op.export_lod = 0
        op = grid.operator('scene.vrt_quick_export', text="LOD 1"); op.export_lod = 1
        op = grid.operator('scene.vrt_quick_export', text="LOD 2"); op.export_lod = 2
        op = grid.operator('scene.vrt_quick_export', text="LOD 3"); op.export_lod = 3
        op = grid.operator('scene.vrt_quick_export', text="LOD 4"); op.export_lod = 4
        grid.operator('scene.vrt_quick_export_collisions', text="Collision")