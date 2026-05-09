import bpy

from .component_operators import (
    EFMI_PostDumpClearComponents,
    EFMI_PostDumpLoadComponents,
    EFMI_PostDumpPatchComponents,
)
from .operators import (
    EFMI_PostDumpApplyTextureNames,
    EFMI_PostDumpAutoFilterTextures,
    EFMI_PostDumpClearTextures,
    EFMI_PostDumpLoadTextures,
    EFMI_PostDumpSetTextureFilter,
)


class EFMI_TOOLS_UL_PostDumpTextures(bpy.types.UIList):
    bl_idname = "EFMI_TOOLS_UL_PostDumpTextures"

    def draw_item(self, context, layout, data, item, icon, active_data, active_propname, index):
        if self.layout_type in {"DEFAULT", "COMPACT"}:
            icon_value = item.preview_icon_id
            split = layout.split(factor=0.09)
            if icon_value:
                split.label(text="", icon_value=icon_value)
            else:
                split.label(text="", icon="ERROR" if not item.image_loaded else "IMAGE_DATA")

            columns = split.split(factor=0.28)
            columns.label(text=item.hash)
            details = columns.split(factor=0.34)
            details.label(text=item.filter_label())
            details.label(text=item.texture_name)
        elif self.layout_type == "GRID":
            layout.alignment = "CENTER"
            layout.label(text="", icon="IMAGE_DATA")


class EFMI_TOOLS_UL_PostDumpComponents(bpy.types.UIList):
    bl_idname = "EFMI_TOOLS_UL_PostDumpComponents"

    def draw_item(self, context, layout, data, item, icon, active_data, active_propname, index):
        if self.layout_type in {"DEFAULT", "COMPACT"}:
            split = layout.split(factor=0.38)
            split.label(text=item.mesh_name, icon="MESH_DATA")

            details = split.split(factor=0.22)
            details.label(text=f"LoDs: {item.lod_count}")

            toggles = details.split(factor=0.5)
            lod_toggle = toggles.row(align=True)
            lod_toggle.enabled = not item.remove_component
            lod_toggle.prop(item, "clear_lods", text="Clear LoDs")
            toggles.prop(item, "remove_component", text="Delete")
        elif self.layout_type == "GRID":
            layout.alignment = "CENTER"
            layout.label(text="", icon="MESH_DATA")


def draw_texture_preview(layout, texture):
    box = layout.box()
    split = box.split(factor=0.42)

    preview_col = split.column()
    if texture.image:
        icon_value = texture.preview_icon_id
        if icon_value:
            preview_col.template_icon(icon_value=icon_value, scale=8.0)
        else:
            preview_col.label(text="Preview unavailable", icon="IMAGE_DATA")
    else:
        preview_col.label(text="Preview unavailable", icon="IMAGE_DATA")

    info_col = split.column()
    info_col.label(text=texture.hash)
    info_col.label(text=texture.filter_label())
    info_col.label(text=texture.texture_name)

    if texture.image:
        size = texture.image.size
        info_col.label(text=f"{size[0]} x {size[1]}")


def draw_texture_filter_buttons(layout, cfg):
    row = layout.row(align=True)
    op = row.operator(EFMI_PostDumpSetTextureFilter.bl_idname, text="Diffuse")
    op.filter_type = "DIFFUSE"
    op = row.operator(EFMI_PostDumpSetTextureFilter.bl_idname, text="NormalMap")
    op.filter_type = "NORMAL_MAP"
    op = row.operator(EFMI_PostDumpSetTextureFilter.bl_idname, text="LightMap")
    op.filter_type = "LIGHT_MAP"
    op = row.operator(EFMI_PostDumpSetTextureFilter.bl_idname, text="Clear")
    op.filter_type = "UNMARKED"
    op = row.operator(EFMI_PostDumpSetTextureFilter.bl_idname, text="Delete")
    op.filter_type = "DELETE"

    custom_row = layout.row(align=True)
    custom_row.prop(cfg, "custom_filter_name", text="Other")
    op = custom_row.operator(EFMI_PostDumpSetTextureFilter.bl_idname, text="Set")
    op.filter_type = "OTHER"


def draw_component_details(layout, component):
    box = layout.box()
    header = box.split(factor=0.42)
    header.label(text=component.mesh_name, icon="MESH_DATA")
    header_stats = header.row(align=True)
    header_stats.label(text=f"Index: {component.index}")
    header_stats.label(text=f"LoDs: {component.lod_count}")

    split = box.split(factor=0.42)
    left_col = split.column()
    left_col.label(text=f"Vertices: {component.vertex_count}")
    left_col.label(text=f"Indices: {component.index_count}")
    right_col = split.column()
    right_col.label(text=f"IB: {component.ib_hash or 'Unknown'}")
    right_col.label(text=f"VB0: {component.vb0_hash or 'Unknown'}")

    if len(component.lods) == 0:
        box.label(text="No LoD metadata.", icon="INFO")
        return

    box.separator()
    for lod in component.lods:
        box.label(text=f"LoD {lod.index + 1}", icon="MESH_DATA")
        lod_split = box.split(factor=0.42)

        lod_left = lod_split.column()
        lod_left.label(text=f"Vertices: {lod.vertex_count}")
        lod_left.label(text=f"Indices: {lod.index_count}")

        lod_right = lod_split.column()
        lod_right.label(text=f"IB: {lod.ib_hash or 'Unknown'}")
        lod_right.label(text=f"VB0: {lod.vb0_hash or 'Unknown'}")


def draw_menu_post_dump_filtering(layout, context):
    settings = context.scene.efmi_tools_settings
    cfg = settings.post_dump_filtering

    layout.row()
    row = layout.row()
    row.prop(settings, "object_source_folder", text="Source")

    layout.row()

    box = layout.box()
    box.label(text="Texture Filtering", icon="IMAGE_DATA")

    row = box.row(align=True)
    row.operator(EFMI_PostDumpLoadTextures.bl_idname, icon="FILE_REFRESH")
    #for now i'll let this out since it needs some work to be useful and not just a gimmick, 
    # and i want to focus on the manual filtering first
    # row.operator(EFMI_PostDumpAutoFilterTextures.bl_idname, text="Auto Filtering")
    row.operator(EFMI_PostDumpClearTextures.bl_idname, text="Clear", icon="TRASH")

    if cfg.loaded_count or cfg.failed_count:
        status = f"Loaded: {len(cfg.textures)}"
        if cfg.failed_count:
            status += f" | Failed: {cfg.failed_count}"
        box.label(text=status, icon="INFO")

    if len(cfg.textures) == 0:
        box.label(text="Choose an object sources folder and load .dds textures.", icon="INFO")
    else:
        box.template_list(
            EFMI_TOOLS_UL_PostDumpTextures.bl_idname,
            "",
            cfg,
            "textures",
            cfg,
            "active_texture_index",
            rows=8,
        )

        texture = cfg.get_active_texture()
        if texture is not None:
            draw_texture_preview(box, texture)
            draw_texture_filter_buttons(box, cfg)
            box.row().operator(EFMI_PostDumpApplyTextureNames.bl_idname, text="Apply")

    layout.row()
    draw_dump_components(layout, context)


def draw_dump_components(layout, context):
    cfg = context.scene.efmi_tools_settings.post_dump_filtering

    box = layout.box()
    box.label(text="Dump Components", icon="MESH_DATA")

    row = box.row(align=True)
    row.operator(EFMI_PostDumpLoadComponents.bl_idname, icon="FILE_REFRESH")
    row.operator(EFMI_PostDumpClearComponents.bl_idname, text="Clear", icon="TRASH")

    if len(cfg.components) == 0:
        box.label(text="Load components to patch Metadata.json and component files.", icon="INFO")
        return

    box.template_list(
        EFMI_TOOLS_UL_PostDumpComponents.bl_idname,
        "",
        cfg,
        "components",
        cfg,
        "active_component_index",
        rows=7,
    )

    component = cfg.get_active_component()
    if component is not None:
        draw_component_details(box, component)

    box.row().operator(EFMI_PostDumpPatchComponents.bl_idname, text="Patch Dump", icon="CHECKMARK")
