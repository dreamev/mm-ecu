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

import struct
import time
import board
import canio
import digitalio

class FeatherSettings:
    CAN_REFRESH_RATE = 0.5


class Logger:
    EMERGENCY = 0
    ALERT = 1
    CRITICAL = 2
    ERROR = 3
    WARNING = 4
    NOTICE = 5
    INFO = 6
    DEBUG = 7
    TRACE = 8

    current_level = DEBUG

    @classmethod
    def log(cls, level, message):
        if level <= cls.current_level:
            print(f"level={level} message=\"{message}\"")

    @classmethod
    def emergency(cls, message):
        cls.log(cls.EMERGENCY, message)

    @classmethod
    def alert(cls, message):
        cls.log(cls.ALERT, message)

    @classmethod
    def critical(cls, message):
        cls.log(cls.CRITICAL, message)

    @classmethod
    def error(cls, message):
        cls.log(cls.ERROR, message)

    @classmethod
    def warning(cls, message):
        cls.log(cls.WARNING, message)

    @classmethod
    def notice(cls, message):
        cls.log(cls.NOTICE, message)

    @classmethod
    def info(cls, message):
        cls.log(cls.INFO, message)

    @classmethod
    def debug(cls, message):
        cls.log(cls.DEBUG, message)
        
    @classmethod
    def trace(cls, message):
        cls.log(cls.TRACE, message)

    
class CanMessage:
    def __init__(self, id, data):
        self.id = id
        # Ensure that data is a list of length 8, padded with 0x00 if necessary
        if isinstance(data, list):
            if len(data) > 8:
                # If data is longer than 8 bytes, truncate the list to 8 bytes
                self.data = bytes(data[:8])
            else:
                # If data is shorter than 8 bytes, pad the list to 8 bytes with 0x00
                self.data = bytes(data + [0x00] * (8 - len(data)))
        else:
            # If data is not a list, create a data payload of 8 bytes of 0x00
            self.data = bytes([0x00] * 8)
            
        Logger.debug(f"CanMessage({self.id}, {self.data})")

    def message(self):
        Logger.trace(f"CanMessage.message")
        return canio.Message(id=self.id, data=self.data)
    

class CanMessageQueue:
    _instance = None
    
    @classmethod
    def get_instance(cls):
        if cls._instance is None:
            cls._instance = cls()
        return cls._instance

    def __init__(self):
        self.queue = []
        
    def push_with_id(self, id, data):
        Logger.trace("CanMessageQueue.push_with_id")
        self.push(CanMessage(id, data).message())
        
    def push(self, message):
        Logger.trace("CanMessageQueue.push")
        self.queue.append(message)
        
    def pop(self):
        Logger.trace("CanMessageQueue.pop")
        if self.queue:
            queue_message = self.queue.pop(0)
            Logger.debug(f"CanMessageQueue.pop {queue_message}")
            
            return queue_message
        return None

    
class PadButton:
    COLORS = {
        "red": (1, 0, 0),
        "blue": (0, 1, 0),
        "green": (0, 1, 0),
        "magenta": (1, 0, 1),
        "cyan": (0, 1, 1),
        "yellow": (1, 1, 0),
        "white": (1, 1, 1),
        "black": (0, 0, 0),
    }

    BUTTONS = {
        "HAZARD": 0,
        "PARK": 1,
        "REVERSE": 2,
        "NEUTRAL": 3,
        "DRIVE": 4,
        "AUTOPILOT_SPEED_UP": 5,
        "EXHAUST_SOUND": 6,
        "F1": 7,
        "F2": 8,
        "REGEN": 9,
        "AUTOPILOT_ON": 10,
        "AUTOPILOT_SPEED_DOWN": 11,
    }
    
    COLOR_CODES = {
        "red" : 100,
        "blue" : 101,
        "green" : 102,
        "magenta" : 103,
        "yellow" : 104,
        "cyan" : 105,
        "white" : 106,
        "black" : 107
    }

    @classmethod
    def get_button_id(cls, button):
        return cls.BUTTONS.get(button)

    @classmethod
    def get_pressed_button_id(cls, button):
        button_id = cls.BUTTONS.get(button)
        return -button_id if button_id is not None else None

    @classmethod
    def get_color_code(cls, color):
        color_code = cls.COLOR_CODES.get(color)
        return -color_code if color_code is not None else None
    
    @classmethod
    def get_button_names(cls):
        return list(cls.BUTTONS.keys())    

    def __init__(self, id):
        self.id = id
        self.red = self.green = self.blue = 0

    def change_color(self, color):
        Logger.trace("PadButton::change_color")
        
        color_values = self.COLORS.get(color)  

        if color_values:
            Logger.info(f"Changing color to {color}")
            self.red, self.green, self.blue = color_values
        else:
            Logger.info("Invalid color")
            
        return self


class ECUState:
    ENABLED = True
    DISABLED = False
    PARK = 0
    REVERSE = 1
    NEUTRAL = 2
    DRIVE = 3 
    HIGH_POWER = 1
    LOW_POWER = 0

    
class ECU:
    def __init__(self):
        self.hazard = ECUState.ENABLED
        self.drive_state = ECUState.PARK
        self.exhaust_sound = ECUState.DISABLED
        self.power_state = ECUState.LOW_POWER
        self.regen_state = ECUState.ENABLED
        self.cruise_state = ECUState.DISABLED
        self.target_cruise_speed = 0
        self.f1 = ECUState.DISABLED
        self.f2 = ECUState.DISABLED

    
    
class ParkingBrake:
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
        
    def init_current_state(self):
        Logger.trace("ParkingBrake.init_current_state")
        
        if self.sensor_engaged_pin.value:
            self.engaged = True
            self.trigger_engage_pin.value = True
            self.trigger_disengage_pin.value = False
        elif self.sensor_disengaged_pin.value:
            self.engaged = False
            self.trigger_engage_pin.value = False
            self.trigger_disengage_pin.value = True
        else:
            Logger.error("shit's weird, bro")      

    def is_engaged(self):
        Logger.trace("ParkingBrake.is_engaged")
        return self.engaged
      
    def engage(self):
        Logger.trace("ParkingBrake.engage")
        
        if not self.engaged:
            self.trigger_disengage_pin.value = False
            self.trigger_engage_pin.value = True
            self.engaged = True
       
    def disengage(self):
        Logger.trace("ParkingBrake.disengage")
        
        if self.engaged:
            self.trigger_engage_pin.value = False
            self.trigger_disengage_pin.value = True
            self.engaged = False
            
    def toggle(self):
        Logger.trace("ParkingBrake.toggle")
        self.engaged = not self.engaged 


class PadState:
    UNKNOWN = "Unknown"
    BOOT_UP = "Boot-up"
    PRE_OPERATIONAL = "Pre-operational"
    OPERATIONAL = "Operational"
 
 
class Pad:
    HEARTBEAT_ID = 0x715
    BUTTON_EVENT_ID = 0x195
    COLOR_REFRESH_ID = 0x215
    
    def __init__(self):
        self.state = PadState.UNKNOWN
        self.buttons = [PadButton(id) for name, id in PadButton.BUTTONS.items()]
        self.can_message_queue = CanMessageQueue.get_instance()
        
    def to_boot_up(self):
        Logger.trace("Pad.to_boot_up")
        
        if self.state == PadState.UNKNOWN:
            self.state = PadState.BOOT_UP
            Logger.info("Pad is now in Boot up.")
        elif self.state == PadState.BOOT_UP:
            pass
        else:
            Logger.info("Transition to Boot-up is not allowed from", self.state)

    def to_operational(self):
        Logger.trace("Pad.to_operational")
        
        if self.state == PadState.BOOT_UP:
            self.state = PadState.OPERATIONAL
            Logger.info("Pad is now Operational.")
        elif self.state == PadState.OPERATIONAL:
            pass
        else:
            Logger.info("Transition to Operational is not allowed from", self.state)

    def reset(self):
        Logger.trace("Pad.reset")
        
        self.state = PadState.UNKNOWN
        Logger.info("Pad has been reset to Unknown state.")
        
    def can_activate_keypad(self):
        Logger.trace("Pad.can_activate_keypad")
        
        id = 0x0
        data = [0x01]
        
        return id, data
        
    def can_refresh_button_colors(self):
        Logger.trace("Pad.can_refresh_button_colors")
        
        id = 0x215
        pad_matrix = self.rgb_matrices()
        payload = self.rgb_matrix_to_hex(pad_matrix)
        
        return id, payload
    
    def update_color(self, index, color):
        Logger.trace("Pad.update_color")
        
        Logger.info(f"updating color for {index} to {color}")
        self.buttons[index].change_color(color)
        id, data = self.can_refresh_button_colors()
        self.can_message_queue.push_with_id(id, data)
        
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

        return [h0, h1, h2, h3, h4]
    
    def decode_button_press(state):
        int_values = [x for x in state]
        b0 = int_values[0]
        b1 = int_values[1]
        bay1 = [int(d) for d in bin((1<<8)+b0)[-8:]]
        bay2 = [int(d) for d in bin((1<<8)+b1)[-4:]]
        button_array = bay2+bay1
        return button_array 
        
    def __str__(self):
        return f"Pad(state={self.state})"


class VehicleController:
    def __init(self, ecu, pad, parking_brake):
        self.ecu = ecu
        self.pad = pad
        self.parking_brake = parking_brake
        self.init_drive_state()

    def init_drive_state(self):
        Logger.trace("VehicleController.init_drive_state")
        
        button_state = {
            "DRIVE": PadButton.get_color_code("blue") if self.parking_brake.is_engaged() else PadButton.get_color_code("black"),
            "REVERSE": PadButton.get_color_code("black"),
            "NEUTRAL": PadButton.get_color_code("black")
        }

        if self.parking_brake.is_engaged():
            Logger.debug("  Parking brake is engaged")
            self.ecu.set_state(ECUState.PARK, ECUState.ENABLED)
            self.parking_brake.engage() 

        for button, color in button_state.items():
            self.pad.update_color(PadButton.get_button_id(button), color)

    def process_button_pressed(self, index):
        Logger.trace("VehicleController.process_button_pressed")
        
        button_id_to_action = {
            PadButton.get_button_id(button): getattr(self, f'process_button_pressed_{button.lower()}')
            for button in PadButton.get_button_names()
        }

        button_id_to_action.get(index, lambda: Logger.info(f"No action defined for button ID: {index}"))() 

    def set_button_color(self, button, color):
        Logger.trace("VehicleController.set_button_color")
        
        self.pad.update_color(PadButton.get_button_id(button), PadButton.get_color_code(color))

    def switch_device_state(self, device, button):
        Logger.trace("VehicleController.switch_device_state")  
        
        state = getattr(self.ecu, device)
        new_state = ECUState.ENALBED if state == ECUState.DISABLED else ECUState.DISABLED
        color = 'yellow' if new_state == ECUState.ENABLED else 'black'
        self.ecu.set_device_state(device, new_state)
        self.set_button_color(button, color)

    def process_button_pressed_hazard(self):
        Logger.trace("VehicleController.process_button_hazard")  
        
        self.switch_device_state('hazard', 'HAZARD')

    def process_button_drive_change(self, new_state, active_button):
        Logger.trace("VehicleController.process_button_drive_change")  
        
        current_state = self.ecu.drive_state
        if current_state == ECUState.PARK:
            self.parking_brake.disengage()

        if current_state != new_state:
            self.ecu.set_drive_state(new_state)

            buttons = ['PARK', 'REVERSE', 'NEUTRAL', 'DRIVE']
            colors = ['black' for _ in buttons]
            colors[buttons.index(active_button)] = 'blue'
            for button, color in zip(buttons, colors):
                self.set_button_color(button, color)

    def process_button_pressed_park(self):
        Logger.trace("VehicleController.process_button_pressed_park")  
        
        self.process_button_drive_change(ECUState.PARK, 'PARK')
        
    def process_button_pressed_reverse(self):
        Logger.trace("VehicleController.process_button_pressed_reverse")  
        
        self.process_button_drive_change(ECUState.REVERSE, 'REVERSE')
        
    def process_button_pressed_neutral(self):
        Logger.trace("VehicleController.process_button_pressed_neutral")  
        
        self.process_button_drive_change(ECUState.NEUTRAL, 'NEUTRAL')
         
    def process_button_pressed_drive(self):
        Logger.trace("VehicleController.process_button_pressed_drive") 
        
        self.process_button_drive_change(ECUState.DRIVE, 'DRIVE')

    def process_button_pressed_exhaust_sound(self):
        Logger.trace("VehicleController.process_button_pressed_exhaust_sound")
        
        self.switch_device_state('exhaust_sound', 'EXHAUST_SOUND')

    def process_button_pressed_f1(self):
        Logger.trace("VehicleController.process_button_pressed_f1")
        
        self.ecu.set_f1(ECUState.ENABLED)
        self.set_button_color('F1', 'cyan')
        self.ecu.set_f2(ECUState.DISABLED)
        self.set_button_color('F2', 'black')

    def process_button_pressed_f2(self):
        Logger.trace("VehicleController.process_button_pressed_f2")
        
        self.ecu.set_f2(ECUState.ENABLED)
        self.set_button_color('F2', 'yellow')
        self.ecu.set_f1(ECUState.DISABLED)
        self.set_button_color('F1', 'black')

    def process_button_pressed_regen(self):
        Logger.trace("VehicleController.process_button_pressed_regen")
        
        self.switch_device_state('regen_state', 'REGEN')

    def process_button_pressed_autopilot_on(self):
        Logger.trace("VehicleController.process_button_pressed_autopilot_on")
        
        pass

    def process_button_pressed_autopilot_speed_up(self):
        Logger.trace("VehicleController.process_button_pressed_autopilot_speed_up")
        
        pass

    def process_button_pressed_autopilot_speed_down(self):
        Logger.trace("VehicleController.process_button_pressed_autopilot_speed_down")
        
        pass
       
           
class Application:
    EXPECTED_BAUD_RATE = 500_000
   
    def __init__(self, can = None, listener = None):
        self.pad = Pad()
        self.ecu = ECU()
        self.parking_brake = ParkingBrake(board.D6, board.D9, board.D13, board.D11)
        self.controller = VehicleController(self.ecu, self.pad, self.parking_brake)
        self.baud_rate = Application.EXPECTED_BAUD_RATE
        self.setup_can_connection(self.baud_rate)
        self.current_bus_state = None
        self.previous_bus_state = None
        self.can_message_queue = CanMessageQueue.get_instance()
        
    def setup_can_connection(self, baudrate):
        Logger.trace("Applcation.setup_can_connection")
        
        self.can = canio.CAN(rx=board.CAN_RX, tx=board.CAN_TX, baudrate=baudrate, auto_restart=True)
        self.listener = self.can.listen(matches=[canio.Match(Pad.HEARTBEAT_ID), canio.Match(Pad.BUTTON_EVENT_ID)], timeout=.1)
        
    def ensure_pad_operational(self):
        Logger.trace("Applcation.ensure_pad_operational")
        
        if self.pad.state == PadState.BOOT_UP or self.pad.state == PadState.UNKNOWN:
            self.send_pad_activate()
        elif self.pad.state == PadState.OPERATIONAL:
            pass
        else:
            Logger.info(f"unknown state: [{self.pad.state}]")
            
    def send_pad_activate(self): 
        Logger.trace("Applcation.send_pad_activate")
        
        id, data = self.pad.can_activate_keypad()
        self.can_message_queue.push_with_id(id, data)
        
    def process_can_bus(self):
        Logger.trace("Applcation.process_can_bus")
        
        self.current_bus_state = self.can.state
        
        if self.current_bus_state != self.previous_bus_state:
            Logger.info(f"CAN bus state: {self.current_bus_state}")
            self.previous_bus_state = self.current_bus_state

    def process_can_message(self):
        Logger.trace("Applcation.process_can_message")
        
        message = self.listener.receive()    
        
        if message is not None:                         
            self._process_message_based_on_id(message) 
            
    def process_can_message_queue(self):
        Logger.trace("Applcation.process_can_message_queue")
        
        message = self.can_message_queue.pop()
        if message:
            self.can.send(message)

    def _process_message_based_on_id(self, message):
        Logger.trace("Applcation._process_message_based_on_id")
        
        process_methods = {
            Pad.HEARTBEAT_ID: self._process_pad_heartbeat,
            Pad.BUTTON_EVENT_ID: self._process_pad_button,
        }
        method = process_methods.get(message.id, self._unknown_message)
        method(message)

    def _unknown_message(self, message):
        Logger.trace("Applcation._unknown_message")
        
        Logger.info(f"unknown message: [{message.id}] {message.data}")
        
    def _process_pad_heartbeat(self, message):
        Logger.trace("Applcation._process_pad_heartbeat") 
        
        if self.pad.can_is_heartbeat_boot_up(message.data):
            self.pad.to_boot_up()
        elif self.pad.can_is_heartbeat_pre_operational(message.data):
            self.pad.to_pre_operational()
        elif self.pad.can_is_heartbeat_operational(message.data):
            self.pad.to_operational()
        else:
            Logger.info(f"unknown heartbeat: [{message.id}] {message.data}")

    def _process_pad_button(self, message):
        Logger.trace("Applcation._process_pad_button")
        
        button_names = PadButton.get_button_names()
        pressed_buttons = Pad.decode_button_press(message.data)
        
        for btn_name in button_names:
            if pressed_buttons[Pad.get_pressed_button_id(btn_name)]:
                Logger.info(f'PRESSED_{btn_name}')
      

####################
### Main Program ###
####################
Logger.current_level = Logger.TRACE
Logger.info("INIT: Starting Feather M4")

# If the CAN transceiver has a standby pin, bring it out of standby mode
if hasattr(board, 'CAN_STANDBY'):
    Logger.info("INIT: Setting CAN_STANDBY")
    standby = digitalio.DigitalInOut(board.CAN_STANDBY)
    standby.switch_to_output(False)

# If the CAN transceiver is powered by a boost converter, turn on its supply
if hasattr(board, 'BOOST_ENABLE'):
    Logger.info("INIT: Setting BOOST_ENABLE")
    boost_enable = digitalio.DigitalInOut(board.BOOST_ENABLE)
    boost_enable.switch_to_output(True)

Logger.info("INIT: Setting up main application")
application = Application()

while True:
    Logger.trace(f"MAIN: tick | refresh: {FeatherSettings.CAN_REFRESH_RATE}")
    
    application.process_can_bus()
    application.process_can_message()
    application.ensure_pad_operational()
    application.process_can_message_queue()
   
    Logger.trace(f"MAIN: END tick -------------------------")
    time.sleep(FeatherSettings.CAN_REFRESH_RATE)