"""PyS identity and phase-based progress widgets."""
from pathlib import Path
import tkinter as tk
from tkinter import ttk
from PIL import Image,ImageTk
BASE=Path(__file__).resolve().parent
BG='#f3eee2'; PANEL='#fffdf7'; INK='#24251f'; BLUE='#86c7fa'
GRADIENT=['#f1e9d5','#eaf8bb','#c4f1ed','#86c7fa']

def identity(root):
    try:
        import ctypes
        ctypes.windll.shell32.SetCurrentProcessExplicitAppUserModelID('PyS.PrivacyStudio')
    except (AttributeError,OSError): pass
    try: root.iconbitmap(default=str(BASE/'assets/pys-ivory.ico'))
    except tk.TclError: pass

def theme(root):
    root.configure(bg=BG)
    style=ttk.Style(root);style.theme_use('clam')
    style.configure('.',background=BG,foreground=INK,font=('Segoe UI',10))
    style.configure('TButton',padding=7,background='#d7ebef',foreground=INK)
    style.map('TButton',background=[('active','#b8def7'),('disabled','#e5e4df')])
    style.configure('TEntry',fieldbackground=PANEL)
    style.configure('TCombobox',fieldbackground=PANEL)
    style.configure('Treeview',background=PANEL,fieldbackground=PANEL,rowheight=27)
    style.map('Treeview',background=[('selected','#c4e5f7')],foreground=[('selected',INK)])
    style.configure('TNotebook.Tab',padding=(14,7))
    style.map('TNotebook.Tab',background=[('selected',PANEL)])
    return style

class GradientProgress(tk.Canvas):
    def __init__(self,master):
        super().__init__(master,height=27,highlightthickness=0,bg=BG)
        self.value=0;self.bind('<Configure>',lambda e:self.paint())
    def set(self,value):
        self.value=max(self.value,min(100,float(value)));self.paint()
    def start(self):
        self.value=0;self.paint()
    def stop(self): pass
    def paint(self):
        self.delete('all');w=max(1,self.winfo_width());h=25
        self.create_rectangle(0,0,w,h,fill='#e2e4df',outline='')
        end=round(w*self.value/100)
        for x in range(0,end,3):
            position=(x/max(1,w-1))*(len(GRADIENT)-1);i=min(len(GRADIENT)-2,int(position));f=position-i
            a=GRADIENT[i];b=GRADIENT[i+1]
            rgb=[round(int(a[k:k+2],16)*(1-f)+int(b[k:k+2],16)*f) for k in (1,3,5)]
            color='#%02x%02x%02x'%tuple(rgb)
            self.create_rectangle(x,0,min(x+3,end),h,fill=color,outline='')
        self.create_text(w/2,h/2,text=f'{self.value:.0f}% · avanzamento per fasi',fill=INK,font=('Segoe UI',9,'bold'))

def splash(root,ready):
    identity(root);root.withdraw()
    win=tk.Toplevel(root);win.overrideredirect(True);win.configure(bg=BG)
    width,height=640,500
    win.geometry(f'{width}x{height}+{(win.winfo_screenwidth()-width)//2}+{(win.winfo_screenheight()-height)//2}')
    picture=Image.open(BASE/'assets/logo.png').convert('RGBA')
    bounds=picture.getchannel('A').point(lambda a:255 if a>=32 else 0).getbbox()
    if bounds: picture=picture.crop(bounds)
    picture.thumbnail((600,365),Image.Resampling.LANCZOS)
    win.logo=ImageTk.PhotoImage(picture)
    tk.Label(win,image=win.logo,bg=BG).pack(pady=(14,6))
    tk.Label(win,text='PyS - Privacy Studio',bg=BG,fg=INK,font=('Segoe UI',17,'bold')).pack()
    tk.Label(win,text='Powered by Salvatore Urbano',bg=BG,fg=INK,font=('Segoe UI',12)).pack(pady=10)
    def reveal():
        win.destroy();ready();root.deiconify()
    root.after(1500,reveal)
