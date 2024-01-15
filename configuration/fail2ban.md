# fail2ban

## Installation

> <https://github.com/fail2ban/fail2ban/wiki/How-to-install-fail2ban-packages>

1. `sudo apt update && sudo apt upgrade -y && sudo apt install fail2ban`

## Configuration

1. Change backend: `sudo vim /etc/fail2ban/jail.conf`

   ```text
    [DEFAULT]
    backend = systemd
    ```

1. Copy jail config to create custom:

   ```bash
   cd /etc/fail2ban
   sudo cp jail.conf jail.local
   ```

1. My preferred settings: `sudo vim jail.local`

   ```text
   ignoreip = 192.168.0.0/16
   findtime  = 24h
   maxretry = 3
   bantime  = 1h
   bantime.increment = true
   bantime.factor = 4
   bantime.maxtime = 4w
   bantime.rndtime = 1h
   ```

1. `sudo systemctl restart fail2ban`

## Check status

* `sudo fail2ban-client status sshd`
