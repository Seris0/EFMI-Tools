import json
from dataclasses import dataclass
from pathlib import Path
from uuid import uuid4


COMPONENT_FILE_SUFFIXES = {".buf", ".fmt", ".ib", ".vb"}


@dataclass(frozen=True)
class DumpComponentLodInfo:
    index: int
    lod_object_name: str
    vertex_count: int
    index_count: int
    ib_hash: str
    vb0_hash: str


@dataclass(frozen=True)
class DumpComponentInfo:
    index: int
    mesh_name: str
    file_count: int
    lod_count: int
    vertex_count: int
    index_count: int
    ib_hash: str
    vb0_hash: str
    lods: tuple[DumpComponentLodInfo, ...]


@dataclass(frozen=True)
class PatchDumpComponentsResult:
    removed_components: int = 0
    removed_files: int = 0
    renamed_files: int = 0
    cleared_lods: int = 0
    remaining_components: int = 0
    texture_usage_updated: bool = False

    def report_message(self):
        return (
            f"Removed components: {self.removed_components}. "
            f"Removed files: {self.removed_files}. "
            f"Renamed files: {self.renamed_files}. "
            f"Cleared LoDs: {self.cleared_lods}. "
            f"Remaining components: {self.remaining_components}."
        )


def metadata_path(source_folder):
    return source_folder / "Metadata.json"


def texture_usage_path(source_folder):
    return source_folder / "TextureUsage.json"


def load_metadata(source_folder):
    path = metadata_path(source_folder)
    with path.open("r", encoding="utf-8") as metadata_file:
        return json.load(metadata_file)


def write_json(path, data):
    temp_path = path.with_name(f"{path.name}.tmp")
    with temp_path.open("w", encoding="utf-8") as output_file:
        json.dump(data, output_file, indent=4)
        output_file.write("\n")
    temp_path.replace(path)


def find_component_files(source_folder, mesh_name):
    return sorted(
        (
            path
            for path in source_folder.iterdir()
            if path.is_file()
            and path.stem == mesh_name
            and path.suffix.lower() in COMPONENT_FILE_SUFFIXES
        ),
        key=lambda path: path.suffix.lower(),
    )


def list_dump_components(source_folder):
    metadata = load_metadata(source_folder)
    components = metadata.get("components")
    if not isinstance(components, list):
        raise ValueError("Metadata.json does not contain a valid components list.")

    result = []
    for index, component in enumerate(components):
        mesh_name = component.get("mesh_name") or f"Component {index}"
        files = find_component_files(source_folder, mesh_name)
        lods = component.get("lods") or []
        result.append(
            DumpComponentInfo(
                index=index,
                mesh_name=mesh_name,
                file_count=len(files),
                lod_count=len(lods),
                vertex_count=int(component.get("vertex_count") or 0),
                index_count=int(component.get("index_count") or 0),
                ib_hash=component.get("ib_hash") or "",
                vb0_hash=component.get("vb0_hash") or "",
                lods=tuple(
                    DumpComponentLodInfo(
                        index=lod_index,
                        lod_object_name=lod.get("lod_object_name") or f"LoD {lod_index + 1}",
                        vertex_count=int(lod.get("vertex_count") or 0),
                        index_count=int(lod.get("index_count") or 0),
                        ib_hash=lod.get("ib_hash") or "",
                        vb0_hash=lod.get("vb0_hash") or "",
                    )
                    for lod_index, lod in enumerate(lods)
                    if isinstance(lod, dict)
                ),
            )
        )
    return result


def reindex_texture_usage(source_folder, index_map):
    path = texture_usage_path(source_folder)
    if not path.is_file():
        return False

    with path.open("r", encoding="utf-8") as usage_file:
        usage = json.load(usage_file)

    if not isinstance(usage, dict):
        return False

    patched_usage = {}
    for old_index, new_index in index_map.items():
        old_key = f"Component {old_index}"
        if old_key in usage:
            patched_usage[f"Component {new_index}"] = usage[old_key]

    write_json(path, patched_usage)
    return True


def delete_component_files(source_folder, mesh_name):
    removed_count = 0
    for path in find_component_files(source_folder, mesh_name):
        path.unlink()
        removed_count += 1
    return removed_count


def rename_component_files(source_folder, old_mesh_name, new_mesh_name):
    if old_mesh_name == new_mesh_name:
        return 0

    temp_token = uuid4().hex
    temp_paths = []
    for path in find_component_files(source_folder, old_mesh_name):
        temp_path = path.with_name(f".efmi_patch_{temp_token}_{path.name}")
        path.rename(temp_path)
        temp_paths.append((temp_path, path.suffix))

    renamed_count = 0
    for temp_path, suffix in temp_paths:
        target_path = source_folder / f"{new_mesh_name}{suffix}"
        if target_path.exists():
            raise FileExistsError(f"Cannot rename component file, target already exists: {target_path}")
        temp_path.rename(target_path)
        renamed_count += 1

    return renamed_count


def patch_dump_components(source_folder, remove_indices, clear_lod_indices):
    metadata = load_metadata(source_folder)
    components = metadata.get("components")
    if not isinstance(components, list):
        raise ValueError("Metadata.json does not contain a valid components list.")

    remove_indices = set(remove_indices)
    clear_lod_indices = set(clear_lod_indices) - remove_indices

    kept_components = []
    index_map = {}
    cleared_lods = 0
    rename_tasks = []

    for old_index, component in enumerate(components):
        old_mesh_name = component.get("mesh_name") or f"Component {old_index}"
        if old_index in remove_indices:
            continue

        new_index = len(kept_components)
        new_mesh_name = f"Component {new_index}"
        if old_index in clear_lod_indices:
            cleared_lods += len(component.get("lods") or [])
            component["lods"] = []

        component["mesh_name"] = new_mesh_name
        kept_components.append(component)
        index_map[old_index] = new_index
        rename_tasks.append((old_mesh_name, new_mesh_name))

    metadata["components"] = kept_components
    metadata["vertex_count"] = sum(int(component.get("vertex_count") or 0) for component in kept_components)
    metadata["index_count"] = sum(int(component.get("index_count") or 0) for component in kept_components)

    temp_metadata_path = metadata_path(source_folder).with_name("Metadata.json.tmp")
    with temp_metadata_path.open("w", encoding="utf-8") as metadata_file:
        json.dump(metadata, metadata_file, indent=4)
        metadata_file.write("\n")

    removed_files = 0
    for old_index, component in enumerate(components):
        if old_index in remove_indices:
            mesh_name = component.get("mesh_name") or f"Component {old_index}"
            removed_files += delete_component_files(source_folder, mesh_name)

    renamed_files = 0
    for old_mesh_name, new_mesh_name in rename_tasks:
        renamed_files += rename_component_files(source_folder, old_mesh_name, new_mesh_name)

    temp_metadata_path.replace(metadata_path(source_folder))
    texture_usage_updated = reindex_texture_usage(source_folder, index_map)

    return PatchDumpComponentsResult(
        removed_components=len(remove_indices),
        removed_files=removed_files,
        renamed_files=renamed_files,
        cleared_lods=cleared_lods,
        remaining_components=len(kept_components),
        texture_usage_updated=texture_usage_updated,
    )
