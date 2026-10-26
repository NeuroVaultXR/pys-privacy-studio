"""Migrate only known installation bookkeeping; never remove user documents."""
from pathlib import Path
import os

def tidy(root):
 root=Path(root).resolve();internal=root/'_internal';internal.mkdir(exist_ok=True)
 for name in ('installation.json','install.log'):
  old=root/name;new=internal/name
  if old.is_file():
   if not new.exists():os.replace(old,new)
   elif name=='install.log':
    with new.open('a',encoding='utf-8') as log:log.write('\n'+old.read_text(encoding='utf-8',errors='replace'))
    old.unlink()
   else:old.unlink()
 # Only obsolete, explicitly named application documentation is removed.
 for name in ('LEGGIMI.txt','NEUROVAULTXR_LEGGIMI.txt','PrivacyStudio_Installazione.txt','PyS-PrivacyStudio-Istruzioni.txt','Esito_sicurezza_MSI.txt','PyS-Sicurezza.txt','INSTALLER_PRECEDENTE_RITIRATO.txt','VERIFICA.txt','VERIFICA_STUDIO.txt'):
  path=root/name
  if path.is_file():path.unlink()

 cache=root/'__pycache__'
 if cache.is_dir() and not cache.is_symlink() and cache.resolve().is_relative_to(root):
  for file in cache.glob('*.pyc'):
   if file.resolve().is_relative_to(root):file.unlink()
  try:cache.rmdir()
  except OSError:pass
 for name in ('model_code','opf_source','licenses'):
  directory=root/name
  if directory.is_dir() and not directory.is_symlink():
   try:directory.rmdir()
   except OSError:pass
