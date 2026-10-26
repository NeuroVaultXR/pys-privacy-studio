"""Install isolated environments; only setup accesses the network."""
from pathlib import Path
import json,os,shutil,subprocess,sys
from download_models import download
INTERNAL=Path(__file__).resolve().parent
ROOT=INTERNAL.parent
APP=ROOT/'app'
MODE=sys.argv[1] if len(sys.argv)>1 else 'base'
if MODE not in ('base','cpu','nvidia'): raise SystemExit('Modalita non valida')
os.environ.update(PYTHONUTF8='1',PYTHONUNBUFFERED='1',PIP_DISABLE_PIP_VERSION_CHECK='1',HF_HUB_DISABLE_TELEMETRY='1')

def run(args):
    with subprocess.Popen([str(a) for a in args],stdout=subprocess.PIPE,stderr=subprocess.STDOUT,text=True,encoding='utf-8',errors='replace',creationflags=subprocess.CREATE_NO_WINDOW) as proc:
        for line in proc.stdout: print(line.rstrip(),flush=True)
        if proc.wait(): raise RuntimeError('Componente non configurato: '+str(args[0])+'. Leggi il dettaglio precedente.')

def venv(name):
    path=APP/name
    run([sys.executable,'-m','venv',path])
    return path/'Scripts/python.exe'

def write_state(name,value):
    target=INTERNAL/name;temp=target.with_suffix('.tmp')
    temp.write_text(json.dumps(value),encoding='utf-8');os.replace(temp,target)

def pip(py,*args):
    receipt=INTERNAL/'pending-pip.json'
    item={'python':str(py),'args':[str(a) for a in args]}
    try:interrupted=json.loads(receipt.read_text(encoding='utf-8'))==item
    except (OSError,ValueError):interrupted=False
    write_state('pending-pip.json',item)
    repair=['--force-reinstall'] if interrupted else []
    run([py,'-m','pip','install','--timeout','120','--retries','5','--progress-bar','off',*repair,*args])
    receipt.unlink(missing_ok=True)

def main():
    free=shutil.disk_usage(ROOT).free
    if free< (35 if MODE=='nvidia' else 22 if MODE=='cpu' else 10)*1024**3:
        raise RuntimeError('Spazio libero insufficiente. Servono 10 GiB per Base, 22 per CPU, 35 per NVIDIA durante la configurazione.')
    if MODE=='nvidia':
        smi=shutil.which('nvidia-smi.exe')
        if not smi: raise RuntimeError('Driver NVIDIA non trovato. Scegli Base o CPU.')
        info=subprocess.run([smi,'--query-gpu=compute_cap,memory.total','--format=csv,noheader,nounits'],capture_output=True,text=True,check=True,creationflags=subprocess.CREATE_NO_WINDOW)
        cap,memory=info.stdout.splitlines()[0].split(',')
        if float(cap)<8 or float(memory)<8192: raise RuntimeError('GPU incompatibile: GTX 1650 esclusa. Scegli Base o CPU.')
    write_state('installation.json',{'mode':MODE,'status':'incomplete','devices':[]})
    print('Preparazione Privacy Filter e RapidOCR...',flush=True)
    py=venv('.venv')
    pip(py,'torch==2.10.0+cpu','--index-url','https://download.pytorch.org/whl/cpu')
    pip(py,'rapidocr==3.10.0','onnxruntime==1.31.0','pymupdf==2.0','pillow==13.0.0','tkinterdnd2==0.6.4','python-docx==1.2.0','psutil==7.2.2','tiktoken==0.14.0','numpy==2.5.4','safetensors==0.8.0','huggingface-hub==2.3.0',INTERNAL/'opf_source')
    manifest=json.loads((INTERNAL/'models_manifest.json').read_text())
    for f in manifest['privacy']['files']: download(f,APP/'models/privacy_filter'/f['name'])
    print('Preparazione tokenizer e OCR rapido...',flush=True)
    run([py,INTERNAL/'prepare_runtime.py'])
    if MODE!='base':
        print('Preparazione Unlimited-OCR ('+MODE+')...',flush=True)
        ocr=venv('.ocr');index='https://download.pytorch.org/whl/'+('cu128' if MODE=='nvidia' else 'cpu')
        flavour='cu128' if MODE=='nvidia' else 'cpu'
        pip(ocr,'torch==2.10.0+'+flavour,'torchvision==0.25.0+'+flavour,'--index-url',index)
        pip(ocr,'transformers==4.57.1','accelerate==1.15.0','einops','addict','easydict','matplotlib','pymupdf==2.0','psutil==7.2.2','pillow==13.0.0')
        if MODE=='nvidia':run([ocr,INTERNAL/'verify_gpu.py'])
        model=APP/'models/unlimited'
        for f in manifest['unlimited']['files']:download(f,model/f['name'])
        for f in (INTERNAL/'model_code').iterdir():shutil.copy2(f,model/f.name)
        run([ocr,'-m','pip','check'])
    run([py,'-m','pip','check'])
    write_state('installation.json',{'mode':MODE,'status':'ready','devices':['cpu','cuda'] if MODE=='nvidia' else ['cpu'] if MODE=='cpu' else []})
    print('INSTALLAZIONE COMPLETATA. Avvia Privacy Studio dal collegamento.',flush=True)

if __name__=='__main__':
    try:main()
    except Exception as exc:
        print('ERRORE: '+str(exc)+'\nPuoi riaprire il programma di configurazione per riprendere.',flush=True)
        sys.exit(1)
