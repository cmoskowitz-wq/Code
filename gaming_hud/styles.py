"""Theme and styling constants for the Gaming HUD overlay."""

# ── Color Palette ───────────────────────────────────────────────────────────
BG_PRIMARY = "#0d1117"
BG_SECONDARY = "#161b22"
BG_TERTIARY = "#1c2333"
BG_OVERLAY = "rgba(13, 17, 23, 230)"

ACCENT_CYAN = "#00d4ff"
ACCENT_GREEN = "#00ff88"
ACCENT_ORANGE = "#ff9f43"
ACCENT_RED = "#ff3b5c"
ACCENT_PURPLE = "#b388ff"
ACCENT_YELLOW = "#ffe066"

TEXT_PRIMARY = "#e6edf3"
TEXT_SECONDARY = "#8b949e"
TEXT_DIM = "#484f58"

BORDER_DEFAULT = "#30363d"
BORDER_ACCENT = "#00d4ff"

# ── Key Visualizer Colors ───────────────────────────────────────────────────
KEY_INACTIVE_BG = "#1c2333"
KEY_INACTIVE_BORDER = "#30363d"
KEY_ACTIVE_BG = "#003d4d"
KEY_ACTIVE_BORDER = ACCENT_CYAN
KEY_ACTIVE_TEXT = ACCENT_CYAN
KEY_INACTIVE_TEXT = TEXT_SECONDARY

# ── Bar Colors by Threshold ─────────────────────────────────────────────────
BAR_LOW = ACCENT_GREEN
BAR_MEDIUM = ACCENT_ORANGE
BAR_HIGH = ACCENT_RED

# ── Font Settings ───────────────────────────────────────────────────────────
FONT_FAMILY = "Segoe UI, Consolas, monospace"
FONT_SIZE_TITLE = 13
FONT_SIZE_LABEL = 11
FONT_SIZE_VALUE = 14
FONT_SIZE_SMALL = 9
FONT_SIZE_KEY = 12

# ── Dimensions ──────────────────────────────────────────────────────────────
HUD_WIDTH = 280
HUD_MIN_HEIGHT = 100
CORNER_RADIUS = 12
BAR_HEIGHT = 6
BAR_RADIUS = 3
KEY_SIZE = 38
KEY_RADIUS = 6
SPACING = 8
SECTION_SPACING = 4
PADDING = 14

# ── Timing ──────────────────────────────────────────────────────────────────
STATS_UPDATE_MS = 1000
FPS_UPDATE_MS = 500
PING_UPDATE_MS = 3000
MEDIA_UPDATE_MS = 2000
KEY_FADE_MS = 150


def get_bar_color(percent: float) -> str:
    """Return a color for a usage bar based on percentage thresholds."""
    if percent < 60:
        return BAR_LOW
    elif percent < 85:
        return BAR_MEDIUM
    return BAR_HIGH


MAIN_STYLESHEET = f"""
    QWidget#HUDPanel {{
        background-color: {BG_OVERLAY};
        border: 1px solid {BORDER_DEFAULT};
        border-radius: {CORNER_RADIUS}px;
    }}
    QLabel {{
        color: {TEXT_PRIMARY};
        background: transparent;
        border: none;
        font-family: {FONT_FAMILY};
    }}
    QLabel#title {{
        font-size: {FONT_SIZE_TITLE}px;
        font-weight: bold;
        color: {ACCENT_CYAN};
    }}
    QLabel#sectionLabel {{
        font-size: {FONT_SIZE_SMALL}px;
        font-weight: bold;
        color: {TEXT_SECONDARY};
        text-transform: uppercase;
        letter-spacing: 1px;
    }}
    QLabel#valueLabel {{
        font-size: {FONT_SIZE_VALUE}px;
        font-weight: bold;
        font-family: Consolas, 'Courier New', monospace;
    }}
    QLabel#metricLabel {{
        font-size: {FONT_SIZE_LABEL}px;
        color: {TEXT_SECONDARY};
    }}
    QLabel#mediaLabel {{
        font-size: {FONT_SIZE_LABEL}px;
        color: {TEXT_PRIMARY};
    }}
    QPushButton#closeBtn {{
        background: transparent;
        border: none;
        color: {TEXT_SECONDARY};
        font-size: 14px;
        font-weight: bold;
        padding: 2px 6px;
        border-radius: 4px;
    }}
    QPushButton#closeBtn:hover {{
        background-color: {ACCENT_RED};
        color: white;
    }}
    QPushButton#minBtn {{
        background: transparent;
        border: none;
        color: {TEXT_SECONDARY};
        font-size: 14px;
        font-weight: bold;
        padding: 2px 6px;
        border-radius: 4px;
    }}
    QPushButton#minBtn:hover {{
        background-color: {BG_TERTIARY};
        color: {TEXT_PRIMARY};
    }}
    QFrame#separator {{
        background-color: {BORDER_DEFAULT};
        border: none;
        max-height: 1px;
        min-height: 1px;
    }}
"""
