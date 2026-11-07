#!/usr/bin/env python3
"""Validate or import author-supplied stand-off text. Never retrieve author text."""
import argparse,copy,hashlib,json,os,re,tempfile
from pathlib import Path
ROOT=Path(__file__).resolve().parents[1]
ID=re.compile(r'^[A-Za-z0-9][A-Za-z0-9_.-]{0,127}$')
def digest(b):return 'sha256:'+hashlib.sha256(b).hexdigest()
def read_supplement(root):
 root=Path(root)
 if not (root/'source/canonical.json').is_file() and not ((root/'site/data/j.json').is_file() and (root/'studio/data/review.json').is_file()):raise ValueError('required source inputs missing')
 p=root/'source/variorum.json'
 data=json.loads(p.read_text()) if p.exists() else {'schemaVersion':1,'sources':[]}
 if data.get('schemaVersion')!=1 or not isinstance(data.get('sources'),list):raise ValueError('invalid supplement')
 seen=set()
 for s in data['sources']:
  if not ID.fullmatch(s.get('versionId','')) or s['versionId'] in seen or not ID.fullmatch(s.get('pieceId','')):raise ValueError('invalid source identity')
  seen.add(s['versionId'])
  if s.get('kind') not in ('lyric','notebook'):raise ValueError('invalid source kind')
  path=s.get('file')
  if path:
   rel=Path(path)
   if rel.is_absolute() or '..' in rel.parts or rel.parts[:2]!=('source','external'):raise ValueError('invalid source file path')
   p=Path(root)/rel
   if (root/'source/external').resolve() not in p.resolve().parents:raise ValueError('source path escapes external directory')
   if not p.is_file():
    if s.get('status')!='text-not-supplied':raise ValueError('source file missing')
   elif digest(p.read_bytes())!=s.get('fileSha256'):raise ValueError('source file changed; explicitly import a new revision')
 return data

def import_text(root,piece,kind,file,apply=False):
 root=Path(root);data=read_supplement(root);canonical=json.loads((root/'source/canonical.json').read_text())
 if piece not in {p['id'] for p in canonical['pieces']}:raise ValueError('unknown piece')
 file=Path(file).resolve();base=(root/'source/external').resolve()
 if base not in file.parents or file.is_symlink():raise ValueError('file must be author-placed under source/external')
 raw=file.read_bytes();text=raw.decode('utf-8');fingerprint=digest(raw);versionId='external-'+hashlib.sha256((piece+'\0'+kind+'\0'+fingerprint).encode()).hexdigest()[:32]
 if any(s['versionId']==versionId for s in data['sources']):return {'changed':False,'versionId':versionId}
 source={'pieceId':piece,'versionId':versionId,'kind':kind,'file':'source/external/.versions/'+fingerprint.split(':')[1]+'.txt','originalFile':file.relative_to(root).as_posix(),'fileSha256':fingerprint,'status':'supplied','lines':[{'lineId':versionId+'-L'+str(i+1),'text':line,'originalText':line,'blockType':'text','breakBefore':i>0 and not text.splitlines()[i-1].strip(),'verified':False} for i,line in enumerate(text.splitlines())]}
 updated=copy.deepcopy(data);updated['sources'].append(source)
 if apply:
  preserved=root/source['file'];preserved.parent.mkdir(parents=True,exist_ok=True)
  if preserved.exists() and preserved.read_bytes()!=raw:raise ValueError('source snapshot collision')
  if not preserved.exists():preserved.write_bytes(raw)
  path=root/'source/variorum.json';backup=root/'source'/('variorum.backup-'+hashlib.sha256(path.read_bytes()).hexdigest()+'.json') if path.exists() else None
  if backup and not backup.exists():backup.write_bytes(path.read_bytes())
  fd,temp=tempfile.mkstemp(prefix='.variorum-',dir=path.parent)
  try:
   with os.fdopen(fd,'w')as f:json.dump(updated,f,ensure_ascii=False,indent=2);f.write('\n');f.flush();os.fsync(f.fileno())
   os.replace(temp,path)
  finally:
   if os.path.exists(temp):os.unlink(temp)
 return {'changed':True,'applied':apply,'versionId':versionId,'lineCount':len(source['lines'])}
def main():
 p=argparse.ArgumentParser(description=__doc__);p.add_argument('--root',type=Path,default=ROOT);p.add_argument('--piece');p.add_argument('--kind',choices=['lyric','notebook'],default='lyric');p.add_argument('--file',type=Path);p.add_argument('--apply',action='store_true');a=p.parse_args()
 if a.file:
  if not a.piece:p.error('--piece required')
  print(json.dumps(import_text(a.root,a.piece,a.kind,a.file,a.apply)))
 else:print(json.dumps({'valid':True,'sources':len(read_supplement(a.root)['sources'])}))
if __name__=='__main__':main()
