"""
CAN Feather Controller for Marine CAN PAD interfaced with Tesla drive controller
"""

import time
import board
import canio
import digitalio


class FeatherSettings:
    """
    Represents the settings for the Feather.

    This class provides configuration options for the Feather, such as the CAN refresh rate.

    Attributes:
        CAN_REFRESH_RATE: The refresh rate for the CAN communication.
    """

    CAN_REFRESH_RATE = 0.5


class Logger:
    """
    Provides logging functionality with different log levels.

    Attributes:
        EMERGENCY: The log level for emergency messages.
        ALERT: The log level for alert messages.
        CRITICAL: The log level for critical messages.
        ERROR: The log level for error messages.
        WARNING: The log level for warning messages.
        NOTICE: The log level for notice messages.
        INFO: The log level for informational messages.
        DEBUG: The log level for debug messages.
        TRACE: The log level for trace messages.

    Methods:
        log(level, message): Logs a message with the specified log level.
        emergency(message): Logs an emergency message.
        alert(message): Logs an alert message.
        critical(message): Logs a critical message.
        error(message): Logs an error message.
        warning(message): Logs a warning message.
        notice(message): Logs a notice message.
        info(message): Logs an informational message.
        debug(message): Logs a debug message.
        trace(message): Logs a trace message.

    Args:
        None

    Returns:
        None

    Raises:
        None
    """

    EMERGENCY = 0
    ALERT = 1
    CRITICAL = 2
    ERROR = 3
    WARNING = 4
    NOTICE = 5
    INFO = 6
    DEBUG = 7
    TRACE = 8

    current_level = INFO

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
    """
    Represents a CAN message.

    Args:
        id: The identifier of the CAN message.
        data: The data payload of the CAN message. Should be a list of length 8 or less.

    Returns:
        None

    Raises:
        None

    Examples:
        # Create a CAN message with id 1 and data [0x01, 0x02, 0x03]
        message = CanMessage(1, [0x01, 0x02, 0x03])
    """


    def __init__(self, message_id, data):
        self.message_id = message_id
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

    def message(self):
        """
        Returns a CAN message with the specified identifier and data payload.

        Args:
            self: The instance of the CanMessage class.

        Returns:
            A canio.Message object representing the CAN message.

        Raises:
            None
        """

        Logger.trace("CanMessage.message")

        return canio.Message(id=self.message_id, data=self.data)


class CanMessageQueue:
    """
    Represents a queue for storing CAN messages.

    Args:
        None

    Returns:
        None

    Raises:
        None
    """

    _instance = None

    @classmethod
    def get_instance(cls):
        """
        Returns the instance of the CanMessageQueue class.

        Args:
            cls: The class object.

        Returns:
            The instance of the CanMessageQueue class.

        Raises:
            None
        """

        if cls._instance is None:
            cls._instance = cls()
        return cls._instance

    def __init__(self):
        self.queue = []

    def push_with_id(self, message_id, data):
        """
        Pushes a CAN message to the queue with the specified message ID and data.

        Args:
            self: The instance of the CanMessageQueue class.
            message_id: The identifier of the CAN message.
            data: The data payload of the CAN message.

        Returns:
            None

        Raises:
            None
        """

        Logger.trace("CanMessageQueue.push_with_id")
        self.push(CanMessage(message_id, data).message())

    def push(self, message):
        """
        Pushes a CAN message to the queue.

        Args:
            self: The instance of the CanMessageQueue class.
            message: The CAN message to be pushed to the queue.

        Returns:
            None

        Raises:
            None
        """

        Logger.trace("CanMessageQueue.push")
        self.queue.append(message)

    def pop(self):
        Logger.trace("CanMessageQueue.pop")
        return self.queue.pop(0) if self.queue else None


class PadButton:
    """
    Represents a pad button with the ability to change its color.

    Attributes:
        COLORS: A dictionary mapping color names to RGB values.
        BUTTONS: A dictionary mapping button names to button IDs.

    Methods:
        __init__(button_id): Initializes the PadButton instance with the specified ID.
        get_button_id(button): Returns the button ID for the specified button name.
        get_pressed_button_id(button): Returns the button ID for the specified button name if it exists, otherwise returns None.
        get_button_names(): Returns a list of button names.
        change_color(color): Changes the color of the PadButton.

    Args:
        button_id: The ID of the PadButton instance.

    Returns:
        None

    Raises:
        None
    """

    COLORS = {
        "red": (1, 0, 0),
        "blue": (0, 0, 1),
        "green": (0, 1, 0),
        "magenta": (1, 0, 1),
        "cyan": (0, 1, 1),
        "yellow": (1, 1, 0),
        "white": (1, 1, 1),
        "black": (0, 0, 0),
    }

    BUTTONS = {
        "HAZARD": 11,
        "PARK": 10,
        "REVERSE": 9,
        "NEUTRAL": 8,
        "DRIVE": 7,
        "AUTOPILOT_SPEED_UP": 6,
        "EXHAUST_SOUND": 5,
        "F1": 4,
        "F2": 3,
        "REGEN": 2,
        "AUTOPILOT_ON": 1,
        "AUTOPILOT_SPEED_DOWN": 0,
    }

    @classmethod
    def get_button_id(cls, button):
        return cls.BUTTONS.get(button)

    @classmethod
    def get_pressed_button_id(cls, button):
        button_id = cls.BUTTONS.get(button)
        return button_id if button_id is not None else None

    @classmethod
    def get_button_names(cls):
        return list(cls.BUTTONS.keys())

    def __init__(self, button_id):

        self.button_id = button_id
        self.red = self.green = self.blue = 0

    def change_color(self, color):
        """
        Changes the color of the PadButton to the specified color.

        Args:
            self: The instance of the PadButton class.
            color: The color to change the PadButton to.

        Returns:
            The updated instance of the PadButton.

        Raises:
            None
        """

        Logger.trace("PadButton.change_color")

        if color_values := self.COLORS.get(color):
            Logger.debug(f"Changing button_id {self.button_id} to color {color} with color_values {color_values}")
            self.red, self.green, self.blue = color_values
        else:
            Logger.info("Invalid color")

        return self


class ECUState:
    """
    Represents the possible states of the ECU.

    Attributes:
        ENABLED: The enabled state of the ECU.
        DISABLED: The disabled state of the ECU.
        PARK: The park state of the ECU.
        REVERSE: The reverse state of the ECU.
        NEUTRAL: The neutral state of the ECU.
        DRIVE: The drive state of the ECU.
        HIGH_POWER: The high power state of the ECU.
        LOW_POWER: The low power state of the ECU.

    Args:
        None

    Returns:
        None

    Raises:
        None
    """

    ENABLED = True
    DISABLED = False
    PARK = 0
    REVERSE = 1
    NEUTRAL = 2
    DRIVE = 3
    HIGH_POWER = 1
    LOW_POWER = 0


class ECU:
    """
    Represents the Electronic Control Unit (ECU) of a vehicle.

    Attributes:
        DRIVE_SHIFT_ID: The identifier for the drive shift command.

    Methods:
        __init__(): Initializes an instance of the ECU class.
        set_hazard_lights(state): Sets the state of the hazard lights.
        set_exhaust_sound(state): Sets the state of the exhaust sound.
        set_f1(state): Sets the state of the F1 button.
        set_f2(state): Sets the state of the F2 button.
        set_drive_state(state): Sets the drive state of the ECU.
        set_power_state(state): Sets the power state of the ECU.
        set_regen_state(state): Sets the regen state of the ECU.
        set_cruise_state(state): Sets the cruise state of the ECU.
        modify_cruise_speed(modifier): Modifies the target cruise speed.
        get_current_speed(): Retrieves the current speed.
        can_drive_state_command(state): Sends a drive state command over CAN bus.

    Args:
        None

    Returns:
        None

    Raises:
        None
    """


    DRIVE_SHIFT_ID = 0x697

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
        self.can_message_queue = CanMessageQueue.get_instance()

    def set_hazard_lights(self, state):
        """
        Sets the state of the hazard lights.

        Args:
            self: The instance of the ECU class.
            state: The state to set for the hazard lights.

        Returns:
            None

        Raises:
            None
        """

        self.hazard = state

    def set_exhaust_sound(self, state):
        """
        Sets the state of the exhaust sound.

        Args:
            self: The instance of the ECU class.
            state: The state to set for the exhaust sound.

        Returns:
            None

        Raises:
            None
        """

        self.exhaust_sound = state

    def set_f1(self, state):
        """
        Sets the state of the F1 button.

        Args:
            self: The instance of the ECU class.
            state: The state to set for the F1 button.

        Returns:
            None

        Raises:
            None
        """

        self.f1 = state

    def set_f2(self, state):
        """
        Sets the state of the F2 button.

        Args:
            self: The instance of the ECU class.
            state: The state to set for the F2 button.

        Returns:
            None

        Raises:
            None
        """

        self.f2 = state

    def set_drive_state(self, state):
        """
        Sets the drive state of the ECU.

        Args:
            self: The instance of the ECU class.
            state: The state to set for the drive state.

        Returns:
            None

        Raises:
            None
        """

        self.drive_state = state

    def set_power_state(self, state):
        """
        Sets the power state of the ECU.

        Args:
            self: The instance of the ECU class.
            state: The state to set for the power state.

        Returns:
            None

        Raises:
            None
        """

        self.power_state = state

    def set_regen_state(self, state):
        """
        Sets the regen state of the ECU.

        Args:
            self: The instance of the ECU class.
            state: The state to set for the regen state.

        Returns:
            None

        Raises:
            None
        """

        self.regen_state = state

    def set_cruise_state(self, state):
        """
        Sets the cruise state of the ECU.

        Args:
            self: The instance of the ECU class.
            state: The state to set for the cruise state.

        Returns:
            None

        Raises:
            None
        """

        self.cruise_state = state
        if state == ECUState.ENABLED:
            self.target_cruise_speed = self.get_current_speed()

    def modify_cruise_speed(self, modifier):
        """
        Modifies the target cruise speed of the ECU.

        Args:
            self: The instance of the ECU class.
            modifier: The value to modify the target cruise speed by.

        Returns:
            None

        Raises:
            None
        """

        self.target_cruise_speed += modifier

    def get_current_speed(self):
        """
        Retrieves the current speed from the ECU.

        Args:
            self: The instance of the ECU class.

        Returns:
            The current speed.

        Raises:
            None
        """

        Logger.trace("ECU.get_current_speed")

        return 0

    def can_drive_state_command(self, state):
        """
        Sends a drive state command over the CAN bus.

        Args:
            self: The instance of the ECU class.
            state: The drive state command to send.

        Returns:
            None

        Raises:
            None
        """

        Logger.trace("ECU.can_drive_state_command")

        can_data = {
            ECUState.DRIVE: [0x0d, 0xbe, 0xef],
            ECUState.NEUTRAL: [0x0e, 0xbe, 0xef],
            ECUState.REVERSE: [0x0f, 0xbe, 0xef],
        }

        data = can_data.get(state)  # Set default value to None
        if data is not None:
            Logger.debug(f"Sending drive state command {state} with data {data}")
            # Send the command 4 times to ensure it is received
            for _ in range(4):
                self.can_message_queue.push_with_id(ECU.DRIVE_SHIFT_ID, data)
        else:
            Logger.info(f"No data for drive state command {state}")


class ParkingBrake:
    """
    Represents a parking brake.

    Methods:
        __init__(engaged_pin, disengaged_pin, engage_pin, disengage_pin): Initializes an instance of the ParkingBrake class.
        init_current_state(): Initializes the current state of the parking brake.
        is_engaged(): Checks if the parking brake is engaged.
        engage(): Engages the parking brake.
        disengage(): Disengages the parking brake.
        toggle(): Toggles the state of the parking brake.

    Args:
        engaged_pin: The pin for the engaged state sensor.
        disengaged_pin: The pin for the disengaged state sensor.
        engage_pin: The pin to engage the parking brake.
        disengage_pin: The pin to disengage the parking brake.

    Returns:
        None

    Raises:
        None
    """


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

        self.engaged = ECUState.DISABLED
        self.init_current_state()

    def init_current_state(self):
        """
        Initializes the current state of the parking brake.

        Args:
            self: The instance of the ParkingBrake class.

        Returns:
            None

        Raises:
            None
        """

        Logger.trace("ParkingBrake.init_current_state")

        if self.sensor_engaged_pin.value:
            Logger.info("ParkingBrake Engaged")

            self.engage()
        elif self.sensor_disengaged_pin.value:
            Logger.info("ParkingBrake Disengaged")

            self.disengage()
        else:
            Logger.error("shit's weird, bro")

    def is_engaged(self):
        """
        Checks if the parking brake is engaged.

        Args:
            self: The instance of the ParkingBrake class.

        Returns:
            The state of the parking brake (engaged or disengaged).

        Raises:
            None
        """

        Logger.trace("ParkingBrake.is_engaged")

        return self.engaged

    def engage(self):
        """
        Engages the parking brake.

        Args:
            self: The instance of the ParkingBrake class.

        Returns:
            None

        Raises:
            None
        """

        Logger.trace("ParkingBrake.engage")

        if not self.engaged:
            self.trigger_disengage_pin.value = ECUState.DISABLED
            self.trigger_engage_pin.value = ECUState.ENABLED
            self.engaged = ECUState.ENABLED

    def disengage(self):
        """
        Disengages the parking brake.

        Args:
            self: The instance of the ParkingBrake class.

        Returns:
            None

        Raises:
            None
        """

        Logger.trace("ParkingBrake.disengage")

        if self.engaged:
            self.trigger_engage_pin.value = ECUState.DISABLED
            self.trigger_disengage_pin.value = ECUState.ENABLED
            self.engaged = ECUState.DISABLED

    def toggle(self):
        """
        Toggles the state of the parking brake.

        Args:
            self: The instance of the ParkingBrake class.

        Returns:
            None

        Raises:
            None
        """

        Logger.trace("ParkingBrake.toggle")

        if self.engaged:
            self.disengage()
        else:
            self.engage()


class PadState:
    """
    Represents the possible states of a pad.

    Attributes:
        UNKNOWN: The unknown state of the pad.
        BOOT_UP: The boot-up state of the pad.
        PRE_OPERATIONAL: The pre-operational state of the pad.
        OPERATIONAL: The operational state of the pad.

    Args:
        None

    Returns:
        None

    Raises:
        None
    """

    UNKNOWN = "Unknown"
    BOOT_UP = "Boot-up"
    PRE_OPERATIONAL = "Pre-operational"
    OPERATIONAL = "Operational"


class Pad:
    """
    Represents a pad.

    This class provides functionality to interact with the pad, such as transitioning its state, updating button colors, and decoding button press states.

    Attributes:
        HEARTBEAT_ID (int): The ID of the heartbeat message.
        BUTTON_EVENT_ID (int): The ID of the button event message.
        COLOR_REFRESH_ID (int): The ID of the color refresh message.
    """


    HEARTBEAT_ID = 0x715
    BUTTON_EVENT_ID = 0x195
    COLOR_REFRESH_ID = 0x215

    def __init__(self):
        self.state = PadState.UNKNOWN
        self.buttons = sorted([PadButton(button_id) for _name, button_id in PadButton.BUTTONS.items()], key=lambda button:-button.button_id)
        self.can_message_queue = CanMessageQueue.get_instance()

    def get_button_index_from_id(self, button_id):
        """
        Returns the index of the button with the given ID.

        Args:
            button_id: The ID of the button to search for.

        Returns:
            int or None: The index of the button if found, None otherwise.
        """


        Logger.trace("Pad.get_button_index_from_id")

        return next(
            (
                index
                for index, button in enumerate(self.buttons)
                if button.button_id == button_id
            ),
            None,
        )

    def to_boot_up(self):
        """
        Transitions the pad to the boot-up state.

        If the current state of the pad is UNKNOWN or OPERATIONAL, it is transitioned to BOOT_UP and an informational message is logged.
        If the current state is not BOOT_UP, an informational message is logged.

        Args:
            self: The Pad instance.

        Returns:
            None
        """

        Logger.trace("Pad.to_boot_up")

        if self.state in [PadState.UNKNOWN, PadState.OPERATIONAL]:
            self.state = PadState.BOOT_UP
            Logger.info("Pad is now in Boot up.")
        elif self.state != PadState.BOOT_UP:
            Logger.info(f"Transition to Boot-up is not allowed from {self.state}")

    def to_operational(self):
        """
        Transitions the pad to the operational state.

        If the current state of the pad is BOOT_UP, it is transitioned to OPERATIONAL and an informational message is logged.
        If the current state is not OPERATIONAL, an informational message is logged.

        Args:
            self: The Pad instance.

        Returns:
            None
        """

        Logger.trace("Pad.to_operational")

        if self.state == PadState.BOOT_UP:
            self.state = PadState.OPERATIONAL
            Logger.info("Pad is transitioning to Operational.")
        elif self.state != PadState.OPERATIONAL:
            Logger.info(f"Transition to Operational is not allowed from {self.state}")

    def reset(self):
        """
        Resets the pad to the unknown state.

        This function sets the state of the pad to UNKNOWN and logs an informational message.

        Args:
            self: The Pad instance.

        Returns:
            None
        """

        Logger.trace("Pad.reset")

        self.state = PadState.UNKNOWN
        Logger.info("Pad has been reset to Unknown state.")

    def can_activate_keypad(self):
        """
        Activates the keypad.

        Returns:
            Tuple[int, List[int]]: A tuple containing the message ID and the data.

        Examples:
            >>> pad = Pad()
            >>> pad.can_activate_keypad()
            (0, [1])
        """

        Logger.trace("Pad.can_activate_keypad")

        message_id = 0x0
        data = [0x01]

        return message_id, data

    def can_refresh_button_colors(self):
        """
        Refreshes the colors of the buttons on the pad.

        Returns:
            Tuple[int, str]: A tuple containing the message ID and the payload.

        Examples:
            >>> pad = Pad()
            >>> pad.can_refresh_button_colors()
            (533, '0x00FF00')
        """

        Logger.trace("Pad.can_refresh_button_colors")

        message_id = 0x215
        pad_matrix = self.rgb_matrices()
        payload = self.rgb_matrix_to_hex(pad_matrix)

        return message_id, payload

    def can_is_heartbeat_boot_up(self, data):
        """
        Checks if the given data corresponds to the heartbeat boot-up data.

        Args:
            data (bytes): The data to be checked.

        Returns:
            bool: True if the data matches the heartbeat boot-up data, False otherwise.
        """

        heartbeat_bootup_data = bytes([0x00])
        return heartbeat_bootup_data == data

    def can_is_heartbeat_pre_operational(self, data):
        """
        Checks if the given data corresponds to the heartbeat pre-operational data.

        Args:
            data (bytes): The data to be checked.

        Returns:
            bool: True if the data matches the heartbeat pre-operational data, False otherwise.
        """

        heartbeat_pre_operational_data = bytes([0x7f])
        return heartbeat_pre_operational_data == data

    def can_is_heartbeat_operational(self, data):
        """
        Checks if the received data corresponds to an operational heartbeat.

        Args:
            data: The data received.

        Returns:
            True if the data corresponds to an operational heartbeat, False otherwise.

        Raises:
            None
        """

        heartbeat_operational_data = bytes([0x05])
        return heartbeat_operational_data == data

    def update_color(self, button_id, color):
        """
        Updates the color of a button.

        Args:
            self: The instance of the Pad class.
            button_id: The ID of the button to update the color for.
            color: The color to set for the button.

        Returns:
            None

        Raises:
            None
        """

        Logger.trace("Pad.update_color")

        Logger.info(f"updating color for button ID {button_id} to color {color}")
        button_index = self.get_button_index_from_id(button_id)
        self.buttons[button_index].change_color(color)
        message_id, data = self.can_refresh_button_colors()
        self.can_message_queue.push_with_id(message_id, data)

    def rgb_matrices(self):
        """
        Returns the RGB matrices of the pad.

        Args:
            self: The instance of the Pad class.

        Returns:
            The RGB matrices of the pad.

        Raises:
            None
        """

        i = 0
        pad_rgb_matrix = [
            [0] * 12,
            [0] * 12,
            [0] * 12,
        ]

        for button in self.buttons[:12]:
            pad_rgb_matrix[0][i] = button.red
            pad_rgb_matrix[1][i] = button.green
            pad_rgb_matrix[2][i] = button.blue
            i = i + 1

        return pad_rgb_matrix

    def rgb_matrix_to_hex(self, matrix):
        """
        Converts an RGB matrix to a hexadecimal representation.

        Args:
            matrix: The RGB matrix to convert.

        Returns:
            The hexadecimal representation of the RGB matrix.

        Raises:
            None
        """

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

        hex_matrix = [h0, h1, h2, h3, h4]
        Logger.debug(f"rgb_matrix: {hex_matrix}")
        return hex_matrix

    def decode_button_press(self, state):
        """
        Decodes the button press state.

        Args:
            state: The button press state to decode.

        Returns:
            The decoded button press state.

        Raises:
            None
        """

        int_values = list(state)
        b0 = int_values[0]
        b1 = int_values[1]
        bay1 = [int(d) for d in bin((1 << 8) + b0)[-8:]]
        bay2 = [int(d) for d in bin((1 << 8) + b1)[-4:]]
        return bay2 + bay1

    def __str__(self):
        return f"Pad(state={self.state})"


class VehicleController:
    """
    Processes the button press event for changing the drive state of the vehicle.

    Args:
        self: The instance of the VehicleController class.
        new_state: The new drive state to set.
        active_button: The button that triggered the event.

    Returns:
        None

    Raises:
        None
    """


    def __init__(self, ecu, pad, parking_brake):
        self.ecu = ecu
        self.pad = pad
        self.parking_brake = parking_brake

    def init_drive_state(self):
        Logger.trace("VehicleController.init_drive_state")

        Logger.debug("Initializing drive state")

        button_state = {
            "DRIVE": "blue" if self.parking_brake.is_engaged() else "black",
            "REVERSE": "black",
            "NEUTRAL": "black"
        }

        if self.parking_brake.is_engaged():
            Logger.debug("  Parking brake is engaged")
            self.ecu.set_drive_state(ECUState.PARK)
            self.parking_brake.engage()

        for button, color in button_state.items():
            button_id = PadButton.get_button_id(button)
            Logger.debug(f"  Attempting to set button {button_id} to color {color}")
            self.pad.update_color(button_id, color)

    def process_button_pressed(self, index):
        Logger.trace("VehicleController.process_button_pressed")

        button_id_to_action = {
            button_id: f'process_button_pressed_{button.lower()}'
            for button, button_id in PadButton.BUTTONS.items()
        }

        if action := button_id_to_action.get(index):
            action_function = getattr(self, action)
            action_function()
        else:
            Logger.info(f"No action defined for button ID: {index}")

    def set_button_color(self, button, color):
        Logger.trace("VehicleController.set_button_color")

        self.pad.update_color(PadButton.get_button_id(button), color)

    def switch_device_state(self, device, button):
        Logger.trace("VehicleController.switch_device_state")

        state = getattr(self.ecu, device)
        new_state = ECUState.ENABLED if state == ECUState.DISABLED else ECUState.DISABLED
        Logger.debug(f"Switching device state {new_state}")
        color = 'yellow' if new_state == ECUState.ENABLED else 'black'
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
        # self.ecu.can_drive_state_command(ECUState.NEUTRAL)
        self.parking_brake.engage()

    def process_button_pressed_reverse(self):
        Logger.trace("VehicleController.process_button_pressed_reverse")

        self.process_button_drive_change(ECUState.REVERSE, 'REVERSE')
        self.ecu.can_drive_state_command(ECUState.REVERSE)

    def process_button_pressed_neutral(self):
        Logger.trace("VehicleController.process_button_pressed_neutral")

        self.process_button_drive_change(ECUState.NEUTRAL, 'NEUTRAL')
        self.ecu.can_drive_state_command(ECUState.NEUTRAL)

    def process_button_pressed_drive(self):
        Logger.trace("VehicleController.process_button_pressed_drive")

        self.process_button_drive_change(ECUState.DRIVE, 'DRIVE')
        self.ecu.can_drive_state_command(ECUState.DRIVE)

    def process_button_pressed_exhaust_sound(self):
        Logger.trace("VehicleController.process_button_pressed_exhaust_sound")

        self.switch_device_state('exhaust_sound', 'EXHAUST_SOUND')

    def process_button_pressed_f1(self):
        Logger.trace("VehicleController.process_button_pressed_f1")

        # self.ecu.set_f1(ECUState.ENABLED)
        self.set_button_color('F1', 'cyan')
        # self.ecu.set_f2(ECUState.DISABLED)
        self.set_button_color('F2', 'black')

    def process_button_pressed_f2(self):
        Logger.trace("VehicleController.process_button_pressed_f2")

        # self.ecu.set_f2(ECUState.ENABLED)
        self.set_button_color('F2', 'yellow')
        # self.ecu.set_f1(ECUState.DISABLED)
        self.set_button_color('F1', 'black')

    def process_button_pressed_regen(self):
        Logger.trace("VehicleController.process_button_pressed_regen")

    def process_button_pressed_autopilot_on(self):
        Logger.trace("VehicleController.process_button_pressed_autopilot_on")

    def process_button_pressed_autopilot_speed_up(self):
        Logger.trace("VehicleController.process_button_pressed_autopilot_speed_up")

    def process_button_pressed_autopilot_speed_down(self):
        Logger.trace("VehicleController.process_button_pressed_autopilot_speed_down")


class Application:
    EXPECTED_BAUD_RATE = 500_000

    def __init__(self):
        self.first_run = True
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
        Logger.trace("Application.setup_can_connection")

        self.can = canio.CAN(rx=board.CAN_RX, tx=board.CAN_TX, baudrate=baudrate, auto_restart=True)
        self.listener = self.can.listen(matches=[canio.Match(Pad.HEARTBEAT_ID), canio.Match(Pad.BUTTON_EVENT_ID)], timeout=.1)

    def ensure_pad_operational(self):
        Logger.trace("Application.ensure_pad_operational")

        if self.pad.state == PadState.UNKNOWN and self.first_run:
            self.ensure_pad_init_drive_state()
            self.first_run = False
        elif self.pad.state == PadState.BOOT_UP:
            self.ensure_pad_init_drive_state()
        elif self.pad.state not in [PadState.OPERATIONAL, PadState.UNKNOWN]:
            Logger.info(f"unknown state: [{self.pad.state}]")

    def ensure_pad_init_drive_state(self):
        Logger.trace("Application.ensure_pad_init_drive_state")

        self.send_pad_activate()
        self.pad.to_operational()
        self.controller.init_drive_state()

    def send_pad_activate(self):
        Logger.trace("Application.send_pad_activate")

        message_id, data = self.pad.can_activate_keypad()
        self.can_message_queue.push_with_id(message_id, data)

    def process_can_bus(self):
        Logger.trace("Application.process_can_bus")

        self.current_bus_state = self.can.state

        if self.current_bus_state != self.previous_bus_state:
            Logger.info(f"CAN bus state: {self.current_bus_state}")
            self.previous_bus_state = self.current_bus_state

    def process_can_message(self):
        Logger.trace("Application.process_can_message")

        message = self.listener.receive()

        if message is not None:
            self._process_message_based_on_id(message)

    def process_can_message_queue(self):
        """AI is creating summary for process_can_message_queue
        """
        Logger.trace("Application.process_can_message_queue")

        if message := self.can_message_queue.pop():
            Logger.debug(f"Sending CAN message id: {message.id} data: {message.data}")
            self.can.send(message)

    def _process_message_based_on_id(self, message):
        Logger.trace("Application._process_message_based_on_id")

        process_methods = {
            Pad.HEARTBEAT_ID: self._process_pad_heartbeat,
            Pad.BUTTON_EVENT_ID: self._process_pad_button,
        }
        method = process_methods.get(message.id, self._unknown_message)
        method(message)

    def _unknown_message(self, message):
        Logger.trace("Application._unknown_message")

        Logger.info(f"unknown message: [{message.id}] {message.data}")

    def _process_pad_heartbeat(self, message):
        Logger.trace("Application._process_pad_heartbeat")

        if self.pad.can_is_heartbeat_boot_up(message.data):
            self.pad.to_boot_up()
        elif self.pad.can_is_heartbeat_pre_operational(message.data):
            pass
        elif self.pad.can_is_heartbeat_operational(message.data):
            self.pad.to_operational()
        else:
            Logger.info(f"unknown heartbeat: [{message.id}] {message.data}")

    def _process_pad_button(self, message):
        Logger.trace("Application._process_pad_button")

        button_names = PadButton.get_button_names()
        pressed_buttons = self.pad.decode_button_press(message.data)

        for btn_name in button_names:
            button_id = PadButton.get_button_id(btn_name)
            if pressed_buttons[button_id]:
                Logger.debug(f'PRESSED_{btn_name} / {button_id}')
                self.controller.process_button_pressed(button_id)


####################
### Main Program ###
####################
# Logger.current_level = Logger.DEBUG
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

    Logger.trace("MAIN: END tick -------------------------")
    time.sleep(FeatherSettings.CAN_REFRESH_RATE)