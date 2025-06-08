"""
Control Panel Emulator for Bin Management
Simulates physical buttons and knobs for controlling the bin system
"""

import tkinter as tk
from tkinter import ttk
import logging
from typing import Callable, Dict, Optional

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
    handlers=[logging.FileHandler("controls.log"), logging.StreamHandler()],
)
logger = logging.getLogger("ControlPanel")


class ControlPanel:
    """Emulates a physical control panel with buttons and knobs"""

    def __init__(self, container: ttk.Frame, panel_id: str):
        """
        Initialize the control panel emulator

        Args:
            container: Parent frame to place controls in
            panel_id: Unique identifier for this control panel
        """
        self.container = container
        self.panel_id = panel_id
        self.callbacks: Dict[str, Callable] = {}

        self._create_widgets()
        logger.info(f"Control panel {panel_id} initialized")

    def _create_widgets(self) -> None:
        """Create and configure GUI elements"""
        # Panel Label
        ttk.Label(
            self.container, text="Control Panel", font=("TkDefaultFont", 12, "bold")
        ).grid(row=0, column=0, columnspan=2, pady=10)

        # Emergency Empty Button (Red)
        self.empty_btn = ttk.Button(
            self.container,
            text="EMERGENCY EMPTY",
            style="Emergency.TButton",
            command=self._on_emergency_empty,
        )
        self.empty_btn.grid(row=1, column=0, columnspan=2, pady=10)

        # Fill Rate Knob
        ttk.Label(self.container, text="Fill Rate Control:").grid(
            row=2, column=0, padx=5, pady=5
        )
        self.rate_scale = ttk.Scale(
            self.container,
            from_=0.0,
            to=10.0,
            orient=tk.HORIZONTAL,
            command=self._on_rate_change,
        )
        self.rate_scale.set(1.0)
        self.rate_scale.grid(row=2, column=1, padx=5, pady=5)

        # Power Button
        self.power_btn = ttk.Button(
            self.container, text="Power ON", command=self._on_power_toggle
        )
        self.power_btn.grid(row=3, column=0, columnspan=2, pady=10)

        # Status LED
        self.status_label = ttk.Label(
            self.container, text="●", foreground="red", font=("TkDefaultFont", 14)
        )
        self.status_label.grid(row=4, column=0, columnspan=2)

        # Configure emergency button style
        style = ttk.Style()
        style.configure(
            "Emergency.TButton", foreground="red", font=("TkDefaultFont", 10, "bold")
        )

    def register_callback(self, event: str, callback: Callable) -> None:
        """Register a callback for control panel events"""
        self.callbacks[event] = callback
        logger.debug(f"Registered callback for event: {event}")

    def _on_emergency_empty(self) -> None:
        """Handle emergency empty button press"""
        if "empty" in self.callbacks:
            self.callbacks["empty"]()
            logger.info("Emergency empty triggered")

    def _on_rate_change(self, value: str) -> None:
        """Handle fill rate knob adjustment"""
        try:
            rate = float(value)
            if "rate_change" in self.callbacks:
                self.callbacks["rate_change"](rate)
                logger.debug(f"Fill rate adjusted to {rate}")
        except ValueError:
            logger.error(f"Invalid rate value: {value}")

    def _on_power_toggle(self) -> None:
        """Handle power button press"""
        current_state = self.power_btn.cget("text")
        new_state = "Power OFF" if current_state == "Power ON" else "Power ON"
        self.power_btn.config(text=new_state)

        # Update status LED
        self.status_label.config(
            foreground="green" if new_state == "Power OFF" else "red"
        )

        if "power" in self.callbacks:
            self.callbacks["power"](new_state == "Power OFF")
            logger.info(f"Power toggled to {new_state}")
