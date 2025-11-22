'''
import phonenumbers
from phonenumbers import carrier, geocoder, timezone, PhoneNumberFormat
from colorama import init, Fore, Style
import sys
import json
from datetime import datetime
import csv
import re
import asyncio
from holehe import core
import warnings
import bs4
from bs4 import BeautifulSoup, GuessedAtParserWarning
import tqdm
import tkinter as tk
from tkinter import ttk, scrolledtext
import threading
import aiohttp
import os
import folium
from opencage.geocoder import OpenCageGeocode
import math
import webbrowser
from pathlib import Path
import tkinter.messagebox
import hashlib
import tkinter.filedialog

# Monkey patch tqdm to handle cleanup gracefully
def _del(self):
    try:
        self.close()
    except:
        pass
tqdm.tqdm.__del__ = _del

# Suppress BeautifulSoup warnings
warnings.filterwarnings("ignore", category=GuessedAtParserWarning)

# Configure BeautifulSoup to use lxml parser by default
def _create_soup(*args, **kwargs):
    kwargs['features'] = 'lxml'
    return BeautifulSoup(*args, **kwargs)

bs4.BeautifulSoup = _create_soup

init()  # Initialize colorama for colored output

class PhoneAnalyzer:
    def __init__(self, phone_number):
        self.raw_number = phone_number
        try:
            self.parsed_number = phonenumbers.parse(phone_number)
            # Set OpenCage API key directly
            api_key = "4caa004068ab4c10892476face352941"  # Your OpenCage API key
            self.geocoder = OpenCageGeocode(api_key)
            print(f"{Fore.GREEN}OpenCage API initialized successfully{Style.RESET_ALL}")
        except phonenumbers.NumberParseException:
            print(f"{Fore.RED}Error: Invalid phone number format{Style.RESET_ALL}")
            sys.exit(1)

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

class PhoneAnalyzerGUI:
    def __init__(self, root):
        self.root = root
        self.root.title("Phone Information Tool")
        self.root.geometry("800x600")
        
        # Configure style
        style = ttk.Style()
        style.configure("TButton", padding=5)
        style.configure("TLabel", padding=5)
        style.configure("TEntry", padding=5)
        
        # Create main frame
        main_frame = ttk.Frame(root, padding="10")
        main_frame.grid(row=0, column=0, sticky=(tk.W, tk.E, tk.N, tk.S))
        
        # Empty frame to replace demo labels
        demo_frame = ttk.Frame(main_frame)
        demo_frame.grid(row=0, column=0, columnspan=5, sticky=tk.W)
        
        # Phone number input
        ttk.Label(main_frame, text="Enter Phone Number:").grid(row=1, column=0, sticky=tk.W)
        self.phone_entry = ttk.Entry(main_frame, width=30)
        self.phone_entry.grid(row=1, column=1, sticky=(tk.W, tk.E), padx=5)
        self.phone_entry.insert(0, "+1234567890")  # Default placeholder
        
        # Analyze button
        self.analyze_btn = ttk.Button(main_frame, text="Analyze", command=self.start_analysis)
        self.analyze_btn.grid(row=1, column=2, padx=5)
        
        # Clear button
        clear_btn = ttk.Button(main_frame, text="Clear", command=self.clear_results)
        clear_btn.grid(row=1, column=3, padx=5)
        
        # View Map button
        self.view_map_btn = ttk.Button(main_frame, text="View Map", command=self.view_map)
        self.view_map_btn.grid(row=1, column=4, padx=5)
        self.view_map_btn.state(['disabled'])
        
        # Empty space to replace upgrade button
        ttk.Label(main_frame, text="").grid(row=1, column=5, padx=5)
        
        # Results area with tabs
        self.notebook = ttk.Notebook(main_frame)
        self.notebook.grid(row=2, column=0, columnspan=5, sticky=(tk.W, tk.E, tk.N, tk.S), pady=10)
        
        # Basic Info tab
        self.basic_info_frame = ttk.Frame(self.notebook)
        self.notebook.add(self.basic_info_frame, text="Basic Info")
        self.basic_info_text = scrolledtext.ScrolledText(self.basic_info_frame, wrap=tk.WORD, height=20)
        self.basic_info_text.pack(expand=True, fill='both', padx=5, pady=5)
        
        # Social Accounts tab
        self.social_frame = ttk.Frame(self.notebook)
        self.notebook.add(self.social_frame, text="Social Accounts")
        
        # Create a frame for social media results and buttons
        social_content_frame = ttk.Frame(self.social_frame)
        social_content_frame.pack(expand=True, fill='both', padx=5, pady=5)
        
        # Text area for social media results
        self.social_text = scrolledtext.ScrolledText(social_content_frame, wrap=tk.WORD, height=15)
        self.social_text.pack(expand=True, fill='both', padx=5, pady=5)
        
        # Frame for social media buttons
        self.social_buttons_frame = ttk.Frame(social_content_frame)
        self.social_buttons_frame.pack(fill='x', padx=5, pady=5)
        
        # Social media buttons
        self.telegram_btn = ttk.Button(self.social_buttons_frame, text="Open in Telegram", 
                                     command=lambda: self.open_social_media("telegram"), state='disabled')
        self.telegram_btn.pack(side=tk.LEFT, padx=2)
        
        self.whatsapp_btn = ttk.Button(self.social_buttons_frame, text="Open in WhatsApp", 
                                      command=lambda: self.open_social_media("whatsapp"), state='disabled')
        self.whatsapp_btn.pack(side=tk.LEFT, padx=2)
        
        self.facebook_btn = ttk.Button(self.social_buttons_frame, text="Open in Facebook", 
                                     command=lambda: self.open_social_media("facebook"), state='disabled')
        self.facebook_btn.pack(side=tk.LEFT, padx=2)
        
        self.instagram_btn = ttk.Button(self.social_buttons_frame, text="Open in Instagram", 
                                      command=lambda: self.open_social_media("instagram"), state='disabled')
        self.instagram_btn.pack(side=tk.LEFT, padx=2)
        
        # Map tab
        self.map_frame = ttk.Frame(self.notebook)
        self.notebook.add(self.map_frame, text="Location Map")
        self.map_text = scrolledtext.ScrolledText(self.map_frame, wrap=tk.WORD, height=20)
        self.map_text.pack(expand=True, fill='both', padx=5, pady=5)
        
        # Status bar
        self.status_var = tk.StringVar()
        self.status_bar = ttk.Label(main_frame, textvariable=self.status_var, relief=tk.SUNKEN)
        self.status_bar.grid(row=3, column=0, columnspan=5, sticky=(tk.W, tk.E))
        
        # Configure grid weights
        main_frame.columnconfigure(1, weight=1)
        main_frame.rowconfigure(2, weight=1)
        root.columnconfigure(0, weight=1)
        root.rowconfigure(0, weight=1)
        
        # Store the current phone number
        self.current_phone = None
        self.analyzer = None

    def start_analysis(self):
        """Start the phone number analysis"""
        try:
            phone_number = self.phone_entry.get().strip()
            self.analyzer = PhoneAnalyzer(phone_number)
            self.current_phone = phone_number
            
            # Update basic info
            validation = self.analyzer.validate_number()
            if not validation["is_valid"]:
                self.status_var.set(f"Invalid phone number: {validation['reason']}")
                return

            basic_info = self.analyzer.get_basic_info()
            number_type = self.analyzer.get_number_type()

            info_text = f"Phone Number Analysis:\n\n"
            info_text += f"International Format: {basic_info['formatted']['international']}\n"
            info_text += f"National Format: {basic_info['formatted']['national']}\n"
            info_text += f"E164 Format: {basic_info['formatted']['e164']}\n"
            info_text += f"Region: {basic_info['region']}\n"
            info_text += f"Carrier: {basic_info['carrier'] or 'Unknown'}\n"
            info_text += f"Timezone(s): {', '.join(basic_info['timezone'])}\n"
            info_text += f"Number Type: {number_type}\n"

            self.basic_info_text.delete(1.0, tk.END)
            self.basic_info_text.insert(tk.END, info_text)
            
            # Enable map button
            self.view_map_btn.state(['!disabled'])
            
            # Enable social media buttons
            self.telegram_btn.state(['!disabled'])
            self.whatsapp_btn.state(['!disabled'])
            self.facebook_btn.state(['!disabled'])
            self.instagram_btn.state(['!disabled'])
            
            self.status_var.set("Analysis complete.")

        except Exception as e:
            self.status_var.set(str(e))

    def clear_results(self):
        """Clear all results"""
        self.basic_info_text.delete(1.0, tk.END)
        self.social_text.delete(1.0, tk.END)
        self.map_text.delete(1.0, tk.END)
        self.status_var.set("")
        self.view_map_btn.state(['disabled'])
        self.current_phone = None
        
        # Disable social media buttons
        self.telegram_btn.state(['disabled'])
        self.whatsapp_btn.state(['disabled'])
        self.facebook_btn.state(['disabled'])
        self.instagram_btn.state(['disabled'])

    def open_social_media(self, platform):
        """Open the phone number in various social media platforms"""
        try:
            if not self.current_phone:
                return
                
            number = self.current_phone.replace("+", "").replace(" ", "")
            urls = {
                "telegram": f"https://t.me/+{number}",
                "whatsapp": f"https://wa.me/{number}",
                "facebook": f"https://www.facebook.com/search/top/?q={number}",
                "instagram": f"https://www.instagram.com/explore/tags/{number}"
            }
            
            if platform in urls:
                webbrowser.open(urls[platform])
                
            self.status_var.set(f"Opened {platform}.")
                
        except Exception as e:
            self.status_var.set(str(e))

    def view_map(self):
        """View the location on a map"""
        try:
            if not self.analyzer:
                return

            region = self.analyzer.get_basic_info()['region']
            if not region:
                self.status_var.set("Region not found, cannot generate map.")
                return

            results = self.analyzer.geocoder.geocode(region)

            if results and len(results):
                lat = results[0]['geometry']['lat']
                lng = results[0]['geometry']['lng']

                # Create map
                m = folium.Map(location=[lat, lng], zoom_start=10)
                folium.Marker([lat, lng], popup=region).add_to(m)

                # Save to file
                map_file = "location_map.html"
                m.save(map_file)
                webbrowser.open(map_file)
                self.map_text.delete(1.0, tk.END)
                self.map_text.insert(tk.END, f"Map saved to {map_file} and opened in browser.")
            else:
                self.map_text.delete(1.0, tk.END)
                self.map_text.insert(tk.END, "Could not find location.")

            self.status_var.set("Map generated.")
                
        except Exception as e:
            self.status_var.set(str(e))

if __name__ == "__main__":
    root = tk.Tk()
    app = PhoneAnalyzerGUI(root)
    root.mainloop()
'''
