## Installation

### udev
Copy the [root hub](udev/5-root-hub.rules) and [linak-cbd6s](udev/10-linak-cbd6s.rules) udev rules files into `/etc/udev/rules.d/` and apply them by either rebooting, or running:
```sh
sudo udevadm control --reload-rules && sudo udevadm trigger
```

### systemd
Copy the [service file](systemd/linak-mqtt.service) into `/etc/systemd/system/` and enable it with:
```sh
sudo systemctl enable linak-mqtt.service
```

TODO:

Periodic reporting of height
Report net desk height