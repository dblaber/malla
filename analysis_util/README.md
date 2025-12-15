# Malla Analysis Utilities

This directory contains utilities for analyzing and reporting on Meshtastic mesh network data.

## Overview

The analysis utilities provide:
- **Gateway Performance Reports**: Automated email reports analyzing gateway performance metrics
- **PostgreSQL Data Sync**: Systemd services to sync SQLite data to PostgreSQL for advanced analytics
- **Docker Compose Stack**: Complete MQTT and Malla web interface deployment

## Contents

- `report.py` - Gateway performance report generator
- `requirements.txt` - Python dependencies for report.py
- `compose.yml` - Docker Compose configuration for Malla stack
- `malla-pgloader-sync.service` - Systemd service for database synchronization
- `malla-pgloader-sync.timer` - Systemd timer to run sync every 10 minutes
- `crontab` - Example crontab entry for scheduled reports

## Gateway Performance Report (`report.py`)

### What It Does

The report script analyzes the last 24 hours of mesh network data and generates an HTML email report with gateway performance metrics:

- **RSSI** (Received Signal Strength Indicator) - Average signal strength
- **SNR** (Signal-to-Noise Ratio) - Signal quality metric
- **Coverage** - Number of unique nodes heard by each gateway
- **Volume** - Total direct packets received
- **Performance Score** - Weighted combination of all metrics (RSSI 25%, SNR 15%, Coverage 30%, Volume 30%)

The report ranks gateways by performance and highlights the top performer.

### Configuration

Edit the following sections in `report.py`:

```python
# Database configuration
DB_CONFIG = {
    "dbname": "your_database",
    "user": "your_user",
    "password": "your_password",
    "host": "your_postgres_host",
}

# Email configuration
SMTP_HOST = "smtp.gmail.com"
SMTP_PORT = 587
SMTP_USER = "your_email@gmail.com"
SMTP_PASSWORD = "your_app_password"
TO_EMAIL = "recipient@example.com"
FROM_EMAIL = "sender@example.com"
```

**Note**: For Gmail, you need to use an [App Password](https://support.google.com/accounts/answer/185833), not your regular password.

### Installation

1. Install Python dependencies:
   ```bash
   pip install -r requirements.txt
   ```

2. Configure the script with your database and email credentials (see Configuration above)

3. Test the script:
   ```bash
   python3 report.py
   ```

### Scheduling with Crontab

To run the report daily at 6:00 AM, add to your crontab:

```bash
# Edit your crontab
crontab -e

# Add this line (adjust paths as needed):
0 6 * * * /usr/bin/python3 /path/to/analysis_util/report.py >> /path/to/gateway_report.log 2>&1
```

The example `crontab` file shows the format. To install it:

```bash
# Review the crontab file and update paths
cat crontab

# Install it
crontab crontab
```

## PostgreSQL Data Sync (Systemd)

The systemd service and timer automatically sync the SQLite database to PostgreSQL every 10 minutes using [pgloader](https://pgloader.io/).

### Prerequisites

Install pgloader:

```bash
# Debian/Ubuntu
sudo apt install pgloader

# Fedora/RHEL
sudo dnf install pgloader

# Arch Linux
sudo pacman -s pgloader
```

### Configuration

Edit `malla-pgloader-sync.service` to match your setup:

```ini
ExecStart=/usr/bin/pgloader \
  sqlite:///var/lib/docker/volumes/mosquitto_malla_data/_data/meshtastic_history.db \
  postgresql://user:password@host/database
```

Update the paths and PostgreSQL connection string for your environment.

### Installation

1. Copy systemd files to the system directory:
   ```bash
   sudo cp malla-pgloader-sync.service /etc/systemd/system/
   sudo cp malla-pgloader-sync.timer /etc/systemd/system/
   ```

2. Reload systemd to recognize the new files:
   ```bash
   sudo systemctl daemon-reload
   ```

3. Enable and start the timer:
   ```bash
   sudo systemctl enable malla-pgloader-sync.timer
   sudo systemctl start malla-pgloader-sync.timer
   ```

4. Verify the timer is active:
   ```bash
   sudo systemctl status malla-pgloader-sync.timer
   ```

5. Check when the timer will run next:
   ```bash
   sudo systemctl list-timers malla-pgloader-sync.timer
   ```

### Manual Sync

To manually trigger a sync without waiting for the timer:

```bash
sudo systemctl start malla-pgloader-sync.service
```

### Monitoring

View sync logs:

```bash
# Recent logs
sudo journalctl -u malla-pgloader-sync.service -n 50

# Follow logs in real-time
sudo journalctl -u malla-pgloader-sync.service -f
```

## Docker Compose Stack

The `compose.yml` file provides a complete Malla deployment with:

- **Mosquitto MQTT Broker** - Message broker for Meshtastic data
- **Malla Web UI** - Web interface for browsing mesh network data
- **Malla Capture** - MQTT data capture service

### Configuration

Create a `.env` file in the analysis_util directory:

```bash
# MQTT Configuration
MALLA_MQTT_BROKER_ADDRESS=mosquitto
MALLA_MQTT_PORT=1883
MALLA_MQTT_USERNAME=
MALLA_MQTT_PASSWORD=
MALLA_MQTT_TOPIC_PREFIX=msh
MALLA_MQTT_TOPIC_SUFFIX=/+/+/+/#

# Meshtastic Configuration
MALLA_DEFAULT_CHANNEL_KEY=AQ==

# Web UI Configuration
MALLA_NAME=My Mesh Network
MALLA_SECRET_KEY=change-this-to-a-random-secret-key
MALLA_WEB_PORT=5008
MALLA_DEBUG=false

# Docker Image (optional, defaults to latest)
MALLA_IMAGE=ghcr.io/zenitram/malla:latest
MALLA_WEB_COMMAND=/app/.venv/bin/malla-web
```

### Running the Stack

```bash
# Start all services
docker compose up -d

# View logs
docker compose logs -f

# Stop all services
docker compose down
```

### Accessing Services

- **Malla Web UI**: http://localhost:5008
- **Mosquitto MQTT**: localhost:1883
- **Mosquitto WebSocket**: localhost:9001

### Data Persistence

The SQLite database is stored in the Docker volume `malla_data`. To backup:

```bash
docker run --rm -v malla_data:/data -v $(pwd):/backup \
  alpine tar czf /backup/malla_backup.tar.gz -C /data .
```

## Troubleshooting

### Report Script

**Email not sending:**
- Verify SMTP credentials are correct
- For Gmail, ensure you're using an App Password
- Check firewall allows outbound connections on port 587

**No data in report:**
- Verify PostgreSQL connection works
- Check that data exists in the database for the last 24 hours
- Ensure at least 50 direct packets exist for gateways

### Systemd Sync

**Sync failing:**
- Check pgloader is installed: `which pgloader`
- Verify SQLite file path exists
- Test PostgreSQL connection manually
- Check logs: `sudo journalctl -u malla-pgloader-sync.service`

**Timer not running:**
- Ensure timer is enabled: `sudo systemctl is-enabled malla-pgloader-sync.timer`
- Check timer status: `sudo systemctl list-timers`

### Docker Compose

**Services not starting:**
- Check logs: `docker compose logs`
- Verify `.env` file exists and is configured
- Ensure ports 5008, 1883, 9001 are not in use

**No data being captured:**
- Verify MQTT broker is accessible
- Check MQTT credentials are correct
- Ensure Meshtastic devices are publishing to the broker
- Review malla-capture logs: `docker compose logs malla-capture`

## Additional Resources

- [Malla Main Repository](https://github.com/zenitraM/malla)
- [pgloader Documentation](https://pgloader.readthedocs.io/)
- [Meshtastic Documentation](https://meshtastic.org/)
- [Docker Compose Documentation](https://docs.docker.com/compose/)
