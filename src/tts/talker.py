from .text_speech_helper import speak

def talker(obj_name: str):
    """Speaks a sentence describing the detected object."""
    #sentence = f"The object I am looking at is a {obj_name}."
    #speak(sentence, f"tts_{obj_name}.wav")
    speak(obj_name)
