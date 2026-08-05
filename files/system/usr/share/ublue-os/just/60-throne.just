throne_version := "1.1.6"
throne_repo := "https://github.com/ProjectGDL/gdl-sysexts/releases/download/throne-" + throne_version

# Install Throne
[group('vpn')]
throne-install:
    #!/usr/bin/env bash
    set -euo pipefail

    echo "Downloading Throne {{throne_version}}..."
    sudo mkdir -p /var/lib/extensions

    TMPDIR=$(mktemp -d)
    trap 'rm -rf "$TMPDIR"' EXIT

    curl -fsSL "{{throne_repo}}/throne-{{throne_version}}-x86_64.raw" -o "$TMPDIR/throne.raw"
    curl -fsSL "{{throne_repo}}/throne-{{throne_version}}-x86_64.raw.sha256" -o "$TMPDIR/throne.raw.sha256"

    cd "$TMPDIR"
    EXPECTED=$(cut -d' ' -f1 throne.raw.sha256)
    ACTUAL=$(sha256sum throne.raw | cut -d' ' -f1)
    if [ "$EXPECTED" != "$ACTUAL" ]; then
        echo "Error: checksums are different. Aborting."
        exit 1
    fi

    sudo mv "$TMPDIR/throne.raw" /var/lib/extensions/throne.raw
    sudo chmod 0644 /var/lib/extensions/throne.raw

    sudo systemd-sysext refresh
    sudo update-desktop-database /usr/share/applications 2>/dev/null || true
    sudo gtk-update-icon-cache /usr/share/icons/hicolor 2>/dev/null || true

    if command -v kbuildsycoca6 >/dev/null 2>&1 && [[ "$XDG_CURRENT_DESKTOP" == *"KDE"* ]]; then
        kbuildsycoca6
    fi

    echo "Throne {{throne_version}} is installed."

# Remove Throne
[group('vpn')]
throne-remove:
    #!/usr/bin/env bash
    set -euo pipefail
    if [ ! -f /var/lib/extensions/throne.raw ]; then
        echo "Throne is not installed"
        exit 0
    fi
    sudo rm /var/lib/extensions/throne.raw
    sudo systemd-sysext refresh

    if command -v kbuildsycoca6 >/dev/null 2>&1 && [[ "$XDG_CURRENT_DESKTOP" == *"KDE"* ]]; then
        kbuildsycoca6
    fi

    echo "Throne has been removed."
