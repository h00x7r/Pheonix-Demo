"""Phone-number validation and metadata helpers for Phoenix.

The module uses Google's libphonenumber metadata through the ``phonenumbers``
package.  It intentionally reports only carrier, numbering-plan region and time
zone metadata; it does not claim to locate an individual device or subscriber.
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any

import phonenumbers
from opencage.geocoder import OpenCageGeocode
from phonenumbers import PhoneNumberFormat, PhoneNumberType, carrier, geocoder, timezone
from phonenumbers.phonenumber import PhoneNumber


@dataclass(frozen=True, slots=True)
class PhoneInfo:
    """Normalised, non-sensitive metadata for a valid phone number."""

    international: str
    national: str
    e164: str
    region: str
    country_code: str | None
    carrier: str | None
    timezones: tuple[str, ...]
    number_type: str

    def as_legacy_dict(self) -> dict[str, Any]:
        """Return the historical structure used by the original Tk interface."""

        return {
            "formatted": {
                "international": self.international,
                "national": self.national,
                "e164": self.e164,
            },
            "region": self.region,
            "country_code": self.country_code,
            "carrier": self.carrier,
            "timezone": self.timezones,
            "number_type": self.number_type,
        }


class PhoneAnalyzer:
    """Validate an international telephone number and expose public metadata."""

    def __init__(self, phone_number: str, opencage_api_key: str | None = None) -> None:
        self.raw_number = phone_number.strip()
        if not self.raw_number:
            raise ValueError("Enter a phone number in international E.164 format, for example +12025550123.")

        try:
            self.parsed_number: PhoneNumber = phonenumbers.parse(self.raw_number, None)
        except phonenumbers.NumberParseException as exc:
            raise ValueError("Invalid phone number format. Include the country calling code.") from exc

        self._opencage_api_key = (opencage_api_key or "").strip()
        self._geocoder: OpenCageGeocode | None = None

    @property
    def geocoder(self) -> OpenCageGeocode:
        """Return an OpenCage client when a key is configured.

        A missing key is an actionable configuration error, rather than an
        attempted request with an empty credential.
        """

        if not self._opencage_api_key:
            raise RuntimeError("OpenCage is not configured. Set OPEN_CAGE_API_KEY before generating a map.")
        if self._geocoder is None:
            self._geocoder = OpenCageGeocode(self._opencage_api_key)
        return self._geocoder

    def validate_number(self) -> dict[str, str | bool]:
        """Return a validation result suitable for presentation in the UI."""

        is_valid = phonenumbers.is_valid_number(self.parsed_number)
        return {
            "is_valid": is_valid,
            "reason": "Valid phone number" if is_valid else self._get_validation_error(),
        }

    def _get_validation_error(self) -> str:
        if not phonenumbers.is_possible_number(self.parsed_number):
            return "The number length is invalid for its numbering plan."
        if not self.get_region_code():
            return "The country calling code is invalid or unsupported."
        return "The number does not match a valid regional numbering pattern."

    def get_info(self) -> PhoneInfo:
        """Return formatted values and public metadata for a valid number."""

        validation = self.validate_number()
        if not validation["is_valid"]:
            raise ValueError(str(validation["reason"]))

        return PhoneInfo(
            international=phonenumbers.format_number(self.parsed_number, PhoneNumberFormat.INTERNATIONAL),
            national=phonenumbers.format_number(self.parsed_number, PhoneNumberFormat.NATIONAL),
            e164=phonenumbers.format_number(self.parsed_number, PhoneNumberFormat.E164),
            region=geocoder.description_for_number(self.parsed_number, "en") or "Unknown",
            country_code=self.get_region_code(),
            carrier=carrier.name_for_number(self.parsed_number, "en") or None,
            timezones=tuple(timezone.time_zones_for_number(self.parsed_number)),
            number_type=self.get_number_type(),
        )

    def get_basic_info(self) -> dict[str, Any]:
        """Return the legacy dictionary form for downstream compatibility."""

        return self.get_info().as_legacy_dict()

    def get_region_code(self) -> str | None:
        """Return the ISO 3166-1 region code associated with the number."""

        return phonenumbers.region_code_for_number(self.parsed_number)

    def get_number_type(self) -> str:
        """Return the libphonenumber category without relying on magic integers."""

        type_names = {
            PhoneNumberType.FIXED_LINE: "Fixed line",
            PhoneNumberType.MOBILE: "Mobile",
            PhoneNumberType.FIXED_LINE_OR_MOBILE: "Fixed line or mobile",
            PhoneNumberType.TOLL_FREE: "Toll free",
            PhoneNumberType.PREMIUM_RATE: "Premium rate",
            PhoneNumberType.SHARED_COST: "Shared cost",
            PhoneNumberType.VOIP: "VoIP",
            PhoneNumberType.PERSONAL_NUMBER: "Personal number",
            PhoneNumberType.PAGER: "Pager",
            PhoneNumberType.UAN: "Universal access number",
            PhoneNumberType.VOICEMAIL: "Voicemail",
            PhoneNumberType.UNKNOWN: "Unknown",
        }
        return type_names.get(phonenumbers.number_type(self.parsed_number), "Unknown")
