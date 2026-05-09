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


class PostDumpComponentLodItem(bpy.types.PropertyGroup):
    index: bpy.props.IntProperty(
        name="Index",
        default=0,
        min=0,
    ) # type: ignore

    lod_object_name: bpy.props.StringProperty(
        name="LoD Object",
    ) # type: ignore

    vertex_count: bpy.props.IntProperty(
        name="Vertices",
        default=0,
        min=0,
    ) # type: ignore

    index_count: bpy.props.IntProperty(
        name="Indices",
        default=0,
        min=0,
    ) # type: ignore

    ib_hash: bpy.props.StringProperty(
        name="IB Hash",
    ) # type: ignore

    vb0_hash: bpy.props.StringProperty(
        name="VB0 Hash",
    ) # type: ignore


class PostDumpComponentItem(bpy.types.PropertyGroup):
    index: bpy.props.IntProperty(
        name="Index",
        default=0,
        min=0,
    ) # type: ignore

    mesh_name: bpy.props.StringProperty(
        name="Component",
    ) # type: ignore

    file_count: bpy.props.IntProperty(
        name="Files",
        default=0,
        min=0,
    ) # type: ignore

    lod_count: bpy.props.IntProperty(
        name="LoDs",
        default=0,
        min=0,
    ) # type: ignore

    vertex_count: bpy.props.IntProperty(
        name="Vertices",
        default=0,
        min=0,
    ) # type: ignore

    index_count: bpy.props.IntProperty(
        name="Indices",
        default=0,
        min=0,
    ) # type: ignore

    ib_hash: bpy.props.StringProperty(
        name="IB Hash",
    ) # type: ignore

    vb0_hash: bpy.props.StringProperty(
        name="VB0 Hash",
    ) # type: ignore

    lods: bpy.props.CollectionProperty(
        type=PostDumpComponentLodItem,
    ) # type: ignore

    remove_component: bpy.props.BoolProperty(
        name="Delete",
        description="Delete this component from the dump and reindex the remaining components",
        default=False,
    ) # type: ignore

    clear_lods: bpy.props.BoolProperty(
        name="Clear LoDs",
        description="Remove this component's LoD metadata without deleting the component",
        default=False,
    ) # type: ignore

    def refresh_display_name(self):
        self.name = self.mesh_name or f"Component {self.index}"


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

    components: bpy.props.CollectionProperty(
        type=PostDumpComponentItem,
    ) # type: ignore

    active_component_index: bpy.props.IntProperty(
        name="Component Index",
        default=0,
        min=0,
    ) # type: ignore

    def get_active_texture(self):
        if 0 <= self.active_texture_index < len(self.textures):
            return self.textures[self.active_texture_index]
        return None

    def get_active_component(self):
        if 0 <= self.active_component_index < len(self.components):
            return self.components[self.active_component_index]
        return None
