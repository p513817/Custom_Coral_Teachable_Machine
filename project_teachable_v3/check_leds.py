#!/usr/bin/env python

import RPi.GPIO as GPIO
import time

# Pin Definitions
output_pins = [17 , 22, 6, 19] # BCM pin

def main():
    # Pin Setup:
    # Board pin-numbering scheme
    GPIO.setmode(GPIO.BCM)
    # set pin as an output pin with optional initial state of HIGH
    for p in output_pins:
        GPIO.setup(p, GPIO.OUT, initial=GPIO.HIGH)

    print("Starting demo now! Press CTRL+C to exit")
    curr_value = GPIO.HIGH
    try:
        while True:
            time.sleep(1)
            # Toggle the output every second
            
            for p in output_pins:
                GPIO.output(p, curr_value)
                print("Outputting {} to pin {}".format(curr_value, p))
            curr_value ^= GPIO.HIGH
    finally:
        GPIO.cleanup()

if __name__ == '__main__':
    main()
