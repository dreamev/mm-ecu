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

class PadState:
    UNKNOWN = "Unknown"
    BOOT_UP = "Boot-up"
    PRE_OPERATIONAL = "Pre-operational"
    OPERATIONAL = "Operational"

class Pad:
    HEARTBEAT_ID = 0x715
    BUTTON_EVENT_ID = 0x195
    
    def __init__(self):
        self.state = PadState.UNKNOWN
        
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
        
    def __str__(self):
        return f"Pad(state={self.state})"
    
# - Send an NMT message to start the panel in pre-operational mode (Identifier 00h, Byte 0 80h).
# - Use SDO messages to configure the panel's heartbeat settings (e.g. set Object 1017h to 1000 milliseconds).
# - Use an SDO message to set the panel's communication baudrate to 500k (e.g. set Object 001A:00h to 500000).
# - Deallocate your existing CAN connection and re-establish the connection at the new baudrate.
# - Send an NMT message to start the panel in operational mode (Identifier 00h, Byte 0 01h).
class Application:
    INITAL_BAUD_RATE = 125_000
    EXPECTED_BAUD_RATE = 500_000
   
    def __init__(self, can = None, listener = None):
        # print(f"inside __init__")
        self.pad = Pad()
        self.parking_brake = ParkingBrake(board.D6, board.D9, board.D13, board.D11)
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
        # print(f"inside process_can_bus")
        self.current_bus_state = self.can.state
        if self.current_bus_state != self.previous_bus_state:
            print("CAN bus state:", self.current_bus_state)
            self.previous_bus_state = self.current_bus_state
            
    def process_can_message(self):
        # print(f"inside process_can_message")
        message = self.listener.receive()
        
        if message is None:
            # print(f"no message, passing")
            pass
        elif message.id == Pad.HEARTBEAT_ID:
            print(f"heartbeat detected")
            self.process_pad_heartbeat(message)
        elif message.id == Pad.BUTTON_EVENT_ID:
            print(f"pad button press detected")
            self.process_pad_button(message)
        else:
            print(f"unknown message: [{message.id}] {message.data}")
      

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
    