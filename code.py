
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

# Used ECU controller Process button presses
BUTTON_HAZARD = 0
BUTTON_PARK = 1
BUTTON_REVERSE = 2
BUTTON_NEUTRAL = 3
BUTTON_DRIVE = 4
BUTTON_AUTOPILOT_SPEED_UP = 5
BUTTON_EXHAUST_SOUND = 6
BUTTON_F1 = 7
BUTTON_F2 = 8
BUTTON_REGEN = 9
BUTTON_AUTOPILOT_ON = 10
BUTTON_AUTOPILOT_SPEED_DOWN = 11

# Used ECU Controller 
# Pressed Button values need to be refactored
BUTTON_PRESSED_HAZARD = -1
BUTTON_PRESSED_PARK = -2
BUTTON_PRESSED_REVERSE = -3
BUTTON_PRESSED_NEUTRAL = -4
BUTTON_PRESSED_DRIVE = -5
BUTTON_PRESSED_AUTOPILOT_SPEED_UP = -6
BUTTON_PRESSED_EXHAUST_SOUND = -7
BUTTON_PRESSED_F1 = -8
BUTTON_PRESSED_F2 = -9
BUTTON_PRESSED_REGEN = -10
BUTTON_PRESSED_AUTOPILOT_ON = -11
BUTTON_PRESSED_AUTOPILOT_SPEED_DOWN = -12

WARNING = False

class Logger:
    def __init__(self, level):
        self.log_level = level

    def log(self, n):
        if self.log_level == "debug":
            print(n)
     
# Class ParkingBreak manages four distinct pins on the GPIO board
# GPIO 6 - Status (Engaged/Disengaged?)
# GPIO 9 - Status (Engaged/Disengaged?)
# GPIO 11 - Trigger (Engaged/Disengaged?)
# GPIO 13 - Trigger (Engaged/Disengaged?)
class ParkingBreak:
    # On init, ParkingBreak needs to determine the status of the physical parking
    # break by querying the appropriate "Status" pin and setting the state as appropriate.
    # Usage of any other method in this class should block until state has been properly determined
    #
    # Consumers of ParkingBreak should be able to query for status
    def __init__(self, engaged_pin, disengaged_pin, engage_pin, disengage_pin):
        self.sensor_engaged_pin = digitalio.DigitalInOut(engaged_pin)
        self.sensor_engaged_pin.direction = digitalio.Direction.INPUT
        self.sensor_engaged_pin.pull = digitalio.Pull.UP
        self.sensor_disengaged_pin = digitalio.DigitalInOut(disengaged_pin)
        self.sensor_disengaged_pin.direction = digitalio.Direction.INPUT
        self.sensor_disengaged_pin.pull = digitalio.Pull.UP
        
        self.trigger_engage_pin = digitalio.DigitalInOut(engage_pin)
        self.trigger_engage_pin.direction = digitalio.Direction.OUTPUT
        self.trigger_disengage_pin = digitalio.DigitalInOut(disengage_pin)
        self.trigger_disengage_pin.direction = digitalio.Direction.OUTPUT
        self.engaged = False
        self.init_current_state()
        
    def is_engaged(self):
        print("parking break status %s", self.engaged)
        return self.engaged
        
    def engage(self):
        print("ENGAGE PARKING BREAK %s", self.engaged)
        if not self.engaged:
            print("SETTING GPIO ENABLED PIN")
            self.trigger_disengage_pin.value = False
            self.trigger_engage_pin.value = True
            self.engaged = True
       
    def disengage(self):
        print("DISENGAGE PARKING BREAK")
        if self.engaged:
            print("SETTING GPIO DISABLE PIN")
            self.trigger_engage_pin.value = False
            self.trigger_disengage_pin.value = True
            self.engaged = False
            
    def toggle(self):
        self.engaged = not self.engaged
        
    def init_current_state(self):
        if self.sensor_engaged_pin.value:
            print("PARKING BREAK CURRENTLY ENGAGED")
            self.engaged = True
            self.trigger_engage_pin.value = True
            self.trigger_disengage_pin.value = False
        elif self.sensor_disengaged_pin.value:
            print("PARKING BREAK CURRENTLY DISENGAGED")
            self.engaged = False
            self.trigger_engage_pin.value = False
            self.trigger_disengage_pin.value = True
        else:
            # TODO: Figure out proper error handling in circuitpython
            print("shit's weird, bro")


# Class Microcontroller is designed to interface with GPIO pins directly
# on the board. It should be able to read and report an arbitrary pin
# or set it as such
class Microcontroller:
    def __init__(self):
        print("microcontroller")
       
    def read_pin(self, pin):
        print("pin state")
        
    def set_pin(self, pin, value):
        print("set pin state") 
        

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
            PadButton(BUTTON_HAZARD), 
            PadButton(BUTTON_PARK), 
            PadButton(BUTTON_REVERSE),
            PadButton(BUTTON_NEUTRAL), 
            PadButton(BUTTON_DRIVE), 
            PadButton(BUTTON_AUTOPILOT_SPEED_UP), 
            PadButton(BUTTON_EXHAUST_SOUND), 
            PadButton(BUTTON_F1), 
            PadButton(BUTTON_F2),
            PadButton(BUTTON_REGEN), 
            PadButton(BUTTON_AUTOPILOT_ON), 
            PadButton(BUTTON_AUTOPILOT_SPEED_DOWN),
        ]

    def update_color(self, index, color):
        print("updating color for ", index)
        self.buttons[index].change_color(color)
        self.refresh_button_colors()

    def refresh_button_colors(self):
        pad_matrix = self.rgb_matrices()
        payload = self.rgb_matrix_to_hex(pad_matrix)
        print(payload)
        cm = CanMessage(0x215, payload)
        message = cm.message()
        self.can.send(message)

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
        bb0 = bin(int(''.join(map(str, b0)), 2))
        bb1 = bin(int(''.join(map(str, b1)), 2))
        bb2 = bin(int(''.join(map(str, b2)), 2))
        bb3 = bin(int(''.join(map(str, b3)), 2))
        bb4 = bin(int(''.join(map(str, b4)), 2))

        # Convert each binary value to hex
        h0 = int(bb0, 2)
        h1 = int(bb1, 2)
        h2 = int(bb2, 2)
        h3 = int(bb3, 2)
        h4 = int(bb4, 2)
        # print("rr: ", rr)
        # print("gr: ", gr)
        # print("br: ", br)
        # print("binary byte 4: ", bb4)
        # print("binary byte 3: ", bb3)
        # print("binary byte 2: ", bb2)
        # print("binary byte 1: ", bb1)
        # print("binary byte 0: ", bb0)
        # print("byte 4: ", b4)
        # print("byte 3: ", b3)
        # print("byte 2: ", b2)
        # print("byte 1: ", b1)
        # print("byte 0: ", b0)
        # return [h0, h1, h2, h3, h4]
        # return [1, 16, 0, 0, 0]
        return [h0, h1, h2, h3, h4]
    

class ECUController:
    def __init__(self, ecu, pad, parking_break):
        self.ecu = ecu
        self.pad = pad
        self.parking_break = parking_break

    def init_start_state(self):
        self.init_hazard()
        self.init_drive_state()

    def process_button_pressed(self, index, init=False):
        print("in process_button_pressed %i", index)
        if index == BUTTON_HAZARD:
            self.process_button_pressed_hazard()
        if index == BUTTON_PARK:
            self.process_button_pressed_park()
        if index == BUTTON_REVERSE:
            self.process_button_pressed_reverse()
        if index == BUTTON_NEUTRAL:
            self.process_button_pressed_neutral()
        if index == BUTTON_DRIVE:
            self.process_button_pressed_drive()
        if index == BUTTON_AUTOPILOT_SPEED_UP:
            self.process_button_pressed_autopilot_speed_up()
        if index == BUTTON_EXHAUST_SOUND:
            self.process_button_pressed_exhaust_sound()
        if index == BUTTON_F1:
            self.process_button_pressed_f1()
        if index == BUTTON_F2:
            self.process_button_pressed_f2()
        if index == BUTTON_REGEN:
            self.process_button_pressed_regen()
        if index == BUTTON_AUTOPILOT_ON:
            self.process_button_pressed_autopilot_on()
        if index == BUTTON_AUTOPILOT_SPEED_DOWN:
            self.process_button_pressed_autopilot_speed_down()

    def init_hazard(self):
        if self.ecu.hazard == ENABLED:
            self.hazard_on()

    def hazard_on(self):
        self.ecu.set_hazard_lights(ENABLED)
        self.pad.update_color(BUTTON_HAZARD, COLOR_YELLOW)

    def hazard_off(self):
        self.ecu.set_hazard_lights(DISABLED)
        self.pad.update_color(BUTTON_HAZARD, COLOR_BLACK)

    def process_button_pressed_hazard(self):
        print("PROCESSING HAZARD BUTTON PRESS")
        if self.ecu.hazard == DISABLED:
            self.hazard_on()
        else:
            self.hazard_off()

    def init_drive_state(self):
        if self.parking_break.is_engaged():
            self.ecu.set_drive_state(PARK)
            self.pad.update_color(BUTTON_PARK, COLOR_BLUE)
            self.parking_break.engage() ## Why do I need to re-engage something that is already engaged?
            
        self.pad.update_color(BUTTON_REVERSE, COLOR_BLACK)
        self.pad.update_color(BUTTON_NEUTRAL, COLOR_BLACK)
        self.pad.update_color(BUTTON_DRIVE, COLOR_BLACK)

    def process_button_pressed_park(self):
        print("PROCESSING PARK BUTTON PRESS")
        current_state = self.ecu.drive_state
        
        if current_state != PARK:
            self.ecu.set_drive_state(PARK)
            self.parking_break.engage()
           
            # Change Park to BLUE, all other toggles OFF 
            self.pad.update_color(BUTTON_PARK, COLOR_BLUE)
            self.pad.update_color(BUTTON_REVERSE, COLOR_BLACK)
            self.pad.update_color(BUTTON_NEUTRAL, COLOR_BLACK)
            self.pad.update_color(BUTTON_DRIVE, COLOR_BLACK)

    def process_button_pressed_reverse(self):
        print("PROCESSING REVERSE BUTTON PRESS")
        current_state = self.ecu.drive_state
        if current_state == PARK:
            self.parking_break.disengage()
            
        if current_state != REVERSE: 
            self.ecu.set_drive_state(REVERSE)
            self.pad.update_color(BUTTON_PARK, COLOR_BLACK)
            self.pad.update_color(BUTTON_REVERSE, COLOR_RED)
            self.pad.update_color(BUTTON_NEUTRAL, COLOR_BLACK)
            self.pad.update_color(BUTTON_DRIVE, COLOR_BLACK)

    def process_button_pressed_neutral(self):
        print("PROCESSING NEUTRAL BUTTON PRESS")
        current_state = self.ecu.drive_state
        if current_state == PARK:
            self.parking_break.disengage()
        
        if current_state != NEUTRAL: 
            self.ecu.set_drive_state(NEUTRAL)
            self.pad.update_color(BUTTON_PARK, COLOR_BLACK)
            self.pad.update_color(BUTTON_REVERSE, COLOR_BLACK)
            self.pad.update_color(BUTTON_NEUTRAL, COLOR_YELLOW)
            self.pad.update_color(BUTTON_DRIVE, COLOR_BLACK)
        
    def process_button_pressed_drive(self):
        print("PROCESSING DRIVE BUTTON PRESS")
        current_state = self.ecu.drive_state
        if current_state == PARK:
            self.parking_break.disengage()

        if current_state != DRIVE:
            self.ecu.set_drive_state(DRIVE)
            self.pad.update_color(BUTTON_PARK, COLOR_BLACK)
            self.pad.update_color(BUTTON_REVERSE, COLOR_BLACK)
            self.pad.update_color(BUTTON_NEUTRAL, COLOR_BLACK)
            self.pad.update_color(BUTTON_DRIVE, COLOR_GREEN)
        
    def process_button_pressed_autopilot_speed_up(self):
        print("PROCESSING AUTOPILOT_SPEED_UP BUTTON PRESS")
        
    def process_button_pressed_exhaust_sound(self):
        print("PROCESSING EXHAUST_SOUND BUTTON PRESS")
        if self.ecu.exhaust_sound == DISABLED:
            self.ecu.set_exhaust_sound(ENABLED)
            self.pad.update_color(BUTTON_EXHAUST_SOUND, COLOR_YELLOW)
        else:
            self.ecu.set_exhaust_sound(DISABLED)
            self.pad.update_color(BUTTON_EXHAUST_SOUND, COLOR_BLACK)
        
    # Paired with F2 only one or the other active at once
    def process_button_pressed_f1(self):
        print("PROCESSING F1 BUTTON PRESS")
        if self.ecu.f1 == DISABLED:
            self.ecu.set_f1(ENABLED)
            self.pad.update_color(BUTTON_F1, COLOR_CYAN)
            self.ecu.set_f2(DISABLED)
            self.pad.update_color(BUTTON_F2, COLOR_BLACK)
        
    def process_button_pressed_f2(self):
        print("PROCESSING F2 BUTTON PRESS")
        if self.ecu.f2 == DISABLED:
            self.ecu.set_f2(ENABLED)
            self.pad.update_color(BUTTON_F2, COLOR_YELLOW)
            self.ecu.set_f1(DISABLED)
            self.pad.update_color(BUTTON_F1, COLOR_BLACK)
        
    def process_button_pressed_regen(self):
        print("PROCESSING REGEN BUTTON PRESS")

        if self.ecu.regen_state == ENABLED:
            self.ecu.set_regen_state(DISABLED)
            self.pad.update_color(BUTTON_REGEN, COLOR_BLACK)
        else:
            self.ecu.set_regen_state(ENABLED)
            self.pad.update_color(BUTTON_REGEN, COLOR_YELLOW)
        
    def process_button_pressed_autopilot_on(self):
        print("PROCESSING AUTOPILOT_ON BUTTON PRESS")

    def process_button_pressed_autopilot_speed_down(self):
        print("PROCESSING AUTOPILOT_SPEED_DOWN BUTTON PRESS")


class ECU:
    def __init__(self):
        self.hazard = ENABLED
        self.drive_state = PARK
        self.exhaust_sound = DISABLED
        self.power_state = LOW_POWER
        self.regen_state = ENABLED
        self.cruise_state = DISABLED
        self.target_cruise_speed = 0
        self.f1 = DISABLED
        self.f2 = DISABLED

    def save_state(self):
        True

    def load_state(self, file):
        True

    def set_drive_state(self, state):
        if self.drive_state != state:
            self.drive_state = state

    def set_hazard_lights(self, state):
        self.hazard = state

    def set_exhaust_sound(self, state):
        self.exhaust_sound = state

    def set_f1(self, state):
        self.f1 = state

    def set_f2(self, state):
        self.f2 = state

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
parking_break = ParkingBreak(board.D6, board.D9, board.D13, board.D11)
controller = ECUController(ecu, pad, parking_break)

while True:
    bus_state = can.state
    if bus_state != old_bus_state:
        old_bus_state = bus_state

    if keypad_awake != True:
        print("waiting for keypad to wake")
        # time.sleep(3)
        print("init keypad")
        keypad_awake_message = CanMessage(0x0, [0x01])
        message = keypad_awake_message.message()
        can.send(message)
        controller.init_start_state()
    
    if keypad_awake == False:
        keypad_awake = True
    

    message = listener.receive()
    if message is None:
        continue

    pressed_buttons = decode_button_press(message.data)

    if pressed_buttons[BUTTON_PRESSED_HAZARD]:
        print('PRESSED_HAZARD')
        controller.process_button_pressed(BUTTON_HAZARD)
    if pressed_buttons[BUTTON_PRESSED_PARK]:
        print('PRESSED_PARK')
        controller.process_button_pressed(BUTTON_PARK)
    if pressed_buttons[BUTTON_PRESSED_REVERSE]:
        print('PRESSED_REVERSE')
        controller.process_button_pressed(BUTTON_REVERSE)
    if pressed_buttons[BUTTON_PRESSED_NEUTRAL]:
        print('PRESSED_NEUTRAL')
        controller.process_button_pressed(BUTTON_NEUTRAL)
    if pressed_buttons[BUTTON_PRESSED_DRIVE]:
        print('PRESSED_DRIVE')
        controller.process_button_pressed(BUTTON_DRIVE)
    if pressed_buttons[BUTTON_PRESSED_AUTOPILOT_SPEED_UP]:
        print('PRESSED_AUTOPILOT_SPEED_UP')
        controller.process_button_pressed(BUTTON_AUTOPILOT_SPEED_UP)
    if pressed_buttons[BUTTON_PRESSED_EXHAUST_SOUND]:
        print('PRESSED_EXHAUST_SOUND')
        controller.process_button_pressed(BUTTON_EXHAUST_SOUND)
    if pressed_buttons[BUTTON_PRESSED_F1]:
        print('PRESSED_F1')
        controller.process_button_pressed(BUTTON_F1)
    if pressed_buttons[BUTTON_PRESSED_F2]:
        print('PRESSED_F2')
        controller.process_button_pressed(BUTTON_F2)
    if pressed_buttons[BUTTON_PRESSED_REGEN]:
        print('PRESSED_REGEN')
        controller.process_button_pressed(BUTTON_REGEN)
    if pressed_buttons[BUTTON_PRESSED_AUTOPILOT_ON]:
        print('PRESSED_AUTOPILOT_ON')
        controller.process_button_pressed(BUTTON_AUTOPILOT_ON)
    if pressed_buttons[BUTTON_PRESSED_AUTOPILOT_SPEED_DOWN]:
        print('PRESSED_AUTOPILOT_SPEED_DOWN')
        controller.process_button_pressed(BUTTON_AUTOPILOT_SPEED_DOWN)

    time.sleep(.1)
