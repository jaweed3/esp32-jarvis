import serial
import time
import re

# 1. MATCH BAUDRATE with ESP32
BAUD_RATE = 921600 
PORT = '/dev/cu.usbmodem31201' # Sesuaikan port lo

try:
    ser = serial.Serial(PORT, BAUD_RATE, timeout=10)
    ser.reset_input_buffer()
    print(f"Connected to {PORT} at {BAUD_RATE}")
except Exception as e:
    print(f"Error opening serial: {e}")
    exit()

# 2. WAIT FOR BOOT
print("Waiting for ESP32 boot...")
time.sleep(2) 

# 3. SEND TRIGGER
print("Sending trigger 'r'...")
ser.write(b'r')

data_wav = b""
file_size = 0
current_state = "WAIT_HEADER"

while True:
    try:
        # Baca line text DULU (ini aman karena handshake kita text)
        line = ser.readline().decode('utf-8', errors='ignore').strip()
        
        if line:
            print(f"[ESP32]: {line}")

        # State Machine untuk parsing
        if current_state == "WAIT_HEADER":
            # Nangkep output C++: "WAV in PSRAM: 640044 bytes"
            match = re.search(r"WAV in PSRAM: (\d+) bytes", line)
            if match:
                file_size = int(match.group(1))
                print(f"--> Detected WAV size: {file_size} bytes")
            
            if line == "START_WAV":
                if file_size == 0:
                    print("Error: Size not detected before START_WAV")
                    break
                print("--> Reading binary stream...")
                current_state = "READING_BINARY"

        elif current_state == "READING_BINARY":
            # BACA SEKALIGUS. Jangan diketeng pakai readline.
            # Kita baca persis sejumlah file_size
            data_wav = ser.read(file_size)
            print(f"--> Read complete. Got {len(data_wav)} bytes.")
            current_state = "DONE"
            break
            
    except serial.SerialException as e:
        print(f"Serial Error: {e}")
        break
    except KeyboardInterrupt:
        print("\nAborted by user.")
        break

# 4. SAVE FILE
if len(data_wav) > 0:
    with open("recorded_fixed.wav", "wb") as f:
        f.write(data_wav)
    print(f"Success! Saved 'recorded_fixed.wav' ({len(data_wav)} bytes)")
else:
    print("Failed: No data captured.")

ser.close()
