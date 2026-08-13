"""Runtime configuration loaded exclusively from environment variables.

Export any required credentials in the operating-system environment.  The
application never stores real tokens in source control.
"""

from __future__ import annotations

import os
from dataclasses import dataclass


@dataclass(frozen=True, slots=True)
class Settings:
    """Credentials used by optional third-party enrichment features."""

    opencage_api_key: str = ""
    hibp_api_key: str = ""
    geoapify_api_key: str = ""

    @classmethod
    def from_environment(cls) -> Settings:
        return cls(
            opencage_api_key=os.getenv("OPEN_CAGE_API_KEY", "").strip(),
            hibp_api_key=os.getenv("HIBP_API_KEY", "").strip(),
            geoapify_api_key=os.getenv("GEOAPIFY_API_KEY", "").strip(),
        )


SETTINGS = Settings.from_environment()

# Backwards-compatible names for modules that import individual values.
OPEN_CAGE_API_KEY = SETTINGS.opencage_api_key
HIBP_API_KEY = SETTINGS.hibp_api_key
GEOAPIFY_API_KEY = SETTINGS.geoapify_api_key
