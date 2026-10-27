# PyS – Privacy Studio
**NeuroVaultXR · Windows**

[Italiano](#italiano) · [English](#english)

## Italiano
PyS è un’applicazione desktop per estrarre testo dai documenti e assistere l’oscuramento dei dati personali. Integra OpenAI Privacy Filter, RapidOCR e Baidu Unlimited-OCR in un’interfaccia con anteprima e revisione manuale.

### Cosa puoi fare
- Caricare PDF, immagini, TXT e DOCX tramite drag-and-drop.
- Oscurare dati personali e aggiungere termini da cercare.
- Confrontare originale e risultato, correggendo manualmente gli oscuramenti.
- Usare la modalità Solo OCR ed esportare i risultati.

### Installazione
1. Installa [Python 3.13 a 64 bit](https://www.python.org/downloads/windows/) con pip e Tcl/Tk.
2. Scarica e avvia [l’installer PyS](https://github.com/NeuroVaultXR/pys-privacy-studio/raw/refs/heads/main/downloads/PyS-PrivacyStudio.msi).
3. Apri PyS dal menu Start e completa la configurazione guidata.

La prima configurazione richiede Internet per scaricare i componenti necessari. I documenti vengono elaborati localmente.

Puoi scegliere la configurazione Base o una configurazione completa con Unlimited-OCR. Le istruzioni operative sono in [ISTRUZIONI.txt](ISTRUZIONI.txt).

### Prima di condividere un risultato
Controlla sempre ogni pagina: OCR e oscuramento automatico possono commettere errori o omettere dati. Puoi correggere il risultato nell’anteprima. I PDF oscurati vengono esportati come pagine-immagine, senza testo originale selezionabile.

La modalità NVIDIA è sperimentale e non è ancora stata verificata su hardware GPU reale per questa integrazione.

### Sorgenti
Il repository contiene l’applicazione e i file per costruire l’installer. Per ricompilare l’MSI su Windows, usa lo script `Build-MSI.ps1` con un runtime .NET compatibile, mantenendo la struttura delle cartelle. I modelli vengono scaricati durante la configurazione e non sono inclusi nel repository.

[Checksum SHA-256 dell’installer](downloads/PyS-PrivacyStudio.sha256.txt)

## English
PyS is a Windows desktop application for document OCR and assisted personal-data redaction. It brings OpenAI Privacy Filter, RapidOCR and Baidu Unlimited-OCR together with previews and manual review.

### Features
- Drag-and-drop PDF, image, TXT and DOCX files.
- Redact personal data and add custom search terms.
- Compare the original and the result, then correct redactions manually.
- Use OCR-only mode and export the results.

### Installation
Install [Python 3.13 x64](https://www.python.org/downloads/windows/) with pip and Tcl/Tk, then [download and run the PyS installer](https://github.com/NeuroVaultXR/pys-privacy-studio/raw/refs/heads/main/downloads/PyS-PrivacyStudio.msi). Open PyS from the Start menu and complete the setup wizard. Initial setup requires Internet; documents are processed locally.

Choose Base or a full configuration with Unlimited-OCR. Review every page before sharing a result: automatic OCR and redaction can miss information or make mistakes. Exported redacted PDFs use image-based pages without selectable original text. NVIDIA mode is experimental and has not yet been tested on actual GPU hardware for this integration.

The repository includes application and MSI build sources; model files are downloaded during setup.

## Attribution and rights
PyS design, customisation and integration: Salvatore Urbano, with AI-assisted development.

- [OpenAI Privacy Filter](https://github.com/openai/privacy-filter): OpenAI, Apache 2.0; license included under `work/msi_payload/_internal/licenses/`.
- [Unlimited-OCR](https://github.com/baidu/Unlimited-OCR): Baidu, MIT; license included in the same directory.
- RapidOCR, PyMuPDF/MuPDF and other dependencies retain their own licenses. PyMuPDF/MuPDF is offered under AGPL or a commercial license.

The original authors retain authorship of the underlying engines. No blanket relicensing of this combined distribution is asserted here. See the included notices and upstream licenses before reuse or redistribution.

Contact: neurovaultxr@gmail.com · https://neurovaultxr.com
