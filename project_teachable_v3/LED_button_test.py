import time
import RPi.GPIO as GPIO

BUTTON_PIN = 5
LED_PIN = 17

def my_callback(channel):
    print('按下按鈕')
    GPIO.output(LED_PIN, GPIO.HIGH)
    time.sleep(0.1)
    GPIO.output(LED_PIN, GPIO.LOW)

GPIO.setmode(GPIO.BCM)
GPIO.setup(BUTTON_PIN, GPIO.IN, pull_up_down=GPIO.PUD_UP)
GPIO.setup(LED_PIN, GPIO.OUT)
GPIO.add_event_detect(BUTTON_PIN, GPIO.FALLING, callback=my_callback, bouncetime=250)

try:
    print('按下 Ctrl-C 可停止程式')
    while True:
        time.sleep(1)
except KeyboardInterrupt:
    print('關閉程式')
finally:
    GPIO.cleanup()
