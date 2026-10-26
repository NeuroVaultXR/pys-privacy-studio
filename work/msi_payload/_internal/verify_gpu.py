from pathlib import Path
import sys
sys.path.insert(0,str(Path(__file__).resolve().parent.parent/'app'))
import torch
from hardware import gpu_dtype
gpu_dtype(torch,check_free=False)
print('GPU rilevata: '+torch.cuda.get_device_name(0),flush=True)
