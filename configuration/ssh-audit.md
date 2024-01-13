# Hardening SSH

1. Generate new ssh keys on client: `ssh-keygen -t ed25519 -f .ssh/raspberry_strong -N "" -C "adzik007@gmail.com"`
2. Remote into server
3. Paste public key into `/home/<user>/.ssh/authorized_keys` in a new line
4. Verify you can connect
5. Go to [ssh-audit](https://www.sshaudit.com/hardening_guides.html) hardening guides and run
    commands for server system
    > Note: `sudo -i` to switch to root before running commands
6. Remove the server from `known_hosts` on client: `ssh-keygen -R <hostname>`
7. Connect to te server again
