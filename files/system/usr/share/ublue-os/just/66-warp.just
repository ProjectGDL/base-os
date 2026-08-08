warp_version := "2026.6.880.0"
warp_repo := "https://github.com/ProjectGDL/gdl-sysexts/releases/download/warp-" + warp_version

# Install Cloudflare WARP
[group('vpn')]
warp-install:
    #!/usr/bin/env bash
    set -euo pipefail

    echo "Downloading Cloudflare WARP {{warp_version}}..."
    sudo mkdir -p /var/lib/extensions

    TMPDIR=$(mktemp -d)
    trap 'rm -rf "$TMPDIR"' EXIT

    curl -fsSL "{{warp_repo}}/warp-{{warp_version}}-x86_64.raw" -o "$TMPDIR/warp.raw"
    curl -fsSL "{{warp_repo}}/warp-{{warp_version}}-x86_64.raw.sha256" -o "$TMPDIR/warp.raw.sha256"

    cd "$TMPDIR"
    EXPECTED=$(cut -d' ' -f1 warp.raw.sha256)
    ACTUAL=$(sha256sum warp.raw | cut -d' ' -f1)
    if [ "$EXPECTED" != "$ACTUAL" ]; then
        echo "Error: checksums are different. Aborting."
        exit 1
    fi

    sudo mv "$TMPDIR/warp.raw" /var/lib/extensions/warp.raw
    sudo chmod 0644 /var/lib/extensions/warp.raw

    sudo systemd-sysext refresh
    sudo update-desktop-database /usr/share/applications 2>/dev/null || true
    sudo gtk-update-icon-cache /usr/share/icons/hicolor 2>/dev/null || true

    sudo systemctl daemon-reload
    sudo systemctl enable --now warp-svc
    systemctl --user enable --now warp-desktop-svc

    if command -v kbuildsycoca6 >/dev/null 2>&1 && [[ "$XDG_CURRENT_DESKTOP" == *"KDE"* ]]; then
        kbuildsycoca6
    fi

    echo "Cloudflare WARP {{warp_version}} is installed."

# Remove Cloudflare WARP
[group('vpn')]
warp-remove:
    #!/usr/bin/env bash
    set -euo pipefail
    if [ ! -f /var/lib/extensions/warp.raw ]; then
        echo "Cloudflare WARP is not installed"
        exit 0
    fi

    systemctl --user disable --now warp-desktop-svc 2>/dev/null || true
    sudo systemctl disable --now warp-svc

    sudo rm /var/lib/extensions/warp.raw
    sudo systemd-sysext refresh

    sudo systemctl daemon-reload

    if command -v kbuildsycoca6 >/dev/null 2>&1 && [[ "$XDG_CURRENT_DESKTOP" == *"KDE"* ]]; then
        kbuildsycoca6
    fi

    echo "Cloudflare WARP has been removed."
