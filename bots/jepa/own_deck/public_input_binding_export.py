"""Copy a portable immutable evidence closure. No scientific computation.

Preview is the default. --build creates a NEW directory; --verify reads only
that bundle unless --check-originals is explicitly supplied. No publisher,
stable pointer, engine, model, numerical fit, or network client is used.
"""
import argparse
import gzip
import hashlib
import io
import json
import mimetypes
from pathlib import Path, PurePosixPath
import re

INDEX_SCHEMA = "jepa-public-input-binding-evidence/1"
MANIFEST_SCHEMA = "jepa-public-input-binding-manifest/1"
REQUIRED = {"data", "scores", "causal-pairs", "encoding-controls", "contract", "verification", "accounting"}
ROLES = REQUIRED | {"source", "report"}
IDENTIFIER = re.compile(r"[A-Za-z0-9][A-Za-z0-9._-]*\Z")
SHA = re.compile(r"[0-9a-f]{64}\Z")
DEFAULT_OUT = Path(__file__).resolve().parent / "public-input-binding-evidence"
DEFAULT_GZIP_THRESHOLD = 131072


def require(value, message):
    if not value: raise ValueError(message)


def digest(raw): return hashlib.sha256(raw).hexdigest()
def encoded(value): return (json.dumps(value, sort_keys=True, indent=2, ensure_ascii=False, allow_nan=False) + "\n").encode()


def read_json(path):
    return json.loads(Path(path).read_text(), parse_constant=lambda value: (_ for _ in ()).throw(ValueError("nonfinite JSON constant: " + value)))


def file_pin(path):
    path = Path(path).resolve(strict=True)
    require(path.is_file(), "regular source file required: " + str(path))
    raw = path.read_bytes()
    return dict(path=str(path), sha256=digest(raw), bytes=len(raw))


def artifact(identifier, role, path, sha256=None, size=None, **provenance):
    require(isinstance(identifier, str) and IDENTIFIER.fullmatch(identifier), "safe unique artifact id required")
    require(role in ROLES, "unsupported artifact role: " + str(role))
    result = dict(id=identifier, role=role, path=str(Path(path).resolve(strict=True)), provenance=provenance)
    if sha256 is not None:
        require(isinstance(sha256, str) and SHA.fullmatch(sha256), "lowercase SHA256 required")
        result["expected_sha256"] = sha256
    if size is not None:
        require(type(size) is int and size >= 0, "nonnegative integral byte count required")
        result["expected_bytes"] = size
    return result


def parse_artifact(value):
    fields = value.split(":", 2)
    require(len(fields) == 3, "--artifact must be id:role:path")
    return artifact(*fields)


def artifact_manifest(path):
    """An explicit array, or {artifacts:[{id,role,path,sha256?,bytes?}]}.

    Relative artifact paths are relative to this descriptor, never the CWD.
    The descriptor itself is preserved byte-for-byte as a contract artifact.
    """
    path = Path(path).resolve(strict=True); raw = read_json(path)
    entries = raw if isinstance(raw, list) else raw["artifacts"]
    require(isinstance(entries, list), "artifact manifest must declare a list")
    result = []
    for row in entries:
        target = Path(row["path"])
        if not target.is_absolute(): target = path.parent / target
        result.append(artifact(row["id"], row["role"], target, row.get("sha256"), row.get("bytes"), artifact_manifest=str(path)))
    result.append(artifact("artifact-list-" + digest(path.read_bytes())[:16], "contract", path))
    return result


def direct_config_pins(value, pointer=""):
    """Visit only pin objects explicitly contained in the supplied config.

    Do not interpret arbitrary path strings or recursively follow artifact JSON.
    Every declared pin is retained intact alongside its resolved actual pin.
    """
    found = []
    if isinstance(value, dict):
        if "path" in value and "sha256" in value:
            require(isinstance(value["path"], str) and isinstance(value["sha256"], str) and SHA.fullmatch(value["sha256"]), "malformed direct config source pin")
            if "bytes" in value: require(type(value["bytes"]) is int and value["bytes"] >= 0, "invalid config source byte count")
            found.append(dict(pointer=pointer or "/", declared_pin=value))
        for key, child in value.items():
            escaped = str(key).replace("~", "~0").replace("/", "~1")
            found.extend(direct_config_pins(child, pointer + "/" + escaped))
    elif isinstance(value, list):
        for i, child in enumerate(value): found.extend(direct_config_pins(child, pointer + "/" + str(i)))
    return found


def collect(config, artifacts, expected_config_sha256=None):
    config = Path(config).resolve(strict=True); config_raw = config.read_bytes()
    if expected_config_sha256 is not None: require(digest(config_raw) == expected_config_sha256, "campaign config byte hash changed")
    entries = list(artifacts) + [artifact("campaign-config", "contract", config), artifact("packaging-helper", "source", __file__)]
    pin_records = []
    for i, record in enumerate(direct_config_pins(read_json(config))):
        declared = record["declared_pin"]; path = Path(declared["path"])
        if not path.is_absolute(): path = config.parent / path
        entry = artifact("config-source-" + str(i).zfill(4), "source", path, declared["sha256"], declared.get("bytes"), config_pointer=record["pointer"])
        actual = file_pin(path)
        require(actual["sha256"] == declared["sha256"] and ("bytes" not in declared or actual["bytes"] == declared["bytes"]), "direct config source pin changed: " + str(path))
        pin_records.append(dict(**record, resolved_pin=actual, artifact_id=entry["id"])); entries.append(entry)
    require(len({entry["id"] for entry in entries}) == len(entries), "duplicate artifact id (campaign-config/packaging-helper are reserved)")
    require(REQUIRED <= {entry["role"] for entry in entries}, "missing required artifact roles: " + str(sorted(REQUIRED - {entry["role"] for entry in entries})))
    captured = []
    for entry in sorted(entries, key=lambda e:e["id"]):
        pin = file_pin(entry["path"]); raw = Path(pin["path"]).read_bytes()
        require(digest(raw) == pin["sha256"] and len(raw) == pin["bytes"], "source changed during read")
        require("expected_sha256" not in entry or pin["sha256"] == entry["expected_sha256"], "artifact hash differs: " + entry["id"])
        require("expected_bytes" not in entry or pin["bytes"] == entry["expected_bytes"], "artifact byte count differs: " + entry["id"])
        captured.append(dict(entry=entry, pin=pin, raw=raw))
    return captured, pin_records, file_pin(config)


def deterministic_gzip(raw):
    stream = io.BytesIO()
    with gzip.GzipFile(filename="", mode="wb", fileobj=stream, compresslevel=9, mtime=0) as writer: writer.write(raw)
    result = stream.getvalue()
    require(gzip.decompress(result) == raw, "gzip roundtrip failed")
    return result


def store_plan(captured, gzip_threshold):
    require(type(gzip_threshold) is int and gzip_threshold >= 0, "nonnegative integral gzip threshold")
    groups = {}
    for item in captured:
        key = item["pin"]["sha256"]
        if key in groups: require(groups[key][0]["raw"] == item["raw"], "SHA256 collision or inconsistent captured bytes")
        groups.setdefault(key, []).append(item)
    payloads = {}; logical = []
    for key, items in sorted(groups.items()):
        raw = items[0]["raw"]
        json_like = any(Path(x["pin"]["path"]).suffix.lower() in (".json", ".jsonl", ".ndjson") for x in items)
        encoding = "gzip" if json_like and len(raw) >= gzip_threshold else "identity"
        stored = deterministic_gzip(raw) if encoding == "gzip" else raw
        extension = ".json" if json_like else ".bin"
        url = "raw/" + key + extension + (".gz" if encoding == "gzip" else "")
        payload = dict(url=url, sha256=digest(stored), bytes=len(stored), encoding=encoding, raw_sha256=key, raw_bytes=len(raw))
        payloads[url] = dict(metadata=payload, stored=stored)
        for item in items:
            entry=item["entry"]
            logical.append(dict(id=entry["id"], role=entry["role"], **payload,
                media_type=mimetypes.guess_type(item["pin"]["path"])[0] or "application/octet-stream",
                provenance=dict(original_path=item["pin"]["path"], **entry.get("provenance", {}))))
    return payloads, sorted(logical, key=lambda e:e["id"])


def safe_path(root, url):
    require(isinstance(url, str) and url and not any(c in url for c in ("\\", "%", "?", "#", ":")), "unsafe bundle relative URL")
    relative = PurePosixPath(url)
    require(not relative.is_absolute() and all(p not in ("", ".", "..") for p in url.split("/")), "bundle URL must stay relative and canonical")
    root = Path(root).resolve(strict=True); target = root.joinpath(*relative.parts)
    for parent in [target, *target.parents]:
        if parent == root: break
        require(not parent.is_symlink(), "bundle symlink is forbidden")
    require(target.resolve().is_relative_to(root), "bundle URL escaped root")
    return target


def exclusive_write(path, raw):
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("xb") as writer: writer.write(raw)


def build(config, out, artifacts, gzip_threshold=DEFAULT_GZIP_THRESHOLD, expected_config_sha256=None):
    out = Path(out).absolute()
    require(not out.exists(), "bundle already exists; immutable outputs are never overwritten")
    captured, pin_records, config_pin = collect(config, artifacts, expected_config_sha256)
    payloads, logical = store_plan(captured, gzip_threshold)
    # The output directory is exclusive. Partial failures remain visible and
    # cannot be retried into the same path or erase an older archive.
    out.mkdir(parents=True, exist_ok=False)
    for url, item in payloads.items(): exclusive_write(out/url, item["stored"])
    for item in captured: require(file_pin(item["pin"]["path"]) == item["pin"], "original source changed during packaging")
    index = dict(schema=INDEX_SCHEMA, artifacts=logical,
        required_roles=sorted(REQUIRED), package_scope="Copied immutable evidence only; no vectors, fits, forwards, native actions or publishing.",
        source_paths_scope="Absolute source paths are provenance only. Consumers fetch relative url, never original filesystem paths.")
    index_raw = encoded(index); exclusive_write(out/"index.json", index_raw)
    files = [{key:item["metadata"][key]for key in("url","sha256","bytes")} for _, item in sorted(payloads.items())]
    files.append(dict(url="index.json", sha256=digest(index_raw), bytes=len(index_raw)))
    manifest = dict(schema=MANIFEST_SCHEMA, files=sorted(files, key=lambda p:p["url"]), artifacts=logical,
        payloads=[item["metadata"]for _,item in sorted(payloads.items())],
        direct_config_source_pins=pin_records, config_pin=config_pin, gzip_threshold=gzip_threshold,
        deduplication="Identical raw SHA256 stored once; all logical artifact/source references retained.",
        exact_closure="Every file except this externally pinned manifest is listed, including index.json. No index-to-manifest hash cycle.",
        totals=dict(logical_artifacts=len(logical), unique_payloads=len(payloads), unique_raw_bytes=sum(x["metadata"]["raw_bytes"] for x in payloads.values()), stored_payload_bytes=sum(x["metadata"]["bytes"] for x in payloads.values())),
        compute=dict(native_applies=0,neural_forwards=0,optimizer_updates=0,publishing_actions=0))
    exclusive_write(out/"manifest.json", encoded(manifest))
    verified=verify_bundle(out, check_originals=True)
    return dict(status="created-and-verified", bundle=str(out), index=file_pin(out/"index.json"), manifest=file_pin(out/"manifest.json"), **verified)


def verify_bundle(root, check_originals=False, expected_index_sha256=None, expected_manifest_sha256=None):
    root=Path(root).resolve(strict=True)
    require(root.is_dir(),"bundle directory required")
    index_path=safe_path(root,"index.json");manifest_path=safe_path(root,"manifest.json")
    if expected_index_sha256 is not None: require(file_pin(index_path)["sha256"]==expected_index_sha256,"external index pin differs")
    if expected_manifest_sha256 is not None: require(file_pin(manifest_path)["sha256"]==expected_manifest_sha256,"external manifest pin differs")
    index,manifest=read_json(index_path),read_json(manifest_path)
    require(index["schema"]==INDEX_SCHEMA and manifest["schema"]==MANIFEST_SCHEMA,"portable evidence schema differs")
    require(index["artifacts"]==manifest["artifacts"],"index and manifest artifact descriptors differ")
    entries=index["artifacts"];require(len({e["id"]for e in entries})==len(entries),"duplicate logical id")
    require(REQUIRED <= {e["role"]for e in entries},"required role missing")
    files={}
    for item in manifest["files"]:
        require(item["url"]not in files,"duplicate manifest file")
        require(type(item["bytes"])is int and item["bytes"]>=0 and isinstance(item["sha256"],str)and SHA.fullmatch(item["sha256"]),"invalid stored file pin")
        target=safe_path(root,item["url"]);raw=target.read_bytes()
        require(len(raw)==item["bytes"]and digest(raw)==item["sha256"],"stored artifact pin differs: "+item["url"])
        files[item["url"]]=item
    require("manifest.json"not in files and "index.json"in files,"manifest self-cycle or missing index")
    actual=set()
    for p in root.rglob("*"):
        require(not p.is_symlink(),"bundle symlink is forbidden")
        if p.is_file():actual.add(p.relative_to(root).as_posix())
    require(actual==set(files)|{"manifest.json"},"bundle has missing or unmanifested files")
    raw_descriptors={item["url"]:item for item in manifest["payloads"]}
    require(len(raw_descriptors)==len(manifest["payloads"])and set(raw_descriptors)==set(files)-{"index.json"},"decoded payload closure differs")
    payload_urls=set();source_refs={}
    for entry in entries:
        require(IDENTIFIER.fullmatch(entry["id"])and entry["role"]in ROLES,"artifact id/role invalid")
        url=entry["url"];require(url in files and url!="index.json","artifact URL lacks payload file")
        require(type(entry["bytes"])is int and type(entry["raw_bytes"])is int and entry["bytes"]>=0 and entry["raw_bytes"]>=0 and SHA.fullmatch(entry["sha256"])and SHA.fullmatch(entry["raw_sha256"]),"invalid artifact byte/hash pin")
        stored=safe_path(root,url).read_bytes()
        require(entry["sha256"]==digest(stored)and entry["bytes"]==len(stored),"index stored pin differs")
        require(entry["encoding"]in("gzip","identity"),"unknown byte encoding")
        raw=gzip.decompress(stored)if entry["encoding"]=="gzip"else stored
        require(digest(raw)==entry["raw_sha256"]and len(raw)==entry["raw_bytes"],"decoded raw pin differs")
        require(all(raw_descriptors[url].get(k)==entry[k]for k in("sha256","bytes","encoding","raw_sha256","raw_bytes")),"manifest decoded pin differs")
        payload_urls.add(url);source_refs[entry["id"]]=entry
        if check_originals:
            original=file_pin(entry["provenance"]["original_path"])
            require(original["sha256"]==entry["raw_sha256"]and original["bytes"]==entry["raw_bytes"],"original source changed")
    require(payload_urls==set(files)-{"index.json"},"unreferenced payload in closure")
    for item in manifest["direct_config_source_pins"]:
        entry=source_refs[item["artifact_id"]];declared=item["declared_pin"];resolved=item["resolved_pin"]
        require(entry["role"]=="source"and entry["raw_sha256"]==declared["sha256"]==resolved["sha256"],"direct config source hash not preserved")
        require(entry["raw_bytes"]==resolved["bytes"]and("bytes"not in declared or entry["raw_bytes"]==declared["bytes"]),"direct config source size not preserved")
        require(entry["provenance"]["original_path"]==resolved["path"],"source provenance drift")
    # Re-derive the complete declared source-pin list from the bundled config,
    # without accessing its original private/local filesystem path.
    config_entry=source_refs["campaign-config"];stored=safe_path(root,config_entry["url"]).read_bytes()
    raw=gzip.decompress(stored)if config_entry["encoding"]=="gzip"else stored
    declared=direct_config_pins(json.loads(raw))
    require(declared==[{"pointer":p["pointer"],"declared_pin":p["declared_pin"]}for p in manifest["direct_config_source_pins"]],"config source-pin closure incomplete")
    require(config_entry["raw_sha256"]==manifest["config_pin"]["sha256"]and config_entry["raw_bytes"]==manifest["config_pin"]["bytes"],"config exact bytes changed")
    return dict(verified=True, logical_artifacts=len(entries),unique_payloads=len(payload_urls),originals_checked=check_originals)


def main():
    parser=argparse.ArgumentParser(description=__doc__);group=parser.add_mutually_exclusive_group()
    group.add_argument("--build",action="store_true");group.add_argument("--verify",action="store_true")
    parser.add_argument("--config",type=Path);parser.add_argument("--out",type=Path,default=DEFAULT_OUT)
    parser.add_argument("--artifact",action="append",default=[]);parser.add_argument("--artifact-manifest",type=Path,action="append",default=[])
    parser.add_argument("--gzip-threshold",type=int,default=DEFAULT_GZIP_THRESHOLD);parser.add_argument("--config-sha256")
    parser.add_argument("--check-originals",action="store_true");parser.add_argument("--expected-index-sha256");parser.add_argument("--expected-manifest-sha256")
    args=parser.parse_args()
    if args.verify:
        print(json.dumps(verify_bundle(args.out,args.check_originals,args.expected_index_sha256,args.expected_manifest_sha256)));return
    require(args.config is not None,"explicit --config required for preview/build")
    entries=[parse_artifact(value)for value in args.artifact]
    for path in args.artifact_manifest:entries.extend(artifact_manifest(path))
    if args.build:result=build(args.config,args.out,entries,args.gzip_threshold,args.config_sha256)
    else:
        captured,records,config_pin=collect(args.config,entries,args.config_sha256);payloads,logical=store_plan(captured,args.gzip_threshold)
        result=dict(status="preview-no-write-no-science",config=config_pin,logical_artifacts=len(logical),unique_payloads=len(payloads),direct_config_source_pins=len(records),output=str(args.out))
    print(json.dumps(result,allow_nan=False))


if __name__=="__main__":main()
