"""Optional public-data enrichment helpers.

These methods are intended for accounts, domains and infrastructure that the
operator owns or is explicitly authorised to assess.  They use public metadata
and provider APIs; results must not be treated as proof of identity or precise
physical location.
"""

from __future__ import annotations

import ipaddress
import re
from typing import Any
from urllib.parse import quote

import phonenumbers
import requests
from phonenumbers import carrier, geocoder, timezone

from config import GEOAPIFY_API_KEY, HIBP_API_KEY

EMAIL_PATTERN = re.compile(r"^[^@\s]+@[^@\s]+\.[^@\s]+$")
USERNAME_PATTERN = re.compile(r"^[A-Za-z0-9._-]{1,64}$")
DOMAIN_PATTERN = re.compile(r"^(?=.{1,253}$)(?:[A-Za-z0-9](?:[A-Za-z0-9-]{0,61}[A-Za-z0-9])?\.)+[A-Za-z]{2,63}$")


class OSINTAnalyzer:
    """Run optional metadata lookups with bounded network behaviour."""

    timeout_seconds = 15

    def __init__(self, session: requests.Session | None = None) -> None:
        self._session = session or requests.Session()
        self._session.headers.update({"User-Agent": "Pheonix/2026 (authorised-use desktop client)"})

    async def analyze_email_or_username(self, query: str) -> dict[str, Any]:
        """Return Holehe results when its optional dependency is installed."""

        normalized = query.strip()
        if "@" in normalized:
            if not EMAIL_PATTERN.fullmatch(normalized):
                raise ValueError("Enter a valid email address.")
        elif not USERNAME_PATTERN.fullmatch(normalized):
            raise ValueError("Usernames may contain letters, numbers, dots, underscores and dashes only.")

        try:
            from holehe import core
        except ImportError as exc:
            raise RuntimeError(
                "Email/username enrichment is optional. Install the 'osint' dependency group to enable it."
            ) from exc

        return await core.core(normalized, no_api_key=True, no_clear=True, no_color=True)

    def analyze_phone_number_basic_info(self, phone_number: str) -> str:
        """Return non-sensitive numbering-plan metadata for a valid number."""

        try:
            parsed = phonenumbers.parse(phone_number.strip(), None)
        except phonenumbers.NumberParseException:
            return "Invalid phone number format. Include the country calling code."

        if not phonenumbers.is_valid_number(parsed):
            return "Invalid phone number."

        region = geocoder.description_for_number(parsed, "en") or "Unknown"
        timezones = ", ".join(timezone.time_zones_for_number(parsed)) or "Unknown"
        return f"--- Phone Number Metadata ---\nNumbering-plan region: {region}\nTime zone(s): {timezones}\n"

    def analyze_phone_number_isp(self, phone_number: str) -> str:
        """Return the carrier label embedded in public numbering metadata."""

        try:
            parsed = phonenumbers.parse(phone_number.strip(), None)
        except phonenumbers.NumberParseException:
            return "Invalid phone number format. Include the country calling code."

        if not phonenumbers.is_valid_number(parsed):
            return "Invalid phone number."
        provider = carrier.name_for_number(parsed, "en") or "Unknown"
        return f"--- Phone Number Carrier Metadata ---\nCarrier: {provider}\n"

    def validate_phone_number(self, phone_number: str) -> str:
        """Return whether the number matches the relevant numbering plan."""

        try:
            parsed = phonenumbers.parse(phone_number.strip(), None)
        except phonenumbers.NumberParseException:
            return "Invalid phone number format. Include the country calling code."
        return f"--- Phone Number Validation ---\nIs valid: {phonenumbers.is_valid_number(parsed)}\n"

    def analyze_email_domain(self, email_address: str) -> str:
        """Run a WHOIS lookup for the domain portion of a valid email address."""

        normalized = email_address.strip().lower()
        if not EMAIL_PATTERN.fullmatch(normalized):
            return "Enter a valid email address."

        domain = normalized.rsplit("@", 1)[1]
        if not DOMAIN_PATTERN.fullmatch(domain):
            return "Invalid domain format."

        try:
            import whois
        except ImportError:
            return "Domain enrichment is optional. Install the 'osint' dependency group to enable it."

        try:
            result = whois.whois(domain)
            return str(result)
        except Exception as exc:  # Provider/library errors vary by registry.
            return f"Unable to retrieve WHOIS information: {exc}"

    def check_breach(self, email_address: str) -> str:
        """Check an authorised email address through the HIBP API, if configured."""

        normalized = email_address.strip().lower()
        if not EMAIL_PATTERN.fullmatch(normalized):
            return "Enter a valid email address."
        if not HIBP_API_KEY:
            return "HIBP is not configured. Set HIBP_API_KEY to enable this optional feature."

        url = f"https://haveibeenpwned.com/api/v3/breachedaccount/{quote(normalized, safe='')}"
        headers = {"hibp-api-key": HIBP_API_KEY}
        parameters = {"truncateResponse": "false"}

        try:
            response = self._session.get(url, headers=headers, params=parameters, timeout=self.timeout_seconds)
        except requests.RequestException as exc:
            return f"Network error while checking breach data: {exc}"

        if response.status_code == 404:
            return "No breaches reported by the configured provider."
        if response.status_code == 401:
            return "HIBP rejected the configured API key."
        if response.status_code == 429:
            return "HIBP rate limit reached. Please wait before trying again."
        if response.status_code != 200:
            return f"Breach lookup failed with HTTP {response.status_code}."

        breaches = response.json()
        if not breaches:
            return "No breaches reported by the configured provider."

        lines = [f"Breaches reported for {normalized}:"]
        for breach in breaches:
            title = breach.get("Title", "Unknown")
            domain = breach.get("Domain", "Unknown")
            date = breach.get("BreachDate", "Unknown")
            lines.append(f"  - {title} (domain: {domain}; date: {date})")
        return "\n".join(lines)

    def enumerate_social_media_username(self, username: str) -> str:
        """Run optional username availability checks using SocialScan."""

        normalized = username.strip()
        if not USERNAME_PATTERN.fullmatch(normalized):
            return "Usernames may contain letters, numbers, dots, underscores and dashes only."

        try:
            from socialscan.util import sync_execute_queries
        except ImportError:
            return "Username enrichment is optional. Install the 'osint' dependency group to enable it."

        try:
            results = sync_execute_queries([normalized])
        except Exception as exc:
            return f"Username enrichment failed: {exc}"

        lines = [f"--- Username availability results for {normalized} ---"]
        found_any = False
        for result in results:
            if result.available is False and result.valid is True:
                lines.append(f"  - {result.platform}: unavailable / may be registered ({result.uri})")
                found_any = True
        if not found_any:
            lines.append("No potentially registered profiles were returned by the configured providers.")
        return "\n".join(lines)

    def analyze_ip_address(self, ip_address: str) -> str:
        """Return public network-registration metadata for a valid IP address."""

        normalized = ip_address.strip()
        try:
            parsed = ipaddress.ip_address(normalized)
        except ValueError:
            return "Invalid IP address format."
        if not parsed.is_global:
            return "Enter a public, globally routable IP address."

        lines: list[str] = []
        if GEOAPIFY_API_KEY:
            try:
                response = self._session.get(
                    "https://api.geoapify.com/v1/ipinfo",
                    params={"ip": normalized, "apiKey": GEOAPIFY_API_KEY},
                    timeout=self.timeout_seconds,
                )
                response.raise_for_status()
                data = response.json()
                lines.append("--- Approximate IP network metadata (Geoapify) ---")
                if name := data.get("city", {}).get("name"):
                    lines.append(f"City: {name}")
                if name := data.get("state", {}).get("name"):
                    lines.append(f"State: {name}")
                if name := data.get("country", {}).get("name"):
                    lines.append(f"Country: {name}")
            except requests.RequestException as exc:
                lines.append(f"Geoapify request failed: {exc}")
        else:
            lines.append("Geoapify is not configured; approximate IP location is unavailable.")

        try:
            import whois
        except ImportError:
            lines.append("WHOIS lookup is unavailable; install the 'osint' dependency group to enable it.")
            return "\n".join(lines)

        try:
            lines.extend(("", "--- IP registration lookup ---", str(whois.whois(normalized))))
        except Exception as exc:
            lines.append(f"IP registration lookup failed: {exc}")
        return "\n".join(lines)
