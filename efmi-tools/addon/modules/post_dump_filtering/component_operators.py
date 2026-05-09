import bpy

from .component_utils import list_dump_components, patch_dump_components
from .operators import resolve_object_source_folder


def clear_component_list(cfg):
    cfg.components.clear()
    cfg.active_component_index = 0


def populate_component_list(cfg, components):
    clear_component_list(cfg)
    for component_info in components:
        item = cfg.components.add()
        item.index = component_info.index
        item.mesh_name = component_info.mesh_name
        item.file_count = component_info.file_count
        item.lod_count = component_info.lod_count
        item.vertex_count = component_info.vertex_count
        item.index_count = component_info.index_count
        item.ib_hash = component_info.ib_hash
        item.vb0_hash = component_info.vb0_hash
        item.lods.clear()
        for lod_info in component_info.lods:
            lod_item = item.lods.add()
            lod_item.index = lod_info.index
            lod_item.lod_object_name = lod_info.lod_object_name
            lod_item.vertex_count = lod_info.vertex_count
            lod_item.index_count = lod_info.index_count
            lod_item.ib_hash = lod_info.ib_hash
            lod_item.vb0_hash = lod_info.vb0_hash
        item.remove_component = False
        item.clear_lods = False
        item.refresh_display_name()


class EFMI_PostDumpLoadComponents(bpy.types.Operator):
    bl_idname = "efmi_tools.post_dump_load_components"
    bl_label = "Load Components"
    bl_description = "Load components from the current dump Metadata.json"

    def execute(self, context):
        settings = context.scene.efmi_tools_settings
        cfg = settings.post_dump_filtering

        if not settings.object_source_folder.strip():
            self.report({"ERROR"}, "Object sources folder is not set.")
            return {"CANCELLED"}

        source_folder = resolve_object_source_folder(settings)
        if not source_folder.is_dir():
            self.report({"ERROR"}, f"Object sources folder does not exist: {source_folder}")
            return {"CANCELLED"}

        try:
            components = list_dump_components(source_folder)
        except Exception as error:
            self.report({"ERROR"}, f"Failed to load dump components: {error}")
            return {"CANCELLED"}

        populate_component_list(cfg, components)
        self.report({"INFO"}, f"Loaded {len(cfg.components)} components.")
        return {"FINISHED"}


class EFMI_PostDumpClearComponents(bpy.types.Operator):
    bl_idname = "efmi_tools.post_dump_clear_components"
    bl_label = "Clear Components"
    bl_description = "Clear the current dump component list"

    def execute(self, context):
        cfg = context.scene.efmi_tools_settings.post_dump_filtering
        clear_component_list(cfg)
        return {"FINISHED"}


class EFMI_PostDumpPatchComponents(bpy.types.Operator):
    bl_idname = "efmi_tools.post_dump_patch_components"
    bl_label = "Patch Dump"
    bl_description = "Delete marked dump components and clear selected LoD metadata"

    def has_changes(self, cfg):
        return any(component.remove_component or component.clear_lods for component in cfg.components)

    def invoke(self, context, event):
        cfg = context.scene.efmi_tools_settings.post_dump_filtering
        if not self.has_changes(cfg):
            self.report({"ERROR"}, "No component changes selected.")
            return {"CANCELLED"}
        return context.window_manager.invoke_props_dialog(self, width=520)

    def draw(self, context):
        cfg = context.scene.efmi_tools_settings.post_dump_filtering
        delete_count = sum(1 for component in cfg.components if component.remove_component)
        clear_lod_count = sum(
            1
            for component in cfg.components
            if component.clear_lods and not component.remove_component
        )

        column = self.layout.column()
        column.alert = True
        column.label(text=f"{delete_count} component(s) will be deleted from the dump.", icon="ERROR")
        column.label(text=f"{clear_lod_count} component(s) will have LoD metadata cleared.", icon="INFO")
        column.label(text="Metadata.json and component files will be rewritten/reindexed.", icon="FILE_REFRESH")

    def execute(self, context):
        settings = context.scene.efmi_tools_settings
        cfg = settings.post_dump_filtering

        if len(cfg.components) == 0:
            self.report({"ERROR"}, "No components loaded.")
            return {"CANCELLED"}

        remove_indices = {
            component.index
            for component in cfg.components
            if component.remove_component
        }
        clear_lod_indices = {
            component.index
            for component in cfg.components
            if component.clear_lods
        }

        if not remove_indices and not clear_lod_indices:
            self.report({"ERROR"}, "No component changes selected.")
            return {"CANCELLED"}

        source_folder = resolve_object_source_folder(settings)
        try:
            result = patch_dump_components(source_folder, remove_indices, clear_lod_indices)
            populate_component_list(cfg, list_dump_components(source_folder))
        except Exception as error:
            self.report({"ERROR"}, f"Failed to patch dump components: {error}")
            return {"CANCELLED"}

        message = result.report_message()
        if result.texture_usage_updated:
            message += " TextureUsage.json updated."
        self.report({"INFO"}, message)
        return {"FINISHED"}
