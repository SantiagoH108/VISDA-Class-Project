import time
import serial

# Change this if your device name is different:
PORT = "/dev/ttyACM0"  # or "/dev/ttyUSB0"
BAUD = 9600

ser = serial.Serial(PORT, BAUD, timeout=1)
time.sleep(2)  # wait for Arduino reset

def send_command(cmd):
    # cmd should be a string like "ANGLE 90" or "SWEEP"
    line = cmd.strip() + "\n"
    ser.write(line.encode("utf-8"))
    # optionally read response
    resp = ser.readline().decode("utf-8", errors="ignore").strip()
    if resp:
        print("Arduino:", resp)

try:
    # Move to 0°, 90°, 180°
    send_command("ANGLE 0")
    time.sleep(1)
    send_command("ANGLE 90")
    time.sleep(1)
    send_command("ANGLE 180")
    time.sleep(1)

    # Do a sweep
    send_command("SWEEP")

    # Interactive mode:
    while True:
        angle = input("Enter angle (0-180) or 'q' to quit: ")
        if angle.lower() == 'q':
            break
        try:
            a = int(angle)
        except ValueError:
            print("Please enter a number.")
            continue

        if 0 <= a <= 180:
            send_command(f"ANGLE {a}")
        else:
            print("Angle must be between 0 and 180")

finally:
    ser.close()
