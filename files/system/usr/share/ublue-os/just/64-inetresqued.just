# Enable the inetresqued VPN proxy daemon
[group('vpn')]
inetresqued-enable:
    #!/usr/bin/env bash
    set -euo pipefail
    sudo systemctl enable --now inetresqued.service
    echo "inetresqued is enabled and running."

# Disable the inetresqued VPN proxy daemon
[group('vpn')]
inetresqued-disable:
    #!/usr/bin/env bash
    set -euo pipefail
    sudo systemctl disable --now inetresqued.service
    echo "inetresqued is disabled."

# Show inetresqued service status
[group('vpn')]
inetresqued-status:
    systemctl status inetresqued.service --no-pager

# Follow inetresqued logs
[group('vpn')]
inetresqued-logs:
    journalctl -u inetresqued.service -f
