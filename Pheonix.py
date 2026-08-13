"""Pheonix desktop utility.

Pheonix provides public numbering-plan metadata and opt-in, authorised-use
network or account-enrichment helpers.  This edition has no trial counter,
payment screen, licence key, remote activation or feature-use cap.
"""

from __future__ import annotations

import asyncio
import logging
import re
import subprocess
import threading
import tkinter as tk
import webbrowser
from collections.abc import Callable
from pathlib import Path
from tkinter import messagebox, scrolledtext, ttk
from typing import Any, TypeVar

import folium

from config import SETTINGS
from osint_analyzer import OSINTAnalyzer
from phone_analyzer import PhoneAnalyzer, PhoneInfo

APP_NAME = "Pheonix"
APP_VERSION = "2026.1.0"
APP_DIRECTORY = Path.home() / ".pheonix"
MAP_DIRECTORY = APP_DIRECTORY / "maps"
TARGET_PATTERN = re.compile(r"^[A-Za-z0-9.-]{1,253}$")
ResultT = TypeVar("ResultT")


class PhoneAnalyzerGUI:
    """Thread-safe Tk interface for Pheonix's public-data utilities."""

    def __init__(self, root: tk.Tk) -> None:
        self.root = root
        self.root.title(f"{APP_NAME} {APP_VERSION}")
        self.root.geometry("1040x720")
        self.root.minsize(860, 620)

        self.current_phone: PhoneAnalyzer | None = None
        self.current_phone_info: PhoneInfo | None = None
        self.osint_analyzer = OSINTAnalyzer()
        self.status_var = tk.StringVar(value="Ready. No payment, licence key, trial, or use limit is required.")
        self.authorised_use_var = tk.BooleanVar(value=False)
        self.phone_var = tk.StringVar()
        self.osint_query_var = tk.StringVar()
        self.domain_email_var = tk.StringVar()
        self.breach_email_var = tk.StringVar()
        self.ip_var = tk.StringVar()
        self.osint_phone_var = tk.StringVar()
        self.username_var = tk.StringVar()
        self.network_target_var = tk.StringVar()

        self._configure_style()
        self._build_layout()
        self.root.protocol("WM_DELETE_WINDOW", self._on_close)

    def _configure_style(self) -> None:
        style = ttk.Style()
        available = style.theme_names()
        if "clam" in available:
            style.theme_use("clam")
        style.configure("Title.TLabel", font=("TkDefaultFont", 16, "bold"))
        style.configure("Subtitle.TLabel", foreground="#5b6472")
        style.configure("TButton", padding=(10, 6))
        style.configure("TNotebook.Tab", padding=(12, 8))

    def _build_layout(self) -> None:
        container = ttk.Frame(self.root, padding=16)
        container.grid(row=0, column=0, sticky="nsew")
        self.root.columnconfigure(0, weight=1)
        self.root.rowconfigure(0, weight=1)
        container.columnconfigure(0, weight=1)
        container.rowconfigure(3, weight=1)

        ttk.Label(container, text=f"{APP_NAME} {APP_VERSION}", style="Title.TLabel").grid(row=0, column=0, sticky="w")
        ttk.Label(
            container,
            text="Public numbering-plan metadata and authorised-use enrichment utilities.",
            style="Subtitle.TLabel",
        ).grid(row=1, column=0, sticky="w", pady=(2, 12))

        phone_card = ttk.LabelFrame(container, text="Phone metadata", padding=12)
        phone_card.grid(row=2, column=0, sticky="ew")
        phone_card.columnconfigure(1, weight=1)
        ttk.Label(phone_card, text="International number").grid(row=0, column=0, sticky="w", padx=(0, 8))
        phone_entry = ttk.Entry(phone_card, textvariable=self.phone_var)
        phone_entry.grid(row=0, column=1, sticky="ew")
        phone_entry.focus_set()
        self.analyze_button = ttk.Button(phone_card, text="Analyse", command=self.start_phone_analysis)
        self.analyze_button.grid(row=0, column=2, padx=(8, 0))
        ttk.Button(phone_card, text="Clear", command=self.clear_results).grid(row=0, column=3, padx=(8, 0))
        ttk.Label(
            phone_card,
            text="Use E.164 format, for example +12025550123. Results describe the numbering plan, not a person or device location.",
            style="Subtitle.TLabel",
            wraplength=850,
        ).grid(row=1, column=0, columnspan=4, sticky="w", pady=(8, 0))

        self.notebook = ttk.Notebook(container)
        self.notebook.grid(row=3, column=0, sticky="nsew", pady=(12, 10))
        self._build_overview_tab()
        self._build_enrichment_tab()
        self._build_network_tab()
        self._build_map_tab()
        self._build_about_tab()

        status = ttk.Label(container, textvariable=self.status_var, anchor="w", relief="sunken", padding=(8, 5))
        status.grid(row=4, column=0, sticky="ew")

    def _build_overview_tab(self) -> None:
        frame = ttk.Frame(self.notebook, padding=12)
        self.notebook.add(frame, text="Overview")
        frame.columnconfigure(0, weight=1)
        frame.rowconfigure(0, weight=1)
        self.basic_info_text = scrolledtext.ScrolledText(frame, wrap=tk.WORD, state="disabled", font="TkFixedFont")
        self.basic_info_text.grid(row=0, column=0, sticky="nsew")
        self._replace_text(
            self.basic_info_text,
            "Enter an international phone number and select Analyse.\n\n"
            "Pheonix reports public numbering-plan metadata such as formatting, carrier labels, region and time-zone metadata. "
            "It cannot locate an individual or confirm account ownership.",
        )

    def _build_enrichment_tab(self) -> None:
        frame = ttk.Frame(self.notebook, padding=12)
        self.notebook.add(frame, text="Authorised enrichment")
        frame.columnconfigure(1, weight=1)
        frame.rowconfigure(8, weight=1)

        authorisation = ttk.Checkbutton(
            frame,
            text="I confirm that I own, administer, or have explicit permission to assess every account, address, domain, or host submitted below.",
            variable=self.authorised_use_var,
        )
        authorisation.grid(row=0, column=0, columnspan=3, sticky="w", pady=(0, 12))

        fields = [
            ("Email or username", self.osint_query_var, "Check public account indicators", self.start_osint_analysis),
            (
                "Email for domain registration",
                self.domain_email_var,
                "Look up domain registration",
                self.start_domain_analysis,
            ),
            ("Email for breach check", self.breach_email_var, "Check breach provider", self.start_breach_analysis),
            ("Public IP address", self.ip_var, "Look up network registration", self.start_ip_analysis),
            ("Phone number", self.osint_phone_var, "Phone metadata", self.start_phone_metadata_analysis),
            ("Username", self.username_var, "Check username indicators", self.start_username_analysis),
        ]
        self.enrichment_buttons: list[ttk.Button] = []
        for row, (label, variable, button_label, command) in enumerate(fields, start=1):
            ttk.Label(frame, text=label).grid(row=row, column=0, sticky="w", padx=(0, 8), pady=3)
            ttk.Entry(frame, textvariable=variable).grid(row=row, column=1, sticky="ew", pady=3)
            button = ttk.Button(frame, text=button_label, command=command)
            button.grid(row=row, column=2, sticky="e", padx=(8, 0), pady=3)
            self.enrichment_buttons.append(button)

        self.osint_text = scrolledtext.ScrolledText(frame, wrap=tk.WORD, state="disabled", font="TkFixedFont")
        self.osint_text.grid(row=8, column=0, columnspan=3, sticky="nsew", pady=(12, 0))
        self._replace_text(
            self.osint_text,
            "Optional enrichment can contact third-party providers. It is disabled until you confirm authorisation. "
            "Missing API keys or optional packages are reported with setup guidance.",
        )

    def _build_network_tab(self) -> None:
        frame = ttk.Frame(self.notebook, padding=12)
        self.notebook.add(frame, text="Network scan")
        frame.columnconfigure(1, weight=1)
        frame.rowconfigure(3, weight=1)

        ttk.Label(
            frame,
            text="A conservative scan of common ports is available only for systems you own or have written permission to test. It uses nmap -F with a 60-second timeout.",
            style="Subtitle.TLabel",
            wraplength=850,
        ).grid(row=0, column=0, columnspan=3, sticky="w", pady=(0, 12))
        ttk.Label(frame, text="Host or IP address").grid(row=1, column=0, sticky="w", padx=(0, 8))
        ttk.Entry(frame, textvariable=self.network_target_var).grid(row=1, column=1, sticky="ew")
        self.port_scan_button = ttk.Button(frame, text="Run authorised scan", command=self.start_port_scan)
        self.port_scan_button.grid(row=1, column=2, padx=(8, 0))
        self.network_text = scrolledtext.ScrolledText(frame, wrap=tk.WORD, state="disabled", font="TkFixedFont")
        self.network_text.grid(row=3, column=0, columnspan=3, sticky="nsew", pady=(12, 0))
        self._replace_text(self.network_text, "No scan has been run.")

    def _build_map_tab(self) -> None:
        frame = ttk.Frame(self.notebook, padding=12)
        self.notebook.add(frame, text="Region map")
        frame.columnconfigure(0, weight=1)
        frame.rowconfigure(2, weight=1)
        ttk.Label(
            frame,
            text="The map visualises the broader numbering-plan region reported for the analysed number. It is not a live, device, person or address location.",
            style="Subtitle.TLabel",
            wraplength=850,
        ).grid(row=0, column=0, sticky="w")
        self.view_map_button = ttk.Button(frame, text="Generate region map", command=self.view_map, state="disabled")
        self.view_map_button.grid(row=1, column=0, sticky="w", pady=12)
        self.map_text = scrolledtext.ScrolledText(frame, wrap=tk.WORD, state="disabled", font="TkFixedFont")
        self.map_text.grid(row=2, column=0, sticky="nsew")
        self._replace_text(self.map_text, "Analyse a valid phone number to enable the region map.")

    def _build_about_tab(self) -> None:
        frame = ttk.Frame(self.notebook, padding=18)
        self.notebook.add(frame, text="About")
        frame.columnconfigure(0, weight=1)
        about = (
            f"{APP_NAME} {APP_VERSION}\n\n"
            "Free edition: all included capabilities are available without a payment flow, licence key, activation request, trial counter, or usage quota.\n\n"
            "Responsible use: submit only identifiers and network targets that you own, administer, or are explicitly authorised to assess. Public carrier and geocoding metadata is approximate and must not be used to make decisions about individuals.\n\n"
            "Configuration: set OPEN_CAGE_API_KEY for region maps, HIBP_API_KEY for authorised breach checks, and GEOAPIFY_API_KEY for optional IP enrichment. Keep these values out of source control."
        )
        text = scrolledtext.ScrolledText(frame, wrap=tk.WORD, state="normal", height=18, font="TkFixedFont")
        text.grid(row=0, column=0, sticky="nsew")
        text.insert("1.0", about)
        text.configure(state="disabled")

    def _replace_text(self, widget: scrolledtext.ScrolledText, value: str) -> None:
        widget.configure(state="normal")
        widget.delete("1.0", tk.END)
        widget.insert(tk.END, value)
        widget.configure(state="disabled")

    def _append_text(self, widget: scrolledtext.ScrolledText, value: str) -> None:
        widget.configure(state="normal")
        widget.insert(tk.END, value)
        widget.see(tk.END)
        widget.configure(state="disabled")

    def _run_background(
        self,
        button: ttk.Button,
        status: str,
        work: Callable[[], ResultT],
        on_success: Callable[[ResultT], None],
    ) -> None:
        """Execute a blocking task without manipulating Tk widgets off-thread."""

        button.state(["disabled"])
        self.status_var.set(status)

        def runner() -> None:
            try:
                result = work()
            except Exception as exc:  # GUI boundary: preserve useful errors without crashing.
                logging.exception("Background task failed")
                error_message = str(exc)
                self.root.after(0, lambda: self._background_failed(button, error_message))
            else:
                self.root.after(0, lambda: self._background_succeeded(button, on_success, result))

        threading.Thread(target=runner, daemon=True, name="pheonix-worker").start()

    def _background_succeeded(self, button: ttk.Button, on_success: Callable[[ResultT], None], result: ResultT) -> None:
        button.state(["!disabled"])
        on_success(result)

    def _background_failed(self, button: ttk.Button, error: str) -> None:
        button.state(["!disabled"])
        self.status_var.set("Operation failed. See the message for details.")
        messagebox.showerror(APP_NAME, error or "An unexpected error occurred.")

    def _require_authorisation(self) -> bool:
        if self.authorised_use_var.get():
            return True
        messagebox.showwarning(
            "Authorisation required",
            "Confirm that you are authorised to assess the submitted data before using an enrichment feature.",
        )
        return False

    def start_phone_analysis(self) -> None:
        phone_number = self.phone_var.get().strip()
        if not phone_number:
            messagebox.showwarning(APP_NAME, "Enter an international phone number first.")
            return

        def work() -> tuple[PhoneAnalyzer, PhoneInfo]:
            analyzer = PhoneAnalyzer(phone_number, SETTINGS.opencage_api_key)
            return analyzer, analyzer.get_info()

        self._run_background(self.analyze_button, "Analysing numbering-plan metadata…", work, self._show_phone_analysis)

    def _show_phone_analysis(self, result: tuple[PhoneAnalyzer, PhoneInfo]) -> None:
        self.current_phone, self.current_phone_info = result
        info = self.current_phone_info
        text = (
            "Phone metadata\n"
            f"{'=' * 60}\n"
            f"International format: {info.international}\n"
            f"National format:      {info.national}\n"
            f"E.164 format:         {info.e164}\n"
            f"Region:               {info.region}\n"
            f"Country/region code:  {info.country_code or 'Unknown'}\n"
            f"Carrier label:        {info.carrier or 'Unknown'}\n"
            f"Time zone(s):         {', '.join(info.timezones) or 'Unknown'}\n"
            f"Number type:          {info.number_type}\n\n"
            "Interpretation notice: these fields are public numbering-plan metadata. They do not identify a subscriber or provide the real-time location of a device."
        )
        self._replace_text(self.basic_info_text, text)
        self.view_map_button.state(["!disabled"])
        self.status_var.set("Phone metadata is ready.")

    def _run_enrichment(self, button: ttk.Button, operation: str, work: Callable[[], str]) -> None:
        if not self._require_authorisation():
            return
        self._replace_text(self.osint_text, f"{operation}…\n")
        self._run_background(button, f"{operation}…", work, self._show_enrichment_result)

    def _show_enrichment_result(self, result: str | dict[str, Any]) -> None:
        if isinstance(result, dict):
            lines: list[str] = []
            for service, data in sorted(result.items()):
                lines.append(f"{service}:")
                if isinstance(data, dict):
                    lines.extend(f"  {key}: {value}" for key, value in data.items())
                else:
                    lines.append(f"  {data}")
                lines.append("")
            display = "\n".join(lines) if lines else "No results returned."
        else:
            display = result
        self._replace_text(self.osint_text, display)
        self.status_var.set("Authorised enrichment request completed.")

    def start_osint_analysis(self) -> None:
        query = self.osint_query_var.get().strip()
        if not query:
            messagebox.showwarning(APP_NAME, "Enter an email address or username first.")
            return

        def work() -> dict[str, Any]:
            return asyncio.run(self.osint_analyzer.analyze_email_or_username(query))

        self._run_enrichment(self.enrichment_buttons[0], "Checking public account indicators", work)

    def start_domain_analysis(self) -> None:
        email = self.domain_email_var.get().strip()
        if not email:
            messagebox.showwarning(APP_NAME, "Enter an email address first.")
            return
        self._run_enrichment(
            self.enrichment_buttons[1],
            "Looking up domain registration",
            lambda: self.osint_analyzer.analyze_email_domain(email),
        )

    def start_breach_analysis(self) -> None:
        email = self.breach_email_var.get().strip()
        if not email:
            messagebox.showwarning(APP_NAME, "Enter an email address first.")
            return
        self._run_enrichment(
            self.enrichment_buttons[2],
            "Checking the configured breach provider",
            lambda: self.osint_analyzer.check_breach(email),
        )

    def start_ip_analysis(self) -> None:
        ip_address = self.ip_var.get().strip()
        if not ip_address:
            messagebox.showwarning(APP_NAME, "Enter a public IP address first.")
            return
        self._run_enrichment(
            self.enrichment_buttons[3],
            "Looking up public network registration metadata",
            lambda: self.osint_analyzer.analyze_ip_address(ip_address),
        )

    def start_phone_metadata_analysis(self) -> None:
        phone_number = self.osint_phone_var.get().strip()
        if not phone_number:
            messagebox.showwarning(APP_NAME, "Enter an international phone number first.")
            return
        self._run_enrichment(
            self.enrichment_buttons[4],
            "Looking up numbering-plan metadata",
            lambda: self.osint_analyzer.analyze_phone_number_basic_info(phone_number),
        )

    def start_username_analysis(self) -> None:
        username = self.username_var.get().strip()
        if not username:
            messagebox.showwarning(APP_NAME, "Enter a username first.")
            return
        self._run_enrichment(
            self.enrichment_buttons[5],
            "Checking username indicators",
            lambda: self.osint_analyzer.enumerate_social_media_username(username),
        )

    def start_port_scan(self) -> None:
        target = self.network_target_var.get().strip()
        if not target or not TARGET_PATTERN.fullmatch(target) or ".." in target:
            messagebox.showerror(
                APP_NAME, "Enter a valid hostname or IP address using letters, digits, dots and dashes."
            )
            return
        if not self._require_authorisation():
            return
        if not messagebox.askyesno(
            "Confirm authorised scan",
            f"Run a conservative common-port scan against {target}?\n\nProceed only if you own or have explicit written permission to test this host.",
        ):
            return

        def work() -> str:
            process = subprocess.run(
                ["nmap", "-F", target],
                capture_output=True,
                text=True,
                timeout=60,
                check=False,
            )
            output = process.stdout.strip()
            if process.stderr.strip():
                output = f"{output}\n\n--- nmap diagnostics ---\n{process.stderr.strip()}".strip()
            return output or f"nmap exited with status {process.returncode} without output."

        self._replace_text(self.network_text, f"Running conservative scan against {target}…\n")
        self._run_background(self.port_scan_button, f"Scanning {target}…", work, self._show_scan_result)

    def _show_scan_result(self, result: str) -> None:
        self._replace_text(self.network_text, result)
        self.status_var.set("Authorised network scan completed.")

    def view_map(self) -> None:
        if self.current_phone is None or self.current_phone_info is None:
            messagebox.showwarning(APP_NAME, "Analyse a valid phone number first.")
            return
        if not SETTINGS.opencage_api_key:
            messagebox.showwarning(APP_NAME, "Set OPEN_CAGE_API_KEY to enable region-map generation.")
            return

        analyzer = self.current_phone
        phone_info = self.current_phone_info

        def work() -> tuple[Path, str]:
            region_query = phone_info.region if phone_info.region != "Unknown" else (phone_info.country_code or "")
            if not region_query:
                raise RuntimeError("No regional metadata is available for this number.")
            results = analyzer.geocoder.geocode(region_query)
            if not results:
                raise RuntimeError(
                    "The geocoding provider did not return a map location for this numbering-plan region."
                )
            location = results[0]["geometry"]
            label = results[0].get("formatted", region_query)
            region_map = folium.Map(location=[location["lat"], location["lng"]], zoom_start=5, control_scale=True)
            folium.Marker(
                [location["lat"], location["lng"]],
                popup=f"Numbering-plan region: {label}",
                tooltip="Approximate numbering-plan region",
            ).add_to(region_map)
            MAP_DIRECTORY.mkdir(parents=True, exist_ok=True)
            file_path = MAP_DIRECTORY / "numbering_plan_region.html"
            region_map.save(file_path)
            return file_path, label

        self._run_background(
            self.view_map_button, "Generating an approximate numbering-plan region map…", work, self._show_map_result
        )

    def _show_map_result(self, result: tuple[Path, str]) -> None:
        file_path, label = result
        webbrowser.open(file_path.as_uri())
        self._replace_text(
            self.map_text,
            f"Saved and opened the approximate numbering-plan region map:\n{file_path}\n\n"
            f"Provider label: {label}\n\n"
            "This map represents the broad numbering-plan region only. It is not a location for a person, phone or device.",
        )
        self.status_var.set("Region map generated.")

    def clear_results(self) -> None:
        self.phone_var.set("")
        self.current_phone = None
        self.current_phone_info = None
        self.view_map_button.state(["disabled"])
        self._replace_text(self.basic_info_text, "Enter an international phone number and select Analyse.")
        self._replace_text(self.map_text, "Analyse a valid phone number to enable the region map.")
        self.status_var.set("Results cleared.")

    def _on_close(self) -> None:
        self.osint_analyzer._session.close()
        self.root.destroy()


def main() -> None:
    """Start the Pheonix desktop application."""

    logging.basicConfig(
        level=logging.INFO,
        format="%(asctime)s %(levelname)s %(name)s: %(message)s",
    )
    root = tk.Tk()
    PhoneAnalyzerGUI(root)
    root.mainloop()


if __name__ == "__main__":
    main()
