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
#  struct - https://docs.python.org/3/library/struct.html
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


class CanMessage:
    def __init__(self, id, data):
        _empty_data = [0x00, 0x00, 0x00, 0x00, 0x00, 0x00, 0x00, 0x00]
        self.id   = id

        if type(data) is list:
            for x in _empty_data:
                data.append(x)
                self.data = data[0:8]
        else:
            self.data = []


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

def log(message):
    print(message)

def send_message(message):
    can.send(message)

while True:
    bus_state = can.state
    if bus_state != old_bus_state:
        print(f"Bus state changed to {bus_state}")
        old_bus_state = bus_state

    if keypad_awake != True:
        wake_keypad = CanMessage(0x00, [0x01, 0x15])
        can.send(canio.Message(id=0x615, data=struct.pack("<b", 00000000)))
    else:
        if demo_mode != True:
            demo_keypad = CanMessage(0x615, [0x2F, 0x00, 0x21, 0x00, 0x01])
            can.send(canio.Message(id=0x615, data=struct.pack("<b", 00000000)))

    message = listener.receive
    if message is None:
        continue

    keypad_awake = True

    time.sleep(1)