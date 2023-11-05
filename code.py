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
    PRE_OPERATIONAL = "Pre-operational"
    OPERATIONAL = "Operational"

class Pad:
    HEARTBEAT_ID = 0x715 
    BUTTON_EVENT_ID = 0x195  
    
    def __init__(self):
        self.state = PadState.UNKNOWN

    def to_pre_operational(self):
        if self.state == PadState.UNKNOWN:
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
        self.baud_rate = Application.INITAL_BAUD_RATE
        self.can = canio.CAN(rx=board.CAN_RX, tx=board.CAN_TX, baudrate=self.baud_rate, auto_restart=True)
        self.listener = self.can.listen(matches=[Pad.HEARTBEAT_ID], timeout=.1)
        self.parking_break = ParkingBreak(board.D6, board.D9, board.D13, board.D11)
        self.pad = Pad()
        
    # def send_baud_rate_upgrade_request(self):
    #     # Request upgrade to 500_000 baud
    #     upgrade_baud_rate_can_message = CanMessage(0x615, [0x2F, 0x10, 0x20, 0x00, 0x02, 0x00, 0x00, 0x00])
    #     upgrade_baud_rate_message = upgrade_baud_rate_can_message.message()
    #     self.can.send(upgrade_baud_rate_message)
    #     
    # def upgrade_baud_rate(self):
    #     self.can.deinit()
    #     self.listener.deinit()
    #     self.baud_rate = Application.EXPECTED_BAUD_RATE
    #     self.can = canio.CAN(rx=board.CAN_RX, tx=board.CAN_TX, baudrate=self.baud_rate, auto_restart=True)
    #     self.listener = self.can.listen(matches=[canio.Matches(pad.HEARTBEAT_ID], timeout=.1)
       
    def process_can_bus(self):
        self.current_bus_state = self.can.state
        if self.current_bus_state != self.previous_bus_state:
            print("CAN bus state:", self.current_bus_state)
            self.previous_bus_state = self.current_bus_state
            
    def process_can_message(self):
        message = self.listener.receive()
        
        if message is None:
            pass
        # if message.id == Application.HEARTBEAT_ID and self.baud_rate == Application.INITAL_BAUD_RATE:
        #     self.send_baud_rate_upgrade_request()
        #     self.upgrade_baud_rate()
        # elif message.id == Application.HEARTBEAT_ID and self.baud_rate == Application.EXPECTED_BAUD_RATE:
        #     print(f"heartbeat")
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
   
    # Proceed to the next CAN message every .1 seconds
    time.sleep(.1)
    