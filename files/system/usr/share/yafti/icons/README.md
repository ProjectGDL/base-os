# Yafti action icons

Place **symbolic monochrome PNG** files here (white glyph + alpha mask). Names match `icon:` in `../yafti.yml`.

`yafti_gtk.py` recolors monochrome assets at runtime for light (near-black) and dark (near-white)
Breeze. Keep icons white-on-transparent so both themes work.

Iconify SVGs with `currentColor` / `1em` often fail under GTK `set_from_file` — rasterize to PNG.

Lookup order in `yafti_gtk.py`:

1. Absolute path in `icon:`
2. `<dir of yafti.yml>/icons/<icon>.svg` (local debug / repo tree)
3. `/usr/share/yafti/icons/<icon>.svg` (system install; also `.png`, `.svgz`, …)
4. Theme icon name (Breeze / hicolor), e.g. `network-wired`

Debug from the repo:

```bash
python3 files/system/usr/bin/yafti_gtk.py files/system/usr/share/yafti/yafti.yml
# icons are loaded from files/system/usr/share/yafti/icons/
```

## Required files (custom / branded)

Stem must match `icon:` in `yafti.yml` (`.svg` preferred; `.png` also works).

| file | used by | source (→ symbolic PNG) |
|------|---------|--------------------------|
| `telegram.png` | Telegram community | `simple-icons:telegram` |
| `project-gdl.png` | Base OS / org branding | `mdi:rocket-launch-outline` |
| `github.png` | GitHub | `simple-icons:github` |
| `android.png` | Android Platform Tools | `simple-icons:android` |
| `antigravity.png` | Antigravity IDE | `bxl:google-antigravity` |
| `asus-rog.png` | asusctl / ROG | `simple-icons:asus` |
| `dosbox.png` | Boxtron | `mdi:application-brackets-outline` |
| `coolercontrol.png` | CoolerControl | upstream icon.svg |
| `davinci-resolve.png` | DaVinci Resolve | `simple-icons:davinciresolve` |
| `decky.png` | Decky Loader | `simple-icons:steamdeck` |
| `decky-plugin.png` | Decky plugins | `mdi:puzzle-outline` |
| `lossless-scaling.png` | Lossless Scaling / lsfg-vk | `mdi:arrow-expand-all` |
| `optiscaler.png` | OptiScaler / framegen | `mdi:quality-high` |
| `emudeck.png` | EmuDeck | `mdi:gamepad-variant-outline` |
| `jetbrains-toolbox.png` | JetBrains Toolbox | `simple-icons:jetbrains` |
| `lm-studio.png` | LM Studio | `simple-icons:lmstudio` |
| `openrazer.png` | OpenRazer | `simple-icons:razer` |
| `openrgb.png` | OpenRGB | `mdi:led-strip-variant` |
| `opentabletdriver.png` | OpenTabletDriver | `mdi:tablet-dashboard` |
| `resilio-sync.png` | Resilio Sync | `selfhst:resilio-sync` |
| `steam.png` | SteamCMD / reset Steam | `simple-icons:steam` |
| `sunshine.png` | Sunshine | upstream sunshine.svg |
| `visual-studio-code.png` | VS Code | `simple-icons:visualstudiocode` |
| `vscodium.png` | VSCodium | `simple-icons:vscodium` |
| `waydroid.png` | Waydroid | `simple-icons:android` |
| `branch-stable.png` | stable track | `mdi:source-branch` |
| `branch-testing.png` | testing track | `mdi:source-branch-plus` |
| `tailscale.png` | Tailscale | `simple-icons:tailscale` |
| `cockpit.png` | Cockpit | `simple-icons:cockpit` |
| `distributor-logo-windows.png` | Boot to Windows | `mdi:microsoft-windows` |
| `nvidia-dlss.png` | global DLSS | `simple-icons:nvidia` |
| `amd-fsr.png` | global FSR | `simple-icons:amd` |
| `throne-vpn.png` | Throne VPN | `mdi:shield-lock-outline` |
| `wine.png` | Proton hang fix | `simple-icons:wine` |
| `bazzite-cli.png` | Bazzite CLI | ublue `distributor-logo-white.svg` |
| `throne-vpn.png` | Throne VPN | upstream `Throne.icns` → mono |
| theme names (Breeze → mono PNG) | Manage / Tweak / Troubleshoot | e.g. `system-software-update`, `network-wired`, `input-gaming`, … |

## Theme names already used in yafti.yml (no file required on Breeze)

`utilities-terminal`, `tools-report-bug`, `system-software-update`, `edit-clear`,
`process-stop`, `security-high`, `network-wired`, `network-wireless`, `network-server`,
`network-bluetooth`, `video-television`, `video-display`, `desktop`, `dialog-password`,
`dialog-warning`, `audio-card`, `audio-headphones`, `audio-volume-high`, `drive-harddisk`,
`drive-removable-media`, `media-floppy`, `input-gaming`, `input-keyboard`,
`applications-games`, `utilities-system-monitor`, `system-reboot`, `system-shutdown`,
`text-x-log`, `edit-undo`, `preferences-system`, `chronometer`, `computer`

## Iconify tip

```bash
# example: fetch one icon
curl -fsSL "https://api.iconify.design/simple-icons/telegram.svg" -o telegram.svg
```

- Simple Icons: `simple-icons:telegram`, `github`, `android`, `steam`, `visualstudiocode`, `tailscale`, …
- MDI fallbacks: `mdi:puzzle-outline`, `mdi:arrow-expand-all`, `mdi:source-branch`
