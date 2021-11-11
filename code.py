
import struct
import time

import board
import canio
import digitalio


# HEYOO!  Links
# 
# Adafruit Feather
# https://www.adafruit.com/product/4759
# 
# Circut py
# https://circuitpython.readthedocs.io/projects/bundle/en/latest/drivers.html
# 
# Blink Marine 12 Button Keypad 
#   datasheet
#   https://ss-usa.s3.amazonaws.com/c/308474458/media/1417060ec085e997cc28740285766947/PKP-2600-SI%20Datasheet.pdf
#   Can Manual
#   https://ss-usa.s3.amazonaws.com/c/308474458/media/30755e6bc22cc0b7e94093360556784/PKP-2600-SI_CANOpen_UM_REV1.1.pdf

# HEYOO!  Commands!
#
# connect to serial: screen /dev/ttys000 115200
# ref: https://learn.adafruit.com/adafruit-feather-m4-express-atsamd51/advanced-serial-console-on-mac-and-linux

DISABLED = False
ENABLED = True
DEBUG = True

LOW_POWER = 0
HIGH_POWER = 1

LOWER_BIT = 0
HIGHER_BIT = 1

INCREASE_SPEED = 1
DECREASE_SPEED = -1

PARK = 0
REVERSE = 1
NEUTRAL = 2
DRIVE = 3

BUTTON_OFF = False
BUTTON_ON = True

COLOR_RED = 100
COLOR_BLUE = 101
COLOR_GREEN = 102
COLOR_MAGENTA = 103
COLOR_YELLOW = 104
COLOR_CYAN = 105
COLOR_WHITE = 106
COLOR_BLACK = 107

WARNING = False

class Logger:
    def __init__(self, level):
        self.log_level = level

    def log(self, n):
        if self.log_level == "debug":
            print(n)


class CanMessage:
    def __init__(self, id, data):
        _empty_data = [0x00, 0x00, 0x00, 0x00, 0x00, 0x00, 0x00, 0x00]
        self.id   = id

        if type(data) is list:
            for x in _empty_data:
                data.append(x)
                self.data = bytes(data[0:8])
        else:
            self.data = []

    def message(self):
        return canio.Message(id=self.id, data=self.data)

class PadButton:
    def __init__(self, id):
        self.id = id
        self.red = 0
        self.green = 0
        self.blue = 0

    def change_color(self, color):
        if color == COLOR_RED:
            print("changing color to red")
            self.red = 1
            self.green = 0
            self.blue = 0
        elif color == COLOR_BLUE:
            print("changing color to blue")
            self.red = 0
            self.green = 0
            self.blue = 1
        elif color == COLOR_GREEN:
            print("changing color to green")
            self.red = 0
            self.green = 1
            self.blue = 0
        elif color == COLOR_MAGENTA:
            print("changing color to magenta")
            self.red = 1
            self.green = 0
            self.blue = 1
        elif color == COLOR_CYAN:
            print("changing color to cyan")
            self.red = 0
            self.green = 1
            self.blue = 1
        elif color == COLOR_YELLOW:
            print("changing color to yellow")
            self.red = 1
            self.green = 1
            self.blue = 0
        elif color == COLOR_WHITE:
            print("changing color to white")
            self.red = 1
            self.green = 1
            self.blue = 1
        elif color == COLOR_BLACK:
            print("changing color to black")
            self.red = 0
            self.green = 0
            self.blue = 0

        return self


class ControlPadView:
    def __init__(self, can):
        self.can = can
        self.buttons = [
            PadButton(0), 
            PadButton(1), 
            PadButton(2), 
            PadButton(3), 
            PadButton(4), 
            PadButton(5), 
            PadButton(6), 
            PadButton(7), 
            PadButton(8),
            PadButton(9), 
            PadButton(10), 
            PadButton(11), 
            PadButton(12),
        ]

    def update_color(self, id, color):
        self.buttons[id].change_color(color)
        self.refresh_button_colors()

    def refresh_button_colors(self):
        pad_matrix = self.rgb_matrices()
        payload = self.rgb_matrix_to_hex(pad_matrix)
        print(payload)
        # cm = CanMessage(0x215, payload)
        # message = cm.message()
        # self.can.send(message)

    def rgb_matrices(self):
        i = 0
        pad_rgb_matrix = [
            [0] * 12,
            [0] * 12,
            [0] * 12,
        ]

        for button in self.buttons[0:12]:
            pad_rgb_matrix[0][i] = button.red 
            pad_rgb_matrix[1][i] = button.green
            pad_rgb_matrix[2][i] = button.blue
            i = i + 1

        return pad_rgb_matrix

    # TODO: Figure out actual matrix to payload in hex
    def rgb_matrix_to_hex(self, matrix):
        # Flipping ordering of output
        rr = matrix[0][::-1]
        gr = matrix[1][::-1]
        br = matrix[2][::-1]

        # Slice into proper 8-bit sizes
        b0 = rr[4:]
        b1 = gr[8:] + rr[:4]
        b2 = gr[:8]
        b3 = br[4:]
        b4 = [0] * 4 + br[:4]

        # Convert list to binary
        bb0 = bin(int(''.join(map(str, b0)), 2) << 1)
        bb1 = bin(int(''.join(map(str, b1)), 2) << 1)
        bb2 = bin(int(''.join(map(str, b2)), 2) << 1)
        bb3 = bin(int(''.join(map(str, b3)), 2) << 1)
        bb4 = bin(int(''.join(map(str, b4)), 2) << 1)

        # Convert each binary value to hex
        h0 = hex(int(bb0, 2))
        h1 = hex(int(bb1, 2))
        h2 = hex(int(bb2, 2))
        h3 = hex(int(bb3, 2))
        h4 = hex(int(bb4, 2))
        # print("rr: ", rr)
        # print("gr: ", gr)
        # print("br: ", br)
        # print("byte 4: ", b4)
        # print("byte 3: ", b3)
        # print("byte 2: ", b2)
        # print("byte 1: ", b1)
        # print("byte 0: ", b0)
        print(type(h0))
        return [h0, h1, h2, h3, h4]
    

class ECUController:
    def __init__(self, ecu, pad):
        self.ecu = ecu
        self.pad = pad

    def process_hazard_button_press(self):
        if self.ecu.hazard == DISABLED:
            self.ecu.set_hazard_lights(ENABLED)
            self.pad.update_color(0, COLOR_YELLOW)
        else:
            self.ecu.set_hazard_lights(DISABLED)
            turn_off_all_lights()            
            # self.pad.update_color(0, COLOR_BLACK)

    def process_exhaust_sound_button_press(self):
        if self.ecu.exhaust_sound == DISABLED:
            self.ecu.set_exhaust_sound(ENABLED)
        else:
            self.ecu.set_exhaust_sound(DISABLED)

    def process_regen_button_press(self):
        if self.ecu.exhaust_sound == DISABLED:
            self.ecu.set_exhaust_sound(ENABLED)
        else:
            self.ecu.set_exhaust_sound(DISABLED)

    def process_drive_state_press(self, request):
        current_state = self.ecu.drive_state
        future_state = request

        if current_state != future_state:
            self.ecu.set_drive_state(future_state)


class ECU:
    def __init__(self):
        self.hazard = DISABLED
        self.drive_state = PARK
        self.exhaust_sound = DISABLED
        self.power_state = LOW_POWER
        self.regen_state = ENABLED
        self.cruise_state = DISABLED
        self.target_cruise_speed = 0

    def save_state(self):
        True

    def load_state(self, file):
        True

    def set_hazard_lights(self, state):
        self.hazard = state

    def set_exhaust_sound(self, state):
        self.exhaust_sound = state

    def set_drive_state(self, state):
        self.drive_state = state

    def set_power_state(self, state):
        self.power_state = state

    def set_regen_state(self, state):
        self.regen_state = state

    def set_cruise_state(self, state):
        self.cruise_state = state
        if state == ENABLED:
            self.target_cruise_speed = self.get_current_speed()

    def modify_cruise_speed(self, modifier):
        self.target_cruise_speed += modifier

    def get_current_speed(self):
        return 0

def decode_button_press(state):
    int_values = [x for x in state]
    b0 = int_values[0]
    b1 = int_values[1]
    bay1 = [int(d) for d in bin((1<<8)+b0)[-8:]]
    bay2 = [int(d) for d in bin((1<<8)+b1)[-4:]]
    button_array = bay2+bay1
    return button_array

def toggle_warning_light(state):
    if state:
        return turn_off_warning_light()
    else:
        return turn_on_warning_light()

def turn_off_warning_light():
    cm = CanMessage(0x215, [0x00, 0x00, 0x00, 0x00, 0x00, 0x00, 0x00, 0x00])
    message = cm.message()
    can.send(message)
    return False

def turn_on_warning_light():
    cm = CanMessage(0x215, [0x02, 0x20, 0x00, 0x02, 0x00, 0x00, 0x00, 0x00])
    message = cm.message()
    can.send(message)
    return True 

def turn_off_all_lights():
    print("turning off all lights")
    cm = CanMessage(0x215, [0x00, 0x00, 0x00, 0x00, 0x00, 0x00, 0x00, 0x00])
    message = cm.message()
    can.send(message)

# If the CAN transceiver has a standby pin, bring it out of standby mode
if hasattr(board, 'CAN_STANDBY'):
    standby = digitalio.DigitalInOut(board.CAN_STANDBY)
    standby.switch_to_output(False)

# If the CAN transceiver is powered by a boost converter, turn on its supply
if hasattr(board, 'BOOST_ENABLE'):
    boost_enable = digitalio.DigitalInOut(board.BOOST_ENABLE)
    boost_enable.switch_to_output(True)

# Use this line if your board has dedicated CAN pins. (Feather M4 CAN and Feather STM32F405)
can = canio.CAN(rx=board.CAN_RX, tx=board.CAN_TX, baudrate=125_000, auto_restart=True)
# On ESP32S2 most pins can be used for CAN.  Uncomment the following line to use IO5 and IO6
#can = canio.CAN(rx=board.IO6, tx=board.IO5, baudrate=250_000, auto_restart=True)
listener = can.listen(matches=[canio.Match(0x195)], timeout=.1)

keypad_awake = False
demo_mode = False
old_bus_state = None
count = 0
warning = False
ecu = ECU()
pad = ControlPadView(can)
controller = ECUController(ecu, pad)

while True:
    bus_state = can.state
    if bus_state != old_bus_state:
        old_bus_state = bus_state

    if keypad_awake != True:
        print("trying to wake keypad")
        keypad_awake_message = CanMessage(0x0, [0x01])
        message = keypad_awake_message.message()
        can.send(message)
        turn_off_all_lights()

    message = listener.receive()
    if message is None:
        continue

    pressed_buttons = decode_button_press(message.data)
    warning_button = pressed_buttons[-1]
    park_button = pressed_buttons[-2]
    reverse_button = pressed_buttons[-3]
    neutral_button = pressed_buttons[-4]
    drive_button = pressed_buttons[-5]

    if warning_button:
        controller.process_hazard_button_press()

    if park_button:
        print("park button")

    if reverse_button:
        print("reverse button")

    if neutral_button:
        print("neutral button")
    
    if drive_button:
        print("drive button")

    if keypad_awake == False:
        keypad_awake = True

    time.sleep(.1)


