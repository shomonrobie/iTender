# version.py
"""TenderAI Version Management"""

VERSION = "3.0.0"
VERSION_INFO = {
    "major": 3,
    "minor": 0,
    "patch": 0,
    "build": 1,
    "release_date": "2026-05-25",
    "codename": "Unified Report Generation",
    "description": "Added unified PDF/HTML reporting, PPR 2025 compliance dashboard, and individual registration"
}

def get_version():
    """Return formatted version string"""
    return f"v{VERSION} ({VERSION_INFO['codename']})"

def get_full_version():
    """Return detailed version info"""
    return f"TenderAI {get_version()} | Build {VERSION_INFO['build']} | Released {VERSION_INFO['release_date']}"