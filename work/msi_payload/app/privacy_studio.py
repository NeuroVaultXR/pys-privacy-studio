"""Unified local OCR / Privacy Filter desktop interface."""
from pathlib import Path
import json, queue, subprocess, sys, threading
import tkinter as tk
from tkinter import ttk, filedialog, messagebox
from tkinter.scrolledtext import ScrolledText
from tkinterdnd2 import TkinterDnD, DND_FILES
from PIL import ImageTk
import privacy_core as core
from branding import theme,identity,splash,GradientProgress,BG,PANEL,INK

BASE=Path(__file__).resolve().parent
NOTICE='Controlla ogni pagina: modello e OCR possono omettere dati. Puoi aggiungere rettangoli manuali. Il PDF conserva l’aspetto, ma il testo non sarà selezionabile; firme digitali, allegati e metadati originali non vengono conservati.'


class Studio:
    def __init__(self,root):
        self.root=root; self.jobs=[]; self.current=None; self.active=None
        self.busy=None; self.proc=None; self.events=queue.Queue(); self.page=0; self.image=None; self.drag=None; self.resize_timer=None
        root.title('PyS - Privacy Studio'); root.geometry('1260x960'); root.minsize(960,800); identity(root)
        style=theme(root)
        outer=ttk.Frame(root,padding=12); outer.pack(fill='both',expand=True)
        ttk.Label(outer,text='PyS - Privacy Studio',font=('Segoe UI',22,'bold')).pack(anchor='w')
        ttk.Label(outer,text='OCR + Privacy Filter sul tuo PC • PDF, immagini, TXT e DOCX • fino a 20 documenti per sessione').pack(anchor='w')
        settings={}
        try: settings=json.loads((BASE/'privacy_settings.json').read_text(encoding='utf-8'))
        except (OSError,ValueError): pass
        options=ttk.LabelFrame(outer,text='Impostazioni per la prossima elaborazione',padding=8); options.pack(fill='x',pady=8)
        ttk.Label(options,text='Oscura sempre (nomi o frasi separati da ;):').grid(row=0,column=0,sticky='w')
        self.terms=tk.StringVar(value=settings.get('terms',''))
        self.entry=ttk.Entry(options,textvariable=self.terms); self.entry.grid(row=0,column=1,columnspan=3,sticky='ew',padx=6); options.columnconfigure(1,weight=1)
        ttk.Label(options,text='Riconosce maiuscole, spazi e ordine invertito. Segnala i termini non trovati.').grid(row=1,column=0,columnspan=4,sticky='w',pady=3)
        self.dates=tk.BooleanVar(value=True); self.ocr=tk.BooleanVar(value=True); self.only=tk.BooleanVar(value=False)
        self.date_check=ttk.Checkbutton(options,text='Oscura anche le date',variable=self.dates); self.date_check.grid(row=2,column=0,sticky='w')
        self.ocr_check=ttk.Checkbutton(options,text='Controlla anche le immagini con OCR',variable=self.ocr); self.ocr_check.grid(row=2,column=1,sticky='w')
        self.only_check=ttk.Checkbutton(options,text='Solo OCR (NON oscura)',variable=self.only); self.only_check.grid(row=2,column=2,sticky='w')
        ttk.Label(options,text='Motore OCR:').grid(row=3,column=0,sticky='w',pady=(6,0))
        from installed_features import engine_choices
        engines=engine_choices(BASE)
        self.engine=tk.StringVar(value=engines[0])
        self.engine_box=ttk.Combobox(options,textvariable=self.engine,state='readonly',values=engines,width=50)
        self.engine_box.grid(row=3,column=1,sticky='ew',pady=(6,0))
        ttk.Label(options,text='Unlimited: più memoria e minuti per pagina.').grid(row=3,column=2,sticky='w')
        import psutil
        memory=psutil.virtual_memory()
        self.ram_max=max(1,round(min(memory.total*0.85,memory.available-1024**3)/1024**3,1))
        self.ram=tk.DoubleVar(value=min(self.ram_max,max(4,round(self.ram_max*0.8,1))))
        ttk.Label(options,text='Budget RAM (GiB):').grid(row=4,column=0,sticky='w',pady=(6,0))
        self.ram_scale=ttk.Scale(options,from_=min(4,self.ram_max),to=self.ram_max,variable=self.ram,command=lambda value:self.ram_changed())
        self.ram_scale.grid(row=4,column=1,sticky='ew',pady=(6,0))
        self.ram_label=ttk.Label(options);self.ram_label.grid(row=4,column=2,sticky='w',padx=6)
        ttk.Label(options,text='Sinistra: meno RAM; destra: meno attese. La RAM non viene occupata in anticipo: se il consumo supera il valore, l’analisi si interrompe.\nUnlimited-OCR su CPU richiede almeno 17 GiB liberi, anche spostando il cursore a sinistra.').grid(row=5,column=0,columnspan=4,sticky='w')
        self.ram_changed()
        bar=ttk.Frame(outer); bar.pack(fill='x')
        self.open_button=ttk.Button(bar,text='Aggiungi documenti…',command=self.choose); self.open_button.pack(side='left')
        self.retry_button=ttk.Button(bar,text='Rielabora selezionato',command=self.retry); self.retry_button.pack(side='left',padx=5)
        self.cancel_button=ttk.Button(bar,text='Interrompi coda',command=self.cancel,state='disabled'); self.cancel_button.pack(side='left')
        ttk.Button(bar,text='Avvisi completi',command=self.warnings).pack(side='left',padx=5)
        self.save_button=ttk.Button(bar,text='Salva documento…',command=self.save,state='disabled'); self.save_button.pack(side='right')
        self.drop=ttk.Label(outer,text='Trascina qui uno o più file da Esplora file',anchor='center',padding=10,background='#dceff0')
        self.drop.pack(fill='x',pady=6); self.drop.drop_target_register(DND_FILES); self.drop.dnd_bind('<<Drop>>',self.dropped)
        split=ttk.Panedwindow(outer,orient='horizontal'); split.pack(fill='both',expand=True)
        left=ttk.Frame(split,width=225); right=ttk.Frame(split); split.add(left,weight=1); split.add(right,weight=5)
        self.tree=ttk.Treeview(left,columns=('state',),show='tree headings',selectmode='browse',height=10)
        self.tree.heading('#0',text='Documenti'); self.tree.heading('state',text='Stato'); self.tree.column('#0',width=145,minwidth=90); self.tree.column('state',width=100,minwidth=70)
        self.tree.pack(fill='both',expand=True); self.tree.bind('<<TreeviewSelect>>',self.selected)
        self.notebook=ttk.Notebook(right); self.notebook.pack(fill='both',expand=True)
        self.pdf_tab=ttk.Frame(self.notebook); self.text_tab=ttk.Frame(self.notebook)
        self.notebook.add(self.pdf_tab,text='Anteprima PDF / immagine'); self.notebook.add(self.text_tab,text='Testo estratto e oscurato')
        controls=ttk.Frame(self.pdf_tab); controls.pack(fill='x')
        ttk.Button(controls,text='◀',command=lambda:self.navigate(-1)).pack(side='left'); self.page_label=ttk.Label(controls,text='Nessun documento'); self.page_label.pack(side='left',padx=5)
        ttk.Button(controls,text='▶',command=lambda:self.navigate(1)).pack(side='left')
        self.show_original=tk.BooleanVar(value=False)
        ttk.Checkbutton(controls,text='Mostra originale',variable=self.show_original,command=self.draw).pack(side='left',padx=8)
        ttk.Button(controls,text='Annulla ultimo rettangolo',command=self.undo).pack(side='right')
        ttk.Label(self.pdf_tab,text='Trascina sulla pagina per oscurare un’area. Controlla anche firme, codici a barre e immagini.').pack(anchor='w')
        holder=ttk.Frame(self.pdf_tab); holder.pack(fill='both',expand=True)
        self.canvas=tk.Canvas(holder,bg='#e5e6df',highlightthickness=0,cursor='crosshair'); scroll=ttk.Scrollbar(holder,orient='vertical',command=self.canvas.yview)
        self.canvas.configure(yscrollcommand=scroll.set); scroll.pack(side='right',fill='y'); self.canvas.pack(fill='both',expand=True)
        self.canvas.bind('<ButtonPress-1>',self.start_rect); self.canvas.bind('<B1-Motion>',self.move_rect); self.canvas.bind('<ButtonRelease-1>',self.end_rect)
        self.canvas.bind('<MouseWheel>',lambda e:self.canvas.yview_scroll(-int(e.delta/120),'units')); self.canvas.bind('<Configure>',self.resize)
        textbar=ttk.Frame(self.text_tab); textbar.pack(fill='x'); ttk.Label(textbar,text='Seleziona un dato nell’originale da oscurare.').pack(side='left')
        ttk.Button(textbar,text='Oscura selezione',command=self.mask_selection).pack(side='right')
        texts=ttk.Panedwindow(self.text_tab,orient='horizontal'); texts.pack(fill='both',expand=True)
        a=ttk.Frame(texts); b=ttk.Frame(texts); texts.add(a,weight=1); texts.add(b,weight=1)
        ttk.Label(a,text='Originale / OCR').pack(anchor='w'); ttk.Label(b,text='Risultato • per PDF usa selezione o rettangoli').pack(anchor='w')
        self.original=ScrolledText(a,wrap='word',width=30,font=('Segoe UI',10),exportselection=False); self.preview=ScrolledText(b,wrap='word',width=30,font=('Segoe UI',10),undo=True)
        self.original.pack(fill='both',expand=True); self.preview.pack(fill='both',expand=True); self.original.configure(state='disabled'); self.preview.configure(state='disabled'); self.preview.bind('<<Modified>>',self.modified)
        for editor in (self.original,self.preview): editor.configure(bg=PANEL,fg=INK,insertbackground=INK,selectbackground='#b8def7')
        self.info=tk.StringVar(value=NOTICE); self.info_label=ttk.Label(outer,textvariable=self.info,wraplength=1180,foreground='#82440b'); self.info_label.pack(fill='x',pady=6)
        outer.bind('<Configure>',lambda e:self.info_label.configure(wraplength=max(400,e.width-30)))
        self.review=tk.BooleanVar(value=False); ttk.Checkbutton(outer,text='Ho verificato tutte le pagine, gli avvisi e i dati ancora visibili prima di salvare.',variable=self.review,command=self.reviewed).pack(anchor='w')
        ttk.Label(outer,text='Powered by Salvatore Urbano',font=('Segoe UI',9)).pack(anchor='e')
        self.progress=GradientProgress(outer); self.progress.pack(fill='x',pady=4)
        self.status=tk.StringVar(value='Pronto. Nessun documento viene inviato online.'); ttk.Label(outer,textvariable=self.status,wraplength=1100).pack(anchor='w')
        root.protocol('WM_DELETE_WINDOW',self.close); root.after(100,self.poll); root.after(3000,self.refresh_ram)

    def refresh_ram(self):
        if not self.busy:
            import psutil
            memory=psutil.virtual_memory()
            self.ram_max=max(1,round(min(memory.total*0.85,memory.available-1024**3)/1024**3,1))
            self.ram_scale.configure(from_=min(4,self.ram_max),to=self.ram_max)
            self.ram.set(min(self.ram.get(),self.ram_max));self.ram_changed()
        self.root.after(3000,self.refresh_ram)

    def ram_changed(self):
        value=self.ram.get()
        mode='risparmio' if value<8 else 'bilanciato' if value<24 else 'prestazioni'
        self.ram_label.configure(text=f'{value:.1f} GiB / {self.ram_max:.1f} disponibili · {mode}')

    def options(self):
        return {'terms':self.terms.get(),'dates':self.dates.get(),'ocr':self.ocr.get(),'ocr_only':self.only.get(),'engine':'unlimited' if self.engine.get().startswith('Unlimited') else 'rapid','device':'cuda' if 'GPU NVIDIA' in self.engine.get() else 'cpu','ram_gib':round(self.ram.get(),1)}

    def lock(self):
        for w in (self.open_button,self.retry_button,self.entry,self.date_check,self.ocr_check,self.only_check,self.ram_scale): w.configure(state='disabled' if self.busy else 'normal')
        self.save_button.configure(state='normal' if not self.busy and self.result() else 'disabled'); self.cancel_button.configure(state='normal' if self.busy=='process' else 'disabled')
        self.tree.configure(selectmode='none' if self.busy else 'browse')
        self.engine_box.configure(state='disabled' if self.busy else 'readonly')
        self.preview.configure(state='normal' if not self.busy and self.result() and not self.result()['visual'] else 'disabled')

    def result(self):
        return None if self.current is None else self.jobs[self.current].get('result')

    def choose(self):
        self.add(filedialog.askopenfilenames(filetypes=[('Documenti e immagini','*.pdf *.txt *.docx *.png *.jpg *.jpeg *.tif *.tiff *.bmp')]))

    def dropped(self,event):
        if self.busy: return 'refuse_drop'
        self.add(self.root.tk.splitlist(event.data)); return 'copy'

    def add(self,files):
        if self.busy or not files: return
        if self.options()['engine']=='unlimited':
            try:
                from unlimited_adapter import installation
                installation()
            except Exception as exc:
                messagebox.showerror('Unlimited-OCR non disponibile',str(exc)); return
        valid=[str(Path(p).resolve()) for p in files if Path(p).is_file() and Path(p).suffix.lower() in core.SUPPORTED]
        if len(valid)!=len(files): messagebox.showinfo('File ignorati','Sono supportati PDF, TXT, DOCX e immagini PNG/JPG/TIFF/BMP.')
        if len(self.jobs)+len(valid)>20:
            messagebox.showinfo('Limite coda','Massimo 20 documenti per sessione. Salva i risultati e riapri il programma per una nuova coda.'); return
        for path in valid:
            if any(j['path']==path for j in self.jobs): continue
            i=len(self.jobs); self.jobs.append({'path':path,'state':'In attesa','reviewed':False,'dirty':False,'options':self.options()}); self.tree.insert('', 'end', iid=str(i),text=Path(path).name,values=('In attesa',))
        self.next_job()

    def job_state(self,i,value):
        self.jobs[i]['state']=value; self.tree.set(str(i),'state',value)

    def next_job(self):
        if self.busy: return
        for i,job in enumerate(self.jobs):
            if job['state']=='In attesa': self.start(i); return
        self.lock()

    def start(self,i):
        self.active=i; self.current=i; self.busy='process'; self.tree.selection_set(str(i)); self.job_state(i,'Elaborazione'); self.jobs[i].pop('result',None); self.jobs[i].pop('error',None)
        self.display(); self.lock(); self.progress.start(); self.status.set('Caricamento modelli locali…')
        try:
            self.proc=subprocess.Popen([sys.executable,str(BASE/'privacy_core.py')],stdin=subprocess.PIPE,stdout=subprocess.PIPE,stderr=subprocess.DEVNULL,text=True,encoding='utf-8',creationflags=subprocess.CREATE_NO_WINDOW)
            self.proc.stdin.write(json.dumps({'path':self.jobs[i]['path'],'options':self.jobs[i]['options']})+'\n'); self.proc.stdin.close(); worker=self.proc
        except Exception as exc: self.events.put((i,{'error':str(exc)})); return
        finished=threading.Event(); resource_error=[]
        def memory_watch():
            import psutil
            limit=self.jobs[i]['options'].get('ram_gib',24)*1024**3
            while not finished.wait(0.75):
                try:
                    process=psutil.Process(worker.pid); children=process.children(recursive=True)
                    used=sum(p.memory_info().rss for p in [process]+children if p.is_running())
                    if used>limit:
                        resource_error.append('Budget RAM superato: elaborazione interrotta senza risultato esportabile. Aumenta il cursore se hai memoria disponibile, oppure scegli RapidOCR. La soglia e monitorata e puo essere superata brevemente.')
                        for child in reversed(children):
                            try: child.terminate()
                            except psutil.Error: pass
                        worker.terminate();return
                except psutil.NoSuchProcess: return
                except psutil.Error: pass
        threading.Thread(target=memory_watch,daemon=True).start()
        def read():
            terminal=False
            try:
                for line in worker.stdout:
                    if resource_error: continue
                    event=json.loads(line); terminal=terminal or 'result' in event or 'error' in event
                    if terminal: finished.set()
                    self.events.put((i,event))
                worker.wait()
                if resource_error: self.events.put((i,{'error':resource_error[0]}))
                elif not terminal: self.events.put((i,{'error':'Elaborazione interrotta o memoria insufficiente.'}))
            except Exception as exc: self.events.put((i,{'error':'Impossibile leggere il risultato: '+str(exc)}))
            finally: finished.set(); worker.stdout.close()
        threading.Thread(target=read,daemon=True).start()

    def poll(self):
        try:
            while True:
                i,event=self.events.get_nowait()
                if 'progress' in event:
                    self.status.set(event['progress'])
                    if 'percent' in event: self.progress.set(event['percent'])
                    continue
                self.progress.stop(); self.busy=None; self.proc=None
                if 'saved' in event:
                    self.progress.set(100)
                    self.jobs[i]['dirty']=False; self.job_state(i,'Salvato'); self.status.set('Salvato: '+event['saved'])
                elif 'save_error' in event: messagebox.showerror('Salvataggio non riuscito',event['save_error'])
                elif 'error' in event:
                    self.jobs[i]['error']=event['error']; self.job_state(i,'Errore'); self.status.set(event['error']); self.display(); self.show_error(event['error'])
                else:
                    self.progress.set(100)
                    self.jobs[i].update(result=event['result'],reviewed=False,dirty=True); self.job_state(i,'Da verificare'); self.current=i; self.display(); self.status.set('Analisi completata. Controlla tutte le pagine e aggiungi eventuali oscuramenti.')
                self.lock(); self.next_job()
        except queue.Empty: pass
        self.root.after(100,self.poll)

    def selected(self,event=None):
        if self.busy: return
        selection=self.tree.selection()
        if selection: self.current=int(selection[0]); self.page=0; self.display(); self.lock()

    def fill(self,widget,text,disabled=True):
        widget.configure(state='normal'); widget.delete('1.0','end'); widget.insert('1.0',text); widget.edit_modified(False)
        if disabled: widget.configure(state='disabled')

    def display(self):
        data=self.result(); self.show_original.set(False)
        if not data:
            self.fill(self.original,''); self.fill(self.preview,''); self.canvas.delete('all'); self.info.set(self.jobs[self.current].get('error',NOTICE) if self.current is not None else NOTICE); self.review.set(False); return
        self.page=min(self.page,len(data['pages'])-1); self.fill(self.original,'\n\n'.join(p['text'] for p in data['pages']))
        self.fill(self.preview,self.jobs[self.current].get('edited_text',core.output_text(data)),disabled=data['visual']); self.preview.edit_reset(); self.review.set(self.jobs[self.current].get('reviewed',False))
        prefix='SOLO OCR: NESSUN DATO OSCURATO. ' if data['options'].get('ocr_only') else ''
        counts='; '.join(f'{k}: {v} corrispondenze' for k,v in data['term_counts'].items()); dates='Date: oscuramento attivo.' if data['options'].get('dates',True) else 'Date: oscuramento automatico disattivato.'
        if data['options'].get('ocr_only'): dates=''
        self.info.set(prefix+dates+' '+counts+'\n'+NOTICE+'\n'+'\n'.join(data['warnings'][:2])+ ('\nUlteriori avvisi: apri «Avvisi completi».' if len(data['warnings'])>2 else ''))
        self.notebook.select(self.pdf_tab if data['visual'] else self.text_tab); self.draw()

    def resize(self,event=None):
        if self.resize_timer: self.root.after_cancel(self.resize_timer)
        self.resize_timer=self.root.after(200,self.draw)

    def show_error(self, message):
        win=tk.Toplevel(self.root); win.title('Errore: dettaglio copiabile'); win.geometry('760x350')
        text=ScrolledText(win,wrap='word'); text.pack(fill='both',expand=True,padx=10,pady=10); text.insert('1.0',message); text.configure(state='disabled')
        def copy():
            self.root.clipboard_clear(); self.root.clipboard_append(message)
        ttk.Button(win,text='Copia errore',command=copy).pack(pady=8)

    def warnings(self):
        if self.current is not None and self.jobs[self.current].get('error'):
            self.show_error(self.jobs[self.current]['error']); return
        data=self.result()
        if data:
            win=tk.Toplevel(self.root); win.title('Avvisi da verificare'); win.geometry('750x450')
            text=ScrolledText(win,wrap='word',font=('Segoe UI',11)); text.pack(fill='both',expand=True)
            text.insert('1.0',NOTICE+'\n\n'+'\n\n'.join(data['warnings'])); text.configure(state='disabled')

    def draw(self):
        self.resize_timer=None; self.drag=None; data=self.result()
        if not data or not data['visual']:
            self.canvas.delete('all'); self.page_label.configure(text='Anteprima disponibile per PDF e immagini'); return
        try:
            width=max(400,self.canvas.winfo_width()-20); rect=data['pages'][self.page]['size']; self.scale=min(2.2,width/(rect[2]-rect[0]))
            img=core.render_page(data,self.page,dpi=max(40,round(72*self.scale)),original=self.show_original.get()); self.scale=img.width/(rect[2]-rect[0]); self.image=ImageTk.PhotoImage(img)
            self.canvas.delete('all'); self.canvas.create_image(0,0,anchor='nw',image=self.image); self.canvas.configure(scrollregion=(0,0,img.width,img.height)); self.page_label.configure(text=f'Pagina {self.page+1} / {len(data["pages"])}')
        except Exception as exc: self.status.set('Anteprima non disponibile: '+str(exc))

    def navigate(self,delta):
        data=self.result()
        if data: self.page=max(0,min(len(data['pages'])-1,self.page+delta)); self.canvas.yview_moveto(0); self.draw()

    def start_rect(self,event):
        data=self.result()
        if self.busy or not data or not data['visual']: return
        self.drag=(self.canvas.canvasx(event.x),self.canvas.canvasy(event.y)); self.drag_item=self.canvas.create_rectangle(*self.drag,*self.drag,outline='#e63946',width=2)

    def move_rect(self,event):
        if self.drag: self.canvas.coords(self.drag_item,*self.drag,self.canvas.canvasx(event.x),self.canvas.canvasy(event.y))

    def invalidate(self):
        self.jobs[self.current].update(reviewed=False,dirty=True); self.jobs[self.current].pop('edited_text',None); self.review.set(False); self.job_state(self.current,'Da verificare')

    def end_rect(self,event):
        if not self.drag: return
        x,y=self.drag; self.drag=None; a,b=self.canvas.canvasx(event.x),self.canvas.canvasy(event.y); data=self.result(); size=data['pages'][self.page]['size']
        rect=[max(0,min(x,a)/self.scale),max(0,min(y,b)/self.scale),min(size[2],max(x,a)/self.scale),min(size[3],max(y,b)/self.scale)]
        if rect[2]-rect[0]>2 and rect[3]-rect[1]>2:
            data['manual'].append({'page':self.page,'rect':rect}); self.invalidate(); self.fill(self.preview,core.output_text(data),True)
        self.show_original.set(False); self.draw()

    def undo(self):
        data=self.result()
        if self.busy or not data or not data['manual']: return
        data['manual'].pop(); self.invalidate(); self.fill(self.preview,core.output_text(data),data['visual']); self.draw()

    def mask_selection(self):
        data=self.result()
        if self.busy or not data: return
        try: start=len(self.original.get('1.0','sel.first')); end=len(self.original.get('1.0','sel.last'))
        except (tk.TclError,TypeError): messagebox.showinfo('Seleziona un dato','Seleziona prima il testo nel riquadro originale.'); return
        offset=0
        for p in data['pages']:
            lo=max(0,start-offset); hi=min(len(p['text']),end-offset)
            if lo<hi:
                span={'start':lo,'end':hi,'label':'MANUALE','reason':'Selezione'}; p['spans']=core.merge_spans(p['spans']+[span]); p['masks']+=core.rectangles_for_spans(p['units'],[span])
            offset+=len(p['text'])+2
        self.invalidate(); self.fill(self.preview,core.output_text(data),data['visual']); self.draw()

    def modified(self,event=None):
        if self.preview.edit_modified():
            if self.result() and not self.result()['visual']: self.invalidate(); self.jobs[self.current]['edited_text']=self.preview.get('1.0','end-1c')
            self.preview.edit_modified(False)

    def reviewed(self):
        if self.current is not None: self.jobs[self.current]['reviewed']=self.review.get()

    def retry(self):
        if self.busy or self.current is None: return
        if self.jobs[self.current].get('dirty') and not messagebox.askyesno('Rielaborare?','Rielaborando perderai le correzioni non salvate. Continuare?'): return
        self.jobs[self.current].update(options=self.options(),reviewed=False); self.jobs[self.current].pop('edited_text',None); self.start(self.current)

    def save(self):
        data=self.result()
        if self.busy or not data: return
        if not self.review.get(): messagebox.showinfo('Revisione necessaria','Controlla tutte le pagine e spunta la conferma.'); return
        types=([('PDF con impaginazione (pagine immagine)','*.pdf')] if data['visual'] else [])+[('Testo UTF-8','*.txt'),('Word ricostruito','*.docx')]
        ext='.pdf' if data['visual'] else '.txt'; stem='documento_OCR_NON_OSCURATO' if data['options'].get('ocr_only') else 'documento_oscurato'
        dest=filedialog.asksaveasfilename(initialfile=stem+ext,defaultextension=ext,filetypes=types)
        if not dest: return
        import os
        target=Path(dest)
        if any(target.resolve()==Path(j['path']).resolve() or (target.exists() and os.path.samefile(target,j['path'])) for j in self.jobs):
            messagebox.showerror('Originale protetto','Scegli un nome diverso da tutti i documenti originali della coda.'); return
        self.busy='save'; self.lock(); self.progress.start(); self.status.set('Creazione e verifica della copia esportata…'); i=self.current; override=self.jobs[i].get('edited_text')
        def run():
            try: core.save(data,dest,override,progress=lambda value:self.events.put((i,{'progress':'Esportazione della copia oscurata…','percent':value}))); self.events.put((i,{'saved':dest}))
            except Exception as exc: self.events.put((i,{'save_error':str(exc)}))
        threading.Thread(target=run,daemon=True).start()

    def cancel(self):
        if self.busy!='process': return
        for i,j in enumerate(self.jobs):
            if j['state']=='In attesa': self.job_state(i,'Interrotto')
        if self.proc and self.proc.poll() is None: self.proc.terminate()
        self.status.set('Interruzione in corso…')

    def close(self):
        if self.busy=='save': messagebox.showinfo('Salvataggio in corso','Attendi il completamento del salvataggio.'); return
        if (self.busy or any(j.get('dirty') for j in self.jobs)) and not messagebox.askyesno('Chiudere?','Interrompere e chiudere? I risultati non salvati andranno persi.'): return
        self.cancel(); self.root.destroy()


def main():
    root=TkinterDnD.Tk(); splash(root,lambda:Studio(root)); root.mainloop()


if __name__=='__main__': main()
