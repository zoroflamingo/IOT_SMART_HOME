"""
Smart Bin Management System
Integrates the various emulators to create a complete bin monitoring system
"""

import tkinter as tk
from tkinter import ttk, messagebox
import paho.mqtt.client as mqtt
import random
import logging
from mqtt_init import broker_ip, port, username, password, BASE_TOPIC, BinStatus
from UltrasonicSensor import UltrasonicSensor
from ControlPanel import ControlPanel
from BinActuator import BinActuator, ActuatorState

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
    handlers=[logging.FileHandler("bin_system.log"), logging.StreamHandler()],
)
logger = logging.getLogger("BinSystem")


class SmartBinSystem:
    """Integrates sensor, control panel and actuator emulators"""

    def __init__(self, master: tk.Tk):
        """Initialize the smart bin system"""
        self.master = master
        self.master.title("Smart Bin System")

        # Generate unique bin ID
        self.bin_id = f"bin_{random.randint(1000, 9999)}"

        # Create main container with three sections
        self.setup_gui()

        # Initialize MQTT
        self._setup_mqtt()

        # Initialize emulators
        self._setup_emulators()

        # Configure window close handler
        self.master.protocol("WM_DELETE_WINDOW", self._on_closing)

        logger.info(f"Smart bin system {self.bin_id} initialized")

    def setup_gui(self):
        """Set up the main GUI layout"""
        # Main container
        self.main_container = ttk.Frame(self.master, padding="10")
        self.main_container.grid(row=0, column=0, sticky=(tk.W, tk.E, tk.N, tk.S))

        # Title
        ttk.Label(
            self.main_container,
            text=f"Smart Bin System - ID: {self.bin_id}",
            font=("TkDefaultFont", 14, "bold"),
        ).grid(row=0, column=0, columnspan=3, pady=10)

        # Create three sections
        self.sensor_frame = ttk.LabelFrame(
            self.main_container, text="Ultrasonic Sensor", padding="10"
        )
        self.sensor_frame.grid(
            row=1, column=0, padx=10, pady=5, sticky=(tk.W, tk.E, tk.N, tk.S)
        )

        self.control_frame = ttk.LabelFrame(
            self.main_container, text="Control Panel", padding="10"
        )
        self.control_frame.grid(
            row=1, column=1, padx=10, pady=5, sticky=(tk.W, tk.E, tk.N, tk.S)
        )

        self.actuator_frame = ttk.LabelFrame(
            self.main_container, text="Bin Actuator", padding="10"
        )
        self.actuator_frame.grid(
            row=1, column=2, padx=10, pady=5, sticky=(tk.W, tk.E, tk.N, tk.S)
        )

        # Sensor display
        self.level_var = tk.StringVar(value="0.0%")
        ttk.Label(self.sensor_frame, text="Current Fill Level:").grid(
            row=0, column=0, padx=5, pady=5
        )
        ttk.Label(
            self.sensor_frame,
            textvariable=self.level_var,
            font=("TkDefaultFont", 12, "bold"),
        ).grid(row=0, column=1, padx=5, pady=5)

        # Actuator display
        self.actuator_state_var = tk.StringVar(value="IDLE")
        ttk.Label(self.actuator_frame, text="Actuator State:").grid(
            row=0, column=0, padx=5, pady=5
        )
        self.state_label = ttk.Label(
            self.actuator_frame,
            textvariable=self.actuator_state_var,
            font=("TkDefaultFont", 12, "bold"),
        )
        self.state_label.grid(row=0, column=1, padx=5, pady=5)

    def _setup_mqtt(self) -> None:
        """Set up MQTT client and connection"""
        try:
            client_id = f"bin_system_{self.bin_id}_{random.randint(0, 1000)}"
            self.client = mqtt.Client(client_id, clean_session=True)

            # Set up callbacks
            self.client.on_connect = self._on_connect
            self.client.on_disconnect = self._on_disconnect

            # Set up authentication if needed
            if username:
                self.client.username_pw_set(username, password)

            # Connect to broker
            logger.info(f"Connecting to broker {broker_ip}")
            self.client.connect(broker_ip, int(port))
            self.client.loop_start()

        except Exception as e:
            logger.error(f"Failed to setup MQTT: {e}")
            messagebox.showerror(
                "Connection Error", f"Failed to connect to MQTT broker: {e}"
            )

    def _setup_emulators(self) -> None:
        """Initialize and connect the emulators"""
        # Initialize ultrasonic sensor
        self.sensor = UltrasonicSensor(self.bin_id, self._on_sensor_data)

        # Initialize control panel
        self.control_panel = ControlPanel(self.control_frame, self.bin_id)

        # Register control panel callbacks
        self.control_panel.register_callback("empty", self._on_empty_request)
        self.control_panel.register_callback("rate_change", self._on_rate_change)
        self.control_panel.register_callback("power", self._on_power_change)

        # Initialize actuator
        self.actuator = BinActuator(self.bin_id, self._on_actuator_state_change)

    def _on_connect(self, client, userdata, flags, rc: int) -> None:
        """Handle MQTT connection"""
        if rc == 0:
            logger.info("Connected to MQTT broker")
            self.sensor.start()  # Start sensor after connection
        else:
            logger.error(f"Connection failed with code {rc}")

    def _on_disconnect(self, client, userdata, rc: int) -> None:
        """Handle MQTT disconnection"""
        logger.warning(f"Disconnected from broker with code {rc}")

    def _on_sensor_data(self, fill_level: float) -> None:
        """Handle new sensor data"""
        try:
            # Update display
            self.level_var.set(f"{fill_level:.1f}%")

            # Publish fill level
            topic = f"{BASE_TOPIC}{self.bin_id}/fill_level"
            message = f"{fill_level:.1f}"
            logger.info(f"Publishing to {topic}: {message}")
            self.client.publish(topic, message)

            # Determine and publish bin status
            status = "🟢 Normal"
            if fill_level >= 80:
                status = "⚠️ Needs Emptying"
                # Automatically trigger emptying when bin is full
                if self.actuator.get_state() == ActuatorState.IDLE:
                    logger.info(
                        f"Bin {self.bin_id} reached {fill_level}% - automatically emptying"
                    )
                    self.actuator.trigger_empty()
            elif fill_level <= 5:
                status = "✅ Recently Emptied"

            status_topic = f"{BASE_TOPIC}{self.bin_id}/status"
            logger.info(f"Publishing to {status_topic}: {status}")
            self.client.publish(status_topic, status)

        except Exception as e:
            logger.error(f"Error publishing sensor data: {e}")

    def _on_empty_request(self) -> None:
        """Handle empty request from control panel"""
        self.actuator.trigger_empty()

    def _on_rate_change(self, rate: float) -> None:
        """Handle fill rate change from control panel"""
        self.sensor.set_fill_rate(rate)

    def _on_power_change(self, is_on: bool) -> None:
        """Handle power state change from control panel"""
        if is_on:
            self.sensor.start()
            self.actuator.power_on()
        else:
            self.sensor.stop()
            self.actuator.power_off()

    def _on_actuator_state_change(self, state: ActuatorState) -> None:
        """Handle actuator state changes"""
        # Update display
        self.actuator_state_var.set(state.value)

        # Update color based on state
        color = "black"
        if state == ActuatorState.ERROR:
            color = "red"
        elif state == ActuatorState.IDLE:
            color = "green"
        elif state in (
            ActuatorState.OPENING,
            ActuatorState.EMPTYING,
            ActuatorState.CLOSING,
        ):
            color = "blue"
        self.state_label.configure(foreground=color)

        if state == ActuatorState.IDLE:
            # Reset sensor reading when emptying is complete
            self.sensor.simulate_emptying()

        # Publish actuator state
        try:
            topic = f"{BASE_TOPIC}/{self.bin_id}/actuator_state"
            self.client.publish(topic, state.value)
        except Exception as e:
            logger.error(f"Error publishing actuator state: {e}")

    def _on_closing(self) -> None:
        """Clean up resources on window close"""
        self.sensor.stop()
        self.actuator.power_off()
        if hasattr(self, "client"):
            self.client.loop_stop()
            self.client.disconnect()
        self.master.destroy()
        logger.info(f"Smart bin system {self.bin_id} shut down")


def main():
    """Main entry point"""
    root = tk.Tk()
    app = SmartBinSystem(root)
    root.mainloop()


if __name__ == "__main__":
    main()
