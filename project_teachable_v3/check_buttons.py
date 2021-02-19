#!/usr/bin/env python


import RPi.GPIO as GPIO
import time

# Pin Definitions
input_pins = [16 , 6 , 5 , 24, 27]  # BCM pin

def main():
    prev_values = ["LOW","LOW","LOW","LOW","LOW","LOW"] 

    # Pin Setup:
    GPIO.setmode(GPIO.BCM)  # BCM pin-numbering scheme from Raspberry Pi
    for p in input_pins:
        GPIO.setup(p, GPIO.IN)  # set pin as an input pin
    print("Starting demo now! Press CTRL+C to exit")
    try:
        while True:
            for i in range(len(input_pins)):
                value = GPIO.input(input_pins[i])
                if value != prev_values[i]:
                    if value == GPIO.HIGH:
                        value_str = "HIGH"
                    else:
                        value_str = "LOW"
                    print("Value read from pin {} : {}".format(input_pins[i],value_str))
                    prev_values[i] = value
            time.sleep(0.1)
    finally:
        GPIO.cleanup()

if __name__ == '__main__':
    main()
