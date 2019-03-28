import hid
from functools import reduce
from time import sleep
import random
import threading
import queue
from applescript import AppleScript, ScriptError
import Quartz

h = hid.device()
h.open(10171, 15306)

def write(r, g, b, s=128):
    buffer = [0,16,0,0,0,0,0,0,128] + [0] * 50 + [255, 255, 255, 255, 6, 147]
    buffer[3] = r
    buffer[4] = g
    buffer[5] = b
    buffer[8] = s
    checksum = reduce((lambda x, y: x + y), buffer[0:63])
    buffer[63] = (checksum >> 8) & 0xffff
    buffer[64] = checksum % 256

    h.write(buffer)

colours = {
    'off': (0, 0, 0),
    'on': (100, 100, 100),
    'red': (100, 0 , 0),
    'busy': (100, 0, 0),
    'danger': (100, 0, 0),
    'free': (0, 100, 0),
    'green': (0, 100, 0),
    'blue': (0, 0, 100),
    'yellow': (100, 100, 0),
    'orange': (100, 50, 0),
    'warning': (100, 100, 0),
    'purple': (80, 0, 100),
    'afk': (80, 0, 100),
    'cyan': (0, 100, 100)
}

colour_queue = queue.Queue()
end = threading.Event()
playing = threading.Event()
sleeping = threading.Event()

def update():
    r, g, b = 0, 0, 0
    m = 0
    x = 20
    up = False
    pulsing = True
    while True:
        try:
            r, g, b = colour_queue.get(timeout=0.05)
            colour_queue.task_done()
        except queue.Empty:
            pass
        if playing.is_set():
            if up:
                x += 1
                up = (x < 28)
            else:
                x -= 1
                up = (x <= 6)
            m = int(pow(x,3)/200)
        else:
            x = 28
            m = 100
        if sleeping.is_set():
            m = 0
        write(min(r, m), min(g, m), min(b, m))
        if end.is_set():
            break

def check_status():
    while True:
        if end.is_set():
            break
        sleep(1)
        s = AppleScript("""tell application "Spotify"
        	return player state
        end tell""")
        try:
            result = s.run()
        except ScriptError:
            continue
        if result.code == b'kPSP':
            playing.set()
        else:
            playing.clear()
        d = Quartz.CGSessionCopyCurrentDictionary()
        if 'CGSSessionScreenIsLocked' in d and d['CGSSessionScreenIsLocked'] == 1:
            sleeping.set()
        else:
            sleeping.clear()


print('Starting busylight')

start_up_sequence = [(100, 0, 0), (100, 100, 0), (0, 100, 0), (0, 100, 100),
                     (0, 0, 100), (100, 0, 100)]

for r, g, b in start_up_sequence:
    write(r, g, b)
    sleep(0.1)

colour_queue.put((100, 100, 100))

update_thread = threading.Thread(target=update)
update_thread.start()

player_thread = threading.Thread(target=check_status)
player_thread.start()

try:
    while True:
        print('Colour > ', end='')
        choice = input()
        choice = choice.lower()
        if choice in colours:
            colour_queue.put(colours[choice])
except KeyboardInterrupt:
    pass
except EOFError:
    pass

colour_queue.put(colours['off'])
end.set()
print('Shutting down busylight')
update_thread.join()
