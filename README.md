# IoT Smart Bin Monitoring System

A comprehensive IoT-based waste management system that monitors bin fill levels, manages bin status, and provides real-time alerts.

## Features

- Real-time bin fill level monitoring using ultrasonic sensors
- Automated alerts for bins requiring attention
- Interactive control panel for bin management
- Automated bin emptying mechanism simulation
- SQLite database for data persistence
- MQTT-based communication system
- Modern GUI interface for monitoring multiple bins

## System Components

1. **Data Manager** (`app_manager.py`)
   - Handles MQTT communication
   - Manages database operations
   - Processes alerts and events

2. **Smart Bin System** (`SmartBinSystem.py`)
   - Integrates various emulators
   - Manages bin state and operations
   - Handles user interactions

3. **Monitor GUI** (`MonitorGUI.py`)
   - Real-time visualization of bin status
   - Alert management interface
   - System monitoring dashboard

4. **Emulators**
   - `UltrasonicSensor.py`: Simulates fill-level detection
   - `ControlPanel.py`: Provides user control interface
   - `BinActuator.py`: Simulates bin emptying mechanism

## Setup Instructions

1. Clone the repository:
   ```bash
   git clone <repository-url>
   cd IOT_SMART_HOME
   ```

2. Install dependencies:
   ```bash
   pip install -r requirements.txt
   ```

3. Run the system:
   ```bash
   # Start the data manager
   python app_manager.py
   
   # Start the bin system (in a new terminal)
   python SmartBinSystem.py
   
   # Start the monitoring GUI (in a new terminal)
   python MonitorGUI.py
   ```

## Configuration

- MQTT settings can be configured in `mqtt_init.py`
- Default thresholds and system parameters can be adjusted in respective files
- Database configuration is handled automatically

## Technical Details

- **MQTT Broker**: Uses test.mosquitto.org (port 1883)
- **Database**: SQLite3 for local storage
- **GUI Framework**: Tkinter
- **Python Version**: 3.x

## Project Structure

```
IOT_SMART_HOME/
├── app_manager.py      # Main data manager
├── SmartBinSystem.py   # System integration
├── MonitorGUI.py       # GUI interface
├── mqtt_init.py        # MQTT configuration
├── BinActuator.py      # Actuator emulator
├── UltrasonicSensor.py # Sensor emulator
├── ControlPanel.py     # Control panel emulator
└── requirements.txt    # Dependencies
```

## Contributing

Feel free to submit issues, fork the repository, and create pull requests for any improvements.

## License

This project is licensed under the MIT License - see the LICENSE file for details.