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
            
        # print(f"inside CanMessage {self.id} {self.data}")

    def message(self):
        return canio.Message(id=self.id, data=self.data)
  
    
class PadButton:
    # A dictionary containing colors and their corresponding RGB values
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

    # A dictionary containing button names and their corresponding IDs
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
    
    # A dictionary containing color names and their corresponding codes
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

    # Class method to get the ID of a button
    @classmethod
    def get_button_id(cls, button):
        return cls.BUTTONS.get(button)  # Returns the ID or None if button not found

    # Class method to get ID of a button when pressed
    @classmethod
    def get_pressed_button_id(cls, button):
        button_id = cls.BUTTONS.get(button)  # Fetches the ID if button is in BUTTONS, else None
        return -button_id if button_id is not None else None  # Return negated ID when button is pressed

    # Class method to get color code
    @classmethod
    def get_color_code(cls, color):
        color_code = cls.COLOR_CODES.get(color)  # Fetches the color code if color is in COLORS, else None
        return -color_code if color_code is not None else None  # Return negated color code to signify color change

    # Initializer for PadButton instances
    def __init__(self, id):
        self.id = id  # Assumed to be an integer
        self.red = self.green = self.blue = 0  # Initial color codes

    # Method to change color of a PadButton
    def change_color(self, color):
        # Fetches the corresponding RGB values from COLORS if color is present, else None
        color_values = self.COLORS.get(color)  

        # If RGB values are fetched successfully, update RGB values of PadButton and print confirmation
        if color_values:
            self.red, self.green, self.blue = color_values
            print(f"Changing color to {color}")
        else:
            print("Invalid color")  # If color is not found in COLORS, print error message

        return self # Return instance for possible chaining of methods


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
    """ Electronic Control Unit of a car """

    def __init__(self):
        """ Initialize with default states """
        self.hazard = ECUState.ENABLED
        self.drive_state = ECUState.PARK
        self.exhaust_sound = ECUState.DISABLED
        self.power_state = ECUState.LOW_POWER
        self.regen_state = ECUState.ENABLED
        self.cruise_state = ECUState.DISABLED
        self.target_cruise_speed = 0
        self.f1 = ECUState.DISABLED
        self.f2 = ECUState.DISABLED

    def save_state(self):
        """ Placeholder method to save state """
        pass

    def load_state(self, file):
        """ Placeholder method to load state from file """
        pass

    def set_state(self, attribute, state):
        """ General method to set states """
        setattr(self, attribute, state)
        if attribute == 'cruise_state' and state == ECUState.ENABLED:
            self.target_cruise_speed = self.get_current_speed()

    def modify_cruise_speed(self, modifier):
        """ Method to modify cruise speed """
        self.target_cruise_speed += modifier

    def get_current_speed(self):
        """ Placeholder method to get current speed """
        return 0
    
    
class ParkingBrake:
    '''
    This class represents the Parking brake application where we 
    have sensors for engagement/disengagement and triggers to control 
    these actions.
    '''
    def __init__(self, engaged_pin, disengaged_pin, engage_pin, disengage_pin):
        # For engaged state of brake pin
        self.sensor_engaged_pin = digitalio.DigitalInOut(engaged_pin) # Initialize the sensor pin
        self.sensor_engaged_pin.direction = digitalio.Direction.INPUT # Set the direction to input, it's a sensor
        self.sensor_engaged_pin.pull = digitalio.Pull.UP # Set pull up resistor
        
        # For disengaged state of brake pin 
        self.sensor_disengaged_pin = digitalio.DigitalInOut(disengaged_pin) # Initialize the sensor pin
        self.sensor_disengaged_pin.direction = digitalio.Direction.INPUT # Set the direction to input, it's a sensor
        self.sensor_disengaged_pin.pull = digitalio.Pull.UP # Set pull up resistor

        # For engaging the brake
        self.trigger_engage_pin = digitalio.DigitalInOut(engage_pin) # Initialize the engagement action pin
        self.trigger_engage_pin.direction = digitalio.Direction.OUTPUT # Set the direction to output, it's a trigger
        
        # For disengaging the brake
        self.trigger_disengage_pin = digitalio.DigitalInOut(disengage_pin) # Initialize the disengagement action pin
        self.trigger_disengage_pin.direction = digitalio.Direction.OUTPUT # Set the direction to output, it's a trigger
        
        self.engaged = False # Initial state of brake 
        self.init_current_state() # Initialize the current state by checking the configured pins
        
    def init_current_state(self):
        '''
        This function checks the initial state of brake. If the brake is engaged 
        or disengaged it sets the value of triggers accordingly or else print an 
        error.
        '''
        # Brake is engaged
        if self.sensor_engaged_pin.value:
            self.engaged = True
            self.trigger_engage_pin.value = True
            self.trigger_disengage_pin.value = False
        # Brake is disengaged
        elif self.sensor_disengaged_pin.value:
            self.engaged = False
            self.trigger_engage_pin.value = False
            self.trigger_disengage_pin.value = True
        # Neither engaged or disengaged. This is an error state.
        else:
            print("shit's weird, bro")      

    # Function to check if brake is engaged 
    def is_engaged(self):
        return self.engaged
      
    # Function to engage the brake
    def engage(self):
        # If brake is not engaged, engage it.
        if not self.engaged:
            self.trigger_disengage_pin.value = False
            self.trigger_engage_pin.value = True
            self.engaged = True
       
    # Function to disengage the brake
    def disengage(self):
        # If brake is engaged, disengage it.
        if self.engaged:
            self.trigger_engage_pin.value = False
            self.trigger_disengage_pin.value = True
            self.engaged = False
            
    # Function to toggle between brake's engagement and disengagement            
    def toggle(self):
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
        
    def to_boot_up(self):
        if self.state == PadState.UNKNOWN:
            self.state = PadState.BOOT_UP
            print("Pad is now in Boot up.")
        elif self.state == PadState.BOOT_UP:
            pass
        else:
            print("Transition to Boot-up is not allowed from", self.state)

    def to_operational(self):
        if self.state == PadState.BOOT_UP:
            self.state = PadState.OPERATIONAL
            print("Pad is now Operational.")
        elif self.state == PadState.OPERATIONAL:
            pass
        else:
            print("Transition to Operational is not allowed from", self.state)

    def reset(self):
        self.state = PadState.UNKNOWN
        print("Pad has been reset to Unknown state.")
        
    def can_activate_keypad(self):
        id = 0x0
        data = [0x01]
        
        return id, data
        
    def can_baud_rate_upgrade_request(self):
        id = 0x615
        data = []
        
        return id, data
    
    def can_enter_pre_operational(self):
        id = 0x0
        data = [0x80]
        
        return id, data
    
    def can_activate_bootup_service(self):
        id = 0x615
        data = [0x2F, 0x11, 0x20, 0x00, 0x01, 0x00, 0x00]
        
        return id, data
    
    def can_activate_heartbeat(self):
        id = 0x267 # Decimal 615 is hexadecimal 0x267
        data = [0x40, 0x17, 0x10, 0x00, 0xF4, 0x10, 0x00, 0x00]
        
        return id, data
    
    def can_is_heartbeat_boot_up(self, data):
        heartbeat_bootup_data = bytes([0x00])
        return heartbeat_bootup_data == data
    
    def can_is_heartbeat_pre_operational(self, data):
        heartbeat_pre_operational_data = bytes([0x7f])
        return heartbeat_pre_operational_data == data
    
    def can_is_heartbeat_operational(self, data):
        heartbeat_operational_data = bytes([0x05])
        return heartbeat_operational_data == data
   
    def update_color(self, index, color):
        print(f"updating color for {index}")
        self.buttons[index].change_color(color)
        self.refresh_button_colors()
        
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
        
    def __str__(self):
        return f"Pad(state={self.state})"


class VehicleController:
    def __init__(self, ecu, pad, parking_brake):
        self.ecu = ecu
        self.pad = pad
        self.parking_brake = parking_brake
        self.init_drive_state()

    def init_drive_state(self):
        button_state = {
            "DRIVE": PadButton.get_color_code("blue") if self.parking_brake.is_engaged() else PadButton.get_color_code("black"),
            "REVERSE": PadButton.get_color_code("black"),
            "NEUTRAL": PadButton.get_color_code("black")
        }

        if self.parking_brake.is_engaged():
            # self.ecu.set_state(ECUState.PARK, ECUState.ENABLED)
            self.parking_brake.engage() 

        for button, color in button_state.items():
            self.pad.update_color(PadButton.get_button_id(button), color)

    def process_button_pressed(self, index):
        button_id_to_action = {
            PadButton.get_button_id(button): getattr(self, f'process_button_pressed_{button.lower()}')
            for button in PadButton.buttons()
        }

        button_id_to_action.get(index, lambda: print(f"No action defined for button ID: {index}"))() 

    def set_button_color(self, button, color):
        self.pad.update_color(PadButton.get_button_id(button), PadButton.get_color_code(color))

    def switch_device_state(self, device, button):
        state = getattr(self.ecu, device)
        new_state = ECUState.ENALBED if state == ECUState.DISABLED else ECUState.DISABLED
        color = 'yellow' if new_state == ECUState.ENABLED else 'black'
        self.ecu.set_device_state(device, new_state)
        self.set_button_color(button, color)

    def process_button_pressed_hazard(self):
        self.switch_device_state('hazard', 'HAZARD')

    def process_button_drive_change(self, new_state, active_button):
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
        self.process_button_drive_change(ECUState.PARK, 'PARK')
    def process_button_pressed_reverse(self):
        self.process_button_drive_change(ECUState.REVERSE, 'REVERSE')
    def process_button_pressed_neutral(self):
        self.process_button_drive_change(ECUState.NEUTRAL, 'NEUTRAL')
    def process_button_pressed_drive(self):
        self.process_button_drive_change(ECUState.DRIVE, 'DRIVE')

    def process_button_pressed_exhaust_sound(self):
        self.switch_device_state('exhaust_sound', 'EXHAUST_SOUND')

    def process_button_pressed_f1(self):
        self.ecu.set_f1(ECUState.ENABLED)
        self.set_button_color('F1', 'cyan')
        self.ecu.set_f2(ECUState.DISABLED)
        self.set_button_color('F2', 'black')

    def process_button_pressed_f2(self):
        self.ecu.set_f2(ECUState.ENABLED)
        self.set_button_color('F2', 'yellow')
        self.ecu.set_f1(ECUState.DISABLED)
        self.set_button_color('F1', 'black')

    def process_button_pressed_regen(self):
        self.switch_device_state('regen_state', 'REGEN')

    def process_button_pressed_autopilot_on(self):
        pass

    def process_button_pressed_autopilot_speed_up(self):
        pass

    def process_button_pressed_autopilot_speed_down(self):
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
        
    def setup_can_connection(self, baudrate):
        # print(f"inside setup_can_connection")
        self.can = canio.CAN(rx=board.CAN_RX, tx=board.CAN_TX, baudrate=baudrate, auto_restart=True)
        self.listener = self.can.listen(matches=[canio.Match(Pad.HEARTBEAT_ID), canio.Match(Pad.BUTTON_EVENT_ID)], timeout=.1)
        
    def ensure_pad_operational(self):
        # print(f"inside ensure_pad_operational")
        if self.pad.state == PadState.BOOT_UP or self.pad.state == PadState.UNKNOWN:
            self.send_pad_activate()
        elif self.pad.state == PadState.OPERATIONAL:
            pass
        else:
            print(f"unknown state: [{self.pad.state}]")
            
    def process_pad_heartbeat(self, message):
        if self.pad.can_is_heartbeat_boot_up(message.data):
            self.pad.to_boot_up()
        elif self.pad.can_is_heartbeat_pre_operational(message.data):
            self.pad.to_pre_operational()
        elif self.pad.can_is_heartbeat_operational(message.data):
            self.pad.to_operational()
        else:
            print(f"unknown heartbeat: [{message.id}] {message.data}")
                
    def can_send_message(self, id, data):
        # print(f"inside can_send_message {id} {data}")
        message = CanMessage(id, data).message()
        self.can.send(message)
    
    def send_pad_activate(self): 
        # print(f"inside send_pad_activate")
        id, data = self.pad.can_activate_keypad()
        self.can_send_message(id, data)
        
    def send_pad_activate_heartbeat(self):
        print(f"inside send_pad_activate_heartbeat")
        id, data = self.pad.can_activate_heartbeat()
        self.can_send_message(id, data)
        
    def send_pad_enter_pre_operational_mode(self):
        # print(f"inside send_pad_enter_pre_operational_mode")
        id, data = self.pad.can_enter_pre_operational()
        self.can_send_message(id, data)
        
    def send_pad_activate_bootup_service(self):
        # print(f"inside send_pad_activate_bootup_service")
        id, data = self.pad.can_activate_bootup_service()
        self.can_send_message(id, data)
            
    def send_pad_baud_rate_upgrade_request(self):
        # print(f"inside send_baud_rate_upgrade_request")
        id, data = self.pad.can_baud_rate_upgrade_request() 
        self.can_send_message(id, data)
            
    def process_pad_button(self, message):
        print(f"do a thing")
        
    def process_can_bus(self):
        """
        Method to process the state of the Can bus. This method assigns the current state of the Can bus
        to the variable 'current_bus_state' and checks if the state has changed since the last check.
        If the state has changed, it prints a message showing the new state and updates 'previous_bus_state' to
        reflect the change.
        """
        self.current_bus_state = self.can.state
        
        if self.current_bus_state != self.previous_bus_state:
            print(f"CAN bus state: {self.current_bus_state}")
            self.previous_bus_state = self.current_bus_state

    def process_can_message(self):
        """
        This function receives a CAN (Controller Area Network) message and processes it based on its ID.
        """
        # receive a message from listener element
        message = self.listener.receive()    
        
        # message must not be None in order for it to be processed
        if message is not None:                         
            
            # leverage the private method to process message based on its ID
            self._process_message_based_on_id(message)   

    def _process_message_based_on_id(self, message):
        process_methods = {
            Pad.HEARTBEAT_ID: self._process_pad_heartbeat,
            Pad.BUTTON_EVENT_ID: self._process_pad_button,
        }
        method = process_methods.get(message.id, self._unknown_message)
        method(message)

    def _unknown_message(self, message):
        print(f"unknown message: [{message.id}] {message.data}")
        
    def _process_pad_heartbeat(self, message):
        print("heartbeat detected")

    def _process_pad_button(self, message):
        print("pad button press detected")

      

### Main Program ###

# If the CAN transceiver has a standby pin, bring it out of standby mode
if hasattr(board, 'CAN_STANDBY'):
    standby = digitalio.DigitalInOut(board.CAN_STANDBY)
    standby.switch_to_output(False)

# If the CAN transceiver is powered by a boost converter, turn on its supply
if hasattr(board, 'BOOST_ENABLE'):
    boost_enable = digitalio.DigitalInOut(board.BOOST_ENABLE)
    boost_enable.switch_to_output(True)
    
application = Application()

while True:
    print(f"main tick {application.baud_rate}")
    application.process_can_bus()
    application.process_can_message()
    application.ensure_pad_operational()
   
    # Proceed to the next CAN message every .5 seconds
    time.sleep(.1)
    