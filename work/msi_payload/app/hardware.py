"""Hardware checks for the supported BF16 NVIDIA execution path."""
def gpu_dtype(torch,check_free=True):
    if not torch.cuda.is_available():
        raise RuntimeError('GPU NVIDIA non disponibile: scegli CPU oppure installa il pacchetto NVIDIA e aggiorna il driver.')
    if torch.cuda.get_device_capability()[0]<8 or not torch.cuda.is_bf16_supported():
        raise RuntimeError('GPU non compatibile con BF16. GTX 1650 e RTX 20 non supportate: scegli CPU o RapidOCR.')
    free,total=torch.cuda.mem_get_info()
    if (free if check_free else total)<8*1024**3:
        raise RuntimeError('Memoria video insufficiente: servono almeno 8 GiB liberi durante l’uso. Scegli CPU o RapidOCR.')
    return torch.bfloat16
