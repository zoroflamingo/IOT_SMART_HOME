"""
Main Monitoring GUI Application
Displays bin data, status changes, and alarms
"""

import tkinter as tk
from tkinter import ttk, messagebox
import paho.mqtt.client as mqtt
import json
import logging
from datetime import datetime
import sqlite3
from typing import Dict, Optional
import threading
from mqtt_init import broker_ip, port, username, password, BASE_TOPIC, ALARM_TOPIC

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
    handlers=[logging.FileHandler("monitor_gui.log"), logging.StreamHandler()],
)
logger = logging.getLogger("MonitorGUI")


class BinMonitorGUI:
    """Main monitoring interface for the smart bin system"""

    def __init__(self, master: tk.Tk):
        """Initialize the monitoring GUI"""
        self.master = master
        self.master.title("Smart Bin Monitoring System")
        self.master.geometry("1200x800")

        # Initialize variables
        self.bins: Dict[str, Dict] = {}  # Store bin widgets
        self.client: Optional[mqtt.Client] = None
        self.db_path = "bin_data.db"

        # Set up GUI
        self._setup_gui()

        # Set up MQTT
        self._setup_mqtt()

        # Start periodic updates
        self._schedule_updates()

        # Configure window close handler
        self.master.protocol("WM_DELETE_WINDOW", self._on_closing)

        logger.info("Monitoring GUI initialized")

    def _setup_gui(self) -> None:
        """Set up the main GUI layout"""
        # Create main container
        self.main_container = ttk.Frame(self.master, padding="10")
        self.main_container.grid(row=0, column=0, sticky=(tk.W, tk.E, tk.N, tk.S))

        # Configure grid weights
        self.master.columnconfigure(0, weight=1)
        self.master.rowconfigure(0, weight=1)
        self.main_container.columnconfigure(1, weight=1)
        self.main_container.rowconfigure(1, weight=1)

        # Create sections
        self._create_header()
        self._create_bin_view()
        self._create_alarm_view()
        self._create_status_bar()

    def _create_header(self) -> None:
        """Create the header section"""
        header = ttk.Frame(self.main_container)
        header.grid(row=0, column=0, columnspan=2, sticky=(tk.W, tk.E), pady=(0, 10))

        # Title
        ttk.Label(
            header,
            text="Smart Bin Monitoring System",
            font=("TkDefaultFont", 16, "bold"),
        ).pack(side=tk.LEFT)

        # Connection status
        self.conn_status = ttk.Label(
            header, text="●", foreground="red", font=("TkDefaultFont", 14)
        )
        self.conn_status.pack(side=tk.RIGHT)

    def _create_bin_view(self) -> None:
        """Create the bin monitoring section"""
        # Create bin view container
        bin_frame = ttk.LabelFrame(
            self.main_container, text="Monitored Bins", padding="10"
        )
        bin_frame.grid(row=1, column=0, sticky=(tk.W, tk.E, tk.N, tk.S), padx=(0, 5))

        # Create canvas and scrollbar for bins
        self.bin_canvas = tk.Canvas(bin_frame)
        scrollbar = ttk.Scrollbar(
            bin_frame, orient=tk.VERTICAL, command=self.bin_canvas.yview
        )
        self.bin_frame_inner = ttk.Frame(self.bin_canvas)

        self.bin_canvas.configure(yscrollcommand=scrollbar.set)

        # Grid layout
        scrollbar.pack(side=tk.RIGHT, fill=tk.Y)
        self.bin_canvas.pack(side=tk.LEFT, fill=tk.BOTH, expand=True)

        # Create window in canvas
        self.bin_canvas_frame = self.bin_canvas.create_window(
            (0, 0), window=self.bin_frame_inner, anchor=tk.NW
        )

        # Configure scrolling
        self.bin_frame_inner.bind("<Configure>", self._on_frame_configure)
        self.bin_canvas.bind("<Configure>", self._on_canvas_configure)

    def _create_alarm_view(self) -> None:
        """Create the alarm monitoring section"""
        # Create alarm view container
        alarm_frame = ttk.LabelFrame(
            self.main_container, text="Alarms & Events", padding="10"
        )
        alarm_frame.grid(row=1, column=1, sticky=(tk.W, tk.E, tk.N, tk.S), padx=(5, 0))

        # Create treeview for alarms
        self.alarm_tree = ttk.Treeview(
            alarm_frame, columns=("time", "bin", "type", "message"), show="headings"
        )

        # Configure columns
        self.alarm_tree.heading("time", text="Time")
        self.alarm_tree.heading("bin", text="Bin ID")
        self.alarm_tree.heading("type", text="Type")
        self.alarm_tree.heading("message", text="Message")

        self.alarm_tree.column("time", width=150)
        self.alarm_tree.column("bin", width=100)
        self.alarm_tree.column("type", width=100)
        self.alarm_tree.column("message", width=300)

        # Add scrollbar
        alarm_scroll = ttk.Scrollbar(
            alarm_frame, orient=tk.VERTICAL, command=self.alarm_tree.yview
        )
        self.alarm_tree.configure(yscrollcommand=alarm_scroll.set)

        # Grid layout
        self.alarm_tree.pack(side=tk.LEFT, fill=tk.BOTH, expand=True)
        alarm_scroll.pack(side=tk.RIGHT, fill=tk.Y)

        # Bind double-click to acknowledge alarm
        self.alarm_tree.bind("<Double-1>", self._acknowledge_selected_alarm)

    def _create_status_bar(self) -> None:
        """Create the status bar"""
        status_frame = ttk.Frame(self.main_container)
        status_frame.grid(
            row=2, column=0, columnspan=2, sticky=(tk.W, tk.E), pady=(10, 0)
        )

        self.status_var = tk.StringVar(value="Ready")
        ttk.Label(status_frame, textvariable=self.status_var).pack(side=tk.LEFT)

    def _setup_mqtt(self) -> None:
        """Set up MQTT client and connection"""
        try:
            # Create client
            client_id = f"monitor_gui_{datetime.now().strftime('%Y%m%d_%H%M%S')}"
            self.client = mqtt.Client(client_id, clean_session=True)

            # Set up callbacks
            self.client.on_connect = self._on_connect
            self.client.on_message = self._on_message
            self.client.on_disconnect = self._on_disconnect

            # Set up authentication if needed
            if username:
                self.client.username_pw_set(username, password)

            # Connect to broker
            logger.info(f"Connecting to broker {broker_ip}")
            self.client.connect(broker_ip, int(port))
            self.client.loop_start()

        except Exception as e:
            logger.error(f"MQTT setup error: {e}")
            self.status_var.set(f"Error: {e}")

    def _on_connect(self, client, userdata, flags, rc: int) -> None:
        """Handle connection to MQTT broker"""
        if rc == 0:
            self.conn_status.configure(foreground="green")
            self.status_var.set("Connected to MQTT broker")
            # Subscribe to all bin topics and alarms
            # Subscribe to all bin topics
            topics = [
                (f"{BASE_TOPIC}+/fill_level", 0),
                (f"{BASE_TOPIC}+/status", 0),
                (ALARM_TOPIC, 0),
            ]
            self.client.subscribe(topics)
            logger.info(f"Subscribed to topics: {[t[0] for t in topics]}")
            logger.info("Connected to MQTT broker")
        else:
            self.conn_status.configure(foreground="red")
            self.status_var.set(f"Connection failed with code {rc}")
            logger.error(f"Connection failed with code {rc}")

    def _on_disconnect(self, client, userdata, rc: int) -> None:
        """Handle disconnection from MQTT broker"""
        self.conn_status.configure(foreground="red")
        self.status_var.set("Disconnected from broker")
        logger.warning(f"Disconnected from broker with code {rc}")

    def _on_message(self, client, userdata, msg) -> None:
        """Handle incoming MQTT messages"""
        try:
            # Extract topic information
            topic = msg.topic
            payload = msg.payload.decode()
            logger.info(f"Received message on topic {topic}: {payload}")

            if topic == ALARM_TOPIC:
                # Handle alarm messages
                alarm_data = json.loads(payload)
                # Schedule alarm handling in main thread
                self.master.after(0, lambda: self._handle_alarm(alarm_data))
            else:
                # Handle bin data
                # Topic format is either municipal/binsbin_id/fill_level or municipal/binsbin_id/status
                bin_id = topic.replace(BASE_TOPIC, "").split("/")[0]
                data_type = topic.split("/")[-1]

                if data_type == "fill_level":
                    level = float(payload)
                    # Schedule GUI update in main thread
                    self.master.after(0, lambda: self._update_bin_level(bin_id, level))
                elif data_type == "status":
                    # Schedule GUI update in main thread
                    self.master.after(
                        0, lambda: self._update_bin_status(bin_id, payload)
                    )

        except Exception as e:
            logger.error(f"Error processing message: {e}")
            self.master.after(
                0, lambda: self.status_var.set(f"Error processing message: {e}")
            )

    def _handle_alarm(self, alarm_data: dict) -> None:
        """Handle incoming alarm messages"""
        try:
            # Add alarm to treeview
            self.alarm_tree.insert(
                "",
                0,
                values=(
                    alarm_data["timestamp"],
                    alarm_data["bin_id"],
                    alarm_data["type"],
                    alarm_data["message"],
                ),
                tags=("alarm",),
            )

            # Configure tag
            self.alarm_tree.tag_configure("alarm", foreground="red")

            # Show notification
            self.status_var.set(f"New alarm: {alarm_data['message']}")

        except Exception as e:
            logger.error(f"Error handling alarm: {e}")

    def _update_bin_level(self, bin_id: str, level: float) -> None:
        """Update bin fill level display"""
        if bin_id not in self.bins:
            self._create_bin_widget(bin_id)

        bin_widgets = self.bins[bin_id]
        bin_widgets["level_var"].set(f"{level:.1f}%")

        # Update progress bar
        bin_widgets["progress"]["value"] = level

        # Update color based on level
        if level >= 80:
            bin_widgets["progress"]["style"] = "Red.Horizontal.TProgressbar"
        elif level >= 60:
            bin_widgets["progress"]["style"] = "Yellow.Horizontal.TProgressbar"
        else:
            bin_widgets["progress"]["style"] = "Green.Horizontal.TProgressbar"

    def _update_bin_status(self, bin_id: str, status: str) -> None:
        """Update bin status display"""
        if bin_id not in self.bins:
            self._create_bin_widget(bin_id)

        self.bins[bin_id]["status_var"].set(status)

    def _create_bin_widget(self, bin_id: str) -> None:
        """Create a new bin monitoring widget"""
        # Create frame for this bin
        bin_frame = ttk.LabelFrame(
            self.bin_frame_inner, text=f"Bin {bin_id}", padding="5"
        )
        bin_frame.pack(fill=tk.X, padx=5, pady=5)

        # Create progress bar styles
        style = ttk.Style()
        style.configure("Red.Horizontal.TProgressbar", background="red")
        style.configure("Yellow.Horizontal.TProgressbar", background="yellow")
        style.configure("Green.Horizontal.TProgressbar", background="green")

        # Create widgets
        level_var = tk.StringVar(value="0.0%")
        status_var = tk.StringVar(value="Unknown")

        ttk.Label(bin_frame, text="Fill Level:").grid(row=0, column=0, padx=5)
        ttk.Label(bin_frame, textvariable=level_var).grid(row=0, column=1, padx=5)

        progress = ttk.Progressbar(
            bin_frame,
            length=200,
            mode="determinate",
            style="Green.Horizontal.TProgressbar",
        )
        progress.grid(row=1, column=0, columnspan=2, padx=5, pady=5)

        ttk.Label(bin_frame, text="Status:").grid(row=2, column=0, padx=5)
        ttk.Label(bin_frame, textvariable=status_var).grid(row=2, column=1, padx=5)

        # Store widgets
        self.bins[bin_id] = {
            "frame": bin_frame,
            "level_var": level_var,
            "status_var": status_var,
            "progress": progress,
        }

    def _acknowledge_selected_alarm(self, event) -> None:
        """Acknowledge the selected alarm"""
        selection = self.alarm_tree.selection()
        if not selection:
            return

        item = self.alarm_tree.item(selection[0])
        self.alarm_tree.delete(selection[0])

        # Update status
        self.status_var.set(f"Acknowledged alarm: {item['values'][3]}")

    def _schedule_updates(self) -> None:
        """Schedule periodic updates"""
        self._update_from_database()

    def _update_from_database(self) -> None:
        """Update GUI with data from database"""
        try:
            with sqlite3.connect(self.db_path) as conn:
                cursor = conn.cursor()

                # Get active alarms
                try:
                    cursor.execute(
                        """
                        SELECT id, bin_id, alarm_type, message, timestamp 
                        FROM bin_alarms 
                        WHERE acknowledged = FALSE 
                        ORDER BY timestamp DESC
                        """
                    )
                    alarms = cursor.fetchall()

                    # Clear existing items
                    for item in self.alarm_tree.get_children():
                        self.alarm_tree.delete(item)

                    # Add alarms to tree
                    for alarm in alarms:
                        self.alarm_tree.insert(
                            "",
                            tk.END,
                            values=(
                                alarm[4],  # timestamp
                                alarm[1],  # bin_id
                                alarm[2],  # type
                                alarm[3],  # message
                            ),
                            tags=(str(alarm[0]),),  # store alarm id as tag
                        )
                except sqlite3.Error as e:
                    logger.error(f"Error fetching alarms: {e}")
                    # Continue with other updates even if alarms fail

                # Get latest bin readings
                try:
                    cursor.execute(
                        """
                        SELECT DISTINCT bin_id 
                        FROM bin_readings
                        """
                    )
                    bins = cursor.fetchall()

                    for bin_id in [b[0] for b in bins]:
                        # Get latest reading
                        cursor.execute(
                            """
                            SELECT fill_level 
                            FROM bin_readings 
                            WHERE bin_id = ? 
                            ORDER BY timestamp DESC 
                            LIMIT 1
                            """,
                            (bin_id,),
                        )
                        result = cursor.fetchone()
                        if result:
                            self._update_bin_level(bin_id, result[0])
                except sqlite3.Error as e:
                    logger.error(f"Error fetching bin readings: {e}")

        except sqlite3.Error as e:
            logger.error(f"Database error: {e}")
        except Exception as e:
            logger.error(f"Error updating from database: {e}")

        # Schedule next update
        self.master.after(10000, self._update_from_database)

    def _on_frame_configure(self, event=None) -> None:
        """Handle inner frame configuration"""
        self.bin_canvas.configure(scrollregion=self.bin_canvas.bbox("all"))

    def _on_canvas_configure(self, event) -> None:
        """Handle canvas configuration"""
        self.bin_canvas.itemconfig(self.bin_canvas_frame, width=event.width)

    def _on_closing(self) -> None:
        """Handle window closing"""
        if self.client:
            self.client.loop_stop()
            self.client.disconnect()
        self.master.destroy()
        logger.info("Application closed")


def main():
    """Main entry point"""
    try:
        root = tk.Tk()
        app = BinMonitorGUI(root)
        root.mainloop()
    except Exception as e:
        logger.critical(f"Fatal error: {e}")
        messagebox.showerror("Fatal Error", str(e))
        raise


if __name__ == "__main__":
    main()
