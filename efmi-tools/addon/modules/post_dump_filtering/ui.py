import bpy

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


def draw_menu_post_dump_filtering(layout, context):
    settings = context.scene.efmi_tools_settings
    cfg = settings.post_dump_filtering

    layout.row()
    row = layout.row()
    row.prop(settings, "frame_dump_folder", text="Source")

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
        box.label(text="Choose a dump folder and load .dds textures.", icon="INFO")
        return

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
    if texture is None:
        return

    draw_texture_preview(box, texture)
    draw_texture_filter_buttons(box, cfg)

    box.row().operator(EFMI_PostDumpApplyTextureNames.bl_idname, text="Apply")
