# import sounddevice as sd

# print("Devices:")
# for i, dev in enumerate(sd.query_devices()):
#     print(i, dev["name"], "in_ch=", dev["max_input_channels"])

# print("\nChecking sample rates:")
# for rate in [8000, 16000, 32000, 44100, 48000]:
#     try:
#         sd.check_input_settings(device=None, samplerate=rate, channels=1)
#         print("OK ", rate)
#     except Exception as e:
#         print("BAD", rate, "->", e)

import sounddevice as sd

print("Default device:", sd.default.device)
print(sd.query_devices())
