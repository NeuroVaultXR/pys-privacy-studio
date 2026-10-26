# PyS – Privacy Studio
**Salvatore Urbano / NeuroVaultXR** · Windows x64 · Version 1.5.1

[Italiano](#italiano) · [English](#english)

## Italiano
Applicazione desktop per estrarre testo tramite OCR e assistere l'oscuramento dei dati personali. Integra OpenAI Privacy Filter, RapidOCR e, nelle configurazioni complete, Baidu Unlimited-OCR. Ideazione, personalizzazione e integrazione PyS di Salvatore Urbano, con sviluppo assistito dall'AI.

### Funzioni
- Caricamento drag-and-drop di PDF, immagini, TXT e DOCX.
- Oscuramento automatico, termini personalizzati e gestione delle date.
- Confronto originale/risultato e rettangoli manuali di oscuramento.
- Modalità Solo OCR; esportazione PDF, TXT e DOCX secondo il contenuto e la modalità.
- Configurazione guidata Base, Completa CPU o Completa NVIDIA compatibile.

### Installazione
Installa Python **3.13 a 64 bit** da https://www.python.org/downloads/windows/ con pip e Tcl/Tk, poi [il pacchetto PyS-PrivacyStudio.msi](https://github.com/NeuroVaultXR/pys-privacy-studio/raw/refs/heads/main/downloads/PyS-PrivacyStudio.msi). Avvia PyS dal menu Start, scegli la configurazione e premi **Scarica e configura**. Il primo download richiede Internet; i documenti vengono elaborati localmente.
Le istruzioni complete sono in [ISTRUZIONI.txt](ISTRUZIONI.txt). Il repository contiene i sorgenti; non contiene pesi dei modelli o ambienti Python.

### Requisiti indicativi della configurazione
| Modalità | Requisiti |
|---|---|
| Base | Privacy Filter e RapidOCR su CPU; circa 10 GiB di disco libero durante la configurazione |
| Completa CPU | Almeno 17 GiB di RAM libera; circa 22 GiB di disco |
| Completa NVIDIA | GPU BF16, compute capability >= 8.0 e almeno 8 GiB di VRAM libera; circa 35 GiB di disco |
GTX 1650 non compatibile con Unlimited-OCR GPU. Privacy Filter e RapidOCR restano su CPU. I modelli richiedono circa 2,8 GB (Privacy Filter) e ulteriori 6,7 GB (Unlimited-OCR), oltre alle librerie.

### Stato e limiti
Prima versione pubblica, in evoluzione. La modalità NVIDIA non è ancora stata verificata su GPU reale. Non viene dichiarato un nuovo collaudo funzionale completo dell'ultimo installer.
OCR e modelli possono omettere dati o produrre errori: è necessaria la revisione di tutte le pagine prima di condividere il risultato. Nessuna anonimizzazione infallibile o certificazione è dichiarata.
Il PDF oscurato è composto da pagine-immagine, senza testo originale selezionabile. Il budget RAM è monitorato e non è un limite rigido di Windows.

### Ricompilazione MSI
Da Windows, con runtime .NET compatibile (6 o successivo), esegui `./Build-MSI.ps1` dalla radice. Lo script scarica WiX 4.0.6 e produce `outputs/PyS-PrivacyStudio.msi`. La struttura `work/msi_payload` deve essere conservata. Non sono richiesti download di modelli per compilare il pacchetto.
La riproducibilità binaria esatta non è garantita.

SHA-256 dell’installer: [PyS-PrivacyStudio.sha256.txt](downloads/PyS-PrivacyStudio.sha256.txt).

## English
A local Windows application combining document OCR, assisted personal-data redaction, previews and manual review. PyS integrates existing engines; it does not claim authorship of those models.
Install Python 3.13 x64 with pip and Tcl/Tk, [download the MSI](https://github.com/NeuroVaultXR/pys-privacy-studio/raw/refs/heads/main/downloads/PyS-PrivacyStudio.msi) and install it, then use the visible configuration wizard. Initial model/dependency downloads require Internet. Documents are processed locally.
The source tree includes the application and MSI build inputs, not model weights or Python environments. Base runs on CPU; full CPU needs at least 17 GiB free RAM; NVIDIA requires a compatible BF16 GPU with at least 8 GiB free VRAM and has not yet been tested on actual GPU hardware. Human review remains necessary. Redacted PDFs use rasterized pages without selectable original text.

## Attribution and rights
- [OpenAI Privacy Filter](https://github.com/openai/privacy-filter): OpenAI, Apache 2.0; license included under `work/msi_payload/_internal/licenses/`.
- [Unlimited-OCR](https://github.com/baidu/Unlimited-OCR): Baidu, MIT; license included in the same directory.
- RapidOCR, PyMuPDF/MuPDF and other dependencies retain their own licenses. PyMuPDF/MuPDF is offered under AGPL or a commercial license.
PyS branding and customization: Salvatore Urbano. This attribution does not transfer authorship of third-party engines. No blanket relicensing of this combined distribution is asserted here. See included notices and upstream licenses before reuse or redistribution.

Contact: salvatore.urbano99@gmail.com · https://neurovaultxr.com
