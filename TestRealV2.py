
import RPi.GPIO as GPIO
import time
import os
import glob
import sys
from hx711 import HX711  # Import HX711 module for load cell (weight sensor)

# Mount the 1-Wire modules for the temperature sensor
os.system('modprobe w1-gpio')
os.system('modprobe w1-therm')

# Locate the directory for the 1-Wire temperature sensor
base_dir = '/sys/bus/w1/devices/'
device_folder = glob.glob(base_dir + '28*')[0]
device_file = device_folder + '/w1_slave'

# GPIO pin for the button
BUTTON_PIN = 17

# Set up GPIO
GPIO.setwarnings(True)
GPIO.setmode(GPIO.BCM)
GPIO.setup(BUTTON_PIN, GPIO.IN, pull_up_down=GPIO.PUD_UP)

# Track the device's state and button press timing
current_state = False  # False means OFF
press_time = None

# Initialize the HX711 for the load cell
hx = HX711(16, 20)  # DT = GPIO 16, SCK = GPIO 20
hx.set_reading_format("MSB", "MSB")
referenceUnit = 114  # Calibration factor
hx.set_reference_unit(referenceUnit)
hx.reset()
hx.tare()
time.sleep(0.5)

# Function to read and announce weight in grams and ounces
def button_readWeight():
    val = hx.get_weight(5)  # Average of 5 readings
    ounces = val * 0.03527396  # Convert to ounces
    print(f"Weight: {val:.2f} grams ({ounces:.2f} oz)")
    text = f"The weight is {val:.1f} grams or {ounces:.1f} ounces"
    command = f'espeak -v en-uk-north -s 130 -p 20 -a 170 "{text}"'
    os.system(command)

# Function to read and announce temperature in Celsius and Fahrenheit
def button_readTemp():
    temp_c, temp_f = read_temp()
    print(' C=%3.3f  F=%3.3f' % (temp_c, temp_f))
    text = f"The temperature is {temp_c:.1f} degrees Celsius, or {temp_f:.1f} degrees Fahrenheit"
    command = f'espeak -v en-uk-north -s 130 -p 20 -a 170 "{text}"'
    os.system(command)

# Callback for button events (press/release)
def button_callback(channel):
    global current_state, press_time

    if GPIO.input(BUTTON_PIN) == GPIO.LOW:
        # Button pressed: start timing
        press_time = time.time()
    else:
        # Button released: compute duration
        if press_time is not None:
            hold_time = time.time() - press_time
            press_time = None  # Reset press time

            if hold_time >= 4:
                # Toggle device ON/OFF
                current_state = not current_state
                print("ON" if current_state else "OFF")

                # Voice output for ON/OFF state
                if current_state:
                    os.system('espeak -v en-uk-north -s 130 -p 20 -a 170 "System is now on"')
                else:
                    os.system('espeak -v en-uk-north -s 130 -p 20 -a 170 "System is now off"')

            elif 2 <= hold_time < 4:
                # Medium press: zero the weight (if system is ON)
                if current_state:
                    print("Zeroing scale...")
                    hx.tare()
                    os.system('espeak -v en-uk-north -s 130 -p 20 -a 170 "Scale zeroed successfully"')

            elif current_state:
                # Short press: read temperature and weight
                button_readTemp()
                button_readWeight()

# Read raw data from temperature sensor file
def read_temp_raw():
    with open(device_file, 'r') as f:
        return f.readlines()

# Parse temperature data from raw file input
def read_temp():
    lines = read_temp_raw()
    while lines[0].strip()[-3:] != 'YES':
        time.sleep(0.2)
        lines = read_temp_raw()
    equals_pos = lines[1].find('t=')
    if equals_pos != -1:
        temp_string = lines[1][equals_pos+2:]
        temp_c = float(temp_string) / 1000.0
        temp_f = temp_c * 9.0 / 5.0 + 32.0
        return temp_c, temp_f

# Main execution block
if __name__ == '__main__':
    try:
        # Attach event detection to the button
        GPIO.add_event_detect(BUTTON_PIN, GPIO.BOTH, callback=button_callback, bouncetime=50)
        print("Ready.")
        print("➡ Hold button for 4 seconds to toggle ON/OFF")
        print("➡ Hold button for 2 seconds while ON to zero the scale")
        print("➡ Tap the button while ON to read temperature and weight")

        # Run continuously
        while True:
            time.sleep(0.1)

    except KeyboardInterrupt:
        print("\nExiting...")

    finally:
        GPIO.cleanup()  # Clean up GPIO on exit