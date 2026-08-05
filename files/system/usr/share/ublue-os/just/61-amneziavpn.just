amneziavpn_version := "5.0.0.5"
amneziavpn_repo := "https://github.com/ProjectGDL/gdl-sysexts/releases/download/amneziavpn-" + amneziavpn_version

# Install AmneziaVPN
[group('vpn')]
amneziavpn-install:
    #!/usr/bin/env bash
    set -euo pipefail

    echo "Downloading AmneziaVPN {{amneziavpn_version}}..."
    sudo mkdir -p /var/lib/extensions

    TMPDIR=$(mktemp -d)
    trap 'rm -rf "$TMPDIR"' EXIT

    curl -fsSL "{{amneziavpn_repo}}/amneziavpn-{{amneziavpn_version}}-x86_64.raw" -o "$TMPDIR/amneziavpn.raw"
    curl -fsSL "{{amneziavpn_repo}}/amneziavpn-{{amneziavpn_version}}-x86_64.raw.sha256" -o "$TMPDIR/amneziavpn.raw.sha256"

    cd "$TMPDIR"
    EXPECTED=$(cut -d' ' -f1 amneziavpn.raw.sha256)
    ACTUAL=$(sha256sum amneziavpn.raw | cut -d' ' -f1)
    if [ "$EXPECTED" != "$ACTUAL" ]; then
        echo "Error: checksums are different. Aborting."
        exit 1
    fi

    sudo mv "$TMPDIR/amneziavpn.raw" /var/lib/extensions/amneziavpn.raw
    sudo chmod 0644 /var/lib/extensions/amneziavpn.raw

    sudo systemd-sysext refresh
    sudo update-desktop-database /usr/share/applications 2>/dev/null || true
    sudo gtk-update-icon-cache /usr/share/icons/hicolor 2>/dev/null || true

    echo "AmneziaVPN {{amneziavpn_version}} is installed."

# Remove AmneziaVPN
[group('vpn')]
amneziavpn-remove:
    #!/usr/bin/env bash
    set -euo pipefail
    if [ ! -f /var/lib/extensions/amneziavpn.raw ]; then
        echo "AmneziaVPN is not installed"
        exit 0
    fi
    sudo rm /var/lib/extensions/amneziavpn.raw
    sudo systemd-sysext refresh

    echo "AmneziaVPN has been removed."
