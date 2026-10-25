#!/usr/bin/env python3
"""Gestoppte Volume-Daten kopieren und anschließend Inhalt sowie Metadaten prüfen."""
import argparse
import hashlib
import json
import os
from pathlib import Path
import shutil
import stat


def attributes(path):
    return {key:os.getxattr(path,key,follow_symlinks=False)
            for key in os.listxattr(path,follow_symlinks=False)}


def metadata(path):
    s=path.lstat()
    return (stat.S_IFMT(s.st_mode),stat.S_IMODE(s.st_mode),s.st_uid,s.st_gid,s.st_mtime_ns,attributes(path))


def digest(path):
    with path.open('rb') as stream:return hashlib.file_digest(stream,'sha256').hexdigest()


def migrate(source,target):
    if not source.is_dir() or not target.is_dir() or source.is_symlink() or target.is_symlink():
        raise RuntimeError('Quelle und Ziel müssen echte Verzeichnisse sein.')
    if source.resolve()==target.resolve() or target.resolve().is_relative_to(source.resolve()):
        raise RuntimeError('Quelle und Ziel überlappen.')
    if next(target.iterdir(),None) is not None:
        raise RuntimeError('Ziel ist nicht leer. Nichts überschrieben.')
    links={}
    counts={'files':0,'directories':0,'symlinks':0,'bytes':0,'verified':False}
    def copy(src,dst):
        info=src.lstat()
        if stat.S_ISDIR(info.st_mode):
            if dst!=target:dst.mkdir(mode=0o700)
            counts['directories']+=1
            for child in sorted(src.iterdir()):copy(child,dst/child.name)
        elif stat.S_ISLNK(info.st_mode):
            dst.symlink_to(os.readlink(src));counts['symlinks']+=1
        elif stat.S_ISREG(info.st_mode):
            key=(info.st_dev,info.st_ino)
            if key in links:os.link(links[key],dst)
            else:shutil.copyfile(src,dst);links[key]=dst
            counts['files']+=1;counts['bytes']+=info.st_size
        else:
            raise RuntimeError('Nicht unterstützte Spezialdatei: '+str(src))
        os.chown(dst,info.st_uid,info.st_gid,follow_symlinks=False)
        shutil.copystat(src,dst,follow_symlinks=False)
    copy(source,target)
    verified_links={}
    def verify(src,dst):
        if metadata(src)!=metadata(dst):raise RuntimeError('Metadaten unterscheiden sich: '+str(src))
        info=src.lstat()
        if stat.S_ISDIR(info.st_mode):
            if sorted(p.name for p in src.iterdir())!=sorted(p.name for p in dst.iterdir()):
                raise RuntimeError('Verzeichnisinhalt unterscheidet sich: '+str(src))
            for child in sorted(src.iterdir()):verify(child,dst/child.name)
        elif stat.S_ISLNK(info.st_mode):
            if os.readlink(src)!=os.readlink(dst):raise RuntimeError('Symlink unterscheidet sich: '+str(src))
        else:
            if info.st_size!=dst.stat().st_size or digest(src)!=digest(dst):
                raise RuntimeError('Datei-Prüfsumme unterscheidet sich: '+str(src))
            key=(info.st_dev,info.st_ino);other=dst.stat();newkey=(other.st_dev,other.st_ino)
            if key in verified_links and verified_links[key]!=newkey:
                raise RuntimeError('Hardlink wurde nicht erhalten: '+str(src))
            verified_links[key]=newkey
    verify(source,target)
    os.sync()
    counts['verified']=True
    return counts


if __name__=='__main__':
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('source',type=Path);parser.add_argument('target',type=Path)
    args=parser.parse_args()
    print(json.dumps(migrate(args.source,args.target)))
