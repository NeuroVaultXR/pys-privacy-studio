"""CPU / NVIDIA Unlimited-OCR worker; JSON lines over pipes, no network or source files."""
from pathlib import Path
import base64, contextlib, io, json, os, sys, tempfile, time


def main():
    sys.stdin.reconfigure(encoding='utf-8'); sys.stdout.reconfigure(encoding='utf-8')
    wire=sys.stdout
    def send(value):
        wire.write(json.dumps(value,ensure_ascii=True)+'\n'); wire.flush()
    os.environ.update(HF_HUB_OFFLINE='1',TRANSFORMERS_OFFLINE='1',HF_HUB_DISABLE_TELEMETRY='1',TOKENIZERS_PARALLELISM='false')
    import socket
    def blocked(*a,**k): raise RuntimeError('Connessioni di rete disabilitate nel motore OCR.')
    socket.socket.connect=blocked; socket.create_connection=blocked; socket.getaddrinfo=blocked
    model_dir=Path(sys.argv[1])
    device=sys.argv[3] if len(sys.argv)>3 else 'cpu'
    if device not in ('cpu','cuda'): raise ValueError('Dispositivo non supportato.')
    os.environ['HF_MODULES_CACHE']=str(model_dir.parent/'module_cache')
    if len(sys.argv)>2:
        import psutil,threading
        parent=psutil.Process(int(sys.argv[2])); created=parent.create_time()
        def watch_parent():
            while True:
                time.sleep(2)
                try:
                    if not parent.is_running() or parent.create_time()!=created: os._exit(1)
                except psutil.Error: os._exit(1)
        threading.Thread(target=watch_parent,daemon=True).start()
    with contextlib.redirect_stdout(sys.stderr):
        import torch
        from transformers import AutoModel,AutoTokenizer,StoppingCriteria,StoppingCriteriaList
        from PIL import Image
        torch.set_num_threads(6)
        dtype=torch.float32
        if device=='cuda':
            from hardware import gpu_dtype
            dtype=gpu_dtype(torch)
        send({'progress':'Unlimited-OCR: caricamento modello '+device.upper()+'…'})
        tokenizer=AutoTokenizer.from_pretrained(model_dir,trust_remote_code=True,local_files_only=True)
        model=AutoModel.from_pretrained(model_dir,trust_remote_code=True,local_files_only=True,
            use_safetensors=True,torch_dtype=dtype,attn_implementation='eager',low_cpu_mem_usage=True).to(device).eval()
        module=sys.modules[model.__class__.__module__]
        original_generate=model.generate
        last={}
        class Report(StoppingCriteria):
            def __call__(self,input_ids,scores,**kwargs):
                count=input_ids.shape[1]-last['prompt']
                now=time.monotonic()
                if now-last['reported']>12:
                    send({'progress':f'Unlimited-OCR: lettura in corso, {count} token…'})
                    last['reported']=now
                return False
        def generate(**kwargs):
            last['prompt']=kwargs['input_ids'].shape[1]; last['reported']=time.monotonic()
            kwargs.pop('max_length',None)
            kwargs.update(max_new_tokens=4096,max_time=600,stopping_criteria=StoppingCriteriaList([Report()]))
            output=original_generate(**kwargs)
            last['complete']=int(output[0,-1])==tokenizer.eos_token_id
            last['tokens']=output.shape[1]-last['prompt']
            return output
        model.generate=generate
        send({'ready':True})
        for line in sys.stdin:
            request=json.loads(line)
            if request.get('quit'): break
            try:
                start=time.monotonic()
                image=Image.open(io.BytesIO(base64.b64decode(request['png']))).convert('RGB')
                module.load_image=lambda path:image.copy()
                with tempfile.TemporaryDirectory(prefix='privacy_unlimited_') as temp:
                    with torch.inference_mode():
                        text=model.infer(tokenizer,prompt='<image>document parsing.',image_file='memory',
                            output_path=temp,base_size=1024,image_size=1024,crop_mode=False,
                            save_results=False,eval_mode=True,no_repeat_ngram_size=35,ngram_window=128)
                if not text or not text.strip(): raise RuntimeError('Unlimited-OCR ha restituito testo vuoto.')
                if not last.get('complete'): raise RuntimeError('Lettura Unlimited-OCR incompleta: limite di tempo o lunghezza. Dividi la pagina o usa RapidOCR.')
                send({'text':text,'tokens':last['tokens'],'seconds':round(time.monotonic()-start,1)})
            except Exception as exc: send({'error':str(exc)})


if __name__=='__main__':
    try: main()
    except Exception as exc:
        print(json.dumps({'error':str(exc)},ensure_ascii=True),flush=True)
