import asyncio
from holehe import core
import whois
import requests
from config import HIBP_API_KEY, GEOAPIFY_API_KEY
import phonenumbers
from phonenumbers import carrier, geocoder, timezone, PhoneNumberFormat
from socialscan.util import sync_execute_queries

class OSINTAnalyzer:
    def __init__(self):
        pass

    async def analyze_email_or_username(self, query):
        results = await core.core(query, no_api_key=True, no_clear=True, no_color=True)
        return results

    def analyze_phone_number_basic_info(self, phone_number):
        try:
            parse = phonenumbers.parse(phone_number)
            if not phonenumbers.is_valid_number(parse):
                return "Invalid phone number."
            region = geocoder.description_for_number(parse, 'en')
            timezones = timezone.time_zones_for_number(parse)
            
            result = f"--- Phone Number Basic Info ---\n"
            result += f"Parsed Phone Number: {parse}\n"
            result += f"Region: {region}\n"
            result += f"Time Zone(s): {', '.join(timezones)}\n"
            return result
        except Exception as e:
            return f"Error getting basic phone info: {e}"

    def analyze_phone_number_isp(self, phone_number):
        try:
            parse = phonenumbers.parse(phone_number)
            if not phonenumbers.is_valid_number(parse):
                return "Invalid phone number."
            isp = carrier.name_for_number(parse, 'en')
            return f"--- Phone Number ISP ---\nISP: {isp}\n"
        except Exception as e:
            return f"Error getting phone number ISP: {e}"

    def validate_phone_number(self, phone_number):
        try:
            parse = phonenumbers.parse(phone_number)
            is_valid = phonenumbers.is_valid_number(parse)
            return f"--- Phone Number Validation ---\nIs Valid: {is_valid}\n"
        except Exception as e:
            return f"Error validating phone number: {e}"

    def analyze_email_domain(self, email_address):
        try:
            domain = email_address.split('@')[-1]
            w = whois.whois(domain)
            return w.text
        except Exception as e:
            return f"Error performing WHOIS lookup: {e}"

    def check_breach(self, email_address):
        if not HIBP_API_KEY or HIBP_API_KEY == "YOUR_HIBP_API_KEY":
            return "HIBP API key not configured. Please add your API key to config.py to use this feature."

        headers = {
            "hibp-api-key": HIBP_API_KEY,
            "User-Agent": "Pheonix-Phone-Tool"
        }
        url = f"https://haveibeenpwned.com/api/v3/breachedaccount/{email_address}"
        
        try:
            response = requests.get(url, headers=headers, timeout=10)
            if response.status_code == 200:
                breaches = response.json()
                if breaches:
                    result_text = f"Breaches found for {email_address}:\n"
                    for breach in breaches:
                        result_text += f"  - {breach['Title']} (Domain: {breach['Domain']}, Date: {breach['BreachDate']})\n"
                    return result_text
                else:
                    return f"No breaches found for {email_address}."
            elif response.status_code == 404:
                return f"No breaches found for {email_address}."
            elif response.status_code == 401:
                return "HIBP API key is invalid. Please check your API key in config.py."
            else:
                return f"Error checking breaches: {response.status_code} - {response.text}"
        except requests.exceptions.RequestException as e:
            return f"Network error during HIBP API call: {e}"
        except Exception as e:
            return f"An unexpected error occurred during breach check: {e}"

    def enumerate_social_media_username(self, username):
        try:
            results = sync_execute_queries([username])
            output = f"--- Social Media Username Enumeration for {username} ---\n"
            found_any = False
            for result in results:
                if result.available == False and result.valid == True:
                    output += f"  - {result.platform}: Found (URL: {result.uri})\n"
                    found_any = True
                elif result.valid == False:
                    output += f"  - {result.platform}: Invalid/Unavailable\n"
            if not found_any:
                output += "No profiles found for this username on supported platforms.\n"
            return output
        except Exception as e:
            return f"Error during social media username enumeration: {e}"

    def analyze_ip_address(self, ip_address):
        results = ""
        # Geoapify IP Geolocation
        if GEOAPIFY_API_KEY and GEOAPIFY_API_KEY != "YOUR_GEOAPIFY_API_KEY":
            geo_url = f"https://api.geoapify.com/v1/ipinfo?ip={ip_address}&apiKey={GEOAPIFY_API_KEY}"
            try:
                geo_response = requests.get(geo_url, timeout=10)
                if geo_response.status_code == 200:
                    geo_data = geo_response.json()
                    results += "--- IP Geolocation (Geoapify) ---\n"
                    if 'city' in geo_data and 'name' in geo_data['city']:
                        results += f"City: {geo_data['city']['name']}\n"
                    if 'state' in geo_data and 'name' in geo_data['state']:
                        results += f"State: {geo_data['state']['name']}\n"
                    if 'country' in geo_data and 'name' in geo_data['country']:
                        results += f"Country: {geo_data['country']['name']}\n"
                    if 'location' in geo_data:
                        results += f"Latitude: {geo_data['location']['latitude']}, Longitude: {geo_data['location']['longitude']}\n"
                    results += "\n"
                else:
                    results += f"Error with Geoapify IP Geolocation: {geo_response.status_code} - {geo_response.text}\n\n"
            except requests.exceptions.RequestException as e:
                results += f"Network error during Geoapify API call: {e}\n\n"
            except Exception as e:
                results += f"An unexpected error occurred during Geoapify IP Geolocation: {e}\n\n"
        else:
            results += "Geoapify API key not configured. Please add your API key to config.py to use IP geolocation.\n\n"

        # WHOIS Lookup
        results += "--- IP WHOIS Lookup ---\n"
        try:
            w = whois.whois(ip_address)
            results += str(w)
        except Exception as e:
            results += f"Error performing IP WHOIS lookup: {e}\n"
        
        return results
