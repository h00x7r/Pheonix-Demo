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
tqdm.__del__ = _del

# Suppress BeautifulSoup warnings
warnings.filterwarnings("ignore", category=GuessedAtParserWarning)

# Configure BeautifulSoup to use lxml parser by default
def _create_soup(*args, **kwargs):
    kwargs['features'] = 'lxml'
    return BeautifulSoup(*args, **kwargs)

bs4.BeautifulSoup = _create_soup

init()  # Initialize colorama for colored output

class DemoTracker:
    DEMO_FILE = os.path.join(str(Path.home()), '.phone_analyzer_demo_usage')
    MAX_USES = 3

    @classmethod
    def _get_usage_data(cls):
        try:
            if os.path.exists(cls.DEMO_FILE):
                with open(cls.DEMO_FILE, 'r') as f:
                    data = json.load(f)
                return data
            return {
                'basic_info': 0,
                'social_media': 0,
                'map': 0
            }
        except:
            return {
                'basic_info': 0,
                'social_media': 0,
                'map': 0
            }

    @classmethod
    def _save_usage_data(cls, data):
        try:
            with open(cls.DEMO_FILE, 'w') as f:
                json.dump(data, f)
        except:
            pass

    @classmethod
    def get_feature_usage(cls, feature):
        """Get usage count for a specific feature"""
        data = cls._get_usage_data()
        return data.get(feature, 0)

    @classmethod
    def increment_feature_usage(cls, feature):
        """Increment usage count for a specific feature"""
        data = cls._get_usage_data()
        data[feature] = data.get(feature, 0) + 1
        cls._save_usage_data(data)
        return data[feature]

    @classmethod
    def check_feature_limit(cls, feature):
        """Check if a specific feature has reached its limit"""
        count = cls.get_feature_usage(feature)
        if count >= cls.MAX_USES:
            raise Exception(f"Demo limit reached for {feature.replace('_', ' ')} ({cls.MAX_USES} uses)")
        return True

    @classmethod
    def get_remaining_uses(cls):
        """Get remaining uses for all features"""
        data = cls._get_usage_data()
        return {
            'basic_info': cls.MAX_USES - data.get('basic_info', 0),
            'social_media': cls.MAX_USES - data.get('social_media', 0),
            'map': cls.MAX_USES - data.get('map', 0)
        }

class PhoneAnalyzerDemo:
    def __init__(self, phone_number):
        DemoTracker.check_feature_limit('basic_info')
        self.raw_number = phone_number
        try:
            self.parsed_number = phonenumbers.parse(phone_number)
            # Set OpenCage API key directly
            api_key = "4caa004068ab4c10892476face352941"  # Your OpenCage API key
            self.geocoder = OpenCageGeocode(api_key)
            print(f"{Fore.GREEN}OpenCage API initialized successfully{Style.RESET_ALL}")
            DemoTracker.increment_feature_usage('basic_info')
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

class LicenseManager:
    LICENSE_FILE = os.path.join(str(Path.home()), '.phone_analyzer_license')
    HWID_SALT = "PA2024"  # Salt for hardware ID

    @staticmethod
    def get_hardware_id():
        """Generate a unique hardware ID"""
        try:
            import uuid
            # Get system UUID
            system_id = str(uuid.getnode())
            # Get disk serial
            import subprocess
            try:
                result = subprocess.check_output('wmic diskdrive get SerialNumber', shell=True).decode()
                disk_serial = result.split('\n')[1].strip()
            except:
                disk_serial = "unknown"
            
            # Combine and hash
            hw_string = f"{system_id}-{disk_serial}-{LicenseManager.HWID_SALT}"
            return hashlib.sha256(hw_string.encode()).hexdigest()[:16]
        except:
            return "unknown"

    @staticmethod
    def generate_license_key(email):
        """Generate a license key for a given email"""
        key = hashlib.sha256(f"phoneanalyzer2024{email}".encode()).hexdigest()[:32]
        return f"PA-{key[:8]}-{key[8:16]}-{key[16:24]}-{key[24:]}"

    @classmethod
    def verify_license(cls):
        """Verify if a valid license exists"""
        try:
            if os.path.exists(cls.LICENSE_FILE):
                with open(cls.LICENSE_FILE, 'r') as f:
                    data = json.load(f)
                    if all(k in data for k in ['license_key', 'email', 'hardware_id']):
                        # Verify hardware ID matches
                        current_hwid = cls.get_hardware_id()
                        if data['hardware_id'] != current_hwid:
                            print(f"{Fore.RED}License is bound to a different system.{Style.RESET_ALL}")
                            return False
                        # Verify license key matches email
                        expected_key = cls.generate_license_key(data['email'])
                        return data['license_key'] == expected_key
            return False
        except:
            return False

    @classmethod
    def activate_license(cls, license_key, email):
        """Activate the software with a license key"""
        try:
            # Check if license is already activated
            if os.path.exists(cls.LICENSE_FILE):
                return False

            # Verify license key matches email
            expected_key = cls.generate_license_key(email)
            if license_key != expected_key:
                return False

            # Get hardware ID
            hardware_id = cls.get_hardware_id()
            
            # Save license info
            with open(cls.LICENSE_FILE, 'w') as f:
                json.dump({
                    'license_key': license_key,
                    'email': email,
                    'hardware_id': hardware_id,
                    'activation_date': datetime.now().isoformat()
                }, f)
            return True
        except Exception as e:
            print(f"Error during activation: {str(e)}")
            return False

class ActivationDialog:
    def __init__(self, parent, prefill_email=""):
        self.dialog = tk.Toplevel(parent)
        self.dialog.title("Activate Full Version")
        self.dialog.geometry("400x300")  # Made taller for help text
        self.dialog.transient(parent)
        self.dialog.grab_set()

        # Activation frame
        activation_frame = ttk.Frame(self.dialog, padding="20")
        activation_frame.pack(fill=tk.BOTH, expand=True)

        # Title
        title_label = ttk.Label(activation_frame,
                              text="Enter License Information",
                              font=("Helvetica", 12, "bold"))
        title_label.pack(pady=(0, 15))

        # Email entry
        ttk.Label(activation_frame, text="Email:").pack(anchor=tk.W)
        self.email_entry = ttk.Entry(activation_frame, width=40)
        self.email_entry.pack(fill=tk.X, pady=(0, 5))
        if prefill_email:
            self.email_entry.insert(0, prefill_email)
        
        # Email help text
        ttk.Label(activation_frame, 
                 text="⚠️ Use the same email you used for payment",
                 foreground='red').pack(anchor=tk.W, pady=(0, 10))

        # License key entry
        ttk.Label(activation_frame, text="License Key:").pack(anchor=tk.W)
        self.key_entry = ttk.Entry(activation_frame, width=40)
        self.key_entry.pack(fill=tk.X, pady=(0, 5))
        
        # License key help text
        ttk.Label(activation_frame, 
                 text="Enter the license key sent to your email",
                 foreground='gray').pack(anchor=tk.W, pady=(0, 20))

        # Buttons frame
        button_frame = ttk.Frame(activation_frame)
        button_frame.pack(fill=tk.X)

        # Center frame for buttons
        center_frame = ttk.Frame(button_frame)
        center_frame.pack(anchor=tk.CENTER)

        # OK button
        ok_btn = ttk.Button(center_frame, 
                          text="OK",
                          command=self.activate_license,
                          width=10)
        ok_btn.pack(side=tk.LEFT, padx=5)

        # Cancel button
        cancel_btn = ttk.Button(center_frame,
                             text="Cancel",
                             command=self.dialog.destroy,
                             width=10)
        cancel_btn.pack(side=tk.LEFT, padx=5)

    def activate_license(self):
        license_key = self.key_entry.get().strip()
        email = self.email_entry.get().strip()

        if not license_key or not email:
            tkinter.messagebox.showerror("Error", "Please enter both license key and email")
            return

        # Check if license is already activated
        if os.path.exists(LicenseManager.LICENSE_FILE):
            tkinter.messagebox.showerror("Error", 
                "A license is already activated on this system.\n" +
                "Each license can only be activated on one system.")
            return

        if LicenseManager.activate_license(license_key, email):
            tkinter.messagebox.showinfo("Success", 
                "License activated successfully!\n\n" +
                "Important Notes:\n" +
                "1. This license is now bound to your system\n" +
                "2. It cannot be used on other computers\n" +
                "3. Please restart the application to use the full version")
            self.dialog.destroy()
            sys.exit(0)  # Exit the demo version
        else:
            tkinter.messagebox.showerror("Error", 
                "Invalid license key or email.\n\n" +
                "Please make sure:\n" +
                "1. You entered the exact license key sent to you\n" +
                "2. You used the same email used for payment\n" +
                "3. This license hasn't been used on another system")

class PaymentDialog:
    def __init__(self, parent):
        self.dialog = tk.Toplevel(parent)
        self.dialog.title("Upgrade to Full Version")
        self.dialog.geometry("500x700")  # Made taller for verify button
        self.dialog.transient(parent)
        self.dialog.grab_set()

        # Main frame
        payment_frame = ttk.Frame(self.dialog, padding="20")
        payment_frame.pack(fill=tk.BOTH, expand=True)

        # Title
        title_label = ttk.Label(payment_frame,
                              text="Upgrade to Full Version",
                              font=("Helvetica", 14, "bold"))
        title_label.pack(pady=(0, 10))

        # Price frame
        price_frame = ttk.Frame(payment_frame)
        price_frame.pack(fill=tk.X, pady=(0, 20))

        # Price label
        price_label = ttk.Label(price_frame,
                              text="Price: 3 USDT",
                              font=("Helvetica", 12, "bold"),
                              foreground='green')
        price_label.pack(anchor=tk.CENTER)

        # Email frame
        email_frame = ttk.Frame(payment_frame)
        email_frame.pack(fill=tk.X, pady=(0, 20))

        # Email entry
        ttk.Label(email_frame, text="Your Email (required for activation):").pack(anchor=tk.W)
        self.email_entry = ttk.Entry(email_frame, width=50)
        self.email_entry.pack(fill=tk.X, pady=(5, 0))
        ttk.Label(email_frame, 
                 text="⚠️ Save this email! You'll need it to activate your license",
                 foreground='red').pack(anchor=tk.W, pady=(5, 0))

        # Transaction Hash frame
        hash_frame = ttk.Frame(payment_frame)
        hash_frame.pack(fill=tk.X, pady=(0, 20))

        # Transaction Hash entry
        ttk.Label(hash_frame, text="Transaction Hash:").pack(anchor=tk.W)
        self.hash_entry = ttk.Entry(hash_frame, width=50)
        self.hash_entry.pack(fill=tk.X, pady=(5, 0))

        # Wallet address frame
        address_frame = ttk.Frame(payment_frame)
        address_frame.pack(fill=tk.X, pady=(0, 20))

        address_label = ttk.Label(address_frame,
                                text="USDT (ERC20) Wallet Address:")
        address_label.pack(side=tk.LEFT)

        copy_btn = ttk.Button(address_frame,
                            text="Copy",
                            command=self.copy_address)
        copy_btn.pack(side=tk.RIGHT)

        # Address display
        address_display = ttk.Entry(payment_frame, width=50)
        address_display.insert(0, "0x3B6C462543F0BFB5F2C5cF6430D27D9E60C62Faf")
        address_display.configure(state="readonly")
        address_display.pack(pady=(0, 20))

        # Instructions
        instructions_text = """Payment Instructions:
1. Enter your email address above (required for activation)
2. Copy the wallet address
3. Send exactly 3 USDT (ERC20) to activate full version
4. Enter your transaction hash above
5. Click 'Verify Payment' to get your license key immediately

Important Notes:
• Payment amount must be exactly 3 USDT
• Use the same email for payment and activation
• Keep your email safe - you'll need it to activate
• Make sure to use the ERC20 network for USDT transfer
• Save your license key in a safe place

Features You'll Get:
• Unlimited phone number analysis
• Unlimited social media lookups
• Unlimited map location views
• All future updates included
• Priority support"""

        instructions_label = ttk.Label(payment_frame,
                                    text=instructions_text,
                                    justify=tk.LEFT,
                                    wraplength=400)
        instructions_label.pack(pady=(0, 20), anchor=tk.W)

        # Verify Payment button
        verify_btn = ttk.Button(payment_frame,
                              text="Verify Payment",
                              command=self.verify_payment)
        verify_btn.pack(pady=(0, 10))

        # Button Frame
        button_frame = ttk.Frame(payment_frame)
        button_frame.pack(fill=tk.X, pady=(0, 10))

        # Add Activate License button
        activate_btn = ttk.Button(button_frame,
                                text="Already Have a License Key?",
                                command=lambda: self.show_activation_dialog(parent))
        activate_btn.pack(side=tk.LEFT, padx=5)

        # Close button
        close_btn = ttk.Button(button_frame,
                             text="Close",
                             command=self.dialog.destroy)
        close_btn.pack(side=tk.LEFT)

    def copy_address(self):
        self.dialog.clipboard_clear()
        self.dialog.clipboard_append("0x3B6C462543F0BFB5F2C5cF6430D27D9E60C62Faf")
        self.dialog.update()

    def verify_payment(self):
        email = self.email_entry.get().strip()
        tx_hash = self.hash_entry.get().strip()

        if not email or not tx_hash:
            tkinter.messagebox.showerror("Error", "Please enter both email and transaction hash")
            return

        # Here you would verify the transaction hash
        # For demo, we'll generate the license key directly
        license_key = LicenseManager.generate_license_key(email)

        # Create a new dialog to show the license key
        result_dialog = tk.Toplevel(self.dialog)
        result_dialog.title("License Key Generated")
        result_dialog.geometry("500x300")
        result_dialog.transient(self.dialog)
        result_dialog.grab_set()

        # Main frame
        frame = ttk.Frame(result_dialog, padding="20")
        frame.pack(fill=tk.BOTH, expand=True)

        # Success message
        success_label = ttk.Label(frame,
                                text="Payment Verified Successfully!",
                                font=("Helvetica", 12, "bold"),
                                foreground='green')
        success_label.pack(pady=(0, 20))

        # License key display
        ttk.Label(frame, text="Your License Key:").pack()
        key_text = tk.Text(frame, height=3, width=40)
        key_text.insert('1.0', license_key)
        key_text.configure(state='readonly')
        key_text.pack(pady=(5, 10))

        # Copy button
        copy_btn = ttk.Button(frame,
                            text="Copy License Key",
                            command=lambda: self.copy_license_key(license_key))
        copy_btn.pack(pady=(0, 10))

        # Save button
        save_btn = ttk.Button(frame,
                            text="Save License Key to File",
                            command=lambda: self.save_license_key(email, license_key))
        save_btn.pack(pady=(0, 10))

        # Close button
        ttk.Button(frame,
                  text="Close",
                  command=result_dialog.destroy).pack()

    def copy_license_key(self, license_key):
        self.dialog.clipboard_clear()
        self.dialog.clipboard_append(license_key)
        self.dialog.update()
        tkinter.messagebox.showinfo("Success", "License key copied to clipboard!")

    def save_license_key(self, email, license_key):
        # Ask user where to save the file
        file_path = tkinter.filedialog.asksaveasfilename(
            defaultextension=".txt",
            filetypes=[("Text files", "*.txt")],
            initialfile="phone_analyzer_license.txt",
            title="Save License Key"
        )
        
        if file_path:
            try:
                with open(file_path, 'w') as f:
                    f.write(f"Phone Analyzer License Information\n")
                    f.write(f"================================\n\n")
                    f.write(f"Email: {email}\n")
                    f.write(f"License Key: {license_key}\n\n")
                    f.write(f"Important:\n")
                    f.write(f"1. Keep this file in a safe place\n")
                    f.write(f"2. You'll need both email and license key to activate\n")
                    f.write(f"3. This license is tied to your hardware and can only be used once\n")
                tkinter.messagebox.showinfo("Success", f"License key saved to:\n{file_path}")
            except Exception as e:
                tkinter.messagebox.showerror("Error", f"Failed to save license key: {str(e)}")

    def show_activation_dialog(self, parent):
        # Pass the email if entered
        email = self.email_entry.get().strip() if hasattr(self, 'email_entry') else ""
        self.dialog.destroy()
        ActivationDialog(parent, email)

def show_upgrade_dialog(parent):
    PaymentDialog(parent)

class PhoneAnalyzerGUIDemo:
    def __init__(self, root):
        self.root = root
        self.root.title("Phone Information Tool (Demo Version)")
        self.root.geometry("800x600")
        
        # Configure style
        style = ttk.Style()
        style.configure("TButton", padding=5)
        style.configure("TLabel", padding=5)
        style.configure("TEntry", padding=5)
        
        # Create main frame
        main_frame = ttk.Frame(root, padding="10")
        main_frame.grid(row=0, column=0, sticky=(tk.W, tk.E, tk.N, tk.S))
        
        # Demo version labels
        remaining = DemoTracker.get_remaining_uses()
        demo_frame = ttk.Frame(main_frame)
        demo_frame.grid(row=0, column=0, columnspan=5, sticky=tk.W)
        
        ttk.Label(demo_frame, text="DEMO VERSION", foreground='red',
                 font=('Arial', 10, 'bold')).pack(side=tk.LEFT, padx=5)
        
        for feature, uses in remaining.items():
            ttk.Label(demo_frame, 
                     text=f"{feature.replace('_', ' ').title()}: {uses} uses left",
                     foreground='blue').pack(side=tk.LEFT, padx=5)
        
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
        
        # Upgrade button
        self.upgrade_btn = ttk.Button(main_frame, text="Upgrade to Full Version", 
                                    command=lambda: show_upgrade_dialog(self.root))
        self.upgrade_btn.grid(row=1, column=5, padx=5)
        
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
            DemoTracker.check_feature_limit('basic_info')
            phone_number = self.phone_entry.get().strip()
            self.analyzer = PhoneAnalyzerDemo(phone_number)
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
            
            # Enable map button if map feature still has uses
            try:
                DemoTracker.check_feature_limit('map')
                self.view_map_btn.state(['!disabled'])
            except:
                self.view_map_btn.state(['disabled'])
            
            # Enable social media buttons if social media feature still has uses
            try:
                DemoTracker.check_feature_limit('social_media')
                self.telegram_btn.state(['!disabled'])
                self.whatsapp_btn.state(['!disabled'])
                self.facebook_btn.state(['!disabled'])
                self.instagram_btn.state(['!disabled'])
            except:
                self.telegram_btn.state(['disabled'])
                self.whatsapp_btn.state(['disabled'])
                self.facebook_btn.state(['disabled'])
                self.instagram_btn.state(['disabled'])
            
            # Increment basic info usage and update status
            DemoTracker.increment_feature_usage('basic_info')
            remaining = DemoTracker.get_remaining_uses()
            self.status_var.set(f"Analysis complete. Remaining uses - Basic Info: {remaining['basic_info']}, "
                              f"Social Media: {remaining['social_media']}, Map: {remaining['map']}")

        except Exception as e:
            self.status_var.set(str(e))
            if "Demo limit reached" in str(e):
                tkinter.messagebox.showwarning("Demo Limit Reached", str(e))
                show_upgrade_dialog(self.root)

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
            DemoTracker.check_feature_limit('social_media')
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
                DemoTracker.increment_feature_usage('social_media')
                remaining = DemoTracker.get_remaining_uses()
                self.status_var.set(f"Social media feature used. {remaining['social_media']} uses remaining for social media")
                
                # Disable buttons if no uses left
                if remaining['social_media'] == 0:
                    self.telegram_btn.state(['disabled'])
                    self.whatsapp_btn.state(['disabled'])
                    self.facebook_btn.state(['disabled'])
                    self.instagram_btn.state(['disabled'])
                    
        except Exception as e:
            self.status_var.set(str(e))
            if "Demo limit reached" in str(e):
                tkinter.messagebox.showwarning("Demo Limit Reached", str(e))
                show_upgrade_dialog(self.root)
                self.telegram_btn.state(['disabled'])
                self.whatsapp_btn.state(['disabled'])
                self.facebook_btn.state(['disabled'])
                self.instagram_btn.state(['disabled'])

    def view_map(self):
        """View the location on a map"""
        try:
            DemoTracker.check_feature_limit('map')
            if not self.analyzer:
                return
                
            try:
                basic_info = self.analyzer.get_basic_info()
                region = basic_info['region']
                
                if region:
                    # Get coordinates for the region
                    results = self.analyzer.geocoder.geocode(region)
                    if results and len(results):
                        lat = results[0]['geometry']['lat']
                        lng = results[0]['geometry']['lng']
                        
                        # Create map
                        map_file = "phone_location.html"
                        m = folium.Map(location=[lat, lng], zoom_start=6)
                        folium.Marker([lat, lng], popup=region).add_to(m)
                        m.save(map_file)
                        
                        # Open in browser
                        webbrowser.open(map_file)
                        self.map_text.delete(1.0, tk.END)
                        self.map_text.insert(tk.END, f"Location: {region}\nCoordinates: {lat}, {lng}")
                        
                        # Increment map usage and update status
                        DemoTracker.increment_feature_usage('map')
                        remaining = DemoTracker.get_remaining_uses()
                        self.status_var.set(f"Map feature used. {remaining['map']} uses remaining for map")
                        
                        # Disable map button if no uses left
                        if remaining['map'] == 0:
                            self.view_map_btn.state(['disabled'])
                    else:
                        self.map_text.delete(1.0, tk.END)
                        self.map_text.insert(tk.END, "Could not find coordinates for this region")
                else:
                    self.map_text.delete(1.0, tk.END)
                    self.map_text.insert(tk.END, "No region information available")
                    
            except Exception as e:
                self.map_text.delete(1.0, tk.END)
                self.map_text.insert(tk.END, f"Error generating map: {str(e)}")
                
        except Exception as e:
            self.status_var.set(str(e))
            if "Demo limit reached" in str(e):
                tkinter.messagebox.showwarning("Demo Limit Reached", str(e))
                show_upgrade_dialog(self.root)
                self.view_map_btn.state(['disabled'])

def run_gui():
    """Run the GUI version of the phone analyzer"""
    root = tk.Tk()
    app = PhoneAnalyzerGUIDemo(root)
    root.mainloop()

if __name__ == "__main__":
    try:
        run_gui()
    except Exception as e:
        print(f"\n{Fore.RED}An unexpected error occurred: {str(e)}{Style.RESET_ALL}")
