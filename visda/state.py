from dataclasses import dataclass, field
from threading import Lock
from typing import List, Tuple
import numpy as np

@dataclass
class SharedState:
    lock: Lock = field(default_factory=Lock)
    frame: np.ndarray | None = None
    shape: Tuple[int,int] = (480,640)
    dets: List[Tuple[str, float, Tuple[float,float,float,float]]] = field(default_factory=list)
    fps: float = 0.0
    last_spoken: str = ""
    tts_busy: bool = False
    wake_count: int = 0
    last_asr_partial: str = ""
    last_asr_final: str = ""
    muted: bool = False

STATE = SharedState()
