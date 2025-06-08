"""
Bin Actuator Emulator
Simulates the physical mechanism for emptying the bin
"""

import time
import logging
import threading
from typing import Optional, Callable
from enum import Enum

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
    handlers=[logging.FileHandler("actuators.log"), logging.StreamHandler()],
)
logger = logging.getLogger("BinActuator")


class ActuatorState(Enum):
    """Possible states of the bin actuator"""

    IDLE = "IDLE"
    OPENING = "OPENING"
    EMPTYING = "EMPTYING"
    CLOSING = "CLOSING"
    ERROR = "ERROR"


class BinActuator:
    """Emulates a physical actuator mechanism for emptying bins"""

    def __init__(
        self, actuator_id: str, state_callback: Callable[[ActuatorState], None]
    ):
        """
        Initialize the bin actuator emulator

        Args:
            actuator_id: Unique identifier for this actuator
            state_callback: Callback function to handle state changes
        """
        self.actuator_id = actuator_id
        self.state_callback = state_callback
        self.current_state = ActuatorState.IDLE
        self.is_powered = False
        self._thread: Optional[threading.Thread] = None
        logger.info(f"Bin actuator {actuator_id} initialized")

    def power_on(self) -> None:
        """Power on the actuator"""
        self.is_powered = True
        self._update_state(ActuatorState.IDLE)
        logger.info(f"Actuator {self.actuator_id} powered on")

    def power_off(self) -> None:
        """Power off the actuator"""
        self.is_powered = False
        self._update_state(ActuatorState.IDLE)
        if self._thread and self._thread.is_alive():
            self._thread.join(timeout=1.0)
        logger.info(f"Actuator {self.actuator_id} powered off")

    def trigger_empty(self) -> None:
        """Trigger the bin emptying sequence"""
        if not self.is_powered:
            logger.warning("Cannot empty bin: actuator is not powered on")
            return

        if self.current_state != ActuatorState.IDLE:
            logger.warning(f"Cannot empty bin: actuator is busy ({self.current_state})")
            return

        self._thread = threading.Thread(target=self._emptying_sequence, daemon=True)
        self._thread.start()
        logger.info(f"Started emptying sequence for bin {self.actuator_id}")

    def _emptying_sequence(self) -> None:
        """Simulate the bin emptying sequence"""
        try:
            # Opening the bin
            self._update_state(ActuatorState.OPENING)
            time.sleep(2)  # Simulate time to open

            # Emptying contents
            self._update_state(ActuatorState.EMPTYING)
            time.sleep(3)  # Simulate time to empty

            # Closing the bin
            self._update_state(ActuatorState.CLOSING)
            time.sleep(2)  # Simulate time to close

            # Back to idle
            self._update_state(ActuatorState.IDLE)
            logger.info(f"Emptying sequence completed for bin {self.actuator_id}")

        except Exception as e:
            logger.error(f"Error during emptying sequence: {e}")
            self._update_state(ActuatorState.ERROR)

    def _update_state(self, new_state: ActuatorState) -> None:
        """Update actuator state and notify through callback"""
        self.current_state = new_state
        self.state_callback(new_state)
        logger.debug(f"Actuator {self.actuator_id} state changed to {new_state.value}")

    def get_state(self) -> ActuatorState:
        """Get current actuator state"""
        return self.current_state
