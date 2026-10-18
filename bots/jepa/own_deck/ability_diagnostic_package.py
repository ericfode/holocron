"""Byte-only immutable packaging; no scientific imports, scoring or execution.

Default preparation is read-only. ROOT builds only after the three campaign
closures are independently verified. Linked historical evidence is not copied.
"""
import argparse
import gzip
import hashlib
import io
import json
import os
from pathlib import Path, PurePosixPath
import shutil
import tempfile

HERE = Path(__file__).resolve().parent
EXPERIMENTS = HERE.parents[3] / 'experiments'
NAMES = ('ability-diagnostic-v1', 'ability-correction-v1', 'ability-correction-verification-v1')
ROOTS = {name: EXPERIMENTS / name for name in NAMES}
PRIOR = HERE / 'semantic-discrimination-evidence' / 'manifest.json'
PRIOR_SHA = 'cee8cd7d8ad193057dc3584287f6a4937008391069f4d275d7c8abd95fbcdedb'
COMMITS = ('66c3780e3452d62078c4e4cb19f952719ba94204', '48215e6717b1cc4f6f271786ae2e70b7a191a5da')
EXTENSIONS = {'.json', '.jsonl', '.npz', '.log', '.txt', '.md', '.py', '.rs', '.toml', '.patch', '.diff'}
SKIP_DIRS = {'target', '__pycache__', '.git', '.venv', 'cache', 'buildcache'}
BINARY = 'ability-correction-native-collector'
MAX_SINGLE = 64 * 1024 * 1024
MAX_TOTAL = 128 * 1024 * 1024
MAX_FILES = 1000  # Includes index.json and manifest.json.
MAX_MANIFEST = 4 * 1024 * 1024
LIMITS = dict(single_raw_bytes=MAX_SINGLE, single_stored_bytes=MAX_SINGLE,
              total_raw_bytes=MAX_TOTAL, total_stored_bytes=MAX_TOTAL,
              files=MAX_FILES, manifest_bytes=MAX_MANIFEST)


def digest(data): return hashlib.sha256(data).hexdigest()
def encode(value): return (json.dumps(value, sort_keys=True, indent=2, allow_nan=False) + '\n').encode()
def require(value, message):
    if not value: raise ValueError(message)


def read_limited(path, limit):
    require(path.stat().st_size <= limit, 'file exceeds size limit: ' + str(path))
    with path.open('rb') as stream: data = stream.read(limit + 1)
    require(len(data) <= limit, 'file grew beyond size limit: ' + str(path))
    return data


def check_entries(entries):
    """Validate the complete size budget before reading or decoding any payload."""
    require(isinstance(entries, list) and len(entries) <= MAX_FILES - 1, 'payload file-count limit exceeded')
    for entry in entries:
        for field in ('raw_bytes', 'bytes'):
            require(type(entry.get(field)) is int and 0 <= entry[field] <= MAX_SINGLE,
                    field + ' exceeds single-payload size limit')
    require(sum(e['raw_bytes'] for e in entries) <= MAX_TOTAL, 'aggregate raw size limit exceeded')
    require(sum(e['bytes'] for e in entries) <= MAX_TOTAL, 'aggregate stored size limit exceeded')


def decode_limited(data, encoding, raw_bytes):
    require(encoding in ('identity', 'gzip'), 'unknown encoding')
    if encoding == 'identity': return data
    try:
        with gzip.GzipFile(fileobj=io.BytesIO(data), mode='rb') as stream:
            raw = stream.read(raw_bytes + 1)
    except (OSError, EOFError) as error:
        raise ValueError('invalid bounded gzip payload') from error
    require(len(raw) == raw_bytes, 'decoded size differs from declared raw_bytes')
    return raw


def files_in(roots):
    result, excluded = [], []
    require(tuple(roots) == NAMES, 'exact three ordered campaigns required')
    for name, root in roots.items():
        root = Path(root)
        require(root.is_dir() and not root.is_symlink(), 'campaign directory absent/symlink: ' + name)
        for path in sorted(root.rglob('*')):
            relative = path.relative_to(root)
            if set(relative.parts) & SKIP_DIRS: continue
            require(not path.is_symlink(), 'symlink forbidden: ' + str(path))
            if not path.is_file(): continue
            if path.name != 'Cargo.lock' and path.name.endswith(('.lock', '.lease')): continue
            if path.name == BINARY and len(relative.parts) == 2 and relative.parts[0].startswith('build-'):
                # Excluded build outputs are hashed incrementally, never decoded.
                h = hashlib.sha256()
                with path.open('rb') as stream:
                    for block in iter(lambda: stream.read(1024 * 1024), b''): h.update(block)
                excluded.append(dict(path=name+'/'+relative.as_posix(), reason='compiled binary excluded', sha256=h.hexdigest(), bytes=path.stat().st_size))
                continue
            require(path.suffix in EXTENSIONS or path.name == 'Cargo.lock', 'unreviewed campaign file: ' + str(path))
            result.append((name+'/'+relative.as_posix(), path))
            require(len(result) <= MAX_FILES - 2, 'campaign file-count limit exceeded')
    return result, excluded


def prepare(out, roots=None, prior_manifest=PRIOR, prior_sha=PRIOR_SHA):
    """Inventory only; no package directory, ledger or source is modified."""
    out = Path(out).resolve(); roots = ROOTS if roots is None else roots
    require(not out.exists(), 'immutable destination already exists')
    require(all(not out.is_relative_to(Path(p).resolve()) and not Path(p).resolve().is_relative_to(out)
                for p in roots.values()), 'destination overlaps a campaign')
    prior = Path(prior_manifest); prior_bytes = read_limited(prior, MAX_MANIFEST)
    require(digest(prior_bytes) == prior_sha, 'historical packet manifest mismatch')
    paths, excluded = files_in(roots); entries = []
    for logical, path in paths:
        raw = read_limited(path, MAX_SINGLE); compressed = path.suffix in ('.json', '.jsonl')
        stored = gzip.compress(raw, compresslevel=9, mtime=0) if compressed else raw
        entries.append(dict(path='raw/'+logical+('.gz' if compressed else ''), encoding='gzip' if compressed else 'identity',
            raw_sha256=digest(raw), raw_bytes=len(raw), sha256=digest(stored), bytes=len(stored),
            provenance=dict(original_path=str(path.resolve()))))
        check_entries(entries)
    return dict(schema='jepa-ability-diagnostic-package-plan/1', files=entries, excluded=excluded,
        packager_source_sha256=digest(Path(__file__).read_bytes()),
        limits=dict(LIMITS),
        historical_reference=dict(path='../semantic-discrimination-evidence/manifest.json', sha256=prior_sha, bytes=len(prior_bytes)),
        frozen_source_commits=list(COMMITS), semantic_validated=False,
        scope='Three new campaign trees only; old checkpoints remain in the linked PR41 packet. Packaging is not scientific verification.')


def build(out, roots=None, prior_manifest=PRIOR, prior_sha=PRIOR_SHA):
    """One immutable atomic directory publication; never overwrite old bytes."""
    out = Path(out).resolve(); roots = ROOTS if roots is None else roots
    plan = prepare(out, roots, prior_manifest, prior_sha)
    out.parent.mkdir(parents=True, exist_ok=True)
    temporary = Path(tempfile.mkdtemp(prefix='.'+out.name+'-', dir=out.parent))
    try:
        for entry in plan['files']:
            raw = read_limited(Path(entry['provenance']['original_path']), MAX_SINGLE)
            require(digest(raw) == entry['raw_sha256'] and len(raw) == entry['raw_bytes'], 'source changed during packaging')
            data = gzip.compress(raw, compresslevel=9, mtime=0) if entry['encoding'] == 'gzip' else raw
            require(digest(data) == entry['sha256'] and len(data) == entry['bytes'], 'stored bytes changed')
            path = temporary / entry['path']; path.parent.mkdir(parents=True, exist_ok=True); path.write_bytes(data)
        require(prepare(out, roots, prior_manifest, prior_sha) == plan, 'campaign membership/content changed during packaging')
        index = dict(schema='jepa-ability-diagnostic-evidence/1', manifest='manifest.json',
            campaigns=list(NAMES), historical_reference=plan['historical_reference'],
            frozen_source_commits=list(COMMITS), semantic_validated=False)
        index_bytes = encode(index); (temporary/'index.json').write_bytes(index_bytes)
        manifest = dict(plan, schema='jepa-ability-diagnostic-evidence-manifest/1')
        manifest['files'] = plan['files'] + [dict(path='index.json', encoding='identity', raw_sha256=digest(index_bytes),
            raw_bytes=len(index_bytes), sha256=digest(index_bytes), bytes=len(index_bytes))]
        check_entries(manifest['files']); manifest_bytes=encode(manifest)
        require(len(manifest_bytes) <= MAX_MANIFEST, 'manifest size limit exceeded')
        (temporary/'manifest.json').write_bytes(manifest_bytes)
        verify(temporary); require(not out.exists(), 'immutable destination appeared'); os.rename(temporary, out)
        return verify(out)
    except BaseException:
        shutil.rmtree(temporary); raise


def verify(out, expected_manifest_sha=None):
    """Offline exact-membership verification; provenance paths are never fetched."""
    out = Path(out); require(not out.is_symlink() and not (out/'manifest.json').is_symlink(), 'packet/manifest symlink forbidden')
    manifest_bytes = read_limited(out/'manifest.json', MAX_MANIFEST)
    if expected_manifest_sha is not None: require(digest(manifest_bytes) == expected_manifest_sha, 'manifest pin mismatch')
    manifest = json.loads(manifest_bytes)
    require(manifest['schema'] == 'jepa-ability-diagnostic-evidence-manifest/1', 'manifest schema differs')
    require(manifest.get('limits') == LIMITS, 'fixed packaging limits differ')
    check_entries(manifest['files'])
    expected = {'manifest.json'}
    for entry in manifest['files']:
        name = entry['path']; relative = PurePosixPath(name)
        require(relative.as_posix() == name and not relative.is_absolute() and not set(relative.parts)&{'..','.'}
                and '\\' not in name and ':' not in name and name not in expected, 'unsafe/duplicate payload path')
        expected.add(name); path = out/name
        require(not path.is_symlink() and path.resolve().is_relative_to(out.resolve()), 'payload escapes packet')
        data = read_limited(path, entry['bytes']); require(digest(data) == entry['sha256'] and len(data) == entry['bytes'], 'stored pin mismatch')
        raw = decode_limited(data, entry['encoding'], entry['raw_bytes'])
        require(digest(raw) == entry['raw_sha256'] and len(raw) == entry['raw_bytes'], 'decoded pin mismatch')
    actual = {p.relative_to(out).as_posix() for p in out.rglob('*') if p.is_file() or p.is_symlink()}
    require(actual == expected, 'packet membership differs')
    return dict(status='verified-bytes-only', manifest_sha256=digest(manifest_bytes), files=len(actual),
                raw_payload_bytes=sum(e['raw_bytes'] for e in manifest['files']),
                stored_payload_bytes=sum(e['bytes'] for e in manifest['files']), semantic_validated=False)


def main():
    parser=argparse.ArgumentParser(); group=parser.add_mutually_exclusive_group()
    group.add_argument('--prepare',action='store_true');group.add_argument('--build',action='store_true');group.add_argument('--verify',action='store_true')
    parser.add_argument('--out',type=Path,required=True);parser.add_argument('--expected-manifest-sha')
    args=parser.parse_args()
    value=verify(args.out,args.expected_manifest_sha) if args.verify else build(args.out) if args.build else prepare(args.out)
    print(json.dumps(value,sort_keys=True,indent=2,allow_nan=False))


if __name__=='__main__': main()
