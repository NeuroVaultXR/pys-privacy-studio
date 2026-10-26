"""Verified resumable downloads. Only pinned public models, no user documents."""
from pathlib import Path
from concurrent.futures import ThreadPoolExecutor,as_completed
import urllib.request,hashlib,json,os,time

def verified(path,record):
    if not path.is_file() or path.stat().st_size!=record['size']: return False
    if record.get('sha256'):
        with path.open('rb') as f: return hashlib.file_digest(f,'sha256').hexdigest()==record['sha256']
    data=path.read_bytes()
    return hashlib.sha1(('blob '+str(len(data))+'\0').encode()+data).hexdigest()==record['git_sha1']

def download(record,target):
    target=Path(target);target.parent.mkdir(parents=True,exist_ok=True)
    if verified(target,record): print('Gia verificato: '+target.name,flush=True);return
    part=target.with_suffix(target.suffix+'.part'); state=part.with_suffix('.progress.json')
    total=record['size']; chunk=8*1024*1024
    if total<chunk:
        with urllib.request.urlopen(record['url'],timeout=90) as r: data=r.read(total+1)
        part.write_bytes(data)
    else:
        count=(total+chunk-1)//chunk;done=set()
        if part.exists() and part.stat().st_size==total and state.exists():
            try:
                saved=json.loads(state.read_text())
                if saved['url']==record['url']: done=set(saved['done'])
            except (ValueError,KeyError): pass
        if not part.exists() or part.stat().st_size!=total:
            with part.open('wb') as f: f.truncate(total)
        def piece(i):
            lo=i*chunk; hi=min(total-1,lo+chunk-1)
            for attempt in range(5):
                try:
                    req=urllib.request.Request(record['url'],headers={'Range':f'bytes={lo}-{hi}'})
                    with urllib.request.urlopen(req,timeout=90) as r:
                        if r.status!=206 or r.headers.get('Content-Range')!=f'bytes {lo}-{hi}/{total}': raise ValueError('Risposta download non valida')
                        data=r.read(hi-lo+2)
                    if len(data)!=hi-lo+1: raise ValueError('Download incompleto')
                    with part.open('r+b') as f: f.seek(lo);f.write(data)
                    return i
                except Exception:
                    if attempt==4: raise
                    time.sleep(2+attempt)
        print('Download '+target.name+f': {round(len(done)/count*100)}%',flush=True)
        with ThreadPoolExecutor(max_workers=3) as pool:
            for result in as_completed([pool.submit(piece,i) for i in range(count) if i not in done]):
                done.add(result.result())
                tmp=state.with_suffix('.tmp');tmp.write_text(json.dumps({'url':record['url'],'done':sorted(done)}));os.replace(tmp,state)
                if len(done)%16==0 or len(done)==count: print(target.name+f': {round(len(done)/count*100)}%',flush=True)
    if not verified(part,record):
        state.unlink(missing_ok=True)
        raise RuntimeError('Verifica integrita fallita: '+target.name+'. Ripeti la configurazione.')
    os.replace(part,target);state.unlink(missing_ok=True)
    print('Verificato: '+target.name,flush=True)
