# Service Management via WebApp

The webapp now includes a service management interface in the **Advanced** tab that allows you to control the automation and XML watcher services.

## Features

- **View Service Status**: See real-time status of both services (running/stopped)
- **Start/Stop/Restart**: Control services with button clicks
- **No Terminal Required**: Manage services directly from the web interface

## Services Managed

1. **datalogger.service** - Automation service (XML processing & Unitas uploads)
2. **xml-watcher.service** - XML directory watcher

## How It Works

### Backend API

Two new endpoints in `webapp.py`:

- `GET /api/service_status` - Returns current status of both services
- `POST /api/service_control` - Executes start/stop/restart commands

### Frontend UI

Located in the **Advanced** tab (`templates/tab_advanced.html`):

- Service status display with color-coded indicators
- Control buttons for each service
- Auto-refresh on tab switch

### Security

The webapp user needs sudo permissions to control systemd services. The `install.sh` script automatically configures this by creating `/etc/sudoers.d/datalogger` with:

```
username ALL=(ALL) NOPASSWD: /usr/bin/systemctl start datalogger.service
username ALL=(ALL) NOPASSWD: /usr/bin/systemctl stop datalogger.service
username ALL=(ALL) NOPASSWD: /usr/bin/systemctl restart datalogger.service
username ALL=(ALL) NOPASSWD: /usr/bin/systemctl start xml-watcher.service
username ALL=(ALL) NOPASSWD: /usr/bin/systemctl stop xml-watcher.service
username ALL=(ALL) NOPASSWD: /usr/bin/systemctl restart xml-watcher.service
username ALL=(ALL) NOPASSWD: /usr/bin/systemctl show datalogger.service
username ALL=(ALL) NOPASSWD: /usr/bin/systemctl show xml-watcher.service
```

This is configured automatically during installation.

## Usage

1. Open the webapp in your browser
2. Navigate to the **Advanced** tab
3. View current service status
4. Click buttons to control services:
   - **Green (Start)**: Start the service
   - **Red (Stop)**: Stop the service
   - **Yellow (Restart)**: Restart the service
5. Click **Refresh Status** to update the status display

## Manual Installation (if not using install.sh)

If you need to manually set up sudo permissions:

1. Copy the sudoers template:
   ```bash
   sudo cp datalogger-sudoers /etc/sudoers.d/datalogger
   ```

2. Edit the file to replace `YOUR_USERNAME`:
   ```bash
   sudo visudo -f /etc/sudoers.d/datalogger
   ```

3. Set correct permissions:
   ```bash
   sudo chmod 0440 /etc/sudoers.d/datalogger
   ```

## Troubleshooting

**"Failed to control service" error:**
- Check that sudoers file is configured correctly
- Verify services exist: `systemctl list-units | grep datalogger`
- Check webapp logs for detailed error messages

**Status shows "Failed to load":**
- Ensure systemd is running
- Check that the webapp user can run `systemctl show`
