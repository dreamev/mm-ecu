
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
     
class ParkingBreak:
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
        return self.engaged
        
    def engage(self):
        if not self.engaged:
            self.trigger_disengage_pin.value = False
            self.trigger_engage_pin.value = True
            self.engaged = True
       
    def disengage(self):
        if self.engaged:
            self.trigger_engage_pin.value = False
            self.trigger_disengage_pin.value = True
            self.engaged = False
            
    def toggle(self):
        self.engaged = not self.engaged
        
    def init_current_state(self):
        if self.sensor_engaged_pin.value:
            self.engaged = True
            self.trigger_engage_pin.value = True
            self.trigger_disengage_pin.value = False
        elif self.sensor_disengaged_pin.value:
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
        self.id = id

        if isinstance(data, list):
            self.data = bytes(data[:8] + _empty_data[8-len(data):])
        else:
            self.data = bytes(_empty_data)

    def message(self):
        return canio.Message(id=self.id, data=self.data)


class PadButton:
    COLOR_RED = "red"
    COLOR_BLUE = "blue"
    COLOR_GREEN = "green"
    COLOR_MAGENTA = "magenta"
    COLOR_CYAN = "cyan"
    COLOR_YELLOW = "yellow"
    COLOR_WHITE = "white"
    COLOR_BLACK = "black"

    COLORS = {
        COLOR_RED: (1, 0, 0),
        COLOR_BLUE: (0, 0, 1),
        COLOR_GREEN: (0, 1, 0),
        COLOR_MAGENTA: (1, 0, 1),
        COLOR_CYAN: (0, 1, 1),
        COLOR_YELLOW: (1, 1, 0),
        COLOR_WHITE: (1, 1, 1),
        COLOR_BLACK: (0, 0, 0)
    }

    # init takes an id and initializes the state of the button
    def __init__(self, id):
        self.id = id
        self.red = 0
        self.green = 0
        self.blue = 0

    # change_color takes a color and updates the color of the button
    def change_color(self, color):
        if color in self.COLORS:
            self.red, self.green, self.blue = self.COLORS[color]
            print(f"changing color to {color}")
        else:
            print("Invalid color")

        return self



# ControlPadView is designed to interface with the CAN bus and manage the state of the buttons
class ControlPadView:
    # init takes a CAN bus and initializes the state of the buttons
    def __init__(self, can):
        self.can = can
        self.buttons = [PadButton(button) for button in [
            BUTTON_HAZARD,
            BUTTON_PARK,
            BUTTON_REVERSE,
            BUTTON_NEUTRAL,
            BUTTON_DRIVE,
            BUTTON_AUTOPILOT_SPEED_UP,
            BUTTON_EXHAUST_SOUND,
            BUTTON_F1,
            BUTTON_F2,
            BUTTON_REGEN,
            BUTTON_AUTOPILOT_ON,
            BUTTON_AUTOPILOT_SPEED_DOWN
        ]]

    # update_color takes an index and a color and updates the color of the button at that index
    def update_color(self, index, color):
        print(f"updating color for {index}")
        self.buttons[index].change_color(color)
        self.refresh_button_colors()

    # refresh_button_colors takes the current state of the buttons and sends it to the CAN bus
    def refresh_button_colors(self):
        pad_matrix = self.rgb_matrices()
        payload = self.rgb_matrix_to_hex(pad_matrix)
        print(payload)
        cm = CanMessage(0x215, payload)
        message = cm.message()
        self.can.send(message)

    # rgb_matrices returns a 3x12 matrix of RGB values
    def rgb_matrices(self):
        pad_rgb_matrix = [
            [button.red for button in self.buttons[0:12]],
            [button.green for button in self.buttons[0:12]],
            [button.blue for button in self.buttons[0:12]],
        ]

        return pad_rgb_matrix

    # rgb_matrix_to_hex takes a 3x12 matrix of RGB values and converts it to a list of hex values
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
        bb0 = int(''.join(map(str, b0)), 2)
        bb1 = int(''.join(map(str, b1)), 2)
        bb2 = int(''.join(map(str, b2)), 2)
        bb3 = int(''.join(map(str, b3)), 2)
        bb4 = int(''.join(map(str, b4)), 2)

        # Convert each binary value to hex
        h0 = hex(bb0)
        h1 = hex(bb1)
        h2 = hex(bb2)
        h3 = hex(bb3)
        h4 = hex(bb4)

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
        button_mapping = {
            BUTTON_HAZARD: self.process_button_pressed_hazard,
            BUTTON_PARK: self.process_button_pressed_park,
            BUTTON_REVERSE: self.process_button_pressed_reverse,
            BUTTON_NEUTRAL: self.process_button_pressed_neutral,
            BUTTON_DRIVE: self.process_button_pressed_drive,
            BUTTON_AUTOPILOT_SPEED_UP: self.process_button_pressed_autopilot_speed_up,
            BUTTON_EXHAUST_SOUND: self.process_button_pressed_exhaust_sound,
            BUTTON_F1: self.process_button_pressed_f1,
            BUTTON_F2: self.process_button_pressed_f2,
            BUTTON_REGEN: self.process_button_pressed_regen,
            BUTTON_AUTOPILOT_ON: self.process_button_pressed_autopilot_on,
            BUTTON_AUTOPILOT_SPEED_DOWN: self.process_button_pressed_autopilot_speed_down
        }

        print("in process_button_pressed %i", index)
        button_mapping.get(index, lambda: None)()

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
    b0, b1 = state[:2]
    bay1 = [int(d) for d in bin((1 << 8) + b0)[-8:]]
    bay2 = [int(d) for d in bin((1 << 8) + b1)[-4:]]
    button_array = bay2 + bay1
    return button_array

def toggle_warning_light(state):
    if state:
        return turn_off_warning_light()
    else:
        return turn_on_warning_light()
    

def turn_off_warning_light():
    cm = CanMessage(0x215, [0x00, 0x00, 0x00, 0x00, 0x00, 0x00, 0x00, 0x00])
    message = cm.message()
    application.can.send(message)
    return False

def turn_on_warning_light():
    cm = CanMessage(0x215, [0x02, 0x20, 0x00, 0x02, 0x00, 0x00, 0x00, 0x00])
    message = cm.message()
    application.can.send(message)
    return True 

def turn_off_all_lights():
    print("turning off all lights")
    cm = CanMessage(0x215, [0x00, 0x00, 0x00, 0x00, 0x00, 0x00, 0x00, 0x00])
    message = cm.message()
    application.can.send(message)
    
class Application:
    LISTEN_FOR = [canio.Match(0x195), canio.Match(0x595), canio.Match(0x715)] 
    
    def __init__(self, can = None, listener = None):
        self.can = canio.CAN(rx=board.CAN_RX, tx=board.CAN_TX, baudrate=125_000, auto_restart=False)
        self.listener = self.can.listen(matches=Application.LISTEN_FOR, timeout=.1)
        self.ecu = ECU()
        self.pad = ControlPadView(self.can)
        self.parking_break = ParkingBreak(board.D6, board.D9, board.D13, board.D11)
        self.controller = ECUController(self.ecu, self.pad, self.parking_break)
            
    def new_controller(self):
        self.pad = ControlPadView(self.can)
        self.controller = ECUController(self.ecu, self.pad, self.parking_break)
        
    def send_baud_rate_upgrade_request(self):
        # Request upgrade to 500_000 baud
        upgrade_baud_rate_can_message = CanMessage(0x615, [0x2F, 0x10, 0x20, 0x00, 0x02, 0x00, 0x00, 0x00])
        upgrade_baud_rate_message = upgrade_baud_rate_can_message.message()
        self.can.send(upgrade_baud_rate_message)
        
    def upgrade_baud_rate(self):
        self.can.deinit()
        self.listener.deinit()
        self.can = canio.CAN(rx=board.CAN_RX, tx=board.CAN_TX, baudrate=500_000, auto_restart=True)
        self.listener = self.can.listen(matches=Application.LISTEN_FOR, timeout=.1)
        self.new_controller()

    
####### BEGIN MAIN PROGRAM FLOW ########

# If the CAN transceiver has a standby pin, bring it out of standby mode
if hasattr(board, 'CAN_STANDBY'):
    standby = digitalio.DigitalInOut(board.CAN_STANDBY)
    standby.switch_to_output(False)

# If the CAN transceiver is powered by a boost converter, turn on its supply
if hasattr(board, 'BOOST_ENABLE'):
    boost_enable = digitalio.DigitalInOut(board.BOOST_ENABLE)
    boost_enable.switch_to_output(True)

        
application = Application()
keypad_awake = False
demo_mode = False
old_bus_state = None
count = 0
warning = False
failed_attempts = 0
MAX_FAILED_ATTEMPTS = 3  # you can adjust this value

while True:
    bus_state = application.can.state
    if bus_state != old_bus_state:
        old_bus_state = bus_state

    if not keypad_awake:
        print("init keypad")
        keypad_awake_message = CanMessage(0x0, [0x01])
        message = keypad_awake_message.message()
        application.can.send(message)

    message = application.listener.receive()
    if message is None:
        failed_attempts += 1
        if failed_attempts >= MAX_FAILED_ATTEMPTS:
            # Revert back to 125 kbps and attempt to promote again
            application.init_can_and_test(baudrate=125_000)
            application.send_baud_rate_upgrade_request()
            failed_attempts = 0
        continue
    else:
        failed_attempts = 0
    
    # Heartbeat Message 
    if message.id == 0x715:
        keypad_awake = True
        application.controller.init_start_state()
        application.send_upgrade_baud_rate_request()
    elif message.id == 0x595:
        print('upgrade baud rate to 500_000')
        application.upgrade_baud_rate_connection()
    elif message.id == 0x195:
        button_pressed = decode_button_press(message.data)

        button_mapping = {
            BUTTON_PRESSED_HAZARD: 'PRESSED_HAZARD',
            BUTTON_PRESSED_PARK: 'PRESSED_PARK',
            BUTTON_PRESSED_REVERSE: 'PRESSED_REVERSE',
            BUTTON_PRESSED_NEUTRAL: 'PRESSED_NEUTRAL',
            BUTTON_PRESSED_DRIVE: 'PRESSED_DRIVE',
            BUTTON_PRESSED_AUTOPILOT_SPEED_UP: 'PRESSED_AUTOPILOT_SPEED_UP',
            BUTTON_PRESSED_EXHAUST_SOUND: 'PRESSED_EXHAUST_SOUND',
            BUTTON_PRESSED_F1: 'PRESSED_F1',
            BUTTON_PRESSED_F2: 'PRESSED_F2',
            BUTTON_PRESSED_REGEN: 'PRESSED_REGEN',
            BUTTON_PRESSED_AUTOPILOT_ON: 'PRESSED_AUTOPILOT_ON',
            BUTTON_PRESSED_AUTOPILOT_SPEED_DOWN: 'PRESSED_AUTOPILOT_SPEED_DOWN'
        }
        
        for button, button_name in button_mapping.items():
            if button_pressed[button]:
                print(button_name)
                application.controller.process_button_pressed(button)
    else:
        print(f"unknown message: [{message.id}] {message.data}")
        
    time.sleep(.1)