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
from config import OPEN_CAGE_API_KEY
from phone_analyzer import PhoneAnalyzer
from osint_analyzer import OSINTAnalyzer

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
        
        # Control Panel Frame for inputs and main buttons
        control_panel_frame = ttk.Frame(main_frame, padding="5")
        control_panel_frame.grid(row=0, column=0, columnspan=5, sticky=(tk.W, tk.E))
        
        # Phone number input
        ttk.Label(control_panel_frame, text="Enter Phone Number:").grid(row=0, column=0, sticky=tk.W)
        self.phone_entry = ttk.Entry(control_panel_frame, width=30)
        self.phone_entry.grid(row=0, column=1, sticky=(tk.W, tk.E), padx=5)
        self.phone_entry.insert(0, "+1234567890")  # Default placeholder
        
        # Analyze button
        self.analyze_btn = ttk.Button(control_panel_frame, text="Analyze", command=self.start_analysis)
        self.analyze_btn.grid(row=0, column=2, padx=5)
        
        # Clear button
        clear_btn = ttk.Button(control_panel_frame, text="Clear", command=self.clear_results)
        clear_btn.grid(row=0, column=3, padx=5)
        
        # View Map button
        self.view_map_btn = ttk.Button(control_panel_frame, text="View Map", command=self.view_map)
        self.view_map_btn.grid(row=0, column=4, padx=5)
        self.view_map_btn.state(['disabled'])
        
        # Configure control_panel_frame grid weights
        control_panel_frame.columnconfigure(1, weight=1)
        
        # Results area with tabs
        self.notebook = ttk.Notebook(main_frame)
        self.notebook.grid(row=1, column=0, columnspan=5, sticky=(tk.W, tk.E, tk.N, tk.S), pady=10)
        
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
        self.social_text.insert(tk.END, "Welcome to the Social Accounts tab!\n\n")
        self.social_text.insert(tk.END, "To use this feature, first analyze a phone number in the 'Basic Info' tab.\n")
        self.social_text.insert(tk.END, "Once analysis is complete, the buttons below will become active.\n\n")
        self.social_text.insert(tk.END, "Clicking 'Open in Telegram', 'Open in WhatsApp', 'Open in Facebook', or 'Open in Instagram' will attempt to open the respective social media application or website with the analyzed phone number, allowing you to quickly check for associated accounts.\n\n")
        self.social_text.insert(tk.END, "Please note that the success of opening these applications/websites depends on your system's configuration and whether the phone number is publicly associated with an account on that platform.")
        
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
        
        # OSINT tab
        self.osint_frame = ttk.Frame(self.notebook)
        self.notebook.add(self.osint_frame, text="OSINT Analysis")
        
        osint_input_frame = ttk.Frame(self.osint_frame, padding="5")
        osint_input_frame.pack(fill='x')
        
        ttk.Label(osint_input_frame, text="Email/Username:").pack(side=tk.LEFT, padx=5)
        self.osint_entry = ttk.Entry(osint_input_frame, width=40)
        self.osint_entry.pack(side=tk.LEFT, expand=True, fill='x', padx=5)
        self.osint_entry.insert(0, "test@example.com") # Placeholder
        
        self.osint_analyze_btn = ttk.Button(osint_input_frame, text="Analyze OSINT (Username/Email)", command=self.start_osint_analysis)
        self.osint_analyze_btn.pack(side=tk.LEFT, padx=5)

        ttk.Label(osint_input_frame, text="Email Domain:").pack(side=tk.LEFT, padx=5)
        self.email_domain_entry = ttk.Entry(osint_input_frame, width=30)
        self.email_domain_entry.pack(side=tk.LEFT, expand=True, fill='x', padx=5)
        self.email_domain_entry.insert(0, "example.com") # Placeholder

        self.email_domain_analyze_btn = ttk.Button(osint_input_frame, text="Analyze Email Domain", command=self.start_email_domain_analysis)
        self.email_domain_analyze_btn.pack(side=tk.LEFT, padx=5)

        ttk.Label(osint_input_frame, text="Email for Breach Check:").pack(side=tk.LEFT, padx=5)
        self.email_breach_entry = ttk.Entry(osint_input_frame, width=30)
        self.email_breach_entry.pack(side=tk.LEFT, expand=True, fill='x', padx=5)
        self.email_breach_entry.insert(0, "test@example.com") # Placeholder

        self.email_breach_analyze_btn = ttk.Button(osint_input_frame, text="Check Email Breach", command=self.start_email_breach_analysis)
        self.email_breach_analyze_btn.pack(side=tk.LEFT, padx=5)

        ttk.Label(osint_input_frame, text="IP Address:").pack(side=tk.LEFT, padx=5)
        self.ip_entry = ttk.Entry(osint_input_frame, width=30)
        self.ip_entry.pack(side=tk.LEFT, expand=True, fill='x', padx=5)
        self.ip_entry.insert(0, "8.8.8.8")

        self.ip_analyze_btn = ttk.Button(osint_input_frame, text="Analyze IP", command=self.start_ip_analysis)
        self.ip_analyze_btn.pack(side=tk.LEFT, padx=5)

        ttk.Label(osint_input_frame, text="Phone Number (OSINT):").pack(side=tk.LEFT, padx=5)
        self.osint_phone_entry = ttk.Entry(osint_input_frame, width=30)
        self.osint_phone_entry.pack(side=tk.LEFT, expand=True, fill='x', padx=5)
        self.osint_phone_entry.delete(0, tk.END)
        self.osint_phone_entry.insert(0, "+1234567890") # Placeholder

        self.osint_phone_basic_btn = ttk.Button(osint_input_frame, text="Get Basic Info", command=self.start_phone_basic_analysis)
        self.osint_phone_basic_btn.pack(side=tk.LEFT, padx=5)

        self.osint_phone_isp_btn = ttk.Button(osint_input_frame, text="Get ISP", command=self.start_phone_isp_analysis)
        self.osint_phone_isp_btn.pack(side=tk.LEFT, padx=5)

        self.osint_phone_validate_btn = ttk.Button(osint_input_frame, text="Validate Number", command=self.start_phone_validation)
	        self.osint_phone_validate_btn.pack(side=tk.LEFT, padx=5)
	
	        ttk.Label(osint_input_frame, text="Username for Social Enumeration:").pack(side=tk.LEFT, padx=5)
	        self.social_username_entry = ttk.Entry(osint_input_frame, width=30)
	        self.social_username_entry.pack(side=tk.LEFT, expand=True, fill='x', padx=5)
	        self.social_username_entry.insert(0, "username") # Placeholder
	
	        self.social_enumerate_btn = ttk.Button(osint_input_frame, text="Enumerate Social Media", command=self.start_social_enumeration)
	        self.social_enumerate_btn.pack(side=tk.LEFT, padx=5)
	        
	        self.osint_text = scrolledtext.ScrolledText(self.osint_frame, wrap=tk.WORD, height=20)
	        self.osint_text.pack(expand=True, fill='both', padx=5, pady=5)
	        
	        # Network Analysis tab
	        self.network_frame = ttk.Frame(self.notebook)
	        self.notebook.add(self.network_frame, text="Network Analysis")
	        
	        network_input_frame = ttk.Frame(self.network_frame, padding="5")
	        network_input_frame.pack(fill='x')
	        
	        ttk.Label(network_input_frame, text="Target Host/IP:").pack(side=tk.LEFT, padx=5)
	        self.network_target_entry = ttk.Entry(network_input_frame, width=30)
	        self.network_target_entry.pack(side=tk.LEFT, expand=True, fill='x', padx=5)
	        self.network_target_entry.insert(0, "scanme.nmap.org") # Placeholder
	        
	        self.port_scan_btn = ttk.Button(network_input_frame, text="Perform Port Scan (Nmap)", command=self.start_port_scan)
	        self.port_scan_btn.pack(side=tk.LEFT, padx=5)
	        
	        self.network_text = scrolledtext.ScrolledText(self.network_frame, wrap=tk.WORD, height=20)
	        self.network_text.pack(expand=True, fill='both', padx=5, pady=5)
	        
	        # Map tab
        self.map_frame = ttk.Frame(self.notebook)
        self.notebook.add(self.map_frame, text="Location Map")
        self.map_text = scrolledtext.ScrolledText(self.map_frame, wrap=tk.WORD, height=20)
        self.map_text.pack(expand=True, fill='both', padx=5, pady=5)
        self.map_text.insert(tk.END, "Welcome to the Location Map tab!\n\n")
        self.map_text.insert(tk.END, "To use this feature, you need a valid OpenCage Geocoding API key.\n")
        self.map_text.insert(tk.END, "1. Obtain an API key from https://opencagedata.com/.\n")
        self.map_text.insert(tk.END, "2. Replace the placeholder in `config.py` with your actual API key.\n")
        self.map_text.insert(tk.END, "3. Analyze a phone number in the 'Basic Info' tab, and then click 'View Map'.")
        
        # Status bar
        self.status_var = tk.StringVar()
        self.status_bar = ttk.Label(main_frame, textvariable=self.status_var, relief=tk.SUNKEN)
        self.status_bar.grid(row=2, column=0, columnspan=5, sticky=(tk.W, tk.E))
        
        # Configure grid weights
        main_frame.columnconfigure(1, weight=1)
        main_frame.rowconfigure(1, weight=1)
        root.columnconfigure(0, weight=1)
        root.rowconfigure(0, weight=1)
        
        # Store the current phone number
        self.current_phone = None
        self.analyzer = None
        self.osint_analyzer = OSINTAnalyzer()

    def start_analysis(self):
        self.analyze_btn.state(['disabled'])
        self.status_var.set("Analysis in progress...")
        threading.Thread(target=self._run_analysis).start()

    def _run_analysis(self):
        try:
            phone_number = self.phone_entry.get().strip()
            self.analyzer = PhoneAnalyzer(phone_number, OPEN_CAGE_API_KEY)
            self.current_phone = phone_number
            
            # Update basic info
            validation = self.analyzer.validate_number()
            if not validation["is_valid"]:
                self.status_var.set(f"Invalid phone number: {validation['reason']}")
                tkinter.messagebox.showerror("Error", f"Invalid phone number: {validation['reason']}")
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

        except ValueError as e:
            tkinter.messagebox.showerror("Error", str(e))
            self.status_var.set(str(e))
        except Exception as e:
            tkinter.messagebox.showerror("Error", f"An unexpected error occurred: {e}")
            self.status_var.set(f"An unexpected error occurred: {e}")
        finally:
            self.analyze_btn.state(['!disabled'])

    def start_osint_analysis(self):
        self.osint_analyze_btn.state(['disabled'])
        self.status_var.set("OSINT analysis in progress...")
        threading.Thread(target=self._run_osint_analysis).start()

    def _run_osint_analysis(self):
        try:
            query = self.osint_entry.get().strip()
            if not query:
                self.status_var.set("Please enter an email or username for OSINT analysis.")
                tkinter.messagebox.showwarning("Warning", "Please enter an email or username for OSINT analysis.")
                return
            
            self.osint_text.delete(1.0, tk.END)
            self.osint_text.insert(tk.END, f"Running Holehe scan for: {query}\n\n")
            
            # Holehe is an async function, so we need to run it in an event loop
            loop = asyncio.new_event_loop()
            asyncio.set_event_loop(loop)
            results = loop.run_until_complete(self.osint_analyzer.analyze_email_or_username(query))
            loop.close()

            if results:
                for service, data in results.items():
                    self.osint_text.insert(tk.END, f"Service: {service}\n")
                    for key, value in data.items():
                        self.osint_text.insert(tk.END, f"  {key}: {value}\n")
                    self.osint_text.insert(tk.END, "\n")
            else:
                self.osint_text.insert(tk.END, "No OSINT results found.")
            
            self.status_var.set("OSINT analysis complete.")

        except Exception as e:
            self.status_var.set(str(e))
            tkinter.messagebox.showerror("Error", f"Error during OSINT analysis: {e}")
        finally:
            self.osint_analyze_btn.state(['!disabled'])

    def start_email_domain_analysis(self):
        self.email_domain_analyze_btn.state(['disabled'])
        self.status_var.set("Email domain analysis in progress...")
        threading.Thread(target=self._run_email_domain_analysis).start()

    def _run_email_domain_analysis(self):
        try:
            email_address = self.email_domain_entry.get().strip()
            if not email_address:
                self.status_var.set("Please enter an email address for domain analysis.")
                tkinter.messagebox.showwarning("Warning", "Please enter an email address for domain analysis.")
                return
            
            self.osint_text.delete(1.0, tk.END)
            self.osint_text.insert(tk.END, f"Performing WHOIS lookup for: {email_address}\n\n")
            
            whois_info = self.osint_analyzer.analyze_email_domain(email_address)
            self.osint_text.insert(tk.END, whois_info)
            
            self.status_var.set("Email domain analysis complete.")

        except Exception as e:
            self.status_var.set(str(e))
            tkinter.messagebox.showerror("Error", f"Error during email domain analysis: {e}")
        finally:
            self.email_domain_analyze_btn.state(['!disabled'])

    def start_email_breach_analysis(self):
        self.email_breach_analyze_btn.state(['disabled'])
        self.status_var.set("Email breach analysis in progress...")
        threading.Thread(target=self._run_email_breach_analysis).start()

    def _run_email_breach_analysis(self):
        try:
            email_address = self.email_breach_entry.get().strip()
            if not email_address:
                self.status_var.set("Please enter an email address for breach analysis.")
                tkinter.messagebox.showwarning("Warning", "Please enter an email address for breach analysis.")
                return
            
            self.osint_text.delete(1.0, tk.END)
            self.osint_text.insert(tk.END, f"Checking for breaches for: {email_address}\n\n")
            
            breach_info = self.osint_analyzer.check_breach(email_address)
            self.osint_text.insert(tk.END, breach_info)
            
            self.status_var.set("Email breach analysis complete.")

        except Exception as e:
            self.status_var.set(str(e))
            tkinter.messagebox.showerror("Error", f"Error during email breach analysis: {e}")
        finally:
            self.email_breach_analyze_btn.state(['!disabled'])

    def start_ip_analysis(self):
        self.ip_analyze_btn.state(['disabled'])
        self.status_var.set("IP address analysis in progress...")
        threading.Thread(target=self._run_ip_analysis).start()

    def _run_ip_analysis(self):
        try:
            ip_address = self.ip_entry.get().strip()
            if not ip_address:
                self.status_var.set("Please enter an IP address for analysis.")
                tkinter.messagebox.showwarning("Warning", "Please enter an IP address for analysis.")
                return
            
            self.osint_text.delete(1.0, tk.END)
            self.osint_text.insert(tk.END, f"Analyzing IP address: {ip_address}\n\n")
            
            ip_info = self.osint_analyzer.analyze_ip_address(ip_address)
            self.osint_text.insert(tk.END, ip_info)
            
            self.status_var.set("IP address analysis complete.")

        except Exception as e:
            self.status_var.set(str(e))
            tkinter.messagebox.showerror("Error", f"Error during IP address analysis: {e}")
        finally:
            self.ip_analyze_btn.state(['!disabled'])

    def start_phone_basic_analysis(self):
        self.osint_phone_basic_btn.state(['disabled'])
        self.status_var.set("Phone number basic analysis in progress...")
        threading.Thread(target=self._run_phone_basic_analysis).start()

    def _run_phone_basic_analysis(self):
        try:
            phone_number = self.osint_phone_entry.get().strip()
            if not phone_number:
                self.status_var.set("Please enter a phone number for basic analysis.")
                tkinter.messagebox.showwarning("Warning", "Please enter a phone number for basic analysis.")
                return
            
            self.osint_text.delete(1.0, tk.END)
            self.osint_text.insert(tk.END, f"Analyzing basic info for phone number: {phone_number}\n\n")
            
            basic_info = self.osint_analyzer.analyze_phone_number_basic_info(phone_number)
            self.osint_text.insert(tk.END, basic_info)
            
            self.status_var.set("Phone number basic analysis complete.")

        except Exception as e:
            self.status_var.set(str(e))
            tkinter.messagebox.showerror("Error", f"Error during phone number basic analysis: {e}")
        finally:
            self.osint_phone_basic_btn.state(['!disabled'])

    def start_phone_isp_analysis(self):
        self.osint_phone_isp_btn.state(['disabled'])
        self.status_var.set("Phone number ISP analysis in progress...")
        threading.Thread(target=self._run_phone_isp_analysis).start()

    def _run_phone_isp_analysis(self):
        try:
            phone_number = self.osint_phone_entry.get().strip()
            if not phone_number:
                self.status_var.set("Please enter a phone number for ISP analysis.")
                tkinter.messagebox.showwarning("Warning", "Please enter a phone number for ISP analysis.")
                return
            
            self.osint_text.delete(1.0, tk.END)
            self.osint_text.insert(tk.END, f"Analyzing ISP for phone number: {phone_number}\n\n")
            
            isp_info = self.osint_analyzer.analyze_phone_number_isp(phone_number)
            self.osint_text.insert(tk.END, isp_info)
            
            self.status_var.set("Phone number ISP analysis complete.")

        except Exception as e:
            self.status_var.set(str(e))
            tkinter.messagebox.showerror("Error", f"Error during phone number ISP analysis: {e}")
        finally:
            self.osint_phone_isp_btn.state(['!disabled'])

    def start_social_enumeration(self):
        self.social_enumerate_btn.state(['disabled'])
        self.status_var.set("Social media enumeration in progress...")
        threading.Thread(target=self._run_social_enumeration).start()

    def _run_social_enumeration(self):
        try:
            username = self.social_username_entry.get().strip()
            if not username:
                self.status_var.set("Please enter a username for social media enumeration.")
                tkinter.messagebox.showwarning("Warning", "Please enter a username for social media enumeration.")
                return
            
            self.osint_text.delete(1.0, tk.END)
            self.osint_text.insert(tk.END, f"Enumerating social media for username: {username}\n\n")
            
            social_info = self.osint_analyzer.enumerate_social_media_username(username)
            self.osint_text.insert(tk.END, social_info)
            
            self.status_var.set("Social media enumeration complete.")

        except Exception as e:
            self.status_var.set(str(e))
            tkinter.messagebox.showerror("Error", f"Error during social media enumeration: {e}")
        finally:
            self.social_enumerate_btn.state(['!disabled'])

    def start_phone_validation(self):
        self.osint_phone_validate_btn.state(['disabled'])
        self.status_var.set("Phone number validation in progress...")
        threading.Thread(target=self._run_phone_validation).start()

    def _run_phone_validation(self):
        try:
            phone_number = self.osint_phone_entry.get().strip()
            if not phone_number:
                self.status_var.set("Please enter a phone number for validation.")
                tkinter.messagebox.showwarning("Warning", "Please enter a phone number for validation.")
                return
            
            self.osint_text.delete(1.0, tk.END)
            self.osint_text.insert(tk.END, f"Validating phone number: {phone_number}\n\n")
            
            validation_result = self.osint_analyzer.validate_phone_number(phone_number)
            self.osint_text.insert(tk.END, validation_result)
            
            self.status_var.set("Phone number validation complete.")

        except Exception as e:
            self.status_var.set(str(e))
            tkinter.messagebox.showerror("Error", f"Error during phone number validation: {e}")
        finally:
            self.osint_phone_validate_btn.state(['!disabled'])

    def clear_social_results(self):
        self.social_text.delete(1.0, tk.END)
        self.telegram_btn.state(['disabled'])
        self.whatsapp_btn.state(['disabled'])
        self.facebook_btn.state(['disabled'])
        self.instagram_btn.state(['disabled'])

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
                try:
                    webbrowser.open(urls[platform])
                    self.status_var.set(f"Opened {platform} for {self.current_phone}.")
                    self.social_text.insert(tk.END, f"Attempted to open {platform}. Note: Direct social media profile lookup by phone number is often not feasible. Consider using the OSINT Analysis tab for more comprehensive searches.\n\n")
                except webbrowser.Error:
                    self.status_var.set(f"Error: Could not open {platform}. Please check your browser settings.")
                    tkinter.messagebox.showerror("Error", f"Could not open {platform}. Please check your browser settings.")
                
        except Exception as e:
            self.status_var.set(f"Error opening social media: {e}")
            tkinter.messagebox.showerror("Error", f"Error opening social media: {e}")

    def view_map(self):
        self.view_map_btn.state(['disabled'])
        self.status_var.set("Generating map...")
        threading.Thread(target=self._generate_map).start()

	    def start_port_scan(self):
	        """Start the port scan in a separate thread"""
	        target = self.network_target_entry.get().strip()
	        if not target:
	            tkinter.messagebox.showerror("Error", "Please enter a target host or IP.")
	            return
	
	        self.port_scan_btn.state(['disabled'])
	        self.network_text.delete(1.0, tk.END)
	        self.network_text.insert(tk.END, f"Starting Nmap port scan on {target}... This may take a moment.\n")
	        self.status_var.set(f"Running port scan on {target}...")
	        
	        threading.Thread(target=self._run_port_scan_thread, args=(target,)).start()
	
	    def _run_port_scan_thread(self, target):
	        """Threaded function to run nmap and update GUI"""
	        try:
	            # Use a simple, non-aggressive scan for common ports
	            command = f"nmap -F {target}" 
	            
	            # Execute the command using subprocess and capture output
	            import subprocess
	            process = subprocess.run(command, shell=True, capture_output=True, text=True, timeout=60)
	            
	            output = process.stdout
	            if process.stderr:
	                output += "\n--- Nmap Error Output ---\n" + process.stderr
	            
	            self.network_text.insert(tk.END, "\n--- Nmap Scan Results ---\n")
	            self.network_text.insert(tk.END, output)
	            self.status_var.set(f"Port scan on {target} complete.")
	            
	        except subprocess.TimeoutExpired:
	            self.network_text.insert(tk.END, "\n--- Scan Failed ---\nNmap scan timed out after 60 seconds.")
	            self.status_var.set(f"Port scan on {target} failed (Timeout).")
	        except Exception as e:
	            self.network_text.insert(tk.END, f"\n--- Scan Failed ---\nAn error occurred during the scan: {e}")
	            self.status_var.set(f"Port scan on {target} failed.")
	        finally:
	            self.port_scan_btn.state(['!disabled'])
	
	    def _generate_map(self):
	        try:
	            if not self.analyzer:
	                self.status_var.set("No phone number analyzed yet.")
	                return

	            # Use the region name first for geocoding
	            region = self.analyzer.get_basic_info()['region']
	            
	            # Fallback to E164 number for more precise location if region is too broad (e.g., just a country)
	            search_query = region
	            if self.analyzer.get_region_code() == region: # If region is just the country name
	                search_query = self.analyzer.get_e164_number()
	
	            if not search_query:
	                self.status_var.set("No valid search query for map generation.")
	                tkinter.messagebox.showerror("Error", "No valid search query for map generation.")
	                return
	
	            try:
	                results = self.analyzer.geocoder.geocode(search_query)
	            except Exception as e:
                self.status_var.set(f"OpenCage Geocoding API error: {e}")
                tkinter.messagebox.showerror("API Error", f"OpenCage Geocoding API error: {e}. Please check your API key and daily quota.")
                return

            if results and len(results) > 0:
                lat = results[0]['geometry']['lat']
                lng = results[0]['geometry']['lng']

	                # Create map
	                # Adjust zoom level based on result confidence/type
	                zoom_level = 10
	                if 'confidence' in results[0] and results[0]['confidence'] > 5:
	                    zoom_level = 14 # Higher confidence, zoom in more
	                
	                m = folium.Map(location=[lat, lng], zoom_start=zoom_level)
	                folium.Marker([lat, lng], popup=results[0]['formatted']).add_to(m)

                # Save to file
                map_file = "location_map.html"
                m.save(map_file)
                try:
                    webbrowser.open(map_file)
                    self.map_text.delete(1.0, tk.END)
                    self.map_text.insert(tk.END, f"Map saved to {map_file} and opened in browser.")
                    self.status_var.set("Map generated and opened.")
                except webbrowser.Error:
                    self.status_var.set(f"Error: Could not open map in browser. File saved to {map_file}.")
                    tkinter.messagebox.showerror("Error", f"Could not open map in browser. File saved to {map_file}.")
            else:
                self.map_text.delete(1.0, tk.END)
                self.map_text.insert(tk.END, "Could not find location coordinates for the region.")
                tkinter.messagebox.showerror("Error", "Could not find location coordinates for the region.")
                self.status_var.set("Map generation failed: No coordinates found.")
                
        except Exception as e:
            self.status_var.set(f"Error generating map: {e}")
            tkinter.messagebox.showerror("Error", f"Error generating map: {e}")
        finally:
            self.view_map_btn.state(['!disabled'])

if __name__ == "__main__":
    root = tk.Tk()
    app = PhoneAnalyzerGUI(root)
    root.mainloop()
