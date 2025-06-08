"""
Ultrasonic Sensor Emulator for Bin Fill-Level Detection
Simulates an ultrasonic sensor that produces fill-level measurements
"""

import time
import random
import logging
from typing import Optional, Callable
import threading

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
    handlers=[logging.FileHandler("sensors.log"), logging.StreamHandler()],
)
logger = logging.getLogger("UltrasonicSensor")


class UltrasonicSensor:
    """Emulates an ultrasonic sensor that measures fill level"""

    def __init__(self, sensor_id: str, data_callback: Callable[[float], None]):
        """
        Initialize the ultrasonic sensor emulator

        Args:
            sensor_id: Unique identifier for this sensor
            data_callback: Callback function to handle new measurements
        """
        self.sensor_id = sensor_id
        self.data_callback = data_callback
        self.is_running = False
        self.current_level = 0.0
        self.fill_rate = 1.0
        self._thread: Optional[threading.Thread] = None
        logger.info(f"Ultrasonic sensor {sensor_id} initialized")

    def start(self) -> None:
        """Start the sensor measurement simulation"""
        if not self.is_running:
            self.is_running = True
            self._thread = threading.Thread(target=self._measurement_loop, daemon=True)
            self._thread.start()
            logger.info(f"Sensor {self.sensor_id} started")

    def stop(self) -> None:
        """Stop the sensor measurement simulation"""
        self.is_running = False
        if self._thread:
            self._thread.join(timeout=1.0)
        logger.info(f"Sensor {self.sensor_id} stopped")

    def set_fill_rate(self, rate: float) -> None:
        """Set the fill rate for simulation"""
        self.fill_rate = max(0.0, min(rate, 10.0))  # Limit between 0 and 10
        logger.debug(f"Fill rate set to {self.fill_rate}")

    def get_current_level(self) -> float:
        """Get the current fill level"""
        return self.current_level

    def simulate_emptying(self) -> None:
        """Simulate the bin being emptied"""
        self.current_level = 0.0
        self.data_callback(self.current_level)
        logger.info(f"Bin {self.sensor_id} emptied")

    def _measurement_loop(self) -> None:
        """Main measurement simulation loop"""
        while self.is_running:
            try:
                # Add some random noise to the measurement
                noise = random.uniform(-0.2, 0.2)

                # Update fill level with noise
                if self.current_level < 100:
                    self.current_level = min(
                        100, self.current_level + self.fill_rate + noise
                    )

                    # Send measurement through callback
                    self.data_callback(self.current_level)

                    logger.debug(
                        f"Sensor {self.sensor_id} level: {self.current_level:.1f}%"
                    )

                time.sleep(1)  # Simulate sensor reading interval

            except Exception as e:
                logger.error(f"Error in measurement loop: {e}")
                self.is_running = False
                break
