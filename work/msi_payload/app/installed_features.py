"""Select only engines present in this installation; no GPU framework import."""
from pathlib import Path
import json
RAPID='RapidOCR — veloce'
CPU='Unlimited-OCR + RapidOCR — CPU sperimentale'
GPU='Unlimited-OCR + RapidOCR — GPU NVIDIA'

def engine_choices(base):
 choices=[RAPID];base=Path(base)
 try:
  cfg=json.loads((base/'unlimited_config.json').read_text(encoding='utf-8'))
  python=base/cfg['python'];model=base/cfg['model']
  if not python.is_file() or not (model/'model.safetensors').is_file():return choices
  state_path=base.parent/'_internal/installation.json'
  if not state_path.is_file():state_path=base.parent/'installation.json'
  if state_path.is_file():
   state=json.loads(state_path.read_text(encoding='utf-8'))
   if state.get('status')!='ready':return choices
   devices=state.get('devices',['cpu','cuda'] if state.get('mode')=='nvidia' else ['cpu'] if state.get('mode')=='cpu' else [])
  else:devices=cfg.get('devices',['cpu'])
  if 'cpu' in devices:choices.append(CPU)
  if 'cuda' in devices:choices.append(GPU)
 except (OSError,ValueError,KeyError,TypeError):pass
 return choices
