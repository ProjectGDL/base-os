#!/usr/bin/env bash
set -oue pipefail

# Force the Breeze GTK theme on the Bazzite first-run portal (yafti) window.
python3 - <<'EOF'
path = "/usr/bin/yafti_gtk.py"
with open(path) as f:
    content = f.read()

anchor = "    Gtk.init()\n"
patch = (
    "    Gtk.init()\n"
    "    # GDL: force Breeze theme for the first-run portal\n"
    "    _settings = Gtk.Settings.get_default()\n"
    "    if _settings is not None:\n"
    "        _settings.set_property('gtk-theme-name', 'Breeze')\n"
)

if "GDL: force Breeze theme" in content:
    print("yafti_gtk.py already patched")
elif anchor in content:
    with open(path, "w") as f:
        f.write(content.replace(anchor, patch, 1))
    print("patched yafti_gtk.py: forced Breeze theme")
else:
    print("WARN: anchor not found, yafti_gtk.py unchanged", file=sys.stderr)
    exit(1)
EOF