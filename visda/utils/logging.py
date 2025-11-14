import sys, time

COL = {
    "RESET": "\033[0m", "DIM": "\033[2m",
    "CYAN": "\033[36m", "GREEN": "\033[32m",
    "YELLOW": "\033[33m", "RED": "\033[31m",
}

def log(level: str, *msg):
    ts = time.strftime("%H:%M:%S")
    color = {"INFO": "CYAN", "OK": "GREEN", "WARN": "YELLOW", "ERR": "RED"}.get(level, "CYAN")
    s = " ".join(str(x) for x in msg)
    sys.stdout.write(f"{COL[color]}[{ts} {level}]{COL['RESET']} {s}\n")
    sys.stdout.flush()
