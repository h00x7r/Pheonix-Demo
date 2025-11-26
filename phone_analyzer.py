import phonenumbers
from phonenumbers import carrier, geocoder, timezone, PhoneNumberFormat
from opencage.geocoder import OpenCageGeocode
from colorama import Fore, Style

class PhoneAnalyzer:
    def __init__(self, phone_number, opencage_api_key):
        self.raw_number = phone_number
        try:
            self.parsed_number = phonenumbers.parse(phone_number)
            self.geocoder = OpenCageGeocode(opencage_api_key)
            print(f"{Fore.GREEN}OpenCage API initialized successfully{Style.RESET_ALL}")
        except phonenumbers.NumberParseException:
            raise ValueError("Invalid phone number format")

    def validate_number(self):
        """
        Check if the phone number is valid.
        A valid number must:
        - Have the correct length for its region
        - Follow the proper number format for that region
        - Have a valid country calling code
        - Match the numbering pattern for that country
        """
        is_valid = phonenumbers.is_valid_number(self.parsed_number)
        validation_details = {
            "is_valid": is_valid,
            "reason": "Valid phone number" if is_valid else self._get_validation_error()
        }
        return validation_details

    def _get_validation_error(self):
        """Get detailed validation error message"""
        if not phonenumbers.is_possible_number(self.parsed_number):
            return "Number length is invalid for this region"
        
        region = self.get_region_code()
        if not region:
            return "Invalid or missing country code"
            
        number_length = len(phonenumbers.format_number(self.parsed_number, PhoneNumberFormat.NATIONAL).replace(" ", ""))
        if number_length < 5:
            return "Number is too short"
        if number_length > 15:
            return "Number is too long"
            
        return "Number format doesn't match region pattern"

    def get_basic_info(self):
        """Get basic information about the phone number"""
        return {
            "formatted": {
                "international": phonenumbers.format_number(self.parsed_number, PhoneNumberFormat.INTERNATIONAL),
                "national": phonenumbers.format_number(self.parsed_number, PhoneNumberFormat.NATIONAL),
                "e164": phonenumbers.format_number(self.parsed_number, PhoneNumberFormat.E164)
            },
            "region": geocoder.description_for_number(self.parsed_number, "en"),
            "carrier": carrier.name_for_number(self.parsed_number, "en"),
            "timezone": timezone.time_zones_for_number(self.parsed_number)
        }

    def get_region_code(self):
        """Get the region code for the phone number"""
        return phonenumbers.region_code_for_number(self.parsed_number)

    def get_number_type(self):
        """Get the type of the phone number"""
        number_type = phonenumbers.number_type(self.parsed_number)
        type_names = {
            0: "FIXED_LINE",
            1: "MOBILE",
            2: "FIXED_LINE_OR_MOBILE",
            3: "TOLL_FREE",
            4: "PREMIUM_RATE",
            5: "SHARED_COST",
            6: "VOIP",
            7: "PERSONAL_NUMBER",
            8: "PAGER",
            9: "UAN",
            10: "UNKNOWN",
            27: "EMERGENCY",
            28: "VOICEMAIL"
        }
        return type_names.get(number_type, "UNKNOWN")
