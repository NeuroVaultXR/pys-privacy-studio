"""Bridge to isolated local Unlimited-OCR; never sends data to a server."""
from pathlib import Path
import ast,base64,html,json,os,queue,re,subprocess,threading

BASE=Path(__file__).resolve().parent


def installation():
    config=BASE/'unlimited_config.json'
    if not config.is_file(): raise ValueError('Unlimited-OCR non configurato. Usa RapidOCR.')
    cfg=json.loads(config.read_text(encoding='utf-8'))
    python=BASE/ cfg['python']; model=BASE/ cfg['model']
    if not python.is_file() or not (model/'model.safetensors').is_file() or not (model/'cpu_patch.json').is_file():
        raise ValueError('Installazione Unlimited-OCR incompleta o spostata: controlla unlimited_config.json.')
    return python,model


def clean(value):
    value=re.sub(r'<\|[^>]*\|>','',value)
    value=re.sub(r'</?(?:tr|table|p|div|br|h[1-6])\b[^>]*>','\n',value,flags=re.I)
    value=re.sub(r'</?(?:td|th)\b[^>]*>',' | ',value,flags=re.I)
    value=re.sub(r'<[^>]+>','',value)
    return html.unescape(value).strip()


def parse_regions(raw,width,height):
    # Coordinates are model predictions, not guarantees; clamp and reject malformed boxes.
    pattern=(r'<\|ref\|>(.*?)<\|/ref\|>\s*<\|det\|>(.*?)<\|/det\|>'
             r'|<\|det\|>\s*([A-Za-z_][\w-]*)\s*(\[.*?\])\s*<\|/det\|>')
    matches=list(re.finditer(pattern,raw,re.S)); text=''; units=[]
    if not matches: return clean(raw),[]
    prefix=clean(raw[:matches[0].start()])
    if prefix: text=prefix+'\n'
    for i,m in enumerate(matches):
        value=clean(raw[m.end():matches[i+1].start() if i+1<len(matches) else len(raw)])
        if not value: continue
        start=len(text); text+=value+'\n'
        try:
            boxes=ast.literal_eval(m.group(2) or m.group(4))
            if isinstance(boxes,(list,tuple)) and len(boxes)==4 and all(isinstance(x,(int,float)) for x in boxes): boxes=[boxes]
            for box in boxes:
                if len(box)!=4 or not all(isinstance(x,(int,float)) and 0<=x<=1000 for x in box): continue
                x0,y0,x1,y1=box
                if x1>x0 and y1>y0:
                    units.append({'start':start,'end':start+len(value),'rect':[x0/999*width,y0/999*height,min(width,x1/999*width),min(height,y1/999*height)],'origin':'Unlimited-OCR'})
        except (ValueError,SyntaxError,TypeError): pass
    return text,units


class Client:
    def __init__(self,progress,device="cpu",budget=24):
        python,model=installation(); self.events=queue.Queue(); self.progress=progress
        import psutil
        if device not in ('cpu','cuda'): raise ValueError('Dispositivo non supportato.')
        if device=='cpu' and (budget<17 or psutil.virtual_memory().available<17*1024**3):
            raise RuntimeError('Unlimited-OCR su CPU richiede almeno 17 GB di RAM libera per questa configurazione. Chiudi altre applicazioni o usa RapidOCR.')
        self.proc=subprocess.Popen([str(python),str(BASE/'unlimited_worker.py'),str(model),str(os.getpid()),device],
            stdin=subprocess.PIPE,stdout=subprocess.PIPE,stderr=subprocess.DEVNULL,text=True,encoding='utf-8',creationflags=subprocess.CREATE_NO_WINDOW)
        def read():
            try:
                for line in self.proc.stdout: self.events.put(json.loads(line))
            except Exception: pass
            finally: self.events.put({'error':'Il processo Unlimited-OCR si è chiuso senza risultato.'})
        threading.Thread(target=read,daemon=True).start()
        try: self.receive('ready',180)
        except Exception:
            self.close(); raise

    def receive(self,key,timeout):
        while True:
            try: item=self.events.get(timeout=timeout)
            except queue.Empty: raise RuntimeError('Unlimited-OCR non risponde. Interrompi e usa RapidOCR.')
            if 'error' in item: raise RuntimeError(item['error'])
            if 'progress' in item: self.progress(item['progress'])
            if key in item: return item

    def page(self,page):
        png=page.get_pixmap(dpi=150,alpha=False,annots=True).tobytes('png')
        self.proc.stdin.write(json.dumps({'png':base64.b64encode(png).decode('ascii')})+'\n'); self.proc.stdin.flush()
        result=self.receive('text',660)
        text,units=parse_regions(result['text'],page.rect.width,page.rect.height)
        return text,units,result['seconds']

    def close(self):
        if self.proc.poll() is None:
            self.proc.terminate()
            try: self.proc.wait(timeout=10)
            except subprocess.TimeoutExpired: self.proc.kill(); self.proc.wait()
        self.proc.stdout.close(); self.proc.stdin.close()
