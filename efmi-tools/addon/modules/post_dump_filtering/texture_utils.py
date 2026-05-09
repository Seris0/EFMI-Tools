import re
from dataclasses import dataclass


FILTER_UNMARKED = "UNMARKED"
FILTER_DIFFUSE = "DIFFUSE"
FILTER_NORMAL_MAP = "NORMAL_MAP"
FILTER_LIGHT_MAP = "LIGHT_MAP"
FILTER_OTHER = "OTHER"
FILTER_DELETE = "DELETE"


@dataclass(frozen=True)
class TextureFilterDefinition:
    identifier: str
    label: str
    description: str
    parseable_label: bool = True

    def enum_item(self):
        return self.identifier, self.label, self.description


TEXTURE_FILTERS = (
    TextureFilterDefinition(
        FILTER_UNMARKED,
        "Unmarked",
        "Texture has not been categorized yet",
        parseable_label=False,
    ),
    TextureFilterDefinition(FILTER_DIFFUSE, "Diffuse", "Diffuse texture"),
    TextureFilterDefinition(FILTER_NORMAL_MAP, "NormalMap", "Normalmap texture"),
    TextureFilterDefinition(FILTER_LIGHT_MAP, "LightMap", "Lightmap texture"),
    TextureFilterDefinition(
        FILTER_OTHER,
        "Other",
        "Custom texture category",
        parseable_label=False,
    ),
    TextureFilterDefinition(FILTER_DELETE, "Delete", "Delete texture from the dump folder"),
)

TEXTURE_FILTER_ITEMS = tuple(definition.enum_item() for definition in TEXTURE_FILTERS)
TEXTURE_FILTERS_BY_IDENTIFIER = {definition.identifier: definition for definition in TEXTURE_FILTERS}
APPLIED_FILTER_TYPES_BY_LABEL = {
    definition.label: definition.identifier
    for definition in TEXTURE_FILTERS
    if definition.parseable_label
}

HASH_PATTERNS = (
    re.compile(r"(?i)(?:^|[\s_-])t[-=_](?P<hash>[a-f0-9]{7,16})(?=$|[\s_.-])"),
    re.compile(r"(?i)(?:^|-)[a-z]+-t\d+=(?P<hash>[a-f0-9]{7,16})(?=$|[\s_.-])"),
    re.compile(r"(?i)(?P<hash>[a-f0-9]{7,16})(?=$|[\s_.-])"),
)

TEXTURE_FORMAT_SUFFIX_PATTERN = re.compile(
    r"(?ix)"
    r"[\s_-]+"
    r"("
    r"BC[1-7](?:[\s_-]*(?:UNORM|SNORM|SRGB|LINEAR))*"
    r"|R(?:\d+G?){1,4}(?:[\s_-]*(?:FLOAT|UNORM|SNORM|UINT|SINT|TYPELESS))*"
    r")$"
)
INVALID_FILENAME_CHARS_PATTERN = re.compile(r'[<>:"/\\|?*\x00-\x1f]')


@dataclass(frozen=True)
class AppliedFilter:
    base_stem: str
    filter_type: str
    custom_filter_name: str = ""


@dataclass(frozen=True)
class TextureNameInfo:
    hash: str
    texture_name: str


def iter_dds_texture_paths(source_folder):
    return sorted(
        (
            path
            for path in source_folder.rglob("*")
            if path.is_file() and str(path).lower().endswith(".dds")
        ),
        key=lambda path: str(path).lower(),
    )


def infer_texture_filter_type(path):
    stem = split_applied_filter(path.stem).base_stem.upper()
    if "BC5" in stem:
        return FILTER_NORMAL_MAP
    if "BC7" in stem and "SRGB" in stem:
        return FILTER_DIFFUSE
    if "BC7" in stem and "LINEAR" in stem:
        return FILTER_LIGHT_MAP
    return ""


def split_applied_filter(stem):
    legacy_base_stem, separator, filter_label = stem.rpartition(" - ")
    if separator and TEXTURE_FORMAT_SUFFIX_PATTERN.search(legacy_base_stem):
        filter_type = APPLIED_FILTER_TYPES_BY_LABEL.get(filter_label, FILTER_OTHER)
        custom_filter_name = filter_label if filter_type == FILTER_OTHER else ""
        return AppliedFilter(
            base_stem=legacy_base_stem,
            filter_type=filter_type,
            custom_filter_name=custom_filter_name,
        )

    for label, filter_type in APPLIED_FILTER_TYPES_BY_LABEL.items():
        suffix = f"-{label}"
        if stem.endswith(suffix):
            base_stem = stem[:-len(suffix)]
            if TEXTURE_FORMAT_SUFFIX_PATTERN.search(base_stem):
                return AppliedFilter(base_stem=base_stem, filter_type=filter_type)

    return AppliedFilter(base_stem=stem, filter_type=FILTER_UNMARKED)


def strip_texture_format(stem):
    previous = None
    current = stem.strip()
    while previous != current:
        previous = current
        current = TEXTURE_FORMAT_SUFFIX_PATTERN.sub("", current).strip()
    return current


def find_hash(stem):
    for pattern in HASH_PATTERNS:
        match = pattern.search(stem)
        if match:
            return match.group("hash")
    return ""


def strip_hash(stem, hash_value):
    if not hash_value:
        return stem

    patterns = (
        rf"(?i)(?:^|[\s_-])[a-z]+-t\d+={re.escape(hash_value)}(?=$|[\s_.-])",
        rf"(?i)(?:^|[\s_-])t[-=_]?{re.escape(hash_value)}(?=$|[\s_.-])",
        rf"(?i)(?:^|[\s_-]){re.escape(hash_value)}(?=$|[\s_.-])",
    )

    result = stem
    for pattern in patterns:
        result = re.sub(pattern, " ", result).strip()
    return result


def parse_texture_name(path):
    stem = strip_texture_format(split_applied_filter(path.stem).base_stem)
    hash_value = find_hash(stem)
    texture_name = strip_hash(stem, hash_value).strip(" -_")

    if not hash_value:
        hash_value = stem

    if not texture_name:
        texture_name = "Texture"

    return TextureNameInfo(hash=hash_value, texture_name=f"{texture_name}{path.suffix}")


def get_texture_filter_label(filter_type, custom_filter_name=""):
    if filter_type == FILTER_OTHER:
        return custom_filter_name.strip() or TEXTURE_FILTERS_BY_IDENTIFIER[FILTER_OTHER].label
    filter_definition = TEXTURE_FILTERS_BY_IDENTIFIER.get(
        filter_type,
        TEXTURE_FILTERS_BY_IDENTIFIER[FILTER_UNMARKED],
    )
    return filter_definition.label


def format_texture_name(hash_value, filter_label, texture_name):
    return f"{hash_value} - {filter_label} - {texture_name}"


def sanitize_filename_part(value):
    sanitized_value = INVALID_FILENAME_CHARS_PATTERN.sub("_", value).strip()
    return sanitized_value.rstrip(".") or "Other"
