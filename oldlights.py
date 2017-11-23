"""Adapted 2016 light program for temporary use."""

###############################################################################
# Main Variables
###############################################################################

bluetooth = False
bluetooth_delay = 0.22
catch_up_multiplier = 0.66
lag_tolerance = 0.05
time_margin = 0.01
volume = 1
test_light_color = "\033[33m\033[1m0"
test_dim_color = "\033[0m1"
test_endl = "\033[0m"
test_space = " "
test_song = "test"

###############################################################################
# Init Code
###############################################################################

print("Initializing packages...")
try:
    import colorama

    colorama.init()
    print("colorama initialized. :>")
except:
    print("Get colorama if you're on Windows pls.")
from os import getcwd, listdir
from os.path import isdir
import pygame

pygame.mixer.pre_init(frequency=44100)
pygame.mixer.init()
print("pygame mixer initialized. :>")
from random import shuffle

ser = None

try:
    from gpiozero import LEDBoard

    ser = LEDBoard(22, 10, 9, 11, 5, 6, 13, 19)
except ImportError:
    print("No serial package found. Test mode will be used.")
from sys import exc_info
import time

songs = []


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


def get_song(songname):
    toreturn = binary_search(songs, songname, key=lambda a: a.name.lower())
    if toreturn is None:
        for song in songs:
            if song.name.lower().startswith(songname):
                return song
    return toreturn


###############################################################################
# Compiler Code
###############################################################################

def trim(string):
    while string[-1:] == "\r" or string[-1:] == "\n":
        string = string[:-1].strip()
    return string


class Event:
    Print = 0
    Light = 1
    Dark = 2

    def __init__(self, time, typedef, obj):
        self.entry = obj
        self.section = obj
        self.type = typedef
        self.time = time


class Entry:
    def __init__(self, channel, start, duration):
        self.channel = channel
        self.start = start
        self.duration = duration


class Section:
    def __init__(self, name):
        self.bpm = 60
        self.name = name
        self.entries = []
        self.repeat = 1
        self.length = 0
        self.times = []


def compile(song, chain=False):
    toreturn = ""
    try:
        if song.lights in song.maps or song.lights == song.name:
            return "File name conflict between maps and output! Aborted."
        sections = []
        events = []
        main = getcwd() + "/" + song.name + "/"
        for filename in song.maps:
            bpm = 60
            data = open(main + filename, "r")
            section = None
            for line in data:
                line = trim(line)
                if not line or line.startswith("#"):
                    continue
                line = line.split("#")[0].strip()
                if line.lower().startswith("section:"):
                    line = line.split(":", 1)[1].strip()
                    section = binary_search(sections, line, lambda a: a.name)
                    if section is None:
                        section = Section(line)
                        section.bpm = bpm
                        # print(line)
                        # toreturn += line + "\n"
                        sections.append(section)
                        sections.sort(key=lambda a: a.name)
                elif not section is None:
                    if line.lower().startswith("time:"):
                        section.times.append(float(line.split(":", 1)[1]))
                    elif line.lower().startswith("repeat:"):
                        line = line.split(":", 1)[1].split("b")
                        section.repeat = int(line[0])
                        section.length = float(line[1])
                    elif line.startswith("["):
                        line = line[1:-1].split(",")
                        section.entries.append(
                            Entry(int(line[0]), float(line[1]),
                                  float(line[2])))
                    elif line.lower().startswith("bpm"):
                        bpm = float(line.split(":")[1])
                        section.bpm = bpm
        for section in sections:
            # print(section.name + ", " + str(section.bpm))
            toreturn += section.name + ", " + str(section.bpm) + "\n"
            entries = []
            for i in range(0, section.repeat):
                offset = section.length * i
                for old in section.entries:
                    entries.append(
                        Entry(old.channel, old.start + offset, old.duration))
            for time in section.times:
                # print(" - " + str(time))
                toreturn += " - " + str(time) + "\n"
                events.append(Event(time, Event.Print, section))
                for entry in entries:
                    start = time + entry.start * 60 / section.bpm
                    events.append(Event(start, Event.Light, entry))
                    events.append(
                        Event(start + entry.duration * 60 / section.bpm,
                              Event.Dark, entry))
        events.sort(key=lambda a: a.time)
        prev = 0
        cur = 0
        last = [0, 0, 0, 0, 0, 0, 0, 0]
        channels = [-1, -1, -1, -1, -1, -1, -1, -1]
        cut_offs = [0, 0, 0, 0, 0, 0, 0, 0]
        sections = []
        out = open(main + song.lights, "w")
        bpm = 60
        for event in events:
            # print(str(event.time) + ": " + str(event.type))
            if abs(event.time - cur) > time_margin:
                lserial = ""
                # lit = 0
                for i in range(0, 8):
                    ch = channels[i]
                    if ch == 1:
                        lserial += "0,"
                        last[i] = ch
                        # lit += 1
                    elif ch == 0:
                        lserial += "1,"
                        last[i] = ch
                    else:
                        if last[i] == 0:
                            lserial += "1,"
                        else:
                            lserial += "0,"
                lserial = lserial[:-1]
                if len(sections) > 0:
                    out.write("a" + str(cur))
                    for sec in sections:
                        out.write("\ns" + sec)
                else:
                    out.write("w" + str(cur - prev))
                out.write("\n" + lserial + "\n")
                prev = cur
                cur = event.time
                channels = [-1, -1, -1, -1, -1, -1, -1, -1]
                sections = []
            if event.type == Event.Print:
                sections.append(event.section.name)
                bpm = event.section.bpm
            elif event.type == Event.Light:
                entry = event.entry
                channels[entry.channel - 1] = 1
                cut_offs[
                    entry.channel - 1] = event.time + entry.duration * 60 / bpm
            elif event.type == Event.Dark:
                channel = event.entry.channel - 1
                cut = cut_offs[channel]
                if (cut <= event.time or abs(event.time - cut) < time_margin):
                    channels[channel] = 0

        out.write("w" + str(cur - prev))
        out.write("\n1,1,1,1,1,1,1,1\n")
        out.flush()
        out.close()
        wascompiled = song.compiled
        if not wascompiled:
            out = open(main + song.name + ".txt", "a")
            out.write("\nCompiled\n")
            out.flush()
            out.close()
        song.compiled = True
        toreturn += "Song successfully " + (
            "re" if wascompiled else "") + "compiled."
    except:
        e = exc_info()
        toreturn += "Something went wrong while compiling!"
        for a in e:
            toreturn += "\n" + str(a)
        if chain:
            raise Exception("Compile failed!")
    return toreturn


###############################################################################
# Playback Code
###############################################################################

def play(song, chain=False):
    global bluetooth
    global bluetooth_delay
    bt_delay = bluetooth_delay
    global ser
    toreturn = "Song finished playing."
    global volume
    try:
        if song is None:
            return "Song not found. Use 'list' to list available songs."
        elif not song.compiled:
            return "This song hasn't been compiled yet! (Run \"compile " + song.name + "\")"
        main = getcwd() + "/" + song.name + "/"
        data = open(main + song.lights, "r")
        steps = []
        print("Loading lightmap...")
        for line in data:
            line = trim(line)
            if line == "w0":
                continue
            else:
                if ser is None:
                    if line.startswith("0") or line.startswith("1"):
                        line = line.replace("0", "l").replace("1",
                                                              "d").replace(",",
                                                                           test_space)
                        line = line.replace("l", test_light_color).replace("d",
                                                                           test_dim_color)
                        line += test_endl
                steps.append(line)
        data.close()
        print("Loading music...")
        pygame.mixer.music.load(main + song.music)
        pygame.mixer.music.set_volume(0)
        pygame.mixer.music.play()
        time.sleep(0.5)
        print("Playing " + song.title)
        pygame.mixer.music.stop()
        time.sleep(0.5)
        pygame.mixer.music.set_volume(volume)
        pygame.mixer.music.play()
        if not ser is None:
            ser.off()
            # ser.write(str.encode("1,1,1,1,1,1,1,1\n"))
        if bluetooth:
            time.sleep(bt_delay)
        else:
            bt_delay = 0
        elapsed = 0
        last_correction = 0
        lag_debt = 0

        for step in steps:
            if step.startswith("w"):
                towait = float(step[1:])
                elapsed += towait
                time.sleep(towait)
                continue
            elif step.startswith("a"):
                align = float(step[1:])
                sleep = align - elapsed - lag_debt
                lag_debt = 0
                if sleep > 0:
                    elapsed += sleep
                    time.sleep(sleep)
                mixpos = pygame.mixer.music.get_pos() / 1000 - bt_delay
                mark = elapsed - mixpos
                cur = time.time()
                print("Lightmap time: " + str(
                    int(elapsed * 1000) / 1000) + "; pygame time: " + str(
                    int(mixpos * 1000) / 1000))
                if mixpos == -1 or not pygame.mixer.music.get_busy():
                    print("Music failed to load or ended! Aborting...")
                    raise Exception("Music failed to load or ended.")
                elif mark > 0:
                    print("pygame music may be behind.")
                    if int((cur - last_correction) * 1000) / 1000 > 2:
                        mark *= catch_up_multiplier
                        time.sleep(mark)
                        last_correction = cur
                        print("Added " + str(mark) + " seconds to the clock.")
                elif -mark > lag_tolerance and int(
                                (cur - last_correction) * 1000) / 1000 > 2:
                    last_currection = cur
                    lag_debt = -mark * catch_up_multiplier
                    print(str(
                        lag_debt) + " seconds will be shaved off the next alignment time.")
                elapsed = align
                continue
            elif step.startswith("s"):
                print(step[1:])
                continue
            elif not ser is None:
                step = step.split(",")
                for i in range(8):
                    if step[i] == "0":
                        ser[i].on()
                    else:
                        ser[i].off()
                        # ser.write(str.encode(step + "\n"))
            print(step)

        if not ser is None:
            ser.off()
            # ser.write(str.encode("1,1,1,1,1,1,1,1\n"))
        while pygame.mixer.music.get_busy():
            continue
    except KeyboardInterrupt:
        toreturn = "Playback aborted."
        if chain:
            pygame.mixer.music.stop()
            raise Exception("Playback aborted.")
    except:
        e = exc_info()
        toreturn = "Something went wrong during playback!"
        for a in e:
            toreturn += "\n" + str(a)
    pygame.mixer.music.stop()
    return toreturn


###############################################################################
# Data Code
###############################################################################

class Song:
    def __init__(self, m_compiled, m_name, m_lights, m_maps, m_music, m_title):
        self.compiled = m_compiled
        self.name = m_name
        self.lights = m_lights
        self.maps = m_maps
        self.music = m_music
        self.title = m_name if m_title is None else m_title


def scan_songs():
    global songs
    for item in listdir(getcwd()):
        if not isdir(item):
            continue
        song = binary_search(songs, item.lower(), lambda a: a.name.lower())
        try:
            # print(getcwd() + "/" + item + "/" + item + ".txt")
            metainfo = open(getcwd() + "/" + item + "/" + item + ".txt", "r")
            compiled = False
            lights = None
            maps = []
            music = None
            title = None
            for data in metainfo:
                data = data.replace("\r", "").replace("\n",
                                                      "")  # wow I'm lazy.
                ldata = data.lower()
                if ldata.startswith("compile") and data[8:]:
                    maps.append(data[8:])
                elif ldata.startswith("lightmap") and data[9:]:
                    lights = data[9:]
                elif ldata.startswith("music") and data[6:]:
                    music = data[6:]
                elif ldata == "compiled":
                    compiled = True
                elif ldata.startswith("title") and data[6:]:
                    title = data[6:]
            metainfo.close()
            if song is None:
                song = Song(compiled, item, lights, maps, music, title)
                songs.append(song)
            else:
                song.compiled = compiled
                song.name = item
                song.lights = lights
                song.maps = maps
                song.music = music
        except:
            continue
    songs.sort(key=lambda a: a.name.lower())
    return "Found " + str(len(songs)) + " song" + (
        "" if len(songs) == 1 else "s") + "."


###############################################################################
# Runner Code
###############################################################################

print("Finishing up...")
print(scan_songs())
print("\033[1m\033[32mLight Player Menu:\033[31m")
while True:
    print(" - bluetooth [time]: sets bluetooth time delay.")
    print(" - compile <song> : compiles/recompiles a song.")
    print(" - play <song> : plays a song by name.")
    print(" - playall : plays all songs in alpha order.")
    print(" - list : lists all the available songs.")
    print(" - rescan : gets all the songs again.")
    print(" - serial <connect/disconnect> : connects/stops serial.")
    print(" - shuffle : plays all songs randomly.")
    print(" - test [song] : compiles and plays a single song.")
    print(" - volume <0.0-1.0> : sets the playback volume.")
    print(" - quit : exits the program.")
    query = input("\033[0m>>> ")
    query = query.lower()
    result = "Command not recognized or usable..."

    if query.startswith("quit"):
        break
    elif query.startswith("bluetooth") and query[10:]:
        try:
            bluetooth_delay = float(query[10:])
            if bluetooth_delay < 0:
                volume = 0
            result = "Bluetooth time delay set to " + str(
                bluetooth_delay) + " seconds."
        except:
            result = "Invalid time parameter."
    elif query.startswith("bluetooth"):
        bluetooth = not bluetooth
        if bluetooth:
            result = "Bluetooth time delay is on at " + str(
                bluetooth_delay) + " seconds."
        else:
            result = "Bluetooth delay is off."
    elif query.startswith("compile") and query[8:]:
        song = get_song(query[8:])
        if song is None:
            result = "Song not found. Use 'list' to list available songs."
            print("\033[2J\033[0;0H" + result)
            print("\033[1m\033[32mLight Player Menu:\033[31m")
            continue
        result = compile(song)
    elif query.startswith("list") or query.startswith("ls"):
        result = "\033[1m\033[32mSongs:\n\033[0m" if len(
            songs) > 0 else "There are no songs.\n"
        for song in songs:
            titlematch = song.name != song.title
            if titlematch:
                result += "\""
            result += song.name + (
                ("\" " + song.title) if titlematch else "") + "\n"
        result = result[:-1]
    elif query.startswith("play"):
        if query == "playall":
            result = "All songs have been played."
            for song in songs:
                if song.name.lower() != test_song.lower():
                    try:
                        play(song, chain=True)
                    except:
                        try:
                            print(
                                "\nSkipping... Tap Ctrl+C again within 1 sec to abort all playback.")
                            time.sleep(1)
                        except:
                            result = "Playback aborted."
                            break
        else:
            query = query.split(" ")
            if len(query) > 1:
                query = query[1].strip()
                result = play(get_song(query))
            else:
                result = "Specify a song to play. Use 'list' to list the songs."
    elif query == "shuffle":
        shuffled = []
        for song in songs:
            if song.name.lower() != test_song.lower():
                shuffled.append(song)
        result = "All songs have been played randomly."
        shuffle(shuffled)

        for song in shuffled:
            if song.name.lower() != test_song.lower():
                try:
                    play(song, chain=True)
                except:
                    try:
                        print(
                            "\nSkipping... Tap Ctrl+C again within 1 sec to abort all playback.")
                        time.sleep(1)
                    except:
                        result = "Playback aborted."
                        break
    elif query.startswith("rescan") or query.startswith("scan"):
        result = scan_songs()
    elif query == "serial connect":
        pass
    elif query == "serial disconnect":
        pass
    elif query.startswith("serial"):
        result = "Serial is " + ("not " if ser is None else "") + "connected."
    elif query.startswith("test"):
        song = None
        if query[5:]:
            song = get_song(query[5:])
        else:
            song = get_song(test_song)
        if song is None:
            result = "Song not found. Use 'list' to list available songs."
            print("\033[2J\033[0;0H" + result)
            print("\033[1m\033[32mLight Player Menu:\033[31m")
            continue
        try:
            print(compile(song, chain=True))
        except:
            result = "Compile failed! (Run \"compile " + song.name + "\" for more info.)"
            print("\033[2J\033[0;0H" + result)
            print("\033[1m\033[32mLight Player Menu:\033[31m")
            continue
        try:
            play(song, chain=True)
            result = "Song tested."
        except:
            result = "Song either aborted or something went wrong..."
    elif query.startswith("volume"):
        try:
            volume = float(query[7:])
            if volume > 1:
                while volume > 100:
                    volume /= 10
                volume /= 100
            elif volume < 0:
                volume = 0
            result = "Volume set to " + str(volume) + "."
        except:
            result = "Invalid volume parameter."

    print("\033[2J\033[0;0H" + result)
    print("\033[1m\033[32mLight Player Menu:\033[31m")
