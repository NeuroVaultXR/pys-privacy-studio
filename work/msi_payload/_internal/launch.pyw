from pathlib import Path
import sys,subprocess,tkinter as tk
from tkinter import messagebox
INTERNAL=Path(__file__).resolve().parent
ROOT=INTERNAL.parent
from tidy_installation import tidy
tidy(ROOT)
python=ROOT/'app/.venv/Scripts/pythonw.exe'
import json
try:ready=json.loads((INTERNAL/'installation.json').read_text(encoding='utf-8')).get('status')=='ready'
except (OSError,ValueError):ready=False
if python.is_file() and ready:
 subprocess.Popen([str(python),str(ROOT/'app/privacy_studio.py')],cwd=ROOT/'app')
else:
 root=tk.Tk();root.withdraw()
 messagebox.showinfo('Prima configurazione','Seleziona Base nella configurazione e premi Scarica e configura. Serve Internet per il primo download.')
 root.destroy();subprocess.Popen([sys.executable,str(INTERNAL/'configure.pyw')],cwd=ROOT)
