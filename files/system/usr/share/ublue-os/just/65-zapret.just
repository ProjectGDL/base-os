zapret_version := "0.1.0"
zapret_repo := "https://github.com/ProjectGDL/gdl-sysexts/releases/download/gdl-zapret-gui-" + zapret_version

# Install gdl-zapret-gui
[group('vpn')]
zapret-install:
    #!/usr/bin/env bash
    set -euo pipefail

    echo "Downloading gdl-zapret-gui {{zapret_version}}..."
    sudo mkdir -p /var/lib/extensions

    TMPDIR=$(mktemp -d)
    trap 'rm -rf "$TMPDIR"' EXIT

    curl -fsSL "{{zapret_repo}}/gdl-zapret-gui-{{zapret_version}}-x86_64.raw" -o "$TMPDIR/zapret.raw"
    curl -fsSL "{{zapret_repo}}/gdl-zapret-gui-{{zapret_version}}-x86_64.raw.sha256" -o "$TMPDIR/zapret.raw.sha256"

    cd "$TMPDIR"
    EXPECTED=$(cut -d' ' -f1 zapret.raw.sha256)
    ACTUAL=$(sha256sum zapret.raw | cut -d' ' -f1)
    if [ "$EXPECTED" != "$ACTUAL" ]; then
        echo "Error: checksums are different. Aborting."
        exit 1
    fi

    sudo mv "$TMPDIR/zapret.raw" /var/lib/extensions/zapret.raw
    sudo chmod 0644 /var/lib/extensions/zapret.raw

    sudo systemd-sysext refresh
    sudo update-desktop-database /usr/share/applications 2>/dev/null || true
    sudo gtk-update-icon-cache /usr/share/icons/hicolor 2>/dev/null || true

    if command -v kbuildsycoca6 >/dev/null 2>&1 && [[ "$XDG_CURRENT_DESKTOP" == *"KDE"* ]]; then
        kbuildsycoca6
    fi

    echo "gdl-zapret-gui {{zapret_version}} is installed."

# Remove gdl-zapret-gui
[group('vpn')]
zapret-remove:
    #!/usr/bin/env bash
    set -euo pipefail
    if [ ! -f /var/lib/extensions/zapret.raw ]; then
        echo "gdl-zapret-gui is not installed"
        exit 0
    fi
    sudo rm /var/lib/extensions/zapret.raw
    sudo systemd-sysext refresh

    if command -v kbuildsycoca6 >/dev/null 2>&1 && [[ "$XDG_CURRENT_DESKTOP" == *"KDE"* ]]; then
        kbuildsycoca6
    fi

    echo "gdl-zapret-gui has been removed."
