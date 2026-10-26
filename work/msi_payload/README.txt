PyS - Privacy Studio
Powered by Salvatore Urbano

INSTALLAZIONE
Installa Python 3.13 a 64 bit da https://www.python.org/downloads/windows/,
con pip e Tcl/Tk. Avvia il pacchetto MSI e scegli una cartella locale in cui il
tuo utente possa scrivere. Se aggiorni un'installazione gia configurata, mantieni
la stessa cartella per riutilizzare modelli e librerie.

Apri PyS - Privacy Studio dal Desktop o dal menu Start. Alla prima apertura scegli
una versione e premi Scarica e configura. Il primo download richiede Internet;
i documenti vengono poi elaborati localmente.

VERSIONI
Base - Privacy Filter & RapidOCR: oscuramento dei dati e OCR rapido su CPU.
Completa - No Nvidia GPU: aggiunge Unlimited-OCR su CPU; almeno 17 GiB di RAM libera.
Completa - Nvidia GPU: include anche Unlimited-OCR su Nvidia compatibile con BF16
(compute capability >= 8.0), con almeno 8 GiB di memoria video libera durante l'uso.
La GTX 1650 non e compatibile con Unlimited-OCR GPU. Privacy Filter e RapidOCR
restano su CPU. Il menu del programma mostra solo i motori effettivamente installati.

Riserva 10 GiB di disco per Base, 22 GiB per Completa CPU o 35 GiB per Nvidia
in fase di configurazione. Privacy Filter occupa circa 2,8 GB di modello;
Unlimited-OCR aggiunge circa 6,7 GB, oltre alle librerie.

ANNULLARE E RIPRENDERE
Puoi premere Annulla oppure chiudere la finestra anche durante la configurazione:
si fermano il download e i processi di installazione avviati dal configuratore.
I blocchi completi dei modelli gia scaricati vengono conservati per riprendere;
la configurazione incompleta non e indicata come pronta. Una libreria interrotta
puo essere reinstallata al tentativo successivo.
Per riprendere apri Configura PyS - Privacy Studio dal menu Start.
Dopo il completamento il pulsante di download rimane disabilitato per i componenti
presenti. Scegli un pacchetto superiore per aggiungerne altri. Apri PyS - Privacy
Studio avvia il programma e chiude il configuratore.

UTILIZZO
Trascina PDF, immagini, TXT o DOCX nella finestra. Inserisci nomi o frasi da oscurare
sempre, separati da punto e virgola, e scegli se oscurare anche le date.
La modalita Solo OCR non oscura i dati. Per cambiare le impostazioni di un documento
gia caricato usa Rielabora selezionato.
Confronta originale e risultato, controlla tutte le pagine e gli avvisi. Aggiungi
rettangoli o seleziona il testo da oscurare manualmente. Conferma la revisione e
salva una copia: il documento originale non viene sovrascritto.
La barra a gradiente indica le fasi completate, non il tempo residuo; puo restare
ferma mentre un modello sta lavorando.

FORMATO DEI RISULTATI
Il PDF esportato conserva l'aspetto con pagine-immagine gia oscurate; non trasferisce
il testo originale nascosto, firme digitali, allegati, collegamenti o metadati.
Il testo non e selezionabile. Per una chat AI che richiede testo esporta anche TXT.
TXT e DOCX ricostruiti possono perdere tabelle e impaginazione. In modalita Unlimited
il testo puo contenere due letture con ripetizioni.

MEMORIA E LIMITI
Il cursore indica un budget monitorato per il processo di analisi e i suoi processi
OCR: non occupa RAM in anticipo e non impone un limite rigido a Windows. Se il
superamento viene rilevato, l'analisi si interrompe. GUI, anteprima e salvataggio
non rientrano in questo budget. La soglia puo essere superata brevemente tra due
rilevamenti. Sotto 8 GiB si usano risoluzione OCR e blocchi piu piccoli; sotto 24 GiB
i modelli vengono caricati in successione, con piu attese. Unlimited CPU richiede
comunque almeno 17 GiB liberi. Il budget vale per nuovi documenti o dopo rielaborazione.

OCR e modelli possono omettere dati. Unlimited-OCR puo anche inventare testo,
numeri o posizioni: verifica sempre l'originale e non interpretare dati clinici
tramite il solo OCR. Nessun oscuramento automatico garantisce anonimato.
Limiti di caricamento: 20 documenti per sessione, 40 MB per file, 100 pagine e
200.000 caratteri per documento. PDF protetti richiedono una copia senza password.

FILE DEL PROGRAMMA
README.txt contiene le istruzioni. app contiene l'applicazione, gli ambienti
Python e i modelli; _internal contiene i servizi di configurazione, lo stato,
le licenze e install.log. Sono componenti necessari: non spostarli o cancellarli.
Se compare un errore, usa Copia dettagli nella configurazione oppure Copia errore
nel programma. Gli originali e gli output dell'utente non vengono eliminati
durante la riorganizzazione dei file del programma.

RIMOZIONE
Disinstalla da Impostazioni Windows > App. Modelli, librerie, impostazioni e output
creati dopo l'installazione possono restare nella cartella. Conserva gli output
necessari e rimuovi poi gli eventuali residui. Python non viene disinstallato.

DIRITTI E COMPONENTI
Personalizzazione PyS - Privacy Studio e identita grafica: Salvatore Urbano.
La dicitura Powered by Salvatore Urbano non modifica i diritti dei componenti terzi.
OpenAI Privacy Filter - progetto originale di OpenAI.
Licenza: Apache License 2.0.
Progetto: https://github.com/openai/privacy-filter
Licenza originale: https://github.com/openai/privacy-filter/blob/main/LICENSE
Testo incluso: _internal/licenses/OpenAI-Privacy-Filter.txt

Unlimited-OCR - progetto originale di Baidu, copyright (c) 2026 Baidu.
Licenza: MIT.
Progetto: https://github.com/baidu/Unlimited-OCR
Licenza originale: https://github.com/baidu/Unlimited-OCR/blob/main/LICENSE
Testo incluso: _internal/licenses/Unlimited-OCR.txt

PyS integra questi progetti con una GUI e adattamenti per l'elaborazione locale.
Gli autori originali conservano i rispettivi diritti; l'attribuzione a Salvatore
Urbano riguarda la personalizzazione PyS e non la paternita dei motori originali.
PyMuPDF/MuPDF: AGPL o licenza commerciale. Python, PyTorch, RapidOCR, ONNX Runtime,
Pillow, tiktoken, tkinterdnd2, python-docx, Transformers e le altre dipendenze
mantengono le rispettive licenze e attribuzioni, incluse nei componenti installati.
I testi delle licenze originali sono conservati; questo README non li sostituisce.
