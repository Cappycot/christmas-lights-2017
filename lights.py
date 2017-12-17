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
1, 2, 3, 4: The vertical lights
5, 6, 7, 8: The horizontal lights, from bottom to top
9, 10, 11, 12: The white surrounding lights
13: The star.
"""

from configparser import ConfigParser
from os import getcwd, listdir
from os.path import exists, isdir
from pygame import mixer
from random import random
from sys import exc_info
from time import sleep, time

# The compile order must have consecutive numbers from 1 to the length of the
# tuple. e.g. (1, 4, 3, 2) is okay; (1, 2, 3, 5) is not.
compile_order = (1, 2, 3, 4, 5, 6, 7, 8, 9, 10, 11, 12, 13)
# There needs to be at least as many pins as there are numbers in the order.
pins = (19, 13, 6, 5, 11, 9, 10, 22, 2, 3, 4, 17, 27)
# File extension for music config files.
extension = "txt"  # Exclude the dot from this string.
time_margin = 0.01
light_probability = 0.5
lag_tolerance = 0.05
catch_up_multiplier = 0.66
# Testing console display variables blah blah
test_light_color = "\033[33m\033[1m0"
test_dim_color = "\033[0m1"
test_endl = "\033[0m"

# Everything past here doesn't need to be touched.
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
mixer.init()

songs = []


class Song:
    def __init__(self, m_name, m_path):
        self.name = m_name  # Name of the song
        self.path = m_path  # Location of song folder
        config = ConfigParser()
        config.read("{}/{}.{}".format(m_path, m_name, extension))
        # Bool, true if compiled
        self.compiled = config["Music"].getboolean("compiled")
        # Name of the compiled lightmap file
        self.lights = config["Music"]["lightmap"]
        # List of the uncompiled lightmap filenames
        self.maps = []
        for a in config["Compile"]:
            self.maps.append(config["Compile"][a])
        # Name of the audio file
        self.music = config["Music"]["music"]
        self.title = config["Music"].get("title", m_name)
        self.volume = config["Music"].getfloat("volume", 1.0)


class Entry:
    def __init__(self, channel, mode, start, duration, name=None):
        self.channel = channel
        self.mode = mode
        self.start = start
        self.duration = duration
        self.name = name


class Event:
    def __init__(self):
        self.name = None
        self.lights = [0] * ord_count
        self.time = 0
        self.align = False


class Section:
    def __init__(self, name):
        self.bpm = 60
        self.name = name
        self.entries = []
        self.repeat = 1
        self.length = 0
        self.times = []


# Binary search with lambdas woo fucking hoo!
def binary_search(array, query, key=lambda a: a):
    if len(array) == 0:
        return None
    elif len(array) == 1:
        return key(array[0]) == query and array[0] or None
    mid = int(len(array) / 2)
    compare_to = key(array[mid])
    if query < compare_to:
        return binary_search(array[:mid], query, key)
    elif query > compare_to:
        return binary_search(array[mid + 1:], query, key)
    else:
        return array[mid]


def compile_song(song: Song):
    try:
        if song.lights in song.maps or song.lights == song.name:
            print("File name conflict between maps and output! Aborted.")
            return False
        sections = []
        events = []
        for filename in song.maps:
            bpm = 60
            data = open("{}/{}".format(song.path, filename), "r")
            section = None
            for line in data:
                line = line.split("#")[0].strip(" \r\n")
                if not line:
                    continue
                # print("\"{}\"".format(line))
                if line.lower().startswith("section:"):
                    line = line.split(":", 1)[1].strip()
                    section = binary_search(sections, line, lambda a: a.name)
                    if section is None:
                        section = Section(line)
                        section.bpm = bpm
                        sections.append(section)
                        sections.sort(key=lambda a: a.name)
                elif section is not None:
                    if line.lower().startswith("bpm:"):
                        bpm = float(line.split(":")[1].strip())
                        section.bpm = bpm
                    elif line.lower().startswith("repeat:"):
                        line = line.split(":", 1)[1].split("b")
                        section.repeat = int(line[0].strip())
                        section.length = float(line[1].strip())
                    elif line.lower().startswith("time:"):
                        section.times.append(
                            float(line.split(":", 1)[1].strip()))
                    elif line.startswith("["):
                        line = line[1:-1].split(",")
                        channel = int(line[0].strip())
                        mode = 3
                        if len(line) == 4:
                            mode = int(line[1].strip())
                        start = float(line[-2].strip())
                        duration = float(line[-1].strip())
                        section.entries.append(
                            Entry(channel, mode, start, duration))
        for section in sections:
            entries = []
            for i in range(section.repeat):
                offset = section.length * i
                for old in section.entries:
                    entries.append(
                        Entry(old.channel, old.mode, old.start + offset,
                              old.duration))
            for time in section.times:
                events.append(Entry(-1, -1, time, -1, section.name))
                for entry in entries:
                    start = time + entry.start * 60 / section.bpm
                    duration = entry.duration * 60 / section.bpm
                    events.append(
                        Entry(entry.channel, entry.mode, start, duration))
                    events.append(
                        Entry(entry.channel, 1, start + duration, 0))
        events.sort(key=lambda a: a.start)
        prev = 0
        cur = 0
        # last = [0] * ord_count
        channels = [0] * ord_count
        # Fucking pass by reference instead of value cloning
        # cutoffs = [[0, 0]] * ord_count
        cutoffs = []
        for i in range(ord_count):
            cutoffs.append([0, 0])
        sections = []
        out = open("{}/{}".format(song.path, song.lights), "w")
        buffer = []
        for event in events:
            # Dump event data if working in a new time frame.
            if abs(event.start - cur) > time_margin:
                for ch in channels:  # for i in range(ord_count):
                    buffer.append(str(ch))
                    # last[i] = ch
                # The beginning of one or more sections entails that we want
                # a time alignment call rather than a simple wait call.
                if len(sections) > 0:
                    out.write("a" + str(cur))
                    for sec in sections:
                        out.write("\ns" + sec)
                else:
                    out.write("w" + str(cur - prev))
                out.write("\n")
                out.write(",".join(buffer))
                out.write("\n")
                prev = cur
                cur = event.start
                channels = [0] * ord_count
                buffer.clear()  # Cappycot you dumbass...
                sections.clear()
            if event.name is not None:
                sections.append(event.name)
            channel = event.channel - 1
            # We completely ignore out of range light channels based on setup.
            if -1 < channel < ord_count and event.mode != 0:
                # Light on overrules everything else.
                cutoff = cur + event.duration
                if event.mode == 3:
                    channels[channel] = 3
                    if cutoff - time_margin > cutoffs[channel][1]:
                        cutoffs[channel][1] = cutoff
                elif cutoffs[channel][1] - time_margin <= cur:
                    if event.mode == 2:
                        channels[channel] = 2
                        if cutoff - time_margin > cutoffs[channel][0]:
                            cutoffs[channel][0] = cutoff
                    elif cutoffs[channel][0] - time_margin <= cur:
                        channels[channel] = 1
        out.write("w" + str(cur - prev))
        out.flush()
        out.close()
        if not song.compiled:
            song.compiled = True
            song_file = "{}/{}.{}".format(song.path, song.name, extension)
            config = ConfigParser()
            config.read(song_file)
            config["Music"]["compiled"] = "true"
            with open(song_file, "w") as song_file:
                config.write(song_file)
        return True
    # TODO: What other errors can happen here?
    except (FileNotFoundError, ValueError):
        e = exc_info()
        print("Something went wrong while compiling!")
        for a in e:
            print(a)
        return False


def play_song(song: Song):
    try:
        if song is None:
            print("Song not found. Use 'list' to list available songs.")
            return False
        elif not song.compiled:
            print("This song hasn't been compiled yet!")
            return False
        data = open("{}/{}".format(song.path, song.lights), "r")
        event = Event()
        events = []
        print("Loading lightmap...")
        for line in data:
            line = line.strip(" \r\n")
            if line == "w0":
                continue
            elif line.startswith("s"):
                if event.name:
                    event.name = "{}\n{}".format(event.name, line[1:])
                else:
                    event.name = line[1:]
                continue
            elif line.startswith("a"):
                event.align = True
                event.time = float(line[1:])
            elif line.startswith("w"):
                event.time = float(line[1:])
            else:
                instr = line.split(",")
                for i in range(ord_count):
                    event.lights[i] = int(instr[i])
                continue
            events.append(event)
            event = Event()
        events.append(event)
        data.close()
        print("Loading music...")
        mixer.music.load("{}/{}".format(song.path, song.music))
        mixer.music.set_volume(0)
        mixer.music.play()
        sleep(0.5)
        print("Playing {}".format(song.title))
        mixer.music.stop()
        sleep(0.5)
        mixer.music.set_volume(song.volume)
        mixer.music.play()
        last_correction = 0
        lag_debt = 0
        buffer = []
        last = [" "] * ord_count
        mixer.music.play()
        elapsed = 0
        for event in events:
            if event.name is not None:
                print(event.name)
            if pins is None:
                for i in range(ord_count):
                    to_append = last[i]
                    if event.lights[i] == 1:
                        to_append = test_dim_color
                    elif event.lights[i] == 3:
                        to_append = test_light_color
                    elif event.lights[i] == 2:
                        if random() < light_probability:
                            to_append = test_dim_color
                        else:
                            to_append = test_light_color
                    last[i] = to_append
                    buffer.append(to_append)
                buffer.append(test_endl)
                print(" ".join(buffer))
                buffer.clear()
            else:
                for i in range(ord_count):
                    if event.lights[i] == 1:
                        pins[i].off()
                    elif event.lights[i] == 3:
                        pins[i].on()
                    elif event.lights[i] == 2:
                        if random() < light_probability:
                            pins[i].off()
                        else:
                            pins[i].on()
            if event.align:
                wait = event.time - elapsed - lag_debt
                lag_debt = 0
                if wait > 0:
                    elapsed += wait
                    sleep(wait)
                mixpos = mixer.music.get_pos() / 1000
                mark = elapsed - mixpos
                cur = time()
                print("Lightmap time: {}; pygame time: {}".format(
                    str(int(elapsed * 1000) / 1000),
                    str(int(mixpos * 1000) / 1000)))
                if mixpos == -1 or not mixer.music.get_busy():
                    print("Music failed to load or ended! Aborting...")
                    return mixpos != -1
                elif mark > 0:
                    print("pygame music may be behind.")
                    if cur - last_correction > 2:
                        mark *= catch_up_multiplier
                        sleep(mark)
                        last_correction = cur
                        print(
                            "Added {} seconds to the clock.".format(str(mark)))
                elif -mark > lag_tolerance and cur - last_correction > 2:
                    last_correction = cur
                    lag_debt = -mark * catch_up_multiplier
                    print(
                        "Shaving {} seconds off next alignment time.".format(
                            lag_debt))
                # elapsed = event.time
            else:
                elapsed += event.time
                wait = event.time
                if lag_debt > event.time / 2:
                    lag_debt -= event.time / 2
                    wait /= 2
                elif lag_debt > 0:
                    wait -= lag_debt
                    lag_debt = 0
                sleep(wait)
        while mixer.music.get_busy():
            sleep(1)
    except KeyboardInterrupt:
        pass
    mixer.music.stop()
    return True


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
        # print(item)
        if not isdir(item_dir):
            continue
        meta_file = "{}/{}.{}".format(item_dir, item, extension)
        if not exists(meta_file):
            continue
        try:
            # print(meta_file)
            # This is much easier than how things were done last year.
            songs.append(Song(item, item_dir))
        except (KeyError, ValueError):
            e = exc_info()
            for a in e:
                print(a)
    songs.sort(key=lambda a: a.name.lower())


scan_songs("Music")
compile_song(songs[1])
play_song(songs[1])
