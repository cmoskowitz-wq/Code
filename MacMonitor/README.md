# Mosko Meter v7.0 - Professional System Monitor

A comprehensive, real-time system monitoring application for macOS with a modern dark theme interface.

![Mosko Meter](https://img.shields.io/badge/version-7.0-blue)
![Python](https://img.shields.io/badge/python-3.8+-green)
![PyQt6](https://img.shields.io/badge/PyQt6-6.4+-orange)
![License](https://img.shields.io/badge/license-Proprietary-red)

## 📊 Features

### Real-Time Monitoring
- **CPU Usage**: Live CPU percentage with trend analysis
- **Memory Usage**: RAM utilization with detailed statistics
- **System Load Average**: 1-minute load average for system stress monitoring
- **Network Throughput**: Real-time KB/s monitoring with auto-scaling
- **Network Latency**: Ping-based latency measurement to 8.8.8.8
- **Disk I/O**: Separate read/write speed monitoring in MB/s

### Advanced Process Management
- Complete process list with PID, name, CPU, and memory usage
- Real-time search and filtering
- Safe process termination with confirmation dialogs
- Top 10 processes by memory usage display

### System Information
- Comprehensive OS and hardware details
- Disk usage analysis for all mounted partitions
- System uptime and resource statistics
- Configurable alert thresholds

### Professional Features
- **Modern Dark Theme**: Professional UI with custom styling
- **Smooth Animations**: High-performance charts with real-time updates
- **Data Export**: CSV export with timestamp and all metrics
- **Keyboard Shortcuts**: Full keyboard navigation support
- **Statistics Tracking**: Min/Max/Average values for all metrics
- **Auto-scaling Charts**: Dynamic Y-axis adjustment based on data

## 🚀 Installation

### Prerequisites
- macOS 10.15 or later
- Python 3.8 or higher

### Quick Start
```bash
# Clone or download the repository
cd /path/to/MoskoMeter

# Create virtual environment
python3 -m venv venv
source venv/bin/activate

# Install dependencies
pip install -r requirements.txt

# Run the application
python main.py
```

### Standalone Application (Optional)
```bash
# Install PyInstaller
pip install pyinstaller

# Create standalone executable
pyinstaller --onefile --windowed --name="Mosko Meter" main.py

# Run the executable
./dist/Mosko\ Meter
```

## 🎯 Usage

### Interface Overview
- **Monitoring Tab**: 6 real-time charts in a 3x2 grid layout
- **Processes Tab**: Process management with search and kill capabilities
- **System Tab**: System information, disk usage, and export options

### Keyboard Shortcuts
- `Ctrl+Space`: Pause/Resume monitoring
- `Ctrl+Q`: Exit application
- `Ctrl+E`: Export data to CSV
- `Tab`: Navigate between tabs

### Menu Options
- **File**: Export data, Exit
- **View**: Refresh data
- **Help**: Keyboard shortcuts, About

## 📈 Chart Details

### Color Scheme
- **Data Lines**: Red (#ff0000) - Current values
- **Trend Lines**: Orange (#666666) - Moving averages
- **Current Markers**: Green (#00ff00) - Latest values
- **Text Labels**: Green/Yellow - Centered value displays

### Metrics Explained
- **CPU**: Percentage of CPU utilization across all cores
- **Memory**: RAM usage as percentage of total memory
- **Load Average**: 1-minute system load average (processes in queue)
- **Network**: Combined send/receive throughput in KB/s
- **Latency**: Round-trip time to Google DNS (8.8.8.8) in ms
- **Disk I/O**: Read and write speeds in MB/s

## 🔧 Configuration

### Alert Thresholds
Configure CPU and memory alert thresholds in the System tab:
- CPU Alert: Default 80%
- Memory Alert: Default 85%

### Network Settings
- Ping Host: 8.8.8.8 (configurable in source code)
- Update Interval: 1 second for metrics, 2 seconds for processes

## 📊 Data Export

Export all performance metrics to CSV format:
1. Go to System tab
2. Click "Export Data" button
3. Choose save location
4. CSV includes timestamp and all collected metrics

## 🛠️ Development

### Project Structure
```
Mosko Meter/
├── main.py              # Main application
├── requirements.txt     # Python dependencies
├── README.md           # This file
└── venv/               # Virtual environment (created)
```

### Dependencies
- **PyQt6**: Modern GUI framework
- **pyqtgraph**: High-performance plotting
- **psutil**: System and process monitoring
- **PyInstaller**: Standalone executable creation

### Building from Source
```bash
# Install development dependencies
pip install -r requirements.txt

# Run with logging
python main.py 2>&1 | tee mosko_meter.log
```

## 📞 Support

For questions, support, or feature requests:
**Chris Moskowitz** - cmoskowitz@gmail.com

## 📄 License

All rights reserved 2026 copyright, Chris Moskowitz /cmoskowitz@gmail.com

This software is proprietary and may not be redistributed or modified without explicit permission from the author.

## 🔄 Version History

### v7.0 (Current)
- Complete system monitoring suite
- Modern dark theme interface
- Process management capabilities
- CSV export functionality
- Professional UI/UX

### v6.0
- Modern theme implementation
- Enhanced chart visualizations
- Menu system and shortcuts

### v5.0
- Process manager with kill functionality
- Improved error handling

### v4.0
- Multi-chart layout
- Auto-scaling and statistics
- Smooth animations

### v3.0
- Moving averages and trends
- Enhanced visualizations

### v2.0
- Green value labels
- Red chart lines
- Improved UI

### v1.0
- Basic CPU, memory, network, latency monitoring

## ⚠️ System Requirements

- **OS**: macOS 10.15+
- **Python**: 3.8+
- **RAM**: 256MB minimum
- **Storage**: 50MB for installation
- **Permissions**: Standard user permissions (no admin required)

## 🐛 Troubleshooting

### Common Issues

**Application won't start:**
- Ensure Python 3.8+ is installed
- Check virtual environment activation
- Verify all dependencies are installed

**Charts not updating:**
- Check system permissions for psutil
- Ensure no firewall blocking ping
- Try refreshing with View → Refresh Now

**Process kill fails:**
- Some system processes require admin privileges
- Check process ownership and permissions

**High CPU usage:**
- Reduce update frequency in source code
- Close other monitoring applications
- Check for background processes

### Performance Tips
- Close unnecessary applications while monitoring
- Use pause feature (Ctrl+Space) when not actively monitoring
- Export data periodically to free memory

---

**Mosko Meter v7.0** - Professional System Monitoring for macOS
All rights reserved 2026 copyright, Chris Moskowitz /cmoskowitz@gmail.com