"""Copy a finished campaign's bytes; no science imports or computations.

Root GO is required before `package`. `verify` checks only portable stored/raw
bytes and does not follow historical absolute references inside evidence files.
"""
import argparse
import gzip
import hashlib
import io
import json
import os
from pathlib import Path
import stat

HERE=Path(__file__).resolve().parent
EXPERIMENTS=HERE.parents[3]/'experiments'
ROOT_NAMES=('semantic-discrimination-v1','semantic-discrimination-repair-v1','semantic-discrimination-verification-v1')
DEFAULT_OUT=HERE/'semantic-discrimination-evidence'
SKIP_DIRS={'.git','__pycache__','target','node_modules','.venv','cache','caches'}
ARCHIVES={'.gz','.zip','.tar','.tgz','.bz2','.xz','.zst','.7z','.safetensors','.dylib','.so','.a','.rlib','.rmeta','.o','.exe'}


def require(ok,message):
    if not ok:raise ValueError(message)


def digest(data):return dict(sha256=hashlib.sha256(data).hexdigest(),bytes=len(data))
def pin(path):return dict(path=str(Path(path).resolve()),**digest(Path(path).read_bytes()))


def write_new(path,data):
    path.parent.mkdir(parents=True,exist_ok=True)
    with path.open('xb')as stream:stream.write(data);stream.flush();os.fsync(stream.fileno())


def encoded(value):return(json.dumps(value,sort_keys=True,indent=2,allow_nan=False)+'\n').encode()


def compressed(raw):
    stream=io.BytesIO()
    with gzip.GzipFile(fileobj=stream,mode='wb',filename='',compresslevel=9,mtime=0)as archive:archive.write(raw)
    return stream.getvalue()


def inventory(roots):
    """Never traverse a symlink; return stable relative names and exclusions."""
    files=[];excluded=[]
    for root in roots:
        root=Path(root)
        require(root.is_dir()and not root.is_symlink(),'complete non-symlink campaign root required: '+str(root))
        for directory,dirs,names in os.walk(root,followlinks=False):
            base=Path(directory)
            for name in list(dirs):
                path=base/name
                if path.is_symlink()or name in SKIP_DIRS or 'archive'in name.lower():
                    dirs.remove(name);excluded.append(dict(root=root.name,path=path.relative_to(root).as_posix(),reason='symlink'if path.is_symlink()else'cache-or-archive-directory'))
            for name in names:
                path=base/name;rel=path.relative_to(root).as_posix();reason=None
                if path.is_symlink():reason='symlink'
                elif not stat.S_ISREG(path.stat().st_mode):reason='nonregular-file'
                elif path.suffix.lower()in ARCHIVES:reason='archive-or-native-binary'
                if reason:excluded.append(dict(root=root.name,path=rel,reason=reason))
                else:files.append((root,rel,path))
    return sorted(files,key=lambda r:(r[0].name,r[1])),sorted(excluded,key=lambda r:(r['root'],r['path']))


def package(roots,out,source_commits):
    """Exclusive new output; failure leaves partial files for inspection."""
    roots=[Path(p).resolve()for p in roots];out=Path(out).resolve()
    require(len(roots)==3 and tuple(p.name for p in roots)==ROOT_NAMES,'exact three ordered campaign roots required')
    require(all(not out.is_relative_to(root)for root in roots),'output cannot be inside source campaign')
    require(source_commits and len(set(source_commits))==len(source_commits)and all(len(c)==40 and all(ch in'0123456789abcdef'for ch in c)for c in source_commits),'explicit unique source freeze commits required')
    files,excluded=inventory(roots);out.mkdir(parents=True,exist_ok=False);records=[];snapshots={}
    for root,rel,path in files:
        before=path.stat();raw=path.read_bytes();after=path.stat()
        require((before.st_size,before.st_mtime_ns,before.st_ino)==(after.st_size,after.st_mtime_ns,after.st_ino),'source changed while reading: '+str(path))
        snapshots[str(path)]=digest(raw)
        if path.suffix.lower()=='.npz':stored=raw;codec='identity';stored_name='raw/'+root.name+'/'+rel
        else:
            try:raw.decode('utf-8')
            except UnicodeDecodeError:excluded.append(dict(root=root.name,path=rel,reason='non-UTF8-native-or-opaque-binary'));continue
            if b'\0'in raw:excluded.append(dict(root=root.name,path=rel,reason='NUL-containing-native-or-opaque-binary'));continue
            stored=compressed(raw);codec='gzip';stored_name='raw/'+root.name+'/'+rel+'.gz'
        write_new(out/stored_name,stored)
        records.append(dict(campaign=root.name,original_path=str(path),relative_path=rel,raw=digest(raw),stored=dict(path=stored_name,codec=codec,**digest(stored))))
    final_files,final_excluded=inventory(roots)
    require([(str(p),rel)for _,rel,p in files]==[(str(p),rel)for _,rel,p in final_files],'source inventory changed during copy')
    for _,_,path in final_files:require(digest(path.read_bytes())==snapshots[str(path)],'source bytes changed during copy: '+str(path))
    manifest=dict(schema='jepa-semantic-discrimination-evidence-manifest/1',campaign_roots=[str(p)for p in roots],source_freeze_commits=list(source_commits),packager=pin(__file__),records=records,excluded=sorted(excluded,key=lambda r:(r['root'],r['path'])),
        files=len(records),raw_bytes=sum(r['raw']['bytes']for r in records),stored_bytes=sum(r['stored']['bytes']for r in records),semantic_validated=False,
        scope='Byte copies only. Failed attempts and journals retained. Historical absolute references remain origin provenance and are not reinterpreted or dereferenced by portable verification. No model/native/fitting/rescoring performed.')
    manifest_bytes=encoded(manifest);write_new(out/'manifest.json',manifest_bytes)
    index=dict(schema='jepa-semantic-discrimination-evidence/1',manifest=dict(path='manifest.json',**digest(manifest_bytes)),files=manifest['files'],raw_bytes=manifest['raw_bytes'],stored_bytes=manifest['stored_bytes'],source_freeze_commits=list(source_commits),semantic_validated=False)
    write_new(out/'index.json',encoded(index));verify(out);return index


def verify(out):
    """Verify exact file set, stored hashes, gzip decoding, and raw hashes."""
    out=Path(out).resolve();index=json.loads((out/'index.json').read_text());require(index['schema']=='jepa-semantic-discrimination-evidence/1','unknown index schema')
    mp=index['manifest'];require(mp['path']=='manifest.json','fixed manifest path required');raw=(out/mp['path']).read_bytes();require(digest(raw)=={k:mp[k]for k in('sha256','bytes')},'manifest pin mismatch');manifest=json.loads(raw)
    require(manifest['schema']=='jepa-semantic-discrimination-evidence-manifest/1','unknown manifest schema');expected={'index.json','manifest.json'};seen=set()
    for record in manifest['records']:
        item=record['stored'];rel=Path(item['path']);require(not rel.is_absolute()and'..'not in rel.parts and rel.parts[0]=='raw','safe relative stored path required');name=rel.as_posix();require(name not in seen,'duplicate stored file');seen.add(name);expected.add(name)
        path=out/rel;require(path.is_file()and not path.is_symlink(),'missing/nonregular stored payload: '+name);data=path.read_bytes();require(digest(data)=={k:item[k]for k in('sha256','bytes')},'stored pin mismatch: '+name)
        require(item['codec']in('gzip','identity'),'unknown stored codec');decoded=gzip.decompress(data)if item['codec']=='gzip'else data;require(digest(decoded)==record['raw'],'decoded/raw pin mismatch: '+name)
    actual=set()
    for directory,dirs,files in os.walk(out,followlinks=False):
        require(not any((Path(directory)/name).is_symlink()for name in dirs+files),'symlink in package')
        actual.update((Path(directory)/name).relative_to(out).as_posix()for name in files)
    require(actual==expected,'package file set mismatch')
    require(manifest['files']==index['files']==len(manifest['records'])and manifest['raw_bytes']==index['raw_bytes']==sum(r['raw']['bytes']for r in manifest['records'])and manifest['stored_bytes']==index['stored_bytes']==sum(r['stored']['bytes']for r in manifest['records']),'package totals mismatch')
    require(index['source_freeze_commits']==manifest['source_freeze_commits']and index['semantic_validated']is False and manifest['semantic_validated']is False,'provenance/qualification mismatch')
    return dict(verified=True,files=index['files'],raw_bytes=index['raw_bytes'],stored_bytes=index['stored_bytes'],index=pin(out/'index.json'),manifest=pin(out/'manifest.json'),scientific_calls=0)


def main():
    parser=argparse.ArgumentParser(description=__doc__);sub=parser.add_subparsers(dest='command',required=True)
    p=sub.add_parser('package');p.add_argument('--experiments',type=Path,default=EXPERIMENTS);p.add_argument('--out',type=Path,default=DEFAULT_OUT);p.add_argument('--source-commit',action='append',required=True);p.add_argument('--root-go',action='store_true',required=True)
    p=sub.add_parser('verify');p.add_argument('out',type=Path);args=parser.parse_args()
    result=package([args.experiments/name for name in ROOT_NAMES],args.out,args.source_commit)if args.command=='package'else verify(args.out)
    print(json.dumps(result,indent=2,allow_nan=False))


if __name__=='__main__':main()
