import os, sys

# make sure we can import src.vision and src.tts when running `python -m src.main`
CURRENT_DIR = os.path.dirname(__file__)
sys.path.append(CURRENT_DIR)

from tts.talker import talker
from vision.object import run_object_detection

def handle_detected_object(label: str):
    if label[len(label) - 1] == 's':
        sentence = f"I am looking at {label}"
    else:
        sentence = f"I am looking at a {label}"
    talker(sentence)

def main():
    print("System starting...")

    run_object_detection(on_detect=handle_detected_object)

if __name__ == "__main__":
    main()