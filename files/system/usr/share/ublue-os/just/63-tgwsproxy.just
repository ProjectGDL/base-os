tgwsproxy_version := "1.9.1"
tgwsproxy_repo := "https://github.com/ProjectGDL/gdl-sysexts/releases/download/tgwsproxy-" + tgwsproxy_version

# Install tgwsproxy
[group('vpn')]
tgwsproxy-install:
    #!/usr/bin/env bash
    set -euo pipefail

    echo "Downloading tgwsproxy {{tgwsproxy_version}}..."
    sudo mkdir -p /var/lib/extensions

    TMPDIR=$(mktemp -d)
    trap 'rm -rf "$TMPDIR"' EXIT

    curl -fsSL "{{tgwsproxy_repo}}/tgwsproxy-{{tgwsproxy_version}}-x86_64.raw" -o "$TMPDIR/tgwsproxy.raw"
    curl -fsSL "{{tgwsproxy_repo}}/tgwsproxy-{{tgwsproxy_version}}-x86_64.raw.sha256" -o "$TMPDIR/tgwsproxy.raw.sha256"

    cd "$TMPDIR"
    EXPECTED=$(cut -d' ' -f1 tgwsproxy.raw.sha256)
    ACTUAL=$(sha256sum tgwsproxy.raw | cut -d' ' -f1)
    if [ "$EXPECTED" != "$ACTUAL" ]; then
        echo "Error: checksums are different. Aborting."
        exit 1
    fi

    sudo mv "$TMPDIR/tgwsproxy.raw" /var/lib/extensions/tgwsproxy.raw
    sudo chmod 0644 /var/lib/extensions/tgwsproxy.raw

    sudo systemd-sysext refresh
    sudo update-desktop-database /usr/share/applications 2>/dev/null || true
    sudo gtk-update-icon-cache /usr/share/icons/hicolor 2>/dev/null || true

    if command -v kbuildsycoca6 >/dev/null 2>&1 && [[ "$XDG_CURRENT_DESKTOP" == *"KDE"* ]]; then
        kbuildsycoca6
    fi

    echo "tgwsproxy {{tgwsproxy_version}} is installed."

# Remove tgwsproxy
[group('vpn')]
tgwsproxy-remove:
    #!/usr/bin/env bash
    set -euo pipefail
    if [ ! -f /var/lib/extensions/tgwsproxy.raw ]; then
        echo "tgwsproxy is not installed"
        exit 0
    fi
    sudo rm /var/lib/extensions/tgwsproxy.raw
    sudo systemd-sysext refresh

    if command -v kbuildsycoca6 >/dev/null 2>&1 && [[ "$XDG_CURRENT_DESKTOP" == *"KDE"* ]]; then
        kbuildsycoca6
    fi

    echo "tgwsproxy has been removed."
