#!/usr/bin/python3

'''
Control the Brightness of LED using PWM on Raspberry Pi
http://www.electronicwings.com
'''

import RPi.GPIO as GPIO
from time import sleep

def sonar():
    scale_up = [261.63, 293.66, 329.63, 349.23, 392.00, 440.00, 493.88, 523.25]
    scale_down = scale_up[::-1]
    pin = 12				# PWM pin connected to LED
    GPIO.setwarnings(False)			#disable warnings
    GPIO.setmode(GPIO.BOARD)		#set pin numbering system
    GPIO.setup(pin,GPIO.OUT)
    pi_pwm = GPIO.PWM(pin,1000)		#create PWM instance with frequency
    pi_pwm.start(50)				#start PWM of required Duty Cycle 
    for i in range(len(scale_up)):
        pi_pwm.ChangeFrequency(scale_up[i])
        sleep(.20)
    for i in range(len(scale_down)):
        pi_pwm.ChangeFrequency(scale_down[i])
        sleep(.20)
    pi_pwm.stop()


