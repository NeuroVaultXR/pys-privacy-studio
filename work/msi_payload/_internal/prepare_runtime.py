from pathlib import Path
import json,os
root=Path(__file__).resolve().parent.parent/'app'
os.environ['TIKTOKEN_CACHE_DIR']=str(root/'tokenizer_cache')
import tiktoken
config=json.loads((root/'models/privacy_filter/config.json').read_text())
tiktoken.get_encoding(config['encoding'])
from rapidocr import RapidOCR
RapidOCR(params={'Global.log_level':'error','Global.text_score':0.35})
print('Tokenizer e modelli OCR locali pronti',flush=True)
