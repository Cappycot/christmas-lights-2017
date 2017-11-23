from configparser import ConfigParser
from pygame import mixer
from time import sleep

pins = (19, 13, 6, 5, 11, 9, 10, 22, 2, 3, 4, 17, 27)

try:
    import colorama

    colorama.init()
except ImportError:
    colorama = None
    print("Get colorama if you're on Windows pls.")
# gpiozero controls the pins.
try:
    from gpiozero import LEDBoard

    pins = LEDBoard(*pins)
except ImportError:
    LEDBoard = None  # Get rid of PyCharm warning.
    pins = None

songs = {}
