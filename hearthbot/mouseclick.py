import sys

import time
from Quartz.CoreGraphics import *

# This is the offset of the hearthstone client to the top left of window
#offset = (0, 46)
# Default location
#offset = (211, 63)
# Testing location with terminal
offset = (3, 45)

def mouseEvent(type, posx, posy):
    posx += offset[0]
    posy += offset[1]
    theEvent = CGEventCreateMouseEvent(None, type, (posx,posy), kCGMouseButtonLeft)
    CGEventPost(kCGHIDEventTap, theEvent)

def mousemove(posx,posy):
    mouseEvent(kCGEventMouseMoved, posx,posy);

def mouseclick(posx,posy):
    mouseEvent(kCGEventMouseMoved, posx,posy); #uncomment this line if you want to force the mouse to MOVE to the click location first (i found it was not necesary).
    time.sleep(0.5)
    mouseEvent(kCGEventLeftMouseDown, posx,posy);
    time.sleep(0.1)
    mouseEvent(kCGEventLeftMouseUp, posx,posy);

def get_game_coords():
    our_event = CGEventCreate(None)
    curr_pos = CGEventGetLocation(our_event)
    mouse_coords = (int(curr_pos.x)-offset[0], int(curr_pos.y)-offset[1])
    print("Current mouse position is: ", mouse_coords)

def get_absolute_coords():
    our_event = CGEventCreate(None)
    curr_pos = CGEventGetLocation(our_event)
    mouse_coords = (int(curr_pos.x), int(curr_pos.y))
    print("Current mouse position is: ", mouse_coords)
    
delay = 1

# while True:
#     our_event = CGEventCreate(None)
#     curr_pos = CGEventGetLocation(our_event)
#     mouse_coords = (int(curr_pos.x)-offset[0], int(curr_pos.y)-offset[1])
#     print "Current mouse position is: ", mouse_coords
#     # (x, y) = tuple(raw_input("Mouse click: ").split())
#     # print "mouse click at ", x, ",", y," in ", delay, "seconds"
#     # time.sleep(delay);
#     # mouseclick(float(x), float(y));
#     # print "done."
#     time.sleep(delay)

