"""
It's a new year and a new system!
This text-based Christmas light show system is designed for Raspberry Pi units
controlling solid state relays through GPIO pins.

Lights now have four (4) different event types:
0 - The light does not change its current state.
1 - The light turns off.
2 - The light randomly either turns on or off in a 50/50 chance.
3 - The light turns on.

This year's light groupings are:
1, 2, 3, 4:
5, 6, 7, 8:
9, 10, 11, 12: The white surrounding lights
13: The star.
"""

from configparser import ConfigParser
from os import getcwd, listdir
from os.path import exists, isdir
# from pygame import mixer
# from random import random
from sys import exc_info

# from time import sleep

# The compile order must have consecutive numbers from 1 to the length of the
# tuple. e.g. (1, 4, 3, 2) is okay; (1, 2, 3, 5) is not.
compile_order = (1, 2, 3, 4, 5, 6, 7, 8, 9, 10, 11, 12, 13)
# There needs to be at least as many pins as there are numbers in the order.
pins = (19, 13, 6, 5, 11, 9, 10, 22, 2, 3, 4, 17, 27)
# File extension for music config files.
extension = "txt"  # Exclude the dot from this string.

config = ConfigParser()
# Order pins.
ord_count = len(compile_order)
pin_count = len(pins)
lights = [0] * ord_count
if ord_count < pin_count:
    print("Some pins are unassigned orderings and won't be used.")
elif ord_count > pin_count:
    print("There are more orderings than pins. Cannot proceed.")
    exit(1)
# This system lets us keep track of pins in linear time but seems too
# complicated for this tbh.
for i in range(ord_count):
    lights[compile_order[i] - 1] = pins[i]

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

songs = []


class Song:
    def __init__(self, m_compiled, m_name, m_music, m_maps, m_lights, m_title,
                 m_volume):
        self.compiled = m_compiled  # Bool, true if compiled
        self.name = m_name  # Name of the song
        self.lights = m_lights  # Name of the compiled lightmap file
        self.maps = m_maps  # List of the uncompiled lightmap filenames
        self.music = m_music  # Name of the audio file
        self.title = m_title
        # self.title = m_name if m_title is None else m_title  # Custom title
        self.volume = m_volume


class Event:
    def __init__(self):
        self.name = None
        self.lights = [0] * ord_count
        self.time = 0


def compile_song(song: Song):
    try:
        if song.lights in song.maps or song.lights == song.name:
            return False
        return True
    except:
        e = exc_info()
        print("Something went wrong while compiling!")
        for a in e:
            print(a)
        return False


def play_song(song: Song):
    pass


def scan_songs(folder=None):
    # Select directory to scan songs with or use current working directory.
    if folder is None:
        cur_dir = getcwd()
    else:
        cur_dir = "{}/{}".format(getcwd(), folder)
    if not isdir(cur_dir):
        return -1
    for item in listdir(cur_dir):
        item_dir = "{}/{}".format(cur_dir, item)
        print(item)
        if not isdir(item_dir):
            continue
        meta_file = "{}/{}.{}".format(item_dir, item, extension)
        if not exists(meta_file):
            continue
        try:
            print(meta_file)
            config.read(meta_file)
            maps = []
            for a in config["Compile"]:
                maps.append(config["Compile"][a])
            # This is much easier than how things were done last year.
            song = Song(config["Music"].getboolean("compiled"), item,
                        config["Music"]["music"], maps,
                        config["Music"]["lightmap"],
                        config["Music"].get("title", item),
                        config["Music"].getfloat("volume", 1.0))
            songs.append(song)
        except (KeyError, ValueError):
            e = exc_info()
            for a in e:
                print(a)
    songs.sort(key=lambda a: a.name.lower())


scan_songs("Music")
