import os

# Configuration for Phoenix Tool API Keys
# You can set these as environment variables or edit them here.

# OpenCage API Key for Geocoding (https://opencagedata.com/)
OPEN_CAGE_API_KEY = os.getenv("OPEN_CAGE_API_KEY", "")

# Have I Been Pwned API Key (https://haveibeenpwned.com/API/Key)
HIBP_API_KEY = os.getenv("HIBP_API_KEY", "")

# Geoapify API Key for IP Geolocation (https://www.geoapify.com/)
GEOAPIFY_API_KEY = os.getenv("GEOAPIFY_API_KEY", "")
