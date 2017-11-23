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


class Song:
    def __init__(self, m_compiled, m_name, m_lights, m_maps, m_music, m_title):
        self.compiled = m_compiled  # Bool, true if compiled
        self.name = m_name  # Name of the song
        self.lights = m_lights  # Name of the compiled lightmap file
        self.maps = m_maps  # List of the uncompiled lightmap filenames
        self.music = m_music  # Name of the audio file
        self.title = m_name if m_title is None else m_title  # Custom title
