#!/usr/bin/python3

'''
Control the Brightness of LED using PWM on Raspberry Pi
http://www.electronicwings.com
'''

import platform
current_platform = platform.system()

try:
    if current_platform == 'Linux' and 'arm' in platform.machine():  # Verifica si estamos en una plataforma Linux y si es una Raspberry Pi
        import RPi.GPIO as GPIO
    else:
        raise ImportError("No es una Raspberry Pi o RPi.GPIO no está instalado.")
except ImportError:
    # Maneja el caso en el que RPi.GPIO no está disponible en esta plataforma
    # Puedes imprimir un mensaje de advertencia o tomar otras medidas
    print("No es una Raspberry Pi o RPi.GPIO no está instalado.")
    GPIO = None

from time import sleep

def sonar():
    if GPIO:  # Verifica si GPIO se importó correctamente
        scale_up = [261.63, 293.66, 329.63, 349.23, 392.00, 440.00, 493.88, 523.25]
        scale_down = scale_up[::-1]
        pin = 12  # PWM pin connected to LED
        GPIO.setwarnings(False)  # Desactivar advertencias
        GPIO.setmode(GPIO.BOARD)  # Configurar el sistema de numeración de pines
        GPIO.setup(pin, GPIO.OUT)
        pi_pwm = GPIO.PWM(pin, 1000)  # Crear instancia de PWM con frecuencia
        pi_pwm.start(50)  # Iniciar PWM con el ciclo de trabajo requerido
        for i in range(len(scale_up)):
            pi_pwm.ChangeFrequency(scale_up[i])
            sleep(.20)
        for i in range(len(scale_down)):
            pi_pwm.ChangeFrequency(scale_down[i])
            sleep(.20)
        pi_pwm.stop()
    else:
        print(".....Timbre!.....")

# Llamar a la función sonar
sonar()



