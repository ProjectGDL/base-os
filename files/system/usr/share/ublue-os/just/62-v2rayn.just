v2rayn_version := "7.24.5"
v2rayn_repo := "https://github.com/ProjectGDL/gdl-sysexts/releases/download/v2rayn-" + v2rayn_version

# Install v2rayN
[group('vpn')]
v2rayn-install:
    #!/usr/bin/env bash
    set -euo pipefail

    echo "Downloading v2rayN {{v2rayn_version}}..."
    sudo mkdir -p /var/lib/extensions

    TMPDIR=$(mktemp -d)
    trap 'rm -rf "$TMPDIR"' EXIT

    curl -fsSL "{{v2rayn_repo}}/v2rayN-{{v2rayn_version}}-x86_64.raw" -o "$TMPDIR/v2rayn.raw"
    curl -fsSL "{{v2rayn_repo}}/v2rayN-{{v2rayn_version}}-x86_64.raw.sha256" -o "$TMPDIR/v2rayn.raw.sha256"

    cd "$TMPDIR"
    EXPECTED=$(cut -d' ' -f1 v2rayn.raw.sha256)
    ACTUAL=$(sha256sum v2rayn.raw | cut -d' ' -f1)
    if [ "$EXPECTED" != "$ACTUAL" ]; then
        echo "Error: checksums are different. Aborting."
        exit 1
    fi

    sudo mv "$TMPDIR/v2rayn.raw" /var/lib/extensions/v2rayn.raw
    sudo chmod 0644 /var/lib/extensions/v2rayn.raw

    sudo systemd-sysext refresh
    sudo update-desktop-database /usr/share/applications 2>/dev/null || true
    sudo gtk-update-icon-cache /usr/share/icons/hicolor 2>/dev/null || true

    if command -v kbuildsycoca6 >/dev/null 2>&1 && [[ "$XDG_CURRENT_DESKTOP" == *"KDE"* ]]; then
        kbuildsycoca6
    fi

    echo "v2rayN {{v2rayn_version}} is installed."

# Remove v2rayN
[group('vpn')]
v2rayn-remove:
    #!/usr/bin/env bash
    set -euo pipefail
    if [ ! -f /var/lib/extensions/v2rayn.raw ]; then
        echo "v2rayN is not installed"
        exit 0
    fi
    sudo rm /var/lib/extensions/v2rayn.raw
    sudo systemd-sysext refresh

    if command -v kbuildsycoca6 >/dev/null 2>&1 && [[ "$XDG_CURRENT_DESKTOP" == *"KDE"* ]]; then
        kbuildsycoca6
    fi

    echo "v2rayN has been removed."
