from .tts.talker import talker

def main():
    #print("System ready. Say 'Hey Visda' to start")

    obj = "Okay Garmin. Video spizer"

    talker(obj)
    
    # while True:
        # wait_for_wake_word() (Hey Visda)
        
        # obj = detect_object()

        # talker(obj)

if __name__ == "__main__":
    main()