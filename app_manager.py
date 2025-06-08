"""
Data Manager Application
Collects data from MQTT broker, stores in database, and handles alarms
"""

import paho.mqtt.client as mqtt
import sqlite3
import json
import logging
from datetime import datetime
import threading
from typing import Optional
import os
from mqtt_init import (
    broker_ip,
    port,
    username,
    password,
    BASE_TOPIC,
    ALARM_TOPIC,
    BIN_FILL_LEVEL_THRESHOLD,
    BIN_EMPTY_THRESHOLD,
)

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
    handlers=[logging.FileHandler("bin_manager.log"), logging.StreamHandler()],
)
logger = logging.getLogger("DataManager")


def init_database(db_path: str) -> None:
    """Initialize the database and create tables"""
    try:
        with sqlite3.connect(db_path) as conn:
            cursor = conn.cursor()

            # Create tables
            cursor.execute("""DROP TABLE IF EXISTS bin_readings""")
            cursor.execute("""DROP TABLE IF EXISTS bin_events""")
            cursor.execute("""DROP TABLE IF EXISTS bin_alarms""")

            cursor.execute("""
            CREATE TABLE bin_readings (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                bin_id TEXT NOT NULL,
                fill_level REAL NOT NULL,
                timestamp DATETIME DEFAULT CURRENT_TIMESTAMP
            )
            """)

            cursor.execute("""
            CREATE TABLE bin_events (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                bin_id TEXT NOT NULL,
                event_type TEXT NOT NULL,
                details TEXT,
                timestamp DATETIME DEFAULT CURRENT_TIMESTAMP
            )
            """)

            cursor.execute("""
            CREATE TABLE bin_alarms (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                bin_id TEXT NOT NULL,
                alarm_type TEXT NOT NULL,
                message TEXT NOT NULL,
                acknowledged BOOLEAN DEFAULT FALSE,
                timestamp DATETIME DEFAULT CURRENT_TIMESTAMP
            )
            """)

            # Create indexes
            cursor.execute(
                "CREATE INDEX IF NOT EXISTS idx_readings_bin_id ON bin_readings(bin_id)"
            )
            cursor.execute(
                "CREATE INDEX IF NOT EXISTS idx_events_bin_id ON bin_events(bin_id)"
            )
            cursor.execute(
                "CREATE INDEX IF NOT EXISTS idx_alarms_bin_id ON bin_alarms(bin_id)"
            )

            conn.commit()
            logger.info(f"Database initialized at {db_path}")

    except sqlite3.Error as e:
        logger.error(f"Database error during initialization: {e}")
        raise
    except Exception as e:
        logger.error(f"Error initializing database: {e}")
        raise


class DataManager:
    """Manages data collection, storage, and alarm generation"""

    def __init__(self, db_path: str = "bin_data.db"):
        """Initialize the data manager"""
        self.db_path = db_path
        self.client: Optional[mqtt.Client] = None
        self.connected = False

        # Initialize database
        if not os.path.exists(self.db_path):
            logger.info("Creating new database...")
            init_database(self.db_path)
        else:
            logger.info("Using existing database")
            # Verify tables exist
            try:
                with sqlite3.connect(self.db_path) as conn:
                    cursor = conn.cursor()
                    cursor.execute("SELECT name FROM sqlite_master WHERE type='table'")
                    tables = {row[0] for row in cursor.fetchall()}
                    required_tables = {"bin_readings", "bin_events", "bin_alarms"}
                    if not required_tables.issubset(tables):
                        logger.warning(
                            "Missing required tables, reinitializing database..."
                        )
                        init_database(self.db_path)
            except sqlite3.Error as e:
                logger.error(f"Error verifying database tables: {e}")
                logger.info("Reinitializing database...")
                init_database(self.db_path)

        # Set up MQTT connection
        self._setup_mqtt()

    def _setup_mqtt(self) -> None:
        """Set up MQTT client and connection"""
        try:
            # Create client
            client_id = f"data_manager_{datetime.now().strftime('%Y%m%d_%H%M%S')}"
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
            raise

    def _on_connect(self, client, userdata, flags, rc: int) -> None:
        """Handle connection to MQTT broker"""
        if rc == 0:
            self.connected = True
            # Subscribe to all bin topics
            self.client.subscribe(f"{BASE_TOPIC}+/fill_level")
            self.client.subscribe(f"{BASE_TOPIC}+/status")
            self.client.subscribe(f"{BASE_TOPIC}+/actuator_state")
            self.client.subscribe(ALARM_TOPIC)
            logger.info("Connected to MQTT broker")
        else:
            logger.error(f"Connection failed with code {rc}")

    def _on_disconnect(self, client, userdata, rc: int) -> None:
        """Handle disconnection from MQTT broker"""
        self.connected = False
        logger.warning(f"Disconnected from broker with code {rc}")

    def _on_message(self, client, userdata, msg) -> None:
        """Handle incoming MQTT messages"""
        try:
            # Ignore messages from non-bin topics
            if not msg.topic.startswith(BASE_TOPIC) and msg.topic != ALARM_TOPIC:
                logger.debug(f"Ignoring message from unrelated topic: {msg.topic}")
                return

            # Extract bin_id from topic
            topic_parts = msg.topic.split("/")
            if len(topic_parts) < 3:
                return

            bin_id = topic_parts[-2]
            data_type = topic_parts[-1]
            payload = msg.payload.decode()

            # Handle different types of data
            if data_type == "fill_level":
                try:
                    fill_level = float(payload)
                    self._handle_fill_level(bin_id, fill_level)
                except ValueError:
                    logger.error(f"Invalid fill level value: {payload}")
            elif data_type == "status":
                self._handle_status(bin_id, payload)
            elif data_type == "actuator_state":
                self._handle_actuator_state(bin_id, payload)

        except Exception as e:
            logger.error(f"Error processing message: {e}")

    def _handle_fill_level(self, bin_id: str, fill_level: float) -> None:
        """Handle fill level readings"""
        try:
            # Store reading in database
            with sqlite3.connect(self.db_path) as conn:
                cursor = conn.cursor()
                cursor.execute(
                    "INSERT INTO bin_readings (bin_id, fill_level) VALUES (?, ?)",
                    (bin_id, fill_level),
                )
                conn.commit()

            # Check for alarms
            if fill_level >= BIN_FILL_LEVEL_THRESHOLD:
                self._create_alarm(
                    bin_id, "HIGH_FILL", f"Bin {bin_id} is {fill_level:.1f}% full"
                )

        except sqlite3.Error as e:
            logger.error(f"Database error storing fill level: {e}")

    def _handle_status(self, bin_id: str, status: str) -> None:
        """Handle bin status updates"""
        try:
            with sqlite3.connect(self.db_path) as conn:
                cursor = conn.cursor()
                cursor.execute(
                    "INSERT INTO bin_events (bin_id, event_type, details) VALUES (?, 'STATUS_CHANGE', ?)",
                    (bin_id, status),
                )
                conn.commit()

        except sqlite3.Error as e:
            logger.error(f"Database error storing status: {e}")

    def _handle_actuator_state(self, bin_id: str, state: str) -> None:
        """Handle actuator state changes"""
        try:
            with sqlite3.connect(self.db_path) as conn:
                cursor = conn.cursor()
                cursor.execute(
                    "INSERT INTO bin_events (bin_id, event_type, details) VALUES (?, 'ACTUATOR_STATE', ?)",
                    (bin_id, state),
                )
                conn.commit()

            # Create alarm if actuator reports error
            if state == "ERROR":
                self._create_alarm(
                    bin_id, "ACTUATOR_ERROR", f"Bin {bin_id} actuator reported an error"
                )

        except sqlite3.Error as e:
            logger.error(f"Database error storing actuator state: {e}")

    def _create_alarm(self, bin_id: str, alarm_type: str, message: str) -> None:
        """Create and publish an alarm"""
        try:
            # Store alarm in database
            with sqlite3.connect(self.db_path) as conn:
                cursor = conn.cursor()
                cursor.execute(
                    "INSERT INTO bin_alarms (bin_id, alarm_type, message) VALUES (?, ?, ?)",
                    (bin_id, alarm_type, message),
                )
                conn.commit()

            # Publish alarm to MQTT
            alarm_data = {
                "bin_id": bin_id,
                "type": alarm_type,
                "message": message,
                "timestamp": datetime.now().isoformat(),
            }
            self.client.publish(ALARM_TOPIC, json.dumps(alarm_data))
            logger.warning(f"Alarm created: {message}")

        except Exception as e:
            logger.error(f"Error creating alarm: {e}")

    def get_bin_data(self, bin_id: str, limit: int = 100) -> list:
        """Get recent data for a specific bin"""
        try:
            with sqlite3.connect(self.db_path) as conn:
                cursor = conn.cursor()
                cursor.execute(
                    """
                    SELECT fill_level, timestamp 
                    FROM bin_readings 
                    WHERE bin_id = ? 
                    ORDER BY timestamp DESC 
                    LIMIT ?
                    """,
                    (bin_id, limit),
                )
                return cursor.fetchall()
        except sqlite3.Error as e:
            logger.error(f"Error fetching bin data: {e}")
            return []

    def get_active_alarms(self) -> list:
        """Get all unacknowledged alarms"""
        try:
            with sqlite3.connect(self.db_path) as conn:
                cursor = conn.cursor()
                cursor.execute(
                    """
                    SELECT bin_id, alarm_type, message, timestamp 
                    FROM bin_alarms 
                    WHERE acknowledged = FALSE 
                    ORDER BY timestamp DESC
                    """
                )
                return cursor.fetchall()
        except sqlite3.Error as e:
            logger.error(f"Error fetching alarms: {e}")
            return []

    def acknowledge_alarm(self, alarm_id: int) -> None:
        """Mark an alarm as acknowledged"""
        try:
            with sqlite3.connect(self.db_path) as conn:
                cursor = conn.cursor()
                cursor.execute(
                    "UPDATE bin_alarms SET acknowledged = TRUE WHERE id = ?",
                    (alarm_id,),
                )
                conn.commit()
        except sqlite3.Error as e:
            logger.error(f"Error acknowledging alarm: {e}")

    def stop(self) -> None:
        """Stop the data manager"""
        if self.client:
            self.client.loop_stop()
            self.client.disconnect()
        logger.info("Data manager stopped")

    def setup_database(self) -> None:
        """Set up SQLite database and tables"""
        try:
            with sqlite3.connect(self.db_path) as conn:
                cursor = conn.cursor()

                # Create tables
                cursor.execute("""
                CREATE TABLE IF NOT EXISTS bin_readings (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    bin_id TEXT NOT NULL,
                    fill_level REAL NOT NULL,
                    timestamp DATETIME DEFAULT CURRENT_TIMESTAMP
                )
                """)

                cursor.execute("""
                CREATE TABLE IF NOT EXISTS bin_events (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    bin_id TEXT NOT NULL,
                    event_type TEXT NOT NULL,
                    details TEXT,
                    timestamp DATETIME DEFAULT CURRENT_TIMESTAMP
                )
                """)

                cursor.execute("""
                CREATE TABLE IF NOT EXISTS bin_alarms (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    bin_id TEXT NOT NULL,
                    alarm_type TEXT NOT NULL,
                    message TEXT NOT NULL,
                    acknowledged BOOLEAN DEFAULT FALSE,
                    timestamp DATETIME DEFAULT CURRENT_TIMESTAMP
                )
                """)

                # Verify tables were created
                cursor.execute("SELECT name FROM sqlite_master WHERE type='table'")
                tables = cursor.fetchall()
                logger.info(
                    f"Database tables created: {[table[0] for table in tables]}"
                )

                conn.commit()
                logger.info("Database setup complete")

        except sqlite3.Error as e:
            logger.error(f"Database error: {e}")
            raise


def main():
    """Main entry point"""
    try:
        manager = DataManager()
        # Keep the main thread running
        while True:
            try:
                threading.Event().wait()
            except KeyboardInterrupt:
                logger.info("Shutting down...")
                manager.stop()
                break
    except Exception as e:
        logger.critical(f"Fatal error: {e}")
        raise


if __name__ == "__main__":
    main()
