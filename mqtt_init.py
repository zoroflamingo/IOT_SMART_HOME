"""
MQTT Configuration Module
Handles all MQTT broker connection settings and common variables
"""

import socket
import logging
from typing import List, Tuple
from enum import Enum

# Configure logging
logging.basicConfig(
    level=logging.INFO, format="%(asctime)s - %(name)s - %(levelname)s - %(message)s"
)
logger = logging.getLogger("MQTT_Init")

# Broker Configuration
BROKER_CONFIGS: List[Tuple[str, str]] = [
    ("vmm1.saaintertrade.com", "80"),  # HIT broker
    ("test.mosquitto.org", "1883"),  # Mosquitto test broker
]

# Select broker (0 for HIT, 1 for Mosquitto)
SELECTED_BROKER: int = 1

# Resolve broker IP and get configuration
try:
    broker_hostname = BROKER_CONFIGS[SELECTED_BROKER][0]
    logger.info(f"Resolving hostname: {broker_hostname}")
    broker_ip: str = str(socket.gethostbyname(broker_hostname))
    port: str = BROKER_CONFIGS[SELECTED_BROKER][1]
    logger.info(f"Successfully resolved {broker_hostname} to {broker_ip}")
except (socket.gaierror, IndexError) as e:
    logger.error(f"Error resolving broker address: {e}")
    # Fallback to direct hostname
    broker_ip = BROKER_CONFIGS[SELECTED_BROKER][0]  # Use hostname directly
    port = BROKER_CONFIGS[SELECTED_BROKER][1]
    logger.warning(f"Using direct hostname: {broker_ip}:{port}")

# Authentication settings
username: str = "MATZI" if SELECTED_BROKER == 0 else ""
password: str = "MATZI" if SELECTED_BROKER == 0 else ""

# Topic Configuration
BASE_TOPIC: str = "municipal/bins/"
ALARM_TOPIC: str = f"{BASE_TOPIC}alarm"

# Connection settings
CONN_TIME: int = 0  # 0 for endless loop
MANAGER_UPDATE_INTERVAL: int = 10  # seconds

# Threshold settings
BIN_FILL_LEVEL_THRESHOLD: float = 80.0  # Percentage
BIN_EMPTY_THRESHOLD: float = 5.0  # Percentage


# Status Messages
class BinStatus(Enum):
    NEEDS_EMPTYING = "⚠️ Needs Emptying"
    RECENTLY_EMPTIED = "✅ Recently Emptied"
    NORMAL = "🟢 Normal"


# Export all settings
__all__ = [
    "broker_ip",
    "port",
    "username",
    "password",
    "BASE_TOPIC",
    "ALARM_TOPIC",
    "CONN_TIME",
    "MANAGER_UPDATE_INTERVAL",
    "BIN_FILL_LEVEL_THRESHOLD",
    "BIN_EMPTY_THRESHOLD",
    "BinStatus",
]
