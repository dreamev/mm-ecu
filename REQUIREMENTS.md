CAN-PAD Buttons

1)  Hazard 
2)  Park
3)  Reverse
4)  Neurtal
5)  Drive
6)  Cruise Speed Up
7)  Exaust sound
8)  Function 1 - Slow mode
9)  Function 2 - Fast mode
10) Regen braking
11) Cruise 
12) Cruise Speed Down


Hazard
======

Hazard should be on or off
When on:
    Blink yellow led 1 sec. Led off 1sec. Repeat 
    No other function. Future work needed for hazard controls
Hazard can be enabled at any point if keypad has power


Park, Reverse, Neutral, Drive
=============================

Buttons should function as radio group. Only one active at a time.
Vehicle must be stopped to change modes.
(may be more logic around this not entirely sure)


Exaust Sound
============

Sound should be on or off
When on:
    Led should be a solid color (white?)
    No other function at this point. Need exhaust speaker component
    

Functions
=========
Buttons should function as radio group. Only one active at a time.
Vehicle must be stopped to change modes.

F1 will change Power to low number.
F1 will change Regen to low number. 

F2 will change Power to high number.
F2 will change Regen to high number. 


Regen
=====
Regen should be on or off
When on:
    Led should be a solid color (white?)
    Regen enable command should be sent
When off: 
    Led should be off
    Regen disable command should be sent


Cruise/Openpilot
================
button 11 - Cruise should be on or off
When on:
    Led should be a (pulsating?) color (blue?)
    Can commands should be sent to enable openpilot
When off:
    Led should be off
    Can commands should be sent to disable openpilot


Buttor 6 - Cruise Speed Up
Should be momentary-ish
    should track amount of time pressing button.
    should make led green for amount of time heald down
    should increase cruise speed an appropiate amount.


Buttor 12 - Cruise Speed Down
Should be momentary-ish
    should track amount of time pressing button.
    should make led orange for amount of time heald down
    should decrease cruise speed an appropiate amount.


