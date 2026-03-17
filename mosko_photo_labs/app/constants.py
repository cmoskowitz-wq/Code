"""
constants.py — Mosko Photo Labs
Global constants: app metadata, supported formats, color palette,
and EXIF field definitions.
"""

APP_NAME = "Mosko Photo Labs"
APP_VERSION = "1.0.0"
APP_TAGLINE = "Professional EXIF Editor"
APP_AUTHOR = "Mosko Photo Labs"

# ── Supported file extensions ──────────────────────────────────────────────

SUPPORTED_EXTENSIONS = frozenset({
    # Standard raster
    ".jpg", ".jpeg", ".tiff", ".tif", ".png", ".bmp", ".webp",
    # Canon RAW
    ".cr2", ".cr3",
    # Nikon RAW
    ".nef", ".nrw",
    # Sony RAW
    ".arw", ".srf", ".sr2",
    # Adobe DNG
    ".dng",
    # Olympus RAW
    ".orf",
    # Panasonic RAW
    ".rw2",
    # Fujifilm RAW
    ".raf",
    # Pentax RAW
    ".pef",
    # Leica RAW
    ".rwl",
    # Minolta RAW
    ".mrw",
    # Hasselblad RAW
    ".3fr", ".fff",
    # Phase One RAW
    ".iiq", ".cap",
    # Generic RAW
    ".raw",
})

RAW_EXTENSIONS = frozenset({
    ".cr2", ".cr3", ".nef", ".nrw", ".arw", ".srf", ".sr2",
    ".dng", ".orf", ".rw2", ".raf", ".pef", ".rwl", ".mrw",
    ".3fr", ".fff", ".iiq", ".cap", ".raw",
})

# JPEG/TIFF can be edited in-place with piexif
INPLACE_WRITABLE = frozenset({".jpg", ".jpeg", ".tiff", ".tif"})

# ── Color palette — dark photographic theme ────────────────────────────────

COLORS = {
    "bg_dark":       "#111111",
    "bg_panel":      "#1a1a1a",
    "bg_card":       "#222222",
    "bg_input":      "#2a2a2a",
    "bg_hover":      "#2e2e2e",
    "bg_selected":   "#1a3a56",
    "bg_toolbar":    "#181818",
    "accent":        "#d4820a",
    "accent_light":  "#f0a030",
    "accent_dim":    "#7a4a06",
    "text_primary":  "#eaeaea",
    "text_secondary": "#8a8a8a",
    "text_disabled": "#4a4a4a",
    "border":        "#333333",
    "border_focus":  "#d4820a",
    "success":       "#4caf50",
    "warning":       "#ff9800",
    "error":         "#f44336",
    "modified":      "#f0a030",
    "scrollbar":     "#3a3a3a",
    "scrollbar_handle": "#555555",
}

# ── EXIF field definitions ─────────────────────────────────────────────────
# Each entry: (internal_key, display_label, piexif_ifd, piexif_tag_name, value_type, editable)
# value_type: "str" | "int" | "rational" | "exposure" | "aperture" | "gps_coord" | "datetime" | "choice"

EXIF_SECTIONS = {
    "Camera": [
        ("Make",               "Manufacturer",       "0th",  "Make",               "str",      True),
        ("Model",              "Model",               "0th",  "Model",              "str",      True),
        ("BodySerialNumber",   "Body Serial",         "Exif", "BodySerialNumber",   "str",      True),
        ("Software",           "Software/Firmware",   "0th",  "Software",           "str",      True),
        ("DateTimeOriginal",   "Date Taken",          "Exif", "DateTimeOriginal",   "datetime", True),
        ("DateTime",           "Date Modified",       "0th",  "DateTime",           "datetime", True),
        ("ExposureTime",       "Shutter Speed",       "Exif", "ExposureTime",       "exposure", False),
        ("FNumber",            "Aperture",            "Exif", "FNumber",            "aperture", False),
        ("ISOSpeedRatings",    "ISO",                 "Exif", "ISOSpeedRatings",    "int",      True),
        ("ExposureBiasValue",  "Exposure Comp.",      "Exif", "ExposureBiasValue",  "str",      False),
        ("ExposureProgram",    "Exposure Program",    "Exif", "ExposureProgram",    "int",      True),
        ("MeteringMode",       "Metering Mode",       "Exif", "MeteringMode",       "int",      True),
        ("Flash",              "Flash",               "Exif", "Flash",              "int",      True),
        ("WhiteBalance",       "White Balance",       "Exif", "WhiteBalance",       "int",      True),
    ],
    "Lens": [
        ("FocalLength",           "Focal Length",       "Exif", "FocalLength",           "rational", False),
        ("FocalLengthIn35mmFilm", "35mm Equivalent",   "Exif", "FocalLengthIn35mmFilm", "int",      True),
        ("MaxApertureValue",      "Max Aperture",       "Exif", "MaxApertureValue",      "rational", False),
        ("LensMake",              "Lens Manufacturer",  "Exif", "LensMake",              "str",      True),
        ("LensModel",             "Lens Model",         "Exif", "LensModel",             "str",      True),
        ("LensSerialNumber",      "Lens Serial",        "Exif", "LensSerialNumber",      "str",      True),
    ],
    "GPS": [
        ("GPSLatitude",        "Latitude",            "GPS",  "GPSLatitude",        "gps_lat",  True),
        ("GPSLongitude",       "Longitude",           "GPS",  "GPSLongitude",       "gps_lon",  True),
        ("GPSAltitude",        "Altitude (m)",        "GPS",  "GPSAltitude",        "rational", True),
        ("GPSImgDirection",    "Direction (°)",       "GPS",  "GPSImgDirection",    "rational", True),
        ("GPSSpeed",           "Speed",               "GPS",  "GPSSpeed",           "rational", True),
        ("GPSDateStamp",       "GPS Date",            "GPS",  "GPSDateStamp",       "str",      True),
    ],
    "Copyright": [
        ("Artist",             "Photographer",        "0th",  "Artist",             "str",      True),
        ("Copyright",          "Copyright",           "0th",  "Copyright",          "str",      True),
        ("ImageDescription",   "Description",         "0th",  "ImageDescription",   "str",      True),
        ("UserComment",        "User Comment",        "Exif", "UserComment",        "str",      True),
        ("XPKeywords",         "Keywords",            "0th",  "XPKeywords",         "str",      True),
        ("XPAuthor",           "Author (Windows)",    "0th",  "XPAuthor",           "str",      True),
    ],
}

# Choices for integer EXIF fields
EXIF_CHOICES = {
    "ExposureProgram": {
        0: "Not Defined", 1: "Manual", 2: "Normal Auto",
        3: "Aperture Priority", 4: "Shutter Priority", 5: "Creative",
        6: "Action", 7: "Portrait", 8: "Landscape",
    },
    "MeteringMode": {
        0: "Unknown", 1: "Average", 2: "Center-Weighted",
        3: "Spot", 4: "Multi-Spot", 5: "Pattern", 6: "Partial",
    },
    "WhiteBalance": {0: "Auto", 1: "Manual"},
    "Flash": {
        0: "No Flash", 1: "Fired", 5: "Fired, Return not detected",
        7: "Fired, Return detected", 8: "On, not fired", 9: "On, fired",
        16: "Off, not fired", 24: "Auto, did not fire", 25: "Auto, fired",
    },
}

# Thumbnail settings
THUMB_SMALL = (96, 96)
THUMB_LARGE = (240, 240)
PREVIEW_MAX = (1600, 1200)

# Template file location (user home)
TEMPLATE_FILENAME = "mosko_templates.json"
RECENT_FOLDERS_FILE = "mosko_recent.json"
MAX_RECENT_FOLDERS = 10
