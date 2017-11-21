rpi = True

try:
    import colorama

    colorama.init()
except ImportError:
    pass
# gpiozero controls the pins.
try:
    from gpiozero import LED
except ImportError:
    rpi = False
import pygame
from time import sleep
