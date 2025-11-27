import bpy
import re

# Material names
cut_material = "FracturedMaterial01"
glass_material = "WindowGlass"
grate_material = "GratingMetallic"
decal_materials = {
	"AtlasDecal_Trims01", "AtlasDecal_Trims02", "AtlasDecal_Trims03",
	"AtlasButton01", "AtlasDecal_Parts01", "AtlasDecal_Parts02",
	"AtlasDecal_Stickers01", "AtlasDecal_Stickers02", "AtlasFont_BarlowCondensed"
}

suffix_to_preset = {
	"cut": "FractureCut",
	"glass": "Glass",
	"hide": "Hide",
	"grate": "GratingMetallic",
	"support": "Support",
	"window": "Glass",
	"switch": None,
	"switchhide": "Hide",
	"conveyor": "Conveyor",
}

def get_all_mesh_children(obj):
	children = []
	def recurse(current):
		for child in current.children:
			if child.type == 'MESH':
				children.append(child)
			recurse(child)
	recurse(obj)
	return children

def select_faces_by_material(obj, material_names):
    mesh = obj.data
    bpy.ops.object.mode_set(mode='OBJECT')

    # deselect everything first
    for poly in mesh.polygons:
        poly.select = False

    # select only the right material faces
    for poly in mesh.polygons:
        mat_index = poly.material_index
        if mat_index < len(mesh.materials):
            mat_name = mesh.materials[mat_index].name
            if mat_name in material_names:
                poly.select = True

    bpy.ops.object.mode_set(mode='EDIT')

def detach_faces_with_suffix(obj, material_names, suffix):
	print(f"[Detach] Trying to detach: {suffix} for object {obj.name}")

	# Step 1: select faces by material
	select_faces_by_material(obj, material_names)
	bpy.ops.object.mode_set(mode='OBJECT')

	if "group" in obj:
		del obj["group"]

	# Nothing selected? stop.
	if not any(p.select for p in obj.data.polygons):
		print(f"[Detach] No faces found for {suffix} in {obj.name}")
		bpy.ops.object.mode_set(mode='EDIT')
		return None

	# Step 2: detach into new mesh
	# Perform split + separation (fix for cylinders / curved meshes)
	bpy.ops.object.mode_set(mode='EDIT')
	bpy.ops.mesh.split()  # detach selected faces from shared verts
	bpy.ops.mesh.separate(type='SELECTED')  # now separate cleanly
	bpy.ops.object.mode_set(mode='OBJECT')

	# Step 3: find the new object
	new_objs = [o for o in bpy.context.selected_objects if o != obj]
	new_obj = new_objs[-1] if new_objs else None
	if not new_obj:
		print(f"[Detach] Failed to create new mesh for {suffix} in {obj.name}")
		return None

	# Step 4: rename
	prefix_match = re.match(r"(Fracture_\d+)", obj.name)
	base_prefix = prefix_match.group(1) if prefix_match else obj.name
	suffix_name_map = {
		"cut": "Cut",
		"hide": "Hide",
		"support": "Support",
		"glass": "Glass",
		"grate": "Grate",
		"window": "Glass",
		"conveyor": "Conveyor",
		"switch": "Switch",
		"switchhide": "SwitchHide",
		"hide_Display01": "Hide_Display01",
		"hide_LCDScreen_Off": "Hide_LCDScreen_Off",
	}
	desired_name = f"{base_prefix}_{suffix_name_map.get(suffix, suffix.capitalize())}"
	new_obj.name = desired_name
	print(f"[Detach] -> Detached: {new_obj.name}")

	if "ColliderMeshGroups" in new_obj:
		del new_obj["ColliderMeshGroups"]

	# Step 5: assign construction properties
	props = bpy.context.scene.construction_props
	preset_map = props.preset_map()

	# Normalize suffix to preset
	if suffix in {"switchhide", "hide_Display01", "hide_LCDScreen_Off"}:
		preset_name = "Hide"
	else:
		preset_name = suffix_to_preset.get(suffix)


	if preset_name and preset_name in preset_map:
		t, v, p, preset_tick = preset_map[preset_name]

		# Detached mesh properties
		new_obj["ConstructionMeshType"] = t
		new_obj["ConstructionMeshVisibility"] = v

		if preset_tick:
			new_obj["ConstructionMeshPreset"] = p
		else:
			if "ConstructionMeshPreset" in new_obj:
				del new_obj["ConstructionMeshPreset"]

		# Group naming
		if preset_name in {"Hide", "Support", "FrameCut"}:
			group_name = f"{base_prefix}_{preset_name}"
		else:
			group_name = base_prefix

		if re.match(r"Fracture_\d+", group_name):
			new_obj["Group"] = group_name
			print(f"[Group] Assigned group '{group_name}' to {new_obj.name}")

		# Apply to original only for Hide/Support
		already_tagged = obj.get("_already_tagged_hide_support", False)
		if preset_name in {"Hide", "Support"} and not already_tagged:
			obj["ConstructionMeshType"] = t
			obj["ConstructionMeshVisibility"] = v
			obj["_already_tagged_hide_support"] = True

		# Apply group to original only if not Hide/Support
		if preset_name not in ("Hide", "Support"):
			if re.match(r"Fracture_\d+", group_name):
				obj["Group"] = group_name
				print(f"[Group] Assigned group '{group_name}' to {obj.name}")

		# reset flag
		for scene_obj in bpy.context.scene.objects:
			if "_already_tagged_hide_support" in scene_obj:
				del scene_obj["_already_tagged_hide_support"]

	return new_obj

def detach_faces_by_suffixes(obj, suffix_material_map):
	for material_set, suffix in suffix_material_map:
		for use_subpart in (False, True):
			current_suffix = suffix
			current_materials = material_set

			if use_subpart:
				current_materials = {m + "_Subpart" for m in material_set}
				current_suffix = "hide" if suffix == "hide" else "switch"

			detach_faces_with_suffix(obj, current_materials, current_suffix)

class OBJECT_OT_detach_materials(bpy.types.Operator):
	bl_idname = "object.detach_materials_cut_glass_decals"
	bl_label = "Detach Materials: Cut / Glass / Decals / Grate"

	def execute(self, context):
		selected_objs = [o for o in context.selected_objects if o.type == 'MESH']
		all_targets = []

		for obj in selected_objs:
			all_targets.append(obj)
			all_targets.extend(get_all_mesh_children(obj))

		unique_targets = list({obj.name: obj for obj in all_targets}.values())
		print(f"[Detach Operator] Total target objects (including children): {len(unique_targets)}")

		suffix_material_map = [
			({cut_material}, "cut"),
			({glass_material}, "glass"),
			(decal_materials | {"EmissiveOff"}, "hide"),
			({"Display01"}, "hide_Display01"),
			({"LCDScreen_Off"}, "hide_LCDScreen_Off"),  
			({grate_material}, "grate"),
			({"WindowGlassBroken"}, "window"),
			({"ConveyorsAtlas"}, "conveyor"),
		]

		props = context.scene.construction_props
		make_parent = props.make_parent_on_detach

		for obj in unique_targets:
			print(f"\n[Detach Operator] Processing {obj.name}")
			context.view_layer.objects.active = obj
			bpy.ops.object.select_all(action='DESELECT')
			obj.select_set(True)

			bpy.ops.object.mode_set(mode='EDIT')
			bpy.ops.mesh.select_all(action='DESELECT')

			existing_objects = set(bpy.context.selected_objects)
			detach_faces_by_suffixes(obj, suffix_material_map)
			bpy.ops.object.mode_set(mode='OBJECT')

			if make_parent:
				new_selection = set(bpy.context.selected_objects)
				new_detached_objs = new_selection - existing_objects

				for new_obj in new_detached_objs:
					original_matrix = new_obj.matrix_world.copy()
					new_obj.parent = obj
					new_obj.matrix_world = original_matrix
				print(f"[Detach] Parented {new_obj.name} to {obj.name}")

		return {'FINISHED'}
		
class OBJECT_OT_apply_selected_properties(bpy.types.Operator):
	bl_label = "Apply Selected Construction Properties"
	bl_idname = "object.apply_selected_properties"

	def execute(self, context):
		props = context.scene.construction_props
		preset_name = props.selected_preset
		selected_objects = context.selected_objects

		if props.merge_to_existing:
			for obj in selected_objects:
				self.merge_into_existing(obj, preset_name, props, context)
		else:
			for obj in selected_objects:
				self.apply_properties_to_object(obj, preset_name, props)

		self.report({'INFO'}, f"Applied selected properties to {len(selected_objects)} object(s).")
		return {'FINISHED'}

	@staticmethod
	def apply_properties_to_object(obj, preset_name, props):
		if props.apply_type:
			obj["ConstructionMeshType"] = props.type
		elif "ConstructionMeshType" in obj:
			del obj["ConstructionMeshType"]

		if props.apply_visibility:
			obj["ConstructionMeshVisibility"] = props.visibility
		elif "ConstructionMeshVisibility" in obj:
			del obj["ConstructionMeshVisibility"]

		if props.apply_preset:
			obj["ConstructionMeshPreset"] = props.preset
		elif "ConstructionMeshPreset" in obj:
			del obj["ConstructionMeshPreset"]

		if props.apply_order_id:
			obj["ConstructionMeshOrderId"] = props.order_id
		elif "ConstructionMeshOrderId" in obj:
			del obj["ConstructionMeshOrderId"]

		if props.apply_order_duration:
			obj["ConstructionMeshOrderDuration"] = props.order_duration
		elif "ConstructionMeshOrderDuration" in obj:
			del obj["ConstructionMeshOrderDuration"]

		# ✅ Extract Fracture_XX prefix
		base_match = re.match(r"^(Fracture_\d+)", obj.name)
		if not base_match:
			print(f"[Apply] Skipping rename/group: {obj.name} has no valid Fracture_XX name.")
			return

		base = base_match.group(1)

		# ✅ Determine name suffix based on preset
		if preset_name == "Default":
			target_name = base
		elif preset_name == "FractureCut":
			target_name = f"{base}_Cut"
		else:
			target_name = f"{base}_{preset_name}"

		# ✅ Rename if different
		if obj.name != target_name:
			if "ColliderMeshGroups" in obj:
				del obj["ColliderMeshGroups"]
			new_name = target_name
			suffix = 1
			while bpy.data.objects.get(new_name):
				new_name = f"{target_name}.{suffix:03}"
				suffix += 1
			print(f"[Apply] Renaming {obj.name} to {new_name}")
			obj.name = new_name

		# ✅ Assign group
		if preset_name in {"Hide", "Support", "FrameCut"}:
			group_name = f"{base}_{preset_name}"
		else:
			group_name = base

		if re.match(r"Fracture_\d+", group_name):
			obj["Group"] = group_name
			print(f"[Apply] Group set to '{group_name}' for {obj.name}")

	@staticmethod
	def merge_into_existing(obj, preset_name, props, context):
		OBJECT_OT_apply_selected_properties.apply_properties_to_object(obj, preset_name, props)

		base_match = re.match(r"^(Fracture_\d+)", obj.name)
		if not base_match:
			print(f"[Merge] Skipping: {obj.name} has no valid Fracture_ prefix.")
			return
		base_name = base_match.group(1)

		def is_valid_target(candidate):
			if candidate == obj:
				return False
			if not candidate.name.startswith(base_name):
				return False
			if not candidate.visible_get():
				return False  # Not visible in current viewport
			if candidate.hide_viewport:
				return False  # Eye icon is off
			if candidate.hide_get():
				return False  # Hidden directly in viewport
			if candidate.get("ConstructionMeshType") != obj.get("ConstructionMeshType"):
				return False
			if candidate.get("ConstructionMeshVisibility") != obj.get("ConstructionMeshVisibility"):
				return False
			if candidate.get("ConstructionMeshPreset", "") != obj.get("ConstructionMeshPreset", ""):
				return False
			return True

		candidates = [o for o in bpy.data.objects if is_valid_target(o)]
		if not candidates:
			print(f"[Merge] No valid merge target for {obj.name}")
			return

		target = candidates[0]
		target_name = target.name
		obj_name = obj.name
		print(f"[Merge] Merging {obj_name} into {target_name}")

		target.hide_viewport = False
		obj.hide_viewport = False

		bpy.ops.object.select_all(action='DESELECT')
		target.select_set(True)
		obj.select_set(True)
		context.view_layer.objects.active = target

		try:
			# Do not access `obj` after this line!
			bpy.ops.object.join()
			print(f"[Merge] Successfully merged {obj_name} into {target_name}")
		except Exception as e:
			print(f"[Merge] Failed to merge {obj_name} into {target_name}: {e}")
	
class ConstructionPropertySettings(bpy.types.PropertyGroup):
	def update_selected_preset(self, context):
		preset = self.selected_preset
		preset_map = self.preset_map()

		if preset in preset_map:
			t, v, p, preset_tick = preset_map[preset]

			self.type = t
			self.visibility = v

			# ✅ For Support, Glass, GratingMetallic — no preset assigned
			if preset == "GratingMetallic":
				self.preset = ""
				self.apply_preset = False
			else:
				self.preset = p
				self.apply_preset = preset_tick

			self.apply_type = True
			self.apply_visibility = True
			self.apply_order_id = False
			self.apply_order_duration = False
			self.order_id = ""
			self.order_duration = ""

	def preset_map(self):
		return {
			"Default":  	   ("Default", "AlwaysVisible", "Default", True),
			"FractureCut":     ("Split", "HiddenUntilSecondSequenceStart", "Fracture", True),
			"FrameCut": 	   ("Split", "HiddenUntilSecondSequenceStart", "Default", True),
			"Hide": 		   ("Default", "AlwaysHidden", "", False),
			"Scaffold": 	   ("Scaffold", "AlwaysVisible", "Scaffolding", True),
			"Support":  	   ("Default", "AlwaysVisible", "Support", True),
			"Glass":		   ("Default", "AlwaysVisible", "WindowGlass", True),
			"GratingMetallic": ("Default", "AlwaysVisible", "GratingMetallic", True),
			"Conveyor": ("Default", "AlwaysVisible", "Conveyor_Port", True),
		}

	selected_preset: bpy.props.EnumProperty(
		name="Presets",
		items=[
			("Default", "Default", ""),
			("FractureCut", "Cut", ""),
			("FrameCut", "FrameCut", ""),
			("Hide", "Hide", ""),
			("Scaffold", "Scaffold", ""),
			("Conveyor", "Conveyor", ""),
			("Support", "Support", ""),
			("Glass", "Glass", ""),
			("GratingMetallic", "GratingMetallic", ""),
		],
		default="Default",
		update=update_selected_preset
	)

	select_all: bpy.props.BoolProperty(
		name="Select All Properties",
		update=lambda self, context: self.set_all(self.select_all)
	)
		
	select_name_filter: bpy.props.StringProperty(
		name="Name Contains",
		description="Filter objects by name"	
	)

	apply_type: bpy.props.BoolProperty(name="Type")
	apply_visibility: bpy.props.BoolProperty(name="Visibility")
	apply_preset: bpy.props.BoolProperty(name="Preset")
	apply_order_id: bpy.props.BoolProperty(name="Order ID")
	apply_order_duration: bpy.props.BoolProperty(name="Order Duration")

	type: bpy.props.EnumProperty(
		name="",
		items=[
			("Default", "Default", ""),
			("Scaffold", "Scaffold", ""),
			("Split", "Split", "")
		],
		default="Default"
	)

	visibility: bpy.props.EnumProperty(
		name="",
		items=[
			("AlwaysVisible", "AlwaysVisible", ""),
			("HiddenUntilFirstSequenceStart", "HiddenUntilFirstSequenceStart", ""),
			("HiddenUntilSecondSequenceStart", "HiddenUntilSecondSequenceStart", ""),
			("AlwaysHidden", "AlwaysHidden", "")
		],
		default="AlwaysVisible"
	)

	preset: bpy.props.StringProperty(name="")
	order_id: bpy.props.StringProperty(name="", default="")
	order_duration: bpy.props.StringProperty(name="", default="")
	
	merge_to_existing: bpy.props.BoolProperty(
		name="Merge to existing mesh",
		description="Merge into a mesh with matching construction properties",
		default=False
	)
	
	make_parent_on_detach: bpy.props.BoolProperty(
		name="Make Parent Mesh",
		description="Parent newly detached objects back to the source mesh",
		default=False
	)

	def set_all(self, value):
		self.apply_type = value
		self.apply_visibility = value
		self.apply_preset = value
		self.apply_order_id = value
		self.apply_order_duration = value
		
	show_group_tools: bpy.props.BoolProperty(
		name="Group & ColliderMeshGroups Tool",
		description="Show extra group assignment tools",
		default=False
	)

class OBJECT_PT_construction_panel(bpy.types.Panel):
	bl_label = "Construction Mesh Properties"
	bl_idname = "OBJECT_PT_construction_panel"
	bl_space_type = 'VIEW_3D'
	bl_region_type = 'UI'
	bl_parent_id = 'VRT_PT_BlockProperties'
	bl_order = 99
	
	# experimantal_enabled: bpy.props.BoolProperty(
	# 	name="Enable Experimental",
	# 	description="These features are a temporary implementation"
	# )

	def draw(self, context):
		layout = self.layout
		props = context.scene.construction_props

		layout.prop(props, "selected_preset", text="Presets")

		box = layout.box()
		box.label(text="Tick and set properties to apply:")
		box.prop(props, "select_all", text="Select/Deselect All Properties")

		row = box.row(align=True)
		row.prop(props, "apply_type", text="")
		row.label(text="Type")
		row.prop(props, "type", text="")

		row = box.row(align=True)
		row.prop(props, "apply_visibility", text="")
		row.label(text="Visibility")
		row.prop(props, "visibility", text="")

		row = box.row(align=True)
		row.prop(props, "apply_preset", text="")
		row.label(text="Preset")
		row.prop(props, "preset", text="")

		row = box.row(align=True)
		row.prop(props, "apply_order_id", text="")
		row.label(text="Order ID")
		row.prop(props, "order_id", text="")

		row = box.row(align=True)
		row.prop(props, "apply_order_duration", text="")
		row.label(text="Order Duration")
		row.prop(props, "order_duration", text="")

		layout.separator()
		layout.operator("object.apply_selected_properties", icon="CHECKMARK")
		layout.prop(props, "merge_to_existing", text="Merge to existing mesh")
		layout.operator("object.detach_materials_cut_glass_decals", icon="MOD_EXPLODE")
		layout.prop(props, "make_parent_on_detach", text="Make Parent")
		layout.separator()
		layout.label(text="Quick Select by Name:")
		layout.prop(props, "select_name_filter", text="")
		layout.operator("object.select_by_name_filter", text="Select", icon="RESTRICT_SELECT_OFF")
		
		layout.separator()
		box = layout.box()
		box.prop(props, "show_group_tools", icon="TRIA_DOWN" if props.show_group_tools else "TRIA_RIGHT", emboss=False)

		if props.show_group_tools:
			box.label(text="Set Group Tags:")
			box.operator("object.set_fracture_group_default", icon='GROUP')
			box.operator("object.set_fracture_group_hide", icon='HIDE_ON')
			box.operator("object.set_fracture_group_support", icon='MOD_BUILD')
			box.operator("object.set_fracture_group_framecut", icon='MOD_EXPLODE')
			box.separator()
			box.operator("object.set_collidermeshgroups", icon='GROUP')

class OBJECT_OT_select_objects_by_name(bpy.types.Operator):
	bl_idname = "object.select_by_name_filter"
	bl_label = "Select by Name Filter"

	def execute(self, context):
		filter_text = context.scene.construction_props.select_name_filter.lower()
		count = 0
		bpy.ops.object.select_all(action='DESELECT')

		for obj in bpy.context.scene.objects:
			if (
				obj.type == 'MESH'
				and not obj.hide_viewport
				and obj.visible_get()
				and filter_text in obj.name.lower()
			):
				obj.select_set(True)
				count += 1

		self.report({'INFO'}, f"Selected {count} object(s) containing '{filter_text}' (visible only)")
		return {'FINISHED'}
		
# ===============================================================
# === GROUP & COLLIDERMESHGROUPS OPERATORS ======================
# ===============================================================

class OBJECT_OT_SetFractureGroupDefault(bpy.types.Operator):
    bl_idname = "object.set_fracture_group_default"
    bl_label = "Set Group: Default"
    bl_description = "Set 'Group' attribute using Fracture_XX prefix"

    def execute(self, context):
        for obj in context.selected_objects:
            if obj.type != 'MESH':
                self.report({'INFO'}, f"Skipped non-mesh: {obj.name}")
                continue

            match = re.match(r"(Fracture_\d+)", obj.name)
            if match:
                group_name = match.group(1)

                if "group" in obj:
                    del obj["group"]
                obj["Group"] = group_name

                self.report({'INFO'}, f"{obj.name} → Group = {group_name}")
                print(f"[Default] {obj.name}: Group set to '{group_name}'")
            else:
                self.report({'WARNING'}, f"No Fracture_XX prefix in: {obj.name}")
                print(f"[Default] {obj.name}: skipped (no matching prefix)")
        return {'FINISHED'}


class OBJECT_OT_SetFractureGroupHide(bpy.types.Operator):
    bl_idname = "object.set_fracture_group_hide"
    bl_label = "Set Group: Hide"
    bl_description = "Set 'Group' attribute using Fracture_XX prefix + '_Hide'"

    def execute(self, context):
        for obj in context.selected_objects:
            if obj.type != 'MESH':
                self.report({'INFO'}, f"Skipped non-mesh: {obj.name}")
                continue

            match = re.match(r"(Fracture_\d+)", obj.name)
            if match:
                group_name = match.group(1) + "_Hide"

                if "group" in obj:
                    del obj["group"]
                obj["Group"] = group_name

                self.report({'INFO'}, f"{obj.name} → Group = {group_name}")
                print(f"[Hide] {obj.name}: Group set to '{group_name}'")
            else:
                self.report({'WARNING'}, f"No Fracture_XX prefix in: {obj.name}")
                print(f"[Hide] {obj.name}: skipped (no matching prefix)")
        return {'FINISHED'}


class OBJECT_OT_SetFractureGroupSupport(bpy.types.Operator):
    bl_idname = "object.set_fracture_group_support"
    bl_label = "Set Group: Support"
    bl_description = "Set 'Group' attribute using Fracture_XX prefix + '_Support'"

    def execute(self, context):
        for obj in context.selected_objects:
            if obj.type != 'MESH':
                self.report({'INFO'}, f"Skipped non-mesh: {obj.name}")
                continue

            match = re.match(r"(Fracture_\d+)", obj.name)
            if match:
                group_name = match.group(1) + "_Support"

                if "group" in obj:
                    del obj["group"]
                obj["Group"] = group_name

                self.report({'INFO'}, f"{obj.name} → Group = {group_name}")
                print(f"[Support] {obj.name}: Group set to '{group_name}'")
            else:
                self.report({'WARNING'}, f"No Fracture_XX prefix in: {obj.name}")
                print(f"[Support] {obj.name}: skipped (no matching prefix)")
        return {'FINISHED'}


class OBJECT_OT_SetColliderMeshGroups(bpy.types.Operator):
    bl_idname = "object.set_collidermeshgroups"
    bl_label = "Set ColliderMeshGroups"
    bl_description = "Assign ColliderMeshGroups based on Group/group and visible children with same prefix"

    def execute(self, context):
        all_objects = bpy.data.objects
        print("\n[ColliderMeshGroups] Starting processing...")

        for obj in context.selected_objects:
            if obj.type != 'MESH':
                print(f"[ColliderMeshGroups] Skipped non-mesh: {obj.name}")
                continue
            if not obj.visible_get():
                continue

            # Accept both "Group" and "group" keys, with fallback
            base_group = obj.get("Group") or obj.get("group")
            if not base_group:
                print(f"[ColliderMeshGroups] Skipped (no Group/group): {obj.name}")
                continue

            base_group = str(base_group).strip()
            match = re.match(r"(Fracture_\d+)", base_group)
            if not match:
                print(f"[ColliderMeshGroups] Skipped (Group format invalid): {obj.name} → {base_group}")
                continue

            root_prefix = match.group(1)
            collected = set()
            collected.add(base_group)

            print(f"[ColliderMeshGroups] Processing {obj.name}")
            print(f"  → Group = '{base_group}', root_prefix = {root_prefix}")

            for other in all_objects:
                if other == obj or other.type != 'MESH':
                    continue
                if not other.visible_get():
                    continue

                # Accept either "Group" or "group"
                other_group = other.get("Group") or other.get("group")
                if not other_group:
                    print(f"    ~ Ignored {other.name} (no Group/group)")
                    continue

                other_group = str(other_group).strip()
                print(f"    > Checking {other.name}: Group = '{other_group}'")

                if other_group.startswith(root_prefix):
                    collected.add(other_group)
                    print(f"    + Collected: {other_group}")
                else:
                    print(f"    ~ Ignored {other.name} (prefix mismatch: {other_group})")

            # Deduplicate and sort
            unique_sorted = sorted(set(collected))
            collider_val = '|'.join(unique_sorted)
            obj["ColliderMeshGroups"] = collider_val
            self.report({'INFO'}, f"{obj.name} → ColliderMeshGroups = {collider_val}")
            print(f"[ColliderMeshGroups] {obj.name}: ColliderMeshGroups set to '{collider_val}'")

        print("[ColliderMeshGroups] Done.\n")
        return {'FINISHED'}


class OBJECT_OT_SetFractureGroupFrameCut(bpy.types.Operator):
    bl_idname = "object.set_fracture_group_framecut"
    bl_label = "Set Group: FrameCut"
    bl_description = "Set 'Group' attribute using Fracture_XX prefix + '_FrameCut'"

    def execute(self, context):
        for obj in context.selected_objects:
            if obj.type != 'MESH':
                self.report({'INFO'}, f"Skipped non-mesh: {obj.name}")
                continue

            match = re.match(r"(Fracture_\d+)", obj.name)
            if match:
                group_name = match.group(1) + "_FrameCut"

                if "group" in obj:
                    del obj["group"]
                obj["Group"] = group_name

                self.report({'INFO'}, f"{obj.name} → Group = {group_name}")
                print(f"[FrameCut] {obj.name}: Group set to '{group_name}'")
            else:
                self.report({'WARNING'}, f"No Fracture_XX prefix in: {obj.name}")
                print(f"[FrameCut] {obj.name}: skipped (no matching prefix)")
        return {'FINISHED'}


classes = (
	ConstructionPropertySettings,
	OBJECT_PT_construction_panel,
	OBJECT_OT_apply_selected_properties,
	OBJECT_OT_detach_materials,
	OBJECT_OT_select_objects_by_name,
	OBJECT_OT_SetFractureGroupDefault,
	OBJECT_OT_SetFractureGroupHide,
	OBJECT_OT_SetFractureGroupSupport,
	OBJECT_OT_SetFractureGroupFrameCut,
	OBJECT_OT_SetColliderMeshGroups,
)

def register():
	for cls in classes:
		bpy.utils.register_class(cls)
	bpy.types.Scene.construction_props = bpy.props.PointerProperty(type=ConstructionPropertySettings)

def unregister():
	for cls in reversed(classes):
		bpy.utils.unregister_class(cls)
	if hasattr(bpy.types.Scene, "construction_props"):
		del bpy.types.Scene.construction_props