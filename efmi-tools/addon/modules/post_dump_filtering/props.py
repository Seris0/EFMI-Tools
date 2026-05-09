import bpy

from .texture_utils import (
    FILTER_UNMARKED,
    TEXTURE_FILTER_ITEMS,
    format_texture_name,
    get_texture_filter_label,
    sanitize_filename_part,
)


class PostDumpTextureItem(bpy.types.PropertyGroup):
    path: bpy.props.StringProperty(
        name="Path",
        subtype="FILE_PATH",
    ) # type: ignore

    hash: bpy.props.StringProperty(
        name="Hash",
    ) # type: ignore

    texture_name: bpy.props.StringProperty(
        name="Texture",
    ) # type: ignore

    rename_stem: bpy.props.StringProperty(
        name="Rename Stem",
        description="Original filename stem used when applying a category to the file on disk",
    ) # type: ignore

    filter_type: bpy.props.EnumProperty(
        name="Filter",
        items=TEXTURE_FILTER_ITEMS,
        default=FILTER_UNMARKED,
    ) # type: ignore

    custom_filter_name: bpy.props.StringProperty(
        name="Custom Filter",
    ) # type: ignore

    image: bpy.props.PointerProperty(
        type=bpy.types.Image,
    ) # type: ignore

    image_loaded: bpy.props.BoolProperty(
        name="Loaded",
        default=False,
    ) # type: ignore

    preview_icon_id: bpy.props.IntProperty(
        name="Preview Icon",
        default=0,
        min=0,
    ) # type: ignore

    def filter_label(self):
        return get_texture_filter_label(self.filter_type, self.custom_filter_name)

    def formatted_name(self):
        return format_texture_name(self.hash, self.filter_label(), self.texture_name)

    def refresh_display_name(self):
        self.name = self.formatted_name()

    def get_applied_filename(self):
        if self.filter_type == FILTER_UNMARKED:
            return f"{self.rename_stem}.dds"
        filter_label = sanitize_filename_part(self.filter_label())
        return f"{self.rename_stem}-{filter_label}.dds"


class PostDumpFilteringSettings(bpy.types.PropertyGroup):
    textures: bpy.props.CollectionProperty(
        type=PostDumpTextureItem,
    ) # type: ignore

    active_texture_index: bpy.props.IntProperty(
        name="Texture Index",
        default=0,
        min=0,
    ) # type: ignore

    custom_filter_name: bpy.props.StringProperty(
        name="Custom Name",
        description="Name used when applying the Other texture category",
        default="",
    ) # type: ignore

    loaded_count: bpy.props.IntProperty(
        name="Loaded Textures",
        default=0,
        min=0,
    ) # type: ignore

    failed_count: bpy.props.IntProperty(
        name="Failed Textures",
        default=0,
        min=0,
    ) # type: ignore

    def get_active_texture(self):
        if 0 <= self.active_texture_index < len(self.textures):
            return self.textures[self.active_texture_index]
        return None
