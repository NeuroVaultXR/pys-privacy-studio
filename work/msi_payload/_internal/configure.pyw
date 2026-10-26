"""Visible, user-started configuration with persistent installation state."""
from pathlib import Path
import tkinter as tk
from tkinter import ttk,messagebox
import sys,subprocess,threading,queue,os,struct,json
INTERNAL=Path(__file__).resolve().parent
ROOT=INTERNAL.parent
from tidy_installation import tidy
from process_group import ProcessGroup
MODES=['base','cpu','nvidia']
RANK={'base':0,'cpu':1,'nvidia':2}

def installed_mode():
 try:
  saved=json.loads((INTERNAL/'installation.json').read_text(encoding='utf-8'))
  if saved.get('status')=='ready' and (ROOT/'app/.venv/Scripts/pythonw.exe').is_file():return saved.get('mode') if saved.get('mode') in MODES else None
 except (OSError,ValueError):pass
 return None

def main():
 tidy(ROOT)
 root=tk.Tk();root.title('PyS - Privacy Studio - Configurazione');root.geometry('840x590');root.configure(bg='#f3eee2')
 try:root.iconbitmap(str(ROOT/'app/assets/pys-ivory.ico'))
 except tk.TclError:pass
 ttk.Label(root,text='PyS - Privacy Studio',font=('Segoe UI',19,'bold')).pack(pady=12)
 ttk.Label(root,text='Powered by Salvatore Urbano').pack()
 ttk.Label(root,text='Base: oscuramento dati e OCR rapido.\nCompleta - No Nvidia GPU: aggiunge Unlimited-OCR su CPU (almeno 17 GiB di RAM libera).\nCompleta - Nvidia GPU: aggiunge Unlimited-OCR su GPU Nvidia compatibile; include anche la CPU.',wraplength=780).pack(pady=10)
 choice=ttk.Combobox(root,state='readonly',values=['Base - Privacy Filter & RapidOCR','Completa - No Nvidia GPU','Completa - Nvidia GPU'],width=65)
 ready=installed_mode();choice.current(MODES.index(ready) if ready else 0);choice.pack(pady=6)
 from tkinter.scrolledtext import ScrolledText
 log=ScrolledText(root,wrap='word',height=17);log.pack(fill='both',expand=True,padx=12,pady=8)
 controls=ttk.Frame(root);controls.pack(pady=10)
 state={'busy':False,'proc':None,'ready':ready,'cancelled':False,'closing':False,'group':None};events=queue.Queue()
 def append(line):
  log.insert('end',line+'\n');log.see('end')
  with (INTERNAL/'install.log').open('a',encoding='utf-8') as f:f.write(line+'\n')
 def refresh(event=None):
  desired=MODES[choice.current()];ready=state['ready']
  covered=ready is not None and RANK[ready]>=RANK[desired]
  button.configure(state='disabled' if state['busy'] or covered else 'normal',text='Configurazione completata' if covered else 'Aggiungi componenti' if ready else 'Scarica e configura')
  choice.configure(state='disabled' if state['busy'] else 'readonly')
  cancel_button.configure(state='normal' if state['busy'] and not state['cancelled'] else 'disabled')
  open_button.configure(state='normal' if ready and not state['busy'] else 'disabled')
 def launch():
  if state['busy'] or not state['ready']:return
  try:subprocess.Popen([sys.executable,str(INTERNAL/'launch.pyw')],cwd=ROOT)
  except OSError as exc:messagebox.showerror('Avvio non riuscito',str(exc));return
  root.destroy()
 def start():
  mode=MODES[choice.current()]
  if state['busy'] or (state['ready'] and RANK[state['ready']]>=RANK[mode]):return
  if sys.version_info[:2]!=(3,13) or struct.calcsize('P')!=8:
   messagebox.showerror('Python richiesto','Installa Python 3.13 a 64 bit dal sito ufficiale, con Tcl/Tk e pip.');return
  state.update(busy=True,cancelled=False,closing=False);refresh()
  def work():
   group=None;exit_code=1
   try:
    group=ProcessGroup();state['group']=group
    env=os.environ.copy();env.update(PYTHONUTF8='1',PYTHONUNBUFFERED='1')
    python=Path(sys.executable).with_name('python.exe')
    bootstrap="import runpy,sys,os; sys.stdin.readline(); sys.path.insert(0,os.path.dirname(sys.argv[1])); sys.argv=sys.argv[1:]; runpy.run_path(sys.argv[0],run_name='__main__')"
    with subprocess.Popen([str(python),'-u','-c',bootstrap,str(INTERNAL/'setup.py'),mode],cwd=ROOT,env=env,stdin=subprocess.PIPE,stdout=subprocess.PIPE,stderr=subprocess.STDOUT,text=True,encoding='utf-8',errors='replace',creationflags=subprocess.CREATE_NO_WINDOW) as proc:
     group.attach(proc);state['proc']=proc
     if state['cancelled']:group.cancel()
     else:
      proc.stdin.write('start\n');proc.stdin.flush();proc.stdin.close()
     for line in proc.stdout:events.put(('line',line.rstrip()))
     exit_code=proc.wait()
   except Exception as exc:events.put(('line',str(exc)))
   finally:
    if group:group.close()
    state['group']=None
    events.put(('done',exit_code))
  threading.Thread(target=work,daemon=True).start()
 def poll():
  try:
   while True:
    kind,value=events.get_nowait()
    if kind=='line':append(value)
    else:
     state['busy']=False;state['proc']=None;state['ready']=installed_mode();refresh()
     append('Configurazione annullata. Puoi riprenderla piu tardi.' if state['cancelled'] else 'Configurazione completata. Premi Apri PyS - Privacy Studio: questa finestra si chiudera.' if value==0 else 'Configurazione incompleta: leggi il dettaglio e riprova.')
     if state['closing']:root.destroy();return
  except queue.Empty:pass
  root.after(100,poll)
 def cancel(close_after=False):
  if not state['busy']:
   if close_after:root.destroy()
   return
  state['cancelled']=True;state['closing']=state['closing'] or close_after
  group=state['group']
  if group:group.cancel()
  append('Annullamento in corso…');refresh()
 def close():
  if state['busy']:cancel(close_after=True)
  else:root.destroy()
 def copy():root.clipboard_clear();root.clipboard_append(log.get('1.0','end-1c'))
 button=ttk.Button(controls,text='Scarica e configura',command=start);button.pack(side='left',padx=5)
 cancel_button=ttk.Button(controls,text='Annulla',command=cancel,state='disabled');cancel_button.pack(side='left',padx=5)
 ttk.Button(controls,text='Copia dettagli',command=copy).pack(side='left',padx=5)
 open_button=ttk.Button(controls,text='Apri PyS - Privacy Studio',command=launch,state='disabled');open_button.pack(side='left',padx=5)
 choice.bind('<<ComboboxSelected>>',refresh);refresh()
 if ready:append('Componenti gia configurati. Puoi aprire il programma o scegliere un pacchetto superiore da aggiungere.')
 root.protocol('WM_DELETE_WINDOW',close);root.after(100,poll);root.mainloop()
if __name__=='__main__':main()
