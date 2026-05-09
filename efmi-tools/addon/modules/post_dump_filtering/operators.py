import json
from dataclasses import dataclass, field
from pathlib import Path

import bpy

from .texture_utils import (
    FILTER_DELETE,
    FILTER_OTHER,
    FILTER_UNMARKED,
    TEXTURE_FILTER_ITEMS,
    infer_texture_filter_type,
    iter_dds_texture_paths,
    parse_texture_name,
    split_applied_filter,
)


def resolve_path(path):
    return Path(bpy.path.abspath(path)).expanduser()


def load_texture_image(texture_path):
    image = bpy.data.images.load(str(texture_path), check_existing=True)
    image.filepath = str(texture_path)
    image.alpha_mode = "NONE"

    try:
        image.preview_ensure()
    except Exception:
        pass

    return image


def get_preview_icon(image):
    if not image:
        return 0

    try:
        image.preview_ensure()
    except Exception:
        return 0

    return image.preview.icon_id if image.preview else 0


def has_loaded_data(image):
    if not image:
        return False
    try:
        return bool(image.has_data or (image.size[0] > 0 and image.size[1] > 0))
    except Exception:
        return False


@dataclass(frozen=True)
class UsagePruneResult:
    value: object
    removed_count: int = 0
    keep: bool = True


@dataclass(frozen=True)
class TextureUsageCleanupResult:
    removed_entries: int = 0
    file_found: bool = True
    failed: bool = False


@dataclass
class ApplyTextureResult:
    renamed: int = 0
    deleted: int = 0
    skipped: int = 0
    usage_cleanup: TextureUsageCleanupResult = field(default_factory=TextureUsageCleanupResult)

    def report_message(self):
        return (
            f"Renamed {self.renamed} textures. "
            f"Deleted: {self.deleted}. "
            f"Skipped: {self.skipped}. "
            f"TextureUsage entries removed: {self.usage_cleanup.removed_entries}."
        )


def usage_entry_matches_hash(value, texture_hashes):
    if not isinstance(value, str):
        return False
    value = value.lower()
    return any(texture_hash in value for texture_hash in texture_hashes)


def remove_usage_entries(node, texture_hashes):
    if isinstance(node, dict):
        cleaned = {}
        removed_count = 0
        for key, value in node.items():
            result = remove_usage_entries(value, texture_hashes)
            removed_count += result.removed_count
            if result.keep:
                cleaned[key] = result.value
        return UsagePruneResult(cleaned, removed_count, bool(cleaned))

    if isinstance(node, list):
        cleaned = []
        removed_count = 0
        for value in node:
            if usage_entry_matches_hash(value, texture_hashes):
                removed_count += 1
                continue

            result = remove_usage_entries(value, texture_hashes)
            removed_count += result.removed_count
            if result.keep:
                cleaned.append(result.value)
        return UsagePruneResult(cleaned, removed_count, bool(cleaned))

    if usage_entry_matches_hash(node, texture_hashes):
        return UsagePruneResult(None, 1, False)

    return UsagePruneResult(node)


def remove_deleted_textures_from_usage(source_folder, deleted_hashes):
    usage_path = source_folder / "TextureUsage.json"
    if not usage_path.is_file():
        return TextureUsageCleanupResult(file_found=False)

    texture_hashes = {
        texture_hash.lower()
        for texture_hash in deleted_hashes
        if texture_hash and len(texture_hash) >= 6
    }
    if not texture_hashes:
        return TextureUsageCleanupResult()

    try:
        with usage_path.open("r", encoding="utf-8") as usage_file:
            usage_data = json.load(usage_file)
    except Exception as error:
        print(f"Failed to read TextureUsage.json '{usage_path}': {error}")
        return TextureUsageCleanupResult(failed=True)

    result = remove_usage_entries(usage_data, texture_hashes)
    if not result.removed_count:
        return TextureUsageCleanupResult()

    try:
        with usage_path.open("w", encoding="utf-8") as usage_file:
            json.dump(result.value, usage_file, indent=4)
            usage_file.write("\n")
    except Exception as error:
        print(f"Failed to update TextureUsage.json '{usage_path}': {error}")
        return TextureUsageCleanupResult(failed=True)

    return TextureUsageCleanupResult(removed_entries=result.removed_count)


def delete_texture_file(texture):
    texture_path = Path(texture.path)
    if not texture_path.exists():
        return False

    texture_path.unlink()
    return True


def clamp_active_texture_index(cfg):
    if len(cfg.textures) == 0:
        cfg.active_texture_index = 0
    else:
        cfg.active_texture_index = min(cfg.active_texture_index, len(cfg.textures) - 1)


class EFMI_PostDumpLoadTextures(bpy.types.Operator):
    bl_idname = "efmi_tools.post_dump_load_textures"
    bl_label = "Load DDS Textures"
    bl_description = "Load all .dds textures from the current frame dump folder"

    def execute(self, context):
        settings = context.scene.efmi_tools_settings
        cfg = settings.post_dump_filtering

        if not settings.frame_dump_folder.strip():
            self.report({"ERROR"}, "Source dump folder is not set.")
            return {"CANCELLED"}

        source_folder = resolve_path(settings.frame_dump_folder)
        if not source_folder.is_dir():
            self.report({"ERROR"}, f"Source dump folder does not exist: {source_folder}")
            return {"CANCELLED"}

        cfg.textures.clear()
        cfg.active_texture_index = 0
        cfg.loaded_count = 0
        cfg.failed_count = 0

        texture_paths = iter_dds_texture_paths(source_folder)

        for texture_path in texture_paths:
            applied_filter = split_applied_filter(texture_path.stem)
            texture_info = parse_texture_name(texture_path)

            try:
                image = load_texture_image(texture_path)
            except Exception as error:
                cfg.failed_count += 1
                print(f"Failed to load DDS texture '{texture_path}': {error}")
                continue

            item = cfg.textures.add()
            item.path = str(texture_path)
            item.hash = texture_info.hash
            item.texture_name = texture_info.texture_name
            item.rename_stem = applied_filter.base_stem
            item.filter_type = applied_filter.filter_type
            item.custom_filter_name = applied_filter.custom_filter_name
            item.image = image
            item.image_loaded = has_loaded_data(image)
            item.preview_icon_id = get_preview_icon(image)
            item.refresh_display_name()

            cfg.loaded_count += 1

        if not texture_paths:
            self.report({"WARNING"}, "No .dds textures were found in the selected dump folder.")
            return {"FINISHED"}

        if cfg.failed_count:
            self.report({"WARNING"}, f"Loaded {cfg.loaded_count} DDS textures. Failed: {cfg.failed_count}.")
            return {"FINISHED"}

        self.report({"INFO"}, f"Loaded {cfg.loaded_count} DDS textures.")
        return {"FINISHED"}


class EFMI_PostDumpClearTextures(bpy.types.Operator):
    bl_idname = "efmi_tools.post_dump_clear_textures"
    bl_label = "Clear Texture List"
    bl_description = "Clear the current post dump texture list"

    def execute(self, context):
        cfg = context.scene.efmi_tools_settings.post_dump_filtering
        cfg.textures.clear()
        cfg.active_texture_index = 0
        cfg.loaded_count = 0
        cfg.failed_count = 0
        return {"FINISHED"}


class EFMI_PostDumpAutoFilterTextures(bpy.types.Operator):
    bl_idname = "efmi_tools.post_dump_auto_filter_textures"
    bl_label = "Auto Filtering"
    bl_description = "Categorize DDS textures by their BC format and color space"

    def execute(self, context):
        cfg = context.scene.efmi_tools_settings.post_dump_filtering

        if len(cfg.textures) == 0:
            self.report({"ERROR"}, "No textures loaded.")
            return {"CANCELLED"}

        applied_count = 0
        for texture in cfg.textures:
            if texture.filter_type == FILTER_DELETE:
                continue

            filter_type = infer_texture_filter_type(Path(texture.path))
            if not filter_type or texture.filter_type == filter_type:
                continue

            texture.filter_type = filter_type
            texture.custom_filter_name = ""
            texture.refresh_display_name()
            applied_count += 1

        self.report({"INFO"}, f"Auto filtered {applied_count} textures.")
        return {"FINISHED"}


class EFMI_PostDumpApplyTextureNames(bpy.types.Operator):
    bl_idname = "efmi_tools.post_dump_apply_texture_names"
    bl_label = "Apply"
    bl_description = "Rename .dds files in the dump folder using their selected texture category"

    def invoke(self, context, event):
        cfg = context.scene.efmi_tools_settings.post_dump_filtering
        if any(texture.filter_type == FILTER_DELETE for texture in cfg.textures):
            return context.window_manager.invoke_props_dialog(self, width=460)
        return self.execute(context)

    def draw(self, context):
        cfg = context.scene.efmi_tools_settings.post_dump_filtering
        delete_count = sum(1 for texture in cfg.textures if texture.filter_type == FILTER_DELETE)

        column = self.layout.column()
        column.alert = True
        column.label(
            text=f"{delete_count} texture(s) marked as Delete will be permanently deleted.",
            icon="ERROR",
        )
        column.label(text="TextureUsage.json will also be cleaned when found.", icon="INFO")

    def execute(self, context):
        settings = context.scene.efmi_tools_settings
        cfg = settings.post_dump_filtering

        if len(cfg.textures) == 0:
            self.report({"ERROR"}, "No textures loaded.")
            return {"CANCELLED"}

        deleted_hashes = []
        result = ApplyTextureResult()

        for index in range(len(cfg.textures) - 1, -1, -1):
            texture = cfg.textures[index]
            if texture.filter_type != FILTER_DELETE:
                continue

            try:
                if delete_texture_file(texture):
                    result.deleted += 1
                else:
                    print(f"Texture already missing, removing from list: '{texture.path}'")
                    result.skipped += 1
                deleted_hashes.append(texture.hash)
                cfg.textures.remove(index)
            except Exception as error:
                result.skipped += 1
                print(f"Failed to delete texture '{texture.path}': {error}")

        if deleted_hashes and settings.frame_dump_folder.strip():
            result.usage_cleanup = remove_deleted_textures_from_usage(
                resolve_path(settings.frame_dump_folder),
                deleted_hashes,
            )

        for texture in cfg.textures:
            source_path = Path(texture.path)
            target_path = source_path.with_name(texture.get_applied_filename())

            if source_path == target_path:
                result.skipped += 1
                continue

            if target_path.exists():
                result.skipped += 1
                print(f"Skipping texture rename, target already exists: '{target_path}'")
                continue

            try:
                source_path.rename(target_path)
            except Exception as error:
                result.skipped += 1
                print(f"Failed to rename texture '{source_path}' to '{target_path}': {error}")
                continue

            texture.path = str(target_path)
            texture.refresh_display_name()

            if texture.image:
                texture.image.filepath = str(target_path)
                texture.image.name = target_path.name
                texture.image.alpha_mode = "NONE"
            result.renamed += 1

        clamp_active_texture_index(cfg)
        cfg.loaded_count = len(cfg.textures)

        message = result.report_message()

        if result.usage_cleanup.failed:
            self.report({"WARNING"}, f"{message} Failed to update TextureUsage.json.")
        elif deleted_hashes and not result.usage_cleanup.file_found:
            self.report({"WARNING"}, f"{message} TextureUsage.json not found.")
        else:
            self.report({"INFO"}, message)
        return {"FINISHED"}


class EFMI_PostDumpSetTextureFilter(bpy.types.Operator):
    bl_idname = "efmi_tools.post_dump_set_texture_filter"
    bl_label = "Set Texture Filter"
    bl_description = "Apply a texture category to the selected texture"

    filter_type: bpy.props.EnumProperty(
        name="Filter",
        items=TEXTURE_FILTER_ITEMS,
        default=FILTER_UNMARKED,
    ) # type: ignore

    def execute(self, context):
        cfg = context.scene.efmi_tools_settings.post_dump_filtering
        texture = cfg.get_active_texture()

        if texture is None:
            self.report({"ERROR"}, "No texture is selected.")
            return {"CANCELLED"}

        if self.filter_type == FILTER_OTHER:
            custom_filter_name = cfg.custom_filter_name.strip()
            if not custom_filter_name:
                self.report({"ERROR"}, "Custom name is required for Other.")
                return {"CANCELLED"}
            texture.custom_filter_name = custom_filter_name
        else:
            texture.custom_filter_name = ""

        texture.filter_type = self.filter_type
        texture.refresh_display_name()

        self.report({"INFO"}, f"Texture categorized as {texture.filter_label()}.")
        return {"FINISHED"}
