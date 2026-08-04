#!/usr/bin/python3
"""
Yafti GTK - A simple GTK GUI for running scripts from yafti.yml
"""

import subprocess
import sys
import threading

import gi
import yaml
import os
import locale

gi.require_version('Gtk', '4.0')
gi.require_version('GdkPixbuf', '2.0')
from gi.repository import GLib, Gtk, Gdk, GdkPixbuf, Pango

# Constants
APP_ID = 'io.github.ublue_os.yafti_gtk'
APP_TITLE = 'Project GDL Portal'
DEFAULT_WINDOW_WIDTH = 1000
DEFAULT_WINDOW_HEIGHT = 700
STATUS_TIMEOUT_SECONDS = 3
ACTION_DIALOG_WIDTH = 420
SYSTEM_ICONS_DIR = '/usr/share/yafti/icons'
TILE_ICON_SIZE = 48
TILE_WIDTH = 180
TILE_HEIGHT = 168
TILE_TITLE_CHARS = 15
TILE_TITLE_LINES = 2
TILE_DESC_CHARS = 16
TILE_DESC_LINES = 2
DIALOG_ICON_SIZE = 64
FALLBACK_ICON = 'application-x-executable'

# Populated by init_icons_dirs() from the config path (local debug + system install).
ICONS_DIRS = [SYSTEM_ICONS_DIR]


def set_widget_margins(widget, top=10, bottom=10, start=10, end=10):
    """Apply consistent margins to a widget."""
    widget.set_margin_top(top)
    widget.set_margin_bottom(bottom)
    widget.set_margin_start(start)
    widget.set_margin_end(end)


def clear_container(container):
    """Remove all children from a container widget."""
    if hasattr(container, 'remove'):
        # For regular containers (Box, etc.)
        while container.get_first_child() is not None:
            container.remove(container.get_first_child())
    elif hasattr(container, 'set_child'):
        # For dialogs and single-child containers
        container.set_child(None)


def show_error_dialog(parent, title, message):
    """Display an error dialog with the given title and message."""
    dialog = Gtk.MessageDialog(
        transient_for=parent,
        message_type=Gtk.MessageType.ERROR,
        buttons=Gtk.ButtonsType.OK,
        text=title
    )
    dialog.format_secondary_text(message)
    dialog.run()
    dialog.destroy()


def _breeze_theme_name(dark=None):
    """Return Breeze or Breeze-Dark theme directory name."""
    if dark is None:
        dark = _prefer_dark_theme()
    return 'Breeze-Dark' if dark else 'Breeze'


def _breeze_gtk4_css_paths(dark=None):
    """Ordered CSS paths: base Breeze theme, then Plasma color overrides."""
    theme = _breeze_theme_name(dark)
    paths = [
        f'/usr/share/themes/{theme}/gtk-4.0/gtk.css',
        # Light theme also ships gtk-dark.css as a re-export of Breeze-Dark
    ]
    # Plasma writes live color tokens for the active scheme here
    user_gtk = os.path.expanduser('~/.config/gtk-4.0/gtk.css')
    user_colors = os.path.expanduser('~/.config/gtk-4.0/colors.css')
    if os.path.isfile(user_gtk):
        paths.append(user_gtk)
    elif os.path.isfile(user_colors):
        paths.append(user_colors)
    return paths


def _load_css_file(path, priority):
    """Load a CSS file onto the default display; return True on success."""
    if not path or not os.path.isfile(path):
        return False
    display = Gdk.Display.get_default()
    if display is None:
        return False
    try:
        provider = Gtk.CssProvider()
        provider.load_from_path(path)
        Gtk.StyleContext.add_provider_for_display(display, provider, priority)
        return True
    except Exception as e:
        print(f"Warning: could not load CSS {path}: {e}", file=sys.stderr)
        return False


def initialize_gtk():
    """Initialize GTK with Breeze (no libadwaita). GTK4 needs CSS loaded explicitly."""
    dark = _prefer_dark_theme()
    theme = _breeze_theme_name(dark)

    # Must be set before Gtk.init so the settings backend sees it.
    os.environ['GTK_THEME'] = theme
    # Discourage portals / gsettings from forcing Adwaita
    os.environ.setdefault('GTK_THEME_VARIANT', 'dark' if dark else 'light')

    GLib.set_prgname(APP_ID)
    Gtk.init()

    _settings = Gtk.Settings.get_default()
    if _settings is not None:
        try:
            _settings.set_property('gtk-theme-name', theme)
        except Exception:
            pass
        try:
            _settings.set_property('gtk-application-prefer-dark-theme', dark)
        except Exception:
            pass
        try:
            _settings.set_property('gtk-icon-theme-name', 'breeze-dark' if dark else 'breeze')
        except Exception:
            pass

    # GTK4 falls back to Adwaita unless CSS is loaded explicitly. Push Breeze
    # above the stock theme provider so it actually wins.
    loaded = False
    for path in _breeze_gtk4_css_paths(dark):
        if path.startswith(os.path.expanduser('~')):
            prio = Gtk.STYLE_PROVIDER_PRIORITY_USER
        else:
            # Above THEME (Adwaita), below our small app tweaks
            prio = Gtk.STYLE_PROVIDER_PRIORITY_APPLICATION - 10
        if _load_css_file(path, prio):
            loaded = True
    if not loaded:
        print(
            "Warning: Breeze GTK4 CSS not found; UI may look like stock GTK.",
            file=sys.stderr,
        )

    try:
        Gtk.Window.set_default_icon_name(APP_ID)
    except Exception as e:
        print(f"Warning: Could not set app icon: {e}")

    css = b"""
    .action-tile-button {
      padding: 10px 8px;
    }
    .action-tile-title {
      font-weight: bold;
    }
    """
    try:
        provider = Gtk.CssProvider()
        provider.load_from_data(css)
        display = Gdk.Display.get_default()
        if display is not None:
            Gtk.StyleContext.add_provider_for_display(
                display, provider, Gtk.STYLE_PROVIDER_PRIORITY_APPLICATION
            )
    except Exception as e:
        print(f"Warning: Could not load tile CSS: {e}")


def icons_dir_for_config(config_file):
    """Icons live next to the config: <dir of yafti.yml>/icons/."""
    config_dir = os.path.dirname(os.path.abspath(config_file))
    return os.path.join(config_dir, "icons")


def init_icons_dirs(config_file, extra_dirs=None):
    """Prefer icons next to the YAML (debug tree), then the system path."""
    global ICONS_DIRS
    dirs = []
    local = icons_dir_for_config(config_file)
    if local:
        dirs.append(local)
    if SYSTEM_ICONS_DIR not in dirs:
        dirs.append(SYSTEM_ICONS_DIR)
    if extra_dirs:
        for d in extra_dirs:
            if d and d not in dirs:
                dirs.append(d)
    ICONS_DIRS = dirs


def resolve_icon_file(name):
    """Return a path for an icon name from ICONS_DIRS, or an absolute/relative file."""
    if not name:
        return None
    if os.path.isabs(name):
        return name if os.path.isfile(name) else None
    if os.path.sep in name or name.startswith('.'):
        # Relative to first icons dir / CWD for local debug paths in YAML
        for base in list(ICONS_DIRS) + [os.getcwd()]:
            candidate = os.path.normpath(os.path.join(base, name))
            if os.path.isfile(candidate):
                return candidate
        if os.path.isfile(name):
            return name
        return None

    base_name = os.path.basename(name)
    stem, ext = os.path.splitext(base_name)
    for icons_dir in ICONS_DIRS:
        candidates = []
        if ext:
            candidates.append(os.path.join(icons_dir, base_name))
        else:
            for suffix in ('.svg', '.png', '.svgz', '.jpg', '.jpeg', '.webp'):
                candidates.append(os.path.join(icons_dir, stem + suffix))
        for path in candidates:
            if os.path.isfile(path):
                return path
    return None


_DARK_THEME_CACHE = None


def _ini_key(path, key):
    """Return value for key= in a simple INI file (first match), or None."""
    try:
        with open(path, 'r', encoding='utf-8', errors='replace') as fh:
            for line in fh:
                line = line.strip()
                if not line or line.startswith('#') or line.startswith(';'):
                    continue
                if line.lower().startswith(key.lower() + '='):
                    return line.split('=', 1)[1].strip().strip('"').strip("'")
    except OSError:
        pass
    return None


def _scheme_is_dark(name):
    """True if a Plasma/GTK color-scheme or theme name looks dark."""
    if not name:
        return False
    n = name.lower().replace(' ', '')
    if 'light' in n:
        return False
    return 'dark' in n


def _prefer_dark_theme():
    """True when Plasma/GTK is using a dark color scheme. No libadwaita."""
    global _DARK_THEME_CACHE
    if _DARK_THEME_CACHE is not None:
        return _DARK_THEME_CACHE

    # 1) Explicit env (only if we didn't set it ourselves yet — still trustworthy)
    gtk_theme = os.environ.get('GTK_THEME', '')
    if gtk_theme:
        # Breeze vs Breeze-Dark; ignore bare "dark" substring in unrelated names with light
        if _scheme_is_dark(gtk_theme):
            _DARK_THEME_CACHE = True
            return True
        if 'breeze' in gtk_theme.lower() and 'dark' not in gtk_theme.lower():
            _DARK_THEME_CACHE = False
            return False

    # 2) Plasma ColorScheme key only (not whole-file greps — false positives)
    for cmd in (
        ['kreadconfig6', '--file', 'kdeglobals', '--group', 'General', '--key', 'ColorScheme'],
        ['kreadconfig5', '--file', 'kdeglobals', '--group', 'General', '--key', 'ColorScheme'],
    ):
        try:
            out = subprocess.check_output(
                cmd, stderr=subprocess.DEVNULL, text=True, timeout=1
            ).strip()
            if out:
                _DARK_THEME_CACHE = _scheme_is_dark(out)
                return _DARK_THEME_CACHE
        except Exception:
            continue

    for conf in (
        os.path.expanduser('~/.config/kdeglobals'),
        os.path.expanduser('~/.config/kdedefaults/kdeglobals'),
    ):
        scheme = _ini_key(conf, 'ColorScheme')
        if scheme:
            _DARK_THEME_CACHE = _scheme_is_dark(scheme)
            return _DARK_THEME_CACHE

    # 3) gtk settings written by plasma-integration
    for conf in (
        os.path.expanduser('~/.config/gtk-4.0/settings.ini'),
        os.path.expanduser('~/.config/gtk-3.0/settings.ini'),
    ):
        prefer = _ini_key(conf, 'gtk-application-prefer-dark-theme')
        theme = _ini_key(conf, 'gtk-theme-name')
        if prefer is not None:
            _DARK_THEME_CACHE = prefer.lower() in ('true', '1', 'yes')
            # theme name can still force dark (Breeze-Dark) even if prefer flag is false
            if not _DARK_THEME_CACHE and _scheme_is_dark(theme or ''):
                _DARK_THEME_CACHE = True
            return _DARK_THEME_CACHE
        if theme:
            _DARK_THEME_CACHE = _scheme_is_dark(theme)
            return _DARK_THEME_CACHE

    # 4) Gtk.Settings last (may be unset before init)
    settings = Gtk.Settings.get_default()
    if settings is not None:
        try:
            if settings.get_property('gtk-application-prefer-dark-theme'):
                _DARK_THEME_CACHE = True
                return True
        except Exception:
            pass
        try:
            theme = str(settings.get_property('gtk-theme-name') or '')
            if theme:
                _DARK_THEME_CACHE = _scheme_is_dark(theme)
                return _DARK_THEME_CACHE
        except Exception:
            pass

    _DARK_THEME_CACHE = False
    return False


def _pixbuf_is_monochrome(pixbuf, chroma_limit=18, sample_step=3):
    """True if opaque pixels are essentially grayscale (symbolic / simple-icons)."""
    width = pixbuf.get_width()
    height = pixbuf.get_height()
    n_channels = pixbuf.get_n_channels()
    rowstride = pixbuf.get_rowstride()
    pixels = pixbuf.get_pixels()
    chroma_sum = 0
    count = 0
    for y in range(0, height, sample_step):
        row = y * rowstride
        for x in range(0, width, sample_step):
            i = row + x * n_channels
            if n_channels >= 4 and pixels[i + 3] < 40:
                continue
            r, g, b = pixels[i], pixels[i + 1], pixels[i + 2]
            chroma_sum += max(r, g, b) - min(r, g, b)
            count += 1
            if count >= 64 and (chroma_sum / count) > chroma_limit:
                return False
    if count < 8:
        return False
    return (chroma_sum / count) <= chroma_limit


def _recolor_monochrome_pixbuf(pixbuf, rgb):
    """Paint grayscale/symbolic icon with solid rgb, keeping alpha as the mask."""
    width = pixbuf.get_width()
    height = pixbuf.get_height()
    if not pixbuf.get_has_alpha():
        pixbuf = pixbuf.add_alpha(False, 0, 0, 0)
    n_channels = pixbuf.get_n_channels()
    rowstride = pixbuf.get_rowstride()
    src = pixbuf.get_pixels()
    data = bytearray(src)
    r_out, g_out, b_out = rgb
    for y in range(height):
        row = y * rowstride
        for x in range(width):
            i = row + x * n_channels
            if data[i + 3] == 0:
                continue
            # Keep source alpha (mask / anti-alias); replace RGB with theme foreground
            data[i] = r_out
            data[i + 1] = g_out
            data[i + 2] = b_out
    return GdkPixbuf.Pixbuf.new_from_bytes(
        GLib.Bytes.new(bytes(data)),
        GdkPixbuf.Colorspace.RGB,
        True,
        8,
        width,
        height,
        rowstride,
    )


def _load_icon_pixbuf(file_path, size):
    """Load icon file scaled to size; recolor monochrome assets for light/dark UI."""
    try:
        pixbuf = GdkPixbuf.Pixbuf.new_from_file_at_size(file_path, size, size)
    except GLib.Error:
        return None
    if pixbuf is None:
        return None
    if not _pixbuf_is_monochrome(pixbuf):
        return pixbuf
    # Match Breeze text contrast: solid black on light, light gray on dark
    if _prefer_dark_theme():
        rgb = (252, 252, 252)
    else:
        rgb = (24, 24, 24)
    try:
        return _recolor_monochrome_pixbuf(pixbuf, rgb)
    except Exception:
        return pixbuf


def create_action_icon(action, size=TILE_ICON_SIZE):
    """Build a Gtk.Image from action icon (file under yafti/icons or theme name)."""
    raw = (action.get('icon') or action.get('id') or FALLBACK_ICON)
    raw = str(raw).strip() if raw else FALLBACK_ICON

    image = Gtk.Image()
    image.set_pixel_size(size)
    image.set_halign(Gtk.Align.CENTER)

    file_path = resolve_icon_file(raw)
    if file_path:
        pixbuf = _load_icon_pixbuf(file_path, size)
        if pixbuf is not None:
            try:
                image.set_from_paintable(Gdk.Texture.new_for_pixbuf(pixbuf))
            except Exception:
                image.set_from_file(file_path)
            return image
        image.set_from_file(file_path)
        return image

    icon_name = os.path.splitext(os.path.basename(raw))[0] or FALLBACK_ICON
    display = Gdk.Display.get_default()
    if display is not None:
        theme = Gtk.IconTheme.get_for_display(display)
        if theme is not None and not theme.has_icon(icon_name):
            if theme.has_icon(FALLBACK_ICON):
                icon_name = FALLBACK_ICON
    image.set_from_icon_name(icon_name)
    return image


def build_terminal_command(script):
    """Return the default terminal launcher command."""
    # Keep the terminal open after the script exits so the user can read
    # its output/errors instead of the window vanishing immediately.
    # The script runs in a subshell: if it calls `exit N` itself, that must
    # only end the subshell, not this wrapper (otherwise the status check
    # and the "press any key" pause below would never run).
    wrapped = (
        f"( {script}\n)\n"
        'status=$?\n'
        'echo\n'
        'if [ "$status" -ne 0 ]; then echo "Command exited with status $status."; fi\n'
        'read -n 1 -s -r -p "Press any key to close this window..."\n'
    )
    return [
        "xdg-terminal-exec",
        f"--app-id={APP_ID}",
        f"--title={APP_TITLE}",
        "--",
        "bash",
        "--noprofile",
        "--norc",
        "-lc",
        wrapped,
    ]


def build_headless_command(script):
    """Return the non-interactive command used for status checks."""
    return [
        "bash",
        "--noprofile",
        "--norc",
        "-lc",
        script,
    ]


def escape_markup(text):
    """Escape text before using it in a GTK markup label."""
    return GLib.markup_escape_text(text or "")


# ---- i18n ---------------------------------------------------------------

TRANSLATIONS = {}


def _detect_lang():
    """Determine user language from system locale."""
    try:
        locale.setlocale(locale.LC_ALL, "")
        code, _ = locale.getlocale()
        if code:
            return code.split("_")[0].lower()
    except Exception:
        pass
    for var in ("LANGUAGE", "LC_ALL", "LC_MESSAGES", "LANG"):
        value = os.environ.get(var, "")
        if not value or value.lower() in ("c", "posix"):
            continue
        # LANGUAGE may be a colon-separated preference list (ru:en_US:en)
        first = value.split(":")[0].strip()
        if first and first.lower() not in ("c", "posix"):
            return first.split(".")[0].split("_")[0].lower()
    return "en"


def _locale_dir_for_config(config_file):
    """Locale files live next to the config: <dir of yafti.yml>/locale/."""
    config_dir = os.path.dirname(os.path.abspath(config_file))
    return os.path.join(config_dir, "locale")


def _load_translations_file(path):
    """Load a YAML translation map (English source -> localized string)."""
    try:
        with open(path, "r", encoding="utf-8") as f:
            data = yaml.safe_load(f) or {}
    except FileNotFoundError:
        print(f"Warning: translation file not found: {path}", file=sys.stderr)
        return {}
    except yaml.YAMLError as e:
        print(f"Warning: failed to parse translation file {path}: {e}", file=sys.stderr)
        return {}
    if not isinstance(data, dict):
        print(f"Warning: translation file must be a mapping: {path}", file=sys.stderr)
        return {}
    return {str(k): str(v) for k, v in data.items() if k is not None and v is not None}


def _resolve_locale_path(lang, locale_dir):
    """Return path to <locale_dir>/<lang>.yml if it exists."""
    if not lang or lang in ("en", "c", "posix"):
        return None
    for ext in (".yml", ".yaml"):
        candidate = os.path.join(locale_dir, f"{lang}{ext}")
        if os.path.isfile(candidate):
            return candidate
    return None


def init_i18n(config_file, lang=None, locale_file=None, locale_dir=None):
    """Load translations relative to the config file (or an explicit path)."""
    global TRANSLATIONS
    TRANSLATIONS = {}

    if locale_file:
        TRANSLATIONS = _load_translations_file(locale_file)
        return

    if lang is None:
        lang = _detect_lang()

    if locale_dir is None:
        locale_dir = _locale_dir_for_config(config_file)

    path = _resolve_locale_path(lang, locale_dir)
    if path:
        TRANSLATIONS = _load_translations_file(path)


def tr(text):
    """Translate text using the loaded translation map; fall back to original."""
    if text is None:
        return text
    return TRANSLATIONS.get(text, text)



class YaftiGTK(Gtk.Window):
    def __init__(self, config_file='yafti.yml'):
        super().__init__(title=APP_TITLE)
        self.set_default_size(DEFAULT_WINDOW_WIDTH, DEFAULT_WINDOW_HEIGHT)
        self.active_dialog_state = None

        # Load YAML configuration
        self.config = self.load_config(config_file)
        self.screens = self.config.get('screens', [])
        self.actions_index = self._build_actions_index()

        # Create main container
        vbox = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=0)
        self.set_child(vbox)

        # Search bar at the top
        search_entry = Gtk.SearchEntry()
        search_entry.set_placeholder_text(tr("Search Apps and Actions"))
        set_widget_margins(search_entry, 10, 10, 10, 10)
        search_entry.connect("search-changed", self.on_search_changed)
        vbox.append(search_entry)

        # Notebook (tabs) directly below search
        self.notebook = Gtk.Notebook()
        self.notebook.set_scrollable(True)

        # Add tabs for each screen from YAML
        for screen in self.screens:
            page = self.create_screen_page(screen)
            label = Gtk.Label(label=tr(screen.get('title', 'Tab')))
            self.notebook.append_page(page, label)

        # Stack to switch between notebook and search results
        self.content_stack = Gtk.Stack()
        self.content_stack.set_transition_type(Gtk.StackTransitionType.CROSSFADE)
        self.content_stack.set_transition_duration(150)

        # Add notebook to stack
        self.content_stack.add_named(self.notebook, "tabs")

        # Search results page (tiles, same as screens)
        search_scrolled = Gtk.ScrolledWindow()
        search_scrolled.set_policy(Gtk.PolicyType.AUTOMATIC, Gtk.PolicyType.AUTOMATIC)
        search_outer = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=8)
        set_widget_margins(search_outer, 10, 10, 10, 10)
        self.search_header = Gtk.Label()
        self.search_header.set_xalign(0)
        search_outer.append(self.search_header)
        self.search_results_box = self.create_actions_flow()
        search_outer.append(self.search_results_box)
        search_scrolled.set_child(search_outer)
        self.content_stack.add_named(search_scrolled, "search")

        # Start with tabs visible
        self.content_stack.set_visible_child_name("tabs")

        vbox.append(self.content_stack)

        self.connect("notify::is-active", self.on_window_active_changed)
        focus_controller = Gtk.EventControllerFocus.new()
        focus_controller.connect("enter", self.on_window_focus_in)
        self.add_controller(focus_controller)

    def load_config(self, config_file):
        """Load and parse the YAML configuration file."""
        try:
            with open(config_file, 'r') as f:
                return yaml.safe_load(f) or {}
        except FileNotFoundError:
            show_error_dialog(
                self,
                tr("Configuration file not found"),
                tr("Could not find ") + config_file + tr(" in the current directory.")
            )
            sys.exit(1)
        except yaml.YAMLError as e:
            show_error_dialog(self, tr("YAML parsing error"), str(e))
            sys.exit(1)

    def create_actions_flow(self):
        """Create a FlowBox used for action tiles on screens and in search."""
        flow = Gtk.FlowBox()
        flow.set_valign(Gtk.Align.START)
        flow.set_max_children_per_line(6)
        flow.set_min_children_per_line(2)
        flow.set_selection_mode(Gtk.SelectionMode.NONE)
        flow.set_homogeneous(True)
        flow.set_row_spacing(12)
        flow.set_column_spacing(12)
        flow.set_hexpand(True)
        flow.set_vexpand(False)
        set_widget_margins(flow, 12, 12, 12, 12)
        return flow

    def create_screen_page(self, screen):
        """Create a page for a screen with all its actions as icon tiles."""
        scrolled = Gtk.ScrolledWindow()
        scrolled.set_policy(Gtk.PolicyType.AUTOMATIC, Gtk.PolicyType.AUTOMATIC)
        scrolled.set_propagate_natural_height(True)

        flow = self.create_actions_flow()
        for action in screen.get('actions', []):
            flow.append(self.create_action_item(action))

        scrolled.set_child(flow)
        return scrolled

    def _make_tile_label(self, text, *, css_classes, max_chars, lines):
        """Centered wrapping label; natural height only (no empty multi-line padding)."""
        label = Gtk.Label(label=text)
        label.set_wrap(True)
        # NOTE: Gtk.WrapMode.WORD_CHAR makes GTK4's size measurement report
        # min-width == full unwrapped text width, so at the tile's real (smaller)
        # width GTK4 refuses to allocate a 2nd line and ellipsizes the 1st line
        # instead of wrapping. WORD keeps min-width small (per-word) so the
        # label correctly measures/allocates multiple lines, and still falls
        # back to mid-word breaks via WORD_CHAR only when a single word can't
        # fit (see natural_wrap_mode below).
        label.set_wrap_mode(Gtk.WrapMode.WORD)
        label.set_justify(Gtk.Justification.CENTER)
        label.set_xalign(0.5)
        # Cap natural width so long strings wrap instead of stretching the tile.
        label.set_max_width_chars(max_chars)
        label.set_lines(lines)
        label.set_ellipsize(Pango.EllipsizeMode.END)
        # FILL + hexpand: get allocated width from the fixed tile (wrap needs a real width).
        label.set_hexpand(True)
        label.set_halign(Gtk.Align.FILL)
        label.set_valign(Gtk.Align.CENTER)
        for cls in css_classes:
            label.add_css_class(cls)
        return label

    def create_action_item(self, action):
        """Create a clickable action tile with icon, title, and description."""
        button = Gtk.Button()
        button.set_size_request(TILE_WIDTH, TILE_HEIGHT)
        button.set_hexpand(True)
        button.set_vexpand(True)
        button.set_halign(Gtk.Align.FILL)
        button.set_valign(Gtk.Align.FILL)
        button.add_css_class('action-tile-button')
        button.set_tooltip_text(tr(action.get('description') or action.get('title') or ''))

        # Fixed outer size + homogeneous FlowBox keeps every row even.
        # valign=START (not CENTER): pins the icon to the same Y in every tile.
        # With CENTER, tiles with 1-line vs 2-line title/desc had different
        # total content height, so the whole block (icon included) shifted
        # up/down per tile and icons ended up on different rows.
        # spacing=0: gaps below are set explicitly per-label (margin_top) so
        # icon->title and title->desc can have different, wider breathing room.
        content = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=0)
        content.set_halign(Gtk.Align.FILL)
        content.set_valign(Gtk.Align.START)
        content.set_hexpand(True)
        set_widget_margins(content, 10, 4, 4, 4)

        icon = create_action_icon(action, TILE_ICON_SIZE)
        content.append(icon)

        title_label = self._make_tile_label(
            tr(action.get('title', 'Action')),
            css_classes=('action-tile-title',),
            max_chars=TILE_TITLE_CHARS,
            lines=TILE_TITLE_LINES,
        )
        title_label.set_margin_top(10)
        content.append(title_label)

        if action.get('description'):
            desc_label = self._make_tile_label(
                tr(action['description']),
                css_classes=('dim-label',),
                max_chars=TILE_DESC_CHARS,
                lines=TILE_DESC_LINES,
            )
            desc_label.set_margin_top(8)
            content.append(desc_label)

        button.set_child(content)
        button.connect("clicked", self.on_action_clicked, action)

        frame = Gtk.Frame()
        frame.set_child(button)
        frame.set_hexpand(True)
        frame.set_vexpand(True)
        frame.set_halign(Gtk.Align.FILL)
        frame.set_valign(Gtk.Align.FILL)
        frame.set_size_request(TILE_WIDTH, TILE_HEIGHT)
        return frame

    def _build_actions_index(self):
        """Flatten actions for search lookup."""
        index = []
        for screen in self.screens or []:
            for action in screen.get('actions', []):
                index.append({'action': action})
        return index

    def get_action_options(self, action):
        """Return explicit modal options from the config."""
        options = action.get('options')
        if isinstance(options, list) and options:
            return options

        return []

    def action_uses_modal(self, action):
        """Return True when the action should open the management modal."""
        if self.get_action_options(action):
            return True
        return bool((action.get('status_script') or "").strip())

    def on_search_changed(self, entry):
        query = entry.get_text().strip()
        if not query:
            clear_container(self.search_results_box)
            self.content_stack.set_visible_child_name("tabs")
            return

        lowered = query.lower()
        matches = []
        for item in self.actions_index:
            action = item['action']
            title = action.get('title', '')
            desc = action.get('description', '')
            ttitle = tr(title)
            tdesc = tr(desc)
            if (lowered in title.lower() or lowered in ttitle.lower()
                    or lowered in desc.lower() or lowered in tdesc.lower()):
                matches.append(item)

        clear_container(self.search_results_box)

        if matches:
            self.search_header.set_markup(
                "<b>" + escape_markup(tr("Search results")) + "</b>"
            )
            for item in matches:
                self.search_results_box.append(self.create_action_item(item['action']))
        else:
            self.search_header.set_markup(
                "<b>" + escape_markup(tr("No matches found")) + "</b>"
            )

        self.search_results_box.set_visible(True)
        self.content_stack.set_visible_child_name("search")

    def on_action_clicked(self, _button, action):
        """Open a management modal or run the action directly."""
        if not self.action_uses_modal(action):
            script = (action.get('script') or "").strip()
            if not script:
                return

            error_message = self.launch_terminal(script)
            if error_message is None:
                return

            show_error_dialog(
                self,
                tr("No terminal available"),
                tr("Could not open a terminal automatically.\n\n")
                + error_message
                + tr("\n\nYou can also run the following command manually:\n\n")
                + script
            )
            return

        dialog = Gtk.Dialog(title=tr(action.get('title', 'Action')), transient_for=self)
        dialog.set_modal(True)
        dialog.set_destroy_with_parent(True)
        dialog.set_default_size(ACTION_DIALOG_WIDTH, -1)
        dialog.set_resizable(False)

        state = {
            'action': action,
            'dialog': dialog,
            'dirty': False,
            'loading': False,
            'closed': False,
            'request_id': 0,
            'status_token': None,
            'status_timed_out': False,
        }
        self.active_dialog_state = state

        dialog.connect("destroy", self.on_dialog_destroy, state)
        dialog.connect("notify::is-active", self.on_dialog_active_changed, state)
        focus_controller = Gtk.EventControllerFocus.new()
        focus_controller.connect("enter", self.on_dialog_focus_in, state)
        dialog.add_controller(focus_controller)

        if (action.get('status_script') or "").strip():
            self.refresh_action_dialog(state)
        else:
            self.build_action_dialog_content(state, None)

    def on_dialog_destroy(self, _dialog, state):
        """Clear the active dialog reference when the modal closes."""
        state['closed'] = True
        if self.active_dialog_state is state:
            self.active_dialog_state = None

    def on_window_active_changed(self, window, _pspec):
        """Refresh the active dialog when the portal window becomes active."""
        if window.get_property("is-active"):
            self.refresh_active_dialog_if_needed()

    def on_dialog_active_changed(self, dialog, _pspec, state):
        """Refresh the dialog when it becomes active again."""
        if dialog.get_property("is-active"):
            self.refresh_dialog_if_needed(state)

    def on_window_focus_in(self, _controller):
        """Refresh the active dialog on focus return when needed."""
        self.refresh_active_dialog_if_needed()
        return False

    def on_dialog_focus_in(self, _controller, state):
        """Refresh the focused dialog after a launched action when needed."""
        self.refresh_dialog_if_needed(state)
        return False

    def refresh_active_dialog_if_needed(self):
        """Refresh the active dialog if a launched action may have changed status."""
        self.refresh_dialog_if_needed(self.active_dialog_state)

    def refresh_dialog_if_needed(self, state):
        """Refresh a dialog when its status is dirty."""
        if self.should_refresh_dialog(state):
            self.refresh_action_dialog(state)

    def should_refresh_dialog(self, state):
        """Return True when a dialog should refresh its status on focus return."""
        if not state or state.get('closed'):
            return False
        if self.active_dialog_state is not state:
            return False
        if state.get('loading'):
            return False
        return state.get('dirty', False)

    def refresh_action_dialog(self, state):
        """Show the loading state and rerun the dialog status check."""
        if not state or state.get('closed'):
            return

        action = state['action']
        status_script = (action.get('status_script') or "").strip()
        if not status_script:
            self.build_action_dialog_content(state, None)
            return

        state['dirty'] = False
        state['request_id'] += 1
        request_id = state['request_id']
        self.build_action_dialog_loading(state)

        thread = threading.Thread(
            target=self.run_status_check,
            args=(state, request_id, status_script),
            daemon=True,
        )
        thread.start()

    def build_action_dialog_loading(self, state):
        """Render the loading-only modal view."""
        dialog = state['dialog']
        clear_container(dialog)
        state['loading'] = True

        loading_box = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=10)
        loading_box.set_halign(Gtk.Align.CENTER)
        loading_box.set_valign(Gtk.Align.CENTER)
        set_widget_margins(loading_box, 24, 24, 24, 24)

        spinner = Gtk.Spinner()
        spinner.start()
        loading_box.append(spinner)

        label = Gtk.Label(label=tr("Loading..."))
        loading_box.append(label)

        dialog.set_child(loading_box)
        dialog.set_visible(True)

    def run_status_check(self, state, request_id, status_script):
        """Run the modal status check in the background."""
        status_token = "unknown"
        status_timed_out = False

        try:
            result = subprocess.run(
                build_headless_command(status_script),
                capture_output=True,
                text=True,
                timeout=STATUS_TIMEOUT_SECONDS,
                check=False,
            )

            if result.returncode == 0:
                for line in result.stdout.splitlines():
                    token = line.strip()
                    if token:
                        status_token = token
                        break
        except subprocess.TimeoutExpired:
            status_timed_out = True
        except Exception:
            status_token = "unknown"

        GLib.idle_add(
            self.finish_status_check,
            state,
            request_id,
            status_token,
            status_timed_out,
        )

    def finish_status_check(self, state, request_id, status_token, status_timed_out):
        """Update the dialog once the status check completes."""
        if not state or state.get('closed'):
            return False
        if self.active_dialog_state is not state:
            return False
        if state.get('request_id') != request_id:
            return False

        self.build_action_dialog_content(state, status_token, status_timed_out)
        return False

    def build_action_dialog_content(self, state, status_token, status_timed_out=False):
        """Render the full action dialog after status is known."""
        dialog = state['dialog']
        action = state['action']
        clear_container(dialog)

        state['loading'] = False
        state['status_token'] = status_token
        state['status_timed_out'] = status_timed_out

        root = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=12)
        set_widget_margins(root, 16, 16, 16, 16)

        header = Gtk.Box(orientation=Gtk.Orientation.HORIZONTAL, spacing=12)
        header.append(create_action_icon(action, DIALOG_ICON_SIZE))
        title_label = Gtk.Label()
        title_label.set_markup(f"<big><b>{escape_markup(tr(action.get('title', 'Action')))}</b></big>")
        title_label.set_xalign(0)
        title_label.set_wrap(True)
        title_label.set_hexpand(True)
        header.append(title_label)
        root.append(header)

        description = action.get('description')
        if description:
            desc_label = Gtk.Label(label=tr(description))
            desc_label.set_xalign(0)
            desc_label.set_wrap(True)
            desc_label.add_css_class('dim-label')
            root.append(desc_label)

        if status_timed_out:
            status_label = Gtk.Label()
            status_label.set_markup(
                "<span foreground='red'><b>" + escape_markup(tr("Status check timed out. You can still run the action.")) + "</b></span>"
            )
            status_label.set_xalign(0)
            status_label.set_wrap(True)
            root.append(status_label)

        actions_box = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=8)
        for option in self.get_action_options(action):
            option_button = Gtk.Button(label=tr(option.get('label', 'Run')))
            option_button.set_hexpand(True)
            option_button.set_halign(Gtk.Align.FILL)

            if self.option_is_highlighted(option, status_token):
                option_button.add_css_class("suggested-action")

            option_button.connect("clicked", self.on_option_clicked, state, option)
            actions_box.append(option_button)

        root.append(actions_box)

        close_button = Gtk.Button(label=tr("Close"))
        close_button.connect("clicked", lambda _button: dialog.destroy())
        root.append(close_button)

        dialog.set_child(root)
        dialog.set_visible(True)

    def option_is_highlighted(self, option, status_token):
        """Return True when the option ID matches the current status token."""
        if not status_token or status_token == "unknown":
            return False

        option_id = (option.get('id') or "").strip().lower()
        current_status = status_token.strip().lower()
        return bool(option_id) and option_id == current_status

    def on_option_clicked(self, _button, state, option):
        """Launch the selected modal action in a terminal."""
        script = (option.get('script') or "").strip()
        if not script:
            return

        error_message = self.launch_terminal(script)
        if error_message is None:
            if (state['action'].get('status_script') or "").strip():
                state['dirty'] = True
            return

        show_error_dialog(
            state['dialog'],
            tr("No terminal available"),
            tr("Could not open a terminal automatically.\n\n")
            + error_message
            + tr("\n\nYou can also run the following command manually:\n\n")
            + script
        )

    def launch_terminal(self, script):
        """Attempt to run a command in a terminal. Returns None on success."""
        try:
            subprocess.Popen(build_terminal_command(script))
            return None
        except FileNotFoundError:
            return tr("The default terminal launcher (xdg-terminal-exec) was not found.")
        except Exception as e:
            return tr("Terminal launch failed: ") + str(e)


def parse_args(argv):
    """Parse CLI: CONFIG_FILE [--lang LANG | --locale FILE] [--locale-dir DIR]."""
    usage = (
        f"Usage: {APP_ID} CONFIG_FILE [--lang LANG | --locale FILE] [--locale-dir DIR]\n"
        "Locales are loaded from <dir of CONFIG_FILE>/locale/<lang>.yml by default.\n"
        "Example: yafti_gtk.py /usr/share/yafti/yafti.yml\n"
        "         yafti_gtk.py ./yafti.yml --lang ru\n"
        "         yafti_gtk.py ./yafti.yml --locale ./locale/ru.yml"
    )
    if not argv or argv[0].startswith("-"):
        print(usage)
        sys.exit(1)

    config_file = argv[0]
    lang = None
    locale_file = None
    locale_dir = None

    i = 1
    while i < len(argv):
        arg = argv[i]
        if arg in ("--lang", "-l") and i + 1 < len(argv):
            lang = argv[i + 1]
            i += 2
        elif arg in ("--locale", "--translations") and i + 1 < len(argv):
            locale_file = argv[i + 1]
            i += 2
        elif arg == "--locale-dir" and i + 1 < len(argv):
            locale_dir = argv[i + 1]
            i += 2
        elif arg in ("-h", "--help"):
            print(usage)
            sys.exit(0)
        else:
            print(f"Unknown argument: {arg}", file=sys.stderr)
            sys.exit(1)

    return config_file, lang, locale_file, locale_dir


def main():
    config_file, lang, locale_file, locale_dir = parse_args(sys.argv[1:])
    init_i18n(config_file, lang=lang, locale_file=locale_file, locale_dir=locale_dir)
    init_icons_dirs(config_file)

    # Pin Breeze before Gtk.init (GTK4 ignores gtk-theme-name without this + CSS load).
    _dark = _prefer_dark_theme()
    os.environ['GTK_THEME'] = _breeze_theme_name(_dark)

    initialize_gtk()

    loop = GLib.MainLoop()

    win = YaftiGTK(config_file)
    win.connect("close-request", lambda *_: loop.quit())
    win.set_visible(True)

    loop.run()


if __name__ == '__main__':
    main()
