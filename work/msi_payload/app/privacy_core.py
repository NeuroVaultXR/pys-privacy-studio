"""Offline OCR, PII detection and image-only sanitized PDF export.

Coordinates are in rendered page points (rotation included). Only newly painted
pixels enter exported PDFs; original PDF objects, layers and attachments never do.
"""
from pathlib import Path
import hashlib
import json
import os
import re
import tempfile

BASE = Path(__file__).resolve().parent
SUPPORTED = {'.pdf', '.txt', '.docx', '.png', '.jpg', '.jpeg', '.tif', '.tiff', '.bmp'}


def offline():
    os.environ.update(HF_HUB_OFFLINE='1', HF_HUB_DISABLE_TELEMETRY='1',
                      TIKTOKEN_CACHE_DIR=str(BASE / 'tokenizer_cache'))
    import socket
    def blocked(*args, **kwargs):
        raise RuntimeError('Rete disabilitata: manca un componente locale. Ripristina modelli e tokenizer.')
    socket.socket.connect = blocked
    socket.create_connection = blocked
    socket.getaddrinfo = blocked


def digest(path):
    with open(path, 'rb') as handle:
        return hashlib.file_digest(handle, 'sha256').hexdigest()


def intersection(a, b):
    return max(0, min(a[2], b[2])-max(a[0], b[0])) * max(0, min(a[3], b[3])-max(a[1], b[1]))


def area(a):
    return max(0, a[2]-a[0])*max(0, a[3]-a[1])


def terms_list(value):
    if isinstance(value, list):
        return [x.strip() for x in value if x.strip()]
    return [x.strip() for x in re.split(r'[;\n]', value) if x.strip()]


def find_terms(text, terms):
    found, counts = [], {}
    for term in terms_list(terms):
        words = term.split()
        variants = [words]
        if len(words) > 1:
            variants.append(words[::-1])
        patterns = [r'[\s\u00ad-]+'.join(re.escape(w) for w in v) for v in variants]
        matches = list(re.finditer(r'(?<!\w)(?:' + '|'.join(patterns) + r')(?!\w)', text, flags=re.I))
        counts[term] = len(matches)
        found += [{'start':m.start(), 'end':m.end(), 'label':'MANUALE', 'reason':'Oscura sempre'} for m in matches]
    return found, counts


def merge_spans(spans):
    result = []
    for s in sorted(spans, key=lambda s: (s['start'], s['end'])):
        if result and s['start'] < result[-1]['end']:
            result[-1]['end'] = max(result[-1]['end'], s['end'])
        else:
            result.append(dict(s))
    return result


def redact_text(text, spans):
    out, cursor = [], 0
    for s in merge_spans(spans):
        out += [text[cursor:s['start']], '<' + s['label'].upper() + '>']
        cursor = s['end']
    return ''.join(out) + text[cursor:]


def plain_extract(path):
    if path.suffix.lower() == '.txt':
        raw = path.read_bytes()
        if raw.startswith((b'\xff\xfe',b'\xfe\xff')):
            return raw.decode('utf-16'), []
        try:
            return raw.decode('utf-8-sig'), []
        except UnicodeDecodeError:
            return raw.decode('cp1252'), ['TXT interpretato come Windows-1252: controlla gli accenti.']
    from zipfile import ZipFile
    from lxml import etree
    with ZipFile(path) as archive:
        if sum(x.file_size for x in archive.infolist()) > 100*1024*1024:
            raise ValueError('DOCX decompresso troppo grande.')
        names = ['word/document.xml'] + sorted(n for n in archive.namelist()
            if n.startswith(('word/header','word/footer','word/footnotes','word/endnotes')) and n.endswith('.xml'))
        lines=[]
        ns={'w':'http://schemas.openxmlformats.org/wordprocessingml/2006/main'}
        for name in names:
            tree=etree.fromstring(archive.read(name),etree.XMLParser(resolve_entities=False,no_network=True))
            for p in tree.xpath('//w:p',namespaces=ns):
                lines.append(''.join(p.xpath('.//w:t/text()',namespaces=ns)))
    return '\n'.join(lines), ['DOCX: testo ricostruito; immagini, firme, oggetti e commenti non vengono letti. Tabelle e ordine possono cambiare. Per conservarne l’aspetto esporta prima il DOCX in PDF.']


def open_visual(path):
    import pymupdf as fitz
    if Path(path).suffix.lower()=='.pdf':
        return fitz.open(path)
    # Convert image frames in memory. No temporary copies of the original.
    from PIL import Image, ImageOps
    import io
    out=fitz.open()
    with Image.open(path) as source:
        if getattr(source,'n_frames',1)>100:
            raise ValueError('Troppe pagine nell’immagine (massimo 100).')
        for i in range(getattr(source,'n_frames',1)):
            source.seek(i)
            frame=ImageOps.exif_transpose(source).convert('RGB')
            if frame.width*frame.height>40_000_000:
                raise ValueError('Immagine troppo grande (massimo 40 megapixel).')
            data=io.BytesIO(); frame.save(data,format='PNG')
            page=out.new_page(width=frame.width*72/150,height=frame.height*72/150)
            page.insert_image(page.rect,stream=data.getvalue())
    return out


def native_layer(page):
    import pymupdf as fitz
    text, units = '', []
    raw = page.get_text('rawdict', sort=True)
    for block in raw['blocks']:
        if block['type'] != 0:
            continue
        for line in block['lines']:
            for span in line['spans']:
                for char in span['chars']:
                    value=char['c']
                    rect=fitz.Rect(char['bbox']) * page.rotation_matrix
                    units.append({'start':len(text),'end':len(text)+len(value),'rect':list(rect),'origin':'testo'})
                    text+=value
            text+='\n'
    return text, units


class Engine:
    def __init__(self):
        self.model=None
        self.ocr=None
        self.unlimited=None
        self.policy=None

    def detect(self, text, options):
        terms=terms_list(options.get('terms',''))
        manual, counts=find_terms(text,terms)
        if options.get('ocr_only'):
            return [], counts
        if self.model is None:
            from opf import OPF
            checkpoint=Path(os.environ.get('OPF_CHECKPOINT',str(BASE/'models/privacy_filter')))
            if not (checkpoint/'model.safetensors').is_file():
                raise ValueError('Modello Privacy Filter locale mancante.')
            self.model=OPF(model=checkpoint,device='cpu',output_mode='typed',context_window_length=(self.policy or {}).get("context",2048))
        spans=list(manual)
        # Bounded calls with overlap. All matches use offsets into the unchanged source.
        step=(self.policy or {}).get("chunk",5000); overlap=350
        for start in range(0,len(text),step):
            lo=max(0,start-overlap); hi=min(len(text),start+step+overlap)
            chunk=text[lo:hi]
            if not chunk.strip():
                continue
            result=self.model.redact(chunk)
            if result.warning or result.text!=chunk:
                raise ValueError('Il tokenizer ha alterato il testo. Esportazione bloccata per evitare oscuramenti fuori posizione.')
            for s in result.detected_spans:
                if s.label=='private_date' and not options.get('dates',True):
                    continue
                spans.append({'start':lo+s.start,'end':lo+s.end,'label':s.label.upper(),'reason':'Modello'})
        # Supplement the model for common identifiers; dates are separately selectable.
        patterns=[('CODICE_FISCALE',r'(?<!\w)[A-Z]{6}[0-9LMNPQRSTUV]{2}[ABCDEHLMPRST][0-9LMNPQRSTUV]{2}[A-Z][0-9LMNPQRSTUV]{3}[A-Z](?!\w)'),
                  ('PRIVATE_EMAIL',r'\b[\w.+-]+@[\w.-]+\.[A-Z]{2,}\b')]
        if options.get('dates',True):
            patterns.append(('PRIVATE_DATE',r'(?<!\d)\d{1,2}[/.\-]\d{1,2}[/.\-]\d{2,4}(?!\d)'))
        for label, pattern in patterns:
            spans += [{'start':m.start(),'end':m.end(),'label':label,'reason':'Regola'} for m in re.finditer(pattern,text,re.I)]
        # Capitalized names immediately following common Italian form/title labels.
        # Case sensitivity of the name group avoids swallowing surrounding prose.
        name_word=r"[A-ZÀ-ÖØ-Þ][A-Za-zÀ-ÖØ-öø-ÿ'’\-]+"
        labelled=r'(?i:dott\.re/ssa|dott\.ssa|dott\.|sig\.re/ra\s*:|paziente\s*:|nominativo\s*:)\s*(' + name_word + r'(?:[ \t]+'+name_word+r'){1,3})'
        spans += [{'start':m.start(1),'end':m.end(1),'label':'PRIVATE_PERSON','reason':'Etichetta nominativo'} for m in re.finditer(labelled,text)]
        return merge_spans(spans), counts

    def ocr_layer(self, page, native_units, full=False):
        from PIL import Image
        import numpy as np
        if self.ocr is None:
            from rapidocr import RapidOCR
            self.ocr=RapidOCR(params={'Global.log_level':'error','Global.text_score':0.35})
        pix=page.get_pixmap(dpi=(self.policy or {}).get("dpi",180),alpha=False,annots=True)
        # PIL input ensures correct RGB -> BGR handling in RapidOCR.
        img=Image.frombytes('RGB',(pix.width,pix.height),pix.samples)
        result=self.ocr(img,return_word_box=True)
        sx=page.rect.width/pix.width; sy=page.rect.height/pix.height
        text=''; units=[]; low=0
        if not result.txts:
            return text, units, low
        for line, score, box, words in zip(result.txts,result.scores,result.boxes,result.word_results):
            # Word boxes allow masking a name without covering neighbouring test results.
            items=words or [(line,float(score),box.tolist())]
            line_added=False
            for value, confidence, poly in items:
                a=np.asarray(poly)
                rect=[float(a[:,0].min()*sx),float(a[:,1].min()*sy),float(a[:,0].max()*sx),float(a[:,1].max()*sy)]
                coverage=sum(intersection(rect,u['rect']) for u in native_units)
                if not full and coverage/max(1,area(rect))>0.35:
                    continue
                if not value.strip():
                    continue
                if line_added:
                    text+=' '
                units.append({'start':len(text),'end':len(text)+len(value),'rect':rect,'origin':'OCR'})
                text+=value; line_added=True
                if confidence<0.85:
                    low+=1
            if line_added:
                text+='\n'
        return text,units,low

    def process(self, path, options=None, progress=lambda message:None):
        try:
            return self._process(path,options,progress)
        finally:
            if self.unlimited is not None:
                self.unlimited.close(); self.unlimited=None

    def _process(self, path, options=None, progress=lambda message:None):
        options=dict(options or {})
        from memory_policy import profile
        self.policy=profile(options.get('ram_gib',24))
        if not options.get('ocr_only') and self.policy['budget']<4:
            raise ValueError('Budget RAM troppo basso per Privacy Filter: imposta almeno 4 GiB o libera memoria.')
        if options.get('engine')=='unlimited' and self.policy['budget']<(17 if options.get('device','cpu')=='cpu' else 8):
            raise ValueError('Budget insufficiente per Unlimited-OCR: servono almeno 17 GiB su CPU o 8 GiB di RAM di sistema in modalita GPU. Scegli RapidOCR oppure aumenta il budget se disponibile.')
        def report(percent,message): progress({'progress':message,'percent':percent})
        report(0,'Lettura documento…')
        path=Path(path)
        if path.suffix.lower() not in SUPPORTED or not path.is_file():
            raise ValueError('File non supportato o mancante.')
        if path.stat().st_size>40*1024*1024:
            raise ValueError('File troppo grande (massimo 40 MB).')
        fingerprint=digest(path)
        data={'source':str(path),'sha256':fingerprint,'options':options,'pages':[], 'warnings':[], 'manual':[], 'term_counts':{t:0 for t in terms_list(options.get('terms',''))}}
        if self.policy['dpi']<180:
            data['warnings'].append('Risparmio RAM attivo: OCR a 150 DPI e analisi in blocchi piu piccoli. Testi minuti possono essere riconosciuti meno bene; controlla tutte le pagine.')
        visual=path.suffix.lower() not in ('.txt','.docx')
        if visual:
            with open_visual(path) as doc:
                if doc.is_encrypted:
                    raise ValueError('PDF protetto: prepara una copia senza password.')
                if len(doc)>100:
                    raise ValueError('Massimo 100 pagine per documento: dividilo in parti.')
                total=0
                for n,page in enumerate(doc):
                    if page.rect.width*page.rect.height*(180/72)**2 > 40_000_000:
                        raise ValueError('Pagina troppo grande per l’elaborazione locale.')
                    report(95*n/len(doc),f'Pagina {n+1}/{len(doc)}: lettura e OCR locale…')
                    text,units=native_layer(page)
                    used_ocr=False
                    if options.get('ocr',True) or not text.strip():
                        extra,extra_units,low=self.ocr_layer(page,units,full=options.get('force_ocr',False))
                        if extra:
                            offset=len(text)
                            for u in extra_units:
                                u['start']+=offset; u['end']+=offset
                            text+=extra; units+=extra_units
                        used_ocr=True
                        if low:
                            data['warnings'].append(f'Pagina {n+1}: {low} parole OCR con bassa confidenza. Controlla la pagina e aggiungi rettangoli manuali.')
                    if not text.strip():
                        data['warnings'].append(f'Pagina {n+1}: nessun testo riconosciuto. Potrebbe essere vuota, ruotata o illeggibile: devi controllarla visivamente.')
                    report(95*(n+0.3)/len(doc),f'Pagina {n+1}/{len(doc)}: prima lettura completata')
                    base_text=text; base_units=list(units); advanced_units=[]; advanced_start=None
                    if options.get('engine')=='unlimited':
                        from unlimited_adapter import Client
                        if self.policy['unload_between_stages']:
                            self.model=None
                            import gc
                            gc.collect()
                        if self.unlimited is None: self.unlimited=Client(progress, device=options.get('device','cpu'), budget=self.policy['budget'])
                        progress(f'Pagina {n+1}/{len(doc)}: Unlimited-OCR {options.get("device","cpu").upper()} (può richiedere minuti)…')
                        advanced,advanced_units,elapsed=self.unlimited.page(page)
                        if self.policy['unload_between_stages']:
                            self.unlimited.close(); self.unlimited=None
                        text+='\n\n--- LETTURA AGGIUNTIVA UNLIMITED-OCR ---\n'
                        advanced_start=len(text)
                        text+=advanced
                        for u in advanced_units:
                            u['start']+=advanced_start; u['end']+=advanced_start
                        units+=advanced_units
                        used_ocr=True
                        data['warnings'].append(f'Pagina {n+1}: Unlimited-OCR ha impiegato {elapsed}s. Il testo include due letture; la seconda può contenere errori o contenuto inventato. Verifica soprattutto tabelle e numeri.')
                    total+=len(text)
                    if total>200000:
                        raise ValueError('Testo estratto oltre 200.000 caratteri. Dividi il documento.')
                    report(95*(n+0.65)/len(doc),f'Pagina {n+1}/{len(doc)}: ricerca dati personali…')
                    spans,counts=self.detect(text,options) if text.strip() else ([],{})
                    masks=rectangles_for_spans(base_units,spans)
                    if advanced_start is not None:
                        for s in spans:
                            if s['end']<=advanced_start: continue
                            value=text[max(s['start'],advanced_start):s['end']].strip()
                            pattern=r'\s+'.join(re.escape(w) for w in value.split())
                            matches=list(re.finditer(r'(?<!\w)'+pattern+r'(?!\w)',base_text,re.I)) if pattern else []
                            precise=[]
                            for m in matches: precise+=rectangles_for_spans(base_units,[{'start':m.start(),'end':m.end()}])
                            regions=rectangles_for_spans(advanced_units,[s])
                            if precise: masks+=precise
                            elif regions:
                                masks+=regions
                                data['warnings'].append(f'Pagina {n+1}: alcuni dati Unlimited-OCR sono coperti per intero blocco; controlla se sono state nascoste informazioni utili.')
                            else:
                                # Fail closed if a sensitive finding cannot be located on the page.
                                masks.append(list(page.rect))
                                data['warnings'].append(f'Pagina {n+1}: dato rilevato da Unlimited-OCR senza posizione verificabile. Pagina interamente coperta per prudenza; puoi rielaborarla con RapidOCR e intervenire manualmente.')
                        # Unpositioned advanced text remains selectable: mask whole page if selected.
                        if not advanced_units:
                            units.append({'start':advanced_start,'end':len(text),'rect':list(page.rect),'origin':'Unlimited-OCR senza coordinate'})
                    data['pages'].append({'text':text,'units':units,'spans':spans,'masks':masks,'size':list(page.rect),'ocr':used_ocr})
                    report(95*(n+1)/len(doc),f'Pagina {n+1}/{len(doc)}: completata')
                    for term,count in counts.items():
                        data['term_counts'][term]+=count
                data['warnings'].append('PDF finale: pagine-immagine con impaginazione conservata. Il testo non sarà selezionabile; firme digitali, allegati, livelli e metadati originali non vengono trasferiti.')
        else:
            text,warnings=plain_extract(path)
            if not text.strip():
                raise ValueError('Nessun testo leggibile.')
            if len(text)>200000:
                raise ValueError('Testo oltre 200.000 caratteri.')
            report(15,'Testo estratto: ricerca dati personali…')
            spans,counts=self.detect(text,options)
            data['pages']=[{'text':text,'units':[],'spans':spans,'masks':[],'size':None,'ocr':False}]
            data['warnings']+=warnings
            data['term_counts']=counts
        report(97,'Preparazione risultato…')
        data['visual']=visual
        if digest(path)!=fingerprint:
            raise ValueError('Il file è cambiato durante l’elaborazione: riaprilo.')
        if not options.get('ocr_only'):
            for term,count in data['term_counts'].items():
                if not count:
                    data['warnings'].append(f'ATTENZIONE: «{term}» non trovato. L’OCR può averlo letto male: controlla le pagine e coprilo manualmente.')
            if not sum(len(p['spans']) for p in data['pages']):
                data['warnings'].append('Nessun dato riconosciuto NON significa assenza di dati personali.')
        return data


def rectangles_for_spans(units,spans):
    # Keep individual char/word boxes: no union across columns or lines.
    result=[]
    for s in spans:
        for u in units:
            if u['start']<s['end'] and s['start']<u['end']:
                result.append(u['rect'])
    return result


def all_masks(data,page_index):
    return data['pages'][page_index]['masks'] + [m['rect'] for m in data['manual'] if m['page']==page_index]


def output_text(data):
    pages=[]
    for i,p in enumerate(data['pages']):
        spans=list(p['spans'])
        for m in data['manual']:
            if m['page']!=i:
                continue
            spans += [{'start':u['start'],'end':u['end'],'label':'MANUALE'} for u in p['units'] if intersection(m['rect'],u['rect'])>0]
        pages.append(redact_text(p['text'],spans))
    return '\n\n'.join(pages)


def check_source(data):
    if digest(data['source'])!=data['sha256']:
        raise ValueError('L’originale è cambiato dopo l’analisi: riaprilo prima di salvare.')


def render_page(data,index,dpi=120,original=False,document=None):
    from PIL import Image, ImageDraw
    import math
    own=document is None
    doc=document if document is not None else open_visual(data['source'])
    try:
        page=doc[index]
        pix=page.get_pixmap(dpi=dpi,alpha=False,annots=True)
        img=Image.frombytes('RGB',(pix.width,pix.height),pix.samples)
        if not original:
            draw=ImageDraw.Draw(img)
            sx=img.width/page.rect.width; sy=img.height/page.rect.height
            for rect in all_masks(data,index):
                # Small padding covers antialiasing at glyph edges.
                x0,y0,x1,y1=rect
                draw.rectangle((math.floor((x0-1.0)*sx), math.floor((y0-1.0)*sy),
                                math.ceil((x1+1.0)*sx), math.ceil((y1+1.0)*sy)),fill='black')
        return img
    finally:
        if own:
            doc.close()


def save(data,destination,text_override=None,progress=lambda value:None):
    import io
    import pymupdf as fitz
    destination=Path(destination); source=Path(data['source'])
    if destination.resolve()==source.resolve() or (destination.exists() and os.path.samefile(destination,source)):
        raise ValueError('Non puoi sovrascrivere l’originale.')
    check_source(data)
    suffix=destination.suffix.lower()
    if suffix not in ('.pdf','.txt','.docx'):
        raise ValueError('Scegli PDF, TXT oppure DOCX.')
    if suffix=='.pdf' and not data['visual']:
        raise ValueError('Per conservare l’impaginazione, apri prima un PDF o un’immagine. TXT e DOCX si esportano in TXT/DOCX.')
    fd,temp=tempfile.mkstemp(dir=destination.parent,suffix=suffix); os.close(fd)
    try:
        if suffix=='.pdf':
            with open_visual(source) as original, fitz.open() as final:
                for i in range(len(data['pages'])):
                    image=render_page(data,i,dpi=180,document=original)
                    buf=io.BytesIO(); image.save(buf,format='PNG')
                    p=final.new_page(width=original[i].rect.width,height=original[i].rect.height)
                    p.insert_image(p.rect,stream=buf.getvalue())
                    progress(90*(i+1)/len(data['pages']))
                final.set_metadata({})
                final.save(temp,garbage=4,deflate=True)
            with fitz.open(temp) as verify:
                if len(verify)!=len(data['pages']) or verify.embfile_count() or any(p.get_text().strip() or list(p.annots() or []) or list(p.widgets() or []) or p.get_links() for p in verify):
                    raise ValueError('Verifica di rimozione del contenuto originale fallita.')
        else:
            text=output_text(data) if text_override is None else text_override
            if suffix=='.txt':
                Path(temp).write_text(text,encoding='utf-8')
            else:
                from docx import Document
                doc=Document()
                for line in text.split('\n'):
                    doc.add_paragraph(line)
                doc.save(temp)
        check_source(data)
        os.replace(temp,destination)
        progress(100)
    finally:
        Path(temp).unlink(missing_ok=True)


def worker():
    import sys
    from contextlib import redirect_stdout
    sys.stdin.reconfigure(encoding='utf-8'); sys.stdout.reconfigure(encoding='utf-8')
    wire=sys.stdout
    def send(payload):
        wire.write(json.dumps(payload,ensure_ascii=True)+'\n'); wire.flush()
    request=json.loads(sys.stdin.readline())
    offline()
    try:
        with redirect_stdout(sys.stderr):
            data=Engine().process(request['path'],request['options'],lambda m:send(m if isinstance(m,dict) else {'progress':m}))
        send({'result':data})
    except Exception as exc:
        send({'error':str(exc)})


if __name__=='__main__':
    worker()
