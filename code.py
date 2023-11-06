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
        _empty_data = [0x00, 0x00, 0x00, 0x00, 0x00, 0x00, 0x00, 0x00]
        self.id = id

        if isinstance(data, list):
            self.data = bytes(data[:8] + _empty_data[8-len(data):])
        else:
            self.data = bytes(_empty_data)

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
        else:
            print("Transition to Boot-up is not allowed from", self.state)

    def to_pre_operational(self):
        if self.state == PadState.BOOT_UP:
            self.state = PadState.PRE_OPERATIONAL
            print("Pad is now Pre-operational.")
        else:
            print("Transition to Pre-operational is not allowed from", self.state)

    def to_operational(self):
        if self.state == PadState.PRE_OPERATIONAL:
            self.state = PadState.OPERATIONAL
            print("Pad is now Operational.")
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
    
    def can_is_heartbeat_boot_up(self, data):
        heartbeat_bootup_data = [0x00]
        return heartbeat_bootup_data == data
    
    def can_is_heartbeat_pre_operational(self, data):
        heartbeat_pre_operational_data = [0x7f]
        return heartbeat_pre_operational_data == data
    
    def can_is_heartbeat_operational(self, data):
        heartbeat_operational_data = [0x05]
        return heartbeat_operational_data == data
        
    def __str__(self):
        return f"Pad(state={self.state})"
    
#  1. Initialize your CAN bus interface and establish a connection with the panel.
#  2. Send an NMT message to start the panel in pre-operational mode (Identifier 00h, Byte 0 80h).
#  3. Use SDO messages to configure the panel's heartbeat settings (e.g. set Object 1017h to 1000 milliseconds).
#  4. Use an SDO message to set the panel's communication baudrate to 500k (e.g. set Object 001A:00h to 500000).
#  5. Deallocate your existing CAN connection and re-establish the connection at the new baudrate.
#  6. Send an NMT message to start the panel in operational mode (Identifier 00h, Byte 0 01h).
class Application:
    INITAL_BAUD_RATE = 125_000
    EXPECTED_BAUD_RATE = 500_000
   
    def __init__(self, can = None, listener = None):
        self.pad = Pad()
        self.parking_brake = ParkingBrake(board.D6, board.D9, board.D13, board.D11)
        
        self.baud_rate = Application.INITAL_BAUD_RATE
        self.setup_can_connection(self.baud_rate)
        
    def setup_can_connection(self, baudrate):
        self.can = canio.CAN(rx=board.CAN_RX, tx=board.CAN_TX, baudrate=baudrate, auto_restart=True)
        self.listener = self.can.listen(matches=[Pad.HEARTBEAT_ID, Pad.BUTTON_EVENT_ID], timeout=.1)
        
    def upgrade_can_connection_baud_rate(self):
        self.can.deinit()
        self.listener.deinit()
        self.baud_rate = Application.EXPECTED_BAUD_RATE
        self.setup_can_connection(self.baud_rate)
        
    def ensure_pad_operational(self):
        if self.pad.state == PadState.BOOT_UP:
            self.send_pad_enter_pre_operational_mode()
        elif self.pad.state == PadState.PRE_OPERATIONAL and self.baud_rate == Application.INITAL_BAUD_RATE:
            print(f"pad at incorrect baud rate, attempting upgrade")
            self.send_pad_baud_rate_upgrade_request()
            self.upgrade_can_connection_baud_rate()
        elif self.pad.state == PadState.PRE_OPERATIONAL and self.baud_rate == Application.EXPECTED_BAUD_RATE:
            print(f"pad at correct baud rate, activating keypad")
            self.send_pad_activate()
        elif self.pad.state == PadState.UNKNOWN or self.pad.state == PadState.OPERATIONAL:
            print(f"ignoring current state: [{self.pad.state}]")
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
        message = CanMessage(id, data).message()
        self.can.send(message)
    
    def send_pad_activate(self): 
        id, data = self.pad.can_activate_keypad()
        self.can_send_message(id, data)
        
    def send_pad_enter_pre_operational_mode(self):
        id, data = self.pad.can_enter_pre_operational()
        self.can_send_message(id, data)
        
    def send_pad_activate_bootup_service(self):
        id, data = self.pad.can_activate_bootup_service()
        message = CanMessage(0x615, [0x2F, 0x11, 0x20, 0x00, 0x01, 0x00, 0x00]).message()
        self.can_send_message(id, data)
            
    def send_pad_baud_rate_upgrade_request(self):
        id, data = self.pad.can_baud_rate_upgrade_request() 
        message = CanMessage(id, data).message()
        self.can.send(message)
            
    def process_pad_button(self, message):
        print(f"do a thing")
        
    def process_can_bus(self):
        self.current_bus_state = self.can.state
        if self.current_bus_state != self.previous_bus_state:
            print("CAN bus state:", self.current_bus_state)
            self.previous_bus_state = self.current_bus_state
            
    def process_can_message(self):
        message = self.listener.receive()
        
        if message is None:
            pass
        elif message.id == Pad.HEARTBEAT_ID:
            self.process_pad_heartbeat(message)
        elif message.id == Pad.BUTTON_EVENT_ID:
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
    application.process_can_bus()
    application.process_can_message()
    application.ensure_pad_operational()
   
    # Proceed to the next CAN message every .1 seconds
    time.sleep(.1)
    