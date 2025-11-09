"""
PII Guard Preferences GUI
Configure what to obfuscate and where.
"""

import sys
from pathlib import Path
import json
import tkinter as tk
from tkinter import ttk, messagebox
from typing import Dict, List


class PreferencesManager:
    """
    Manages PII Guard preferences.
    Saves/loads configuration to/from JSON file.
    """
    
    DEFAULT_PREFERENCES = {
        'detectors': {
            'regex': False,  # Disabled - transformer-first approach
            'spacy': False,  # Disabled - transformer-first approach
            'transformer': True  # ENABLED by default - primary detection
        },
        'sources': {
            'clipboard': True,
            'typing': True
        },
        'entity_types': {
            'EMAIL': True,
            'PHONE': True,
            'SSN': True,
            'CREDIT_CARD': True,
            'PERSON': True,
            'LOCATION': True,
            'ORGANIZATION': True,
            'DATE': False,  # Often causes false positives
            'IP_ADDRESS': False,
            'URL': False,
            'ID_NUMBER': True
        },
        'whitelist': {
            'apps': [],  # e.g., ['notepad++.exe', 'code.exe']
            'domains': []  # e.g., ['company.com']
        },
        'notifications': {
            'enabled': True,
            'auto_dismiss_seconds': 5,
            'show_preview': True
        },
        'advanced': {
            'confidence_threshold': 0.5,
            'min_text_length': 10,
            'spacy_model': 'en_core_web_sm',
            'transformer_model': 'lakshyakh93/deberta_finetuned_pii',
            'use_consensus': False,
            'consensus_mode': 'any_two'
        }
    }
    
    def __init__(self, config_path: str = "data/pii_guard_config.json"):
        """Initialize preferences manager"""
        self.config_path = Path(config_path)
        self.config_path.parent.mkdir(parents=True, exist_ok=True)
        self.preferences = self.load()
    
    def load(self) -> Dict:
        """Load preferences from file"""
        if self.config_path.exists():
            try:
                with open(self.config_path, 'r') as f:
                    loaded = json.load(f)
                # Merge with defaults (in case new keys were added)
                return self._merge_with_defaults(loaded)
            except Exception as e:
                print(f"Error loading preferences: {e}")
                return self.DEFAULT_PREFERENCES.copy()
        return self.DEFAULT_PREFERENCES.copy()
    
    def save(self) -> bool:
        """Save preferences to file"""
        try:
            with open(self.config_path, 'w') as f:
                json.dump(self.preferences, f, indent=2)
            return True
        except Exception as e:
            print(f"Error saving preferences: {e}")
            return False
    
    def _merge_with_defaults(self, loaded: Dict) -> Dict:
        """Merge loaded config with defaults"""
        result = self.DEFAULT_PREFERENCES.copy()
        
        def deep_update(base, updates):
            for key, value in updates.items():
                if key in base and isinstance(base[key], dict) and isinstance(value, dict):
                    deep_update(base[key], value)
                else:
                    base[key] = value
        
        deep_update(result, loaded)
        return result
    
    def get(self, key: str, default=None):
        """Get preference value"""
        keys = key.split('.')
        value = self.preferences
        for k in keys:
            if isinstance(value, dict) and k in value:
                value = value[k]
            else:
                return default
        return value
    
    def set(self, key: str, value):
        """Set preference value"""
        keys = key.split('.')
        target = self.preferences
        for k in keys[:-1]:
            if k not in target:
                target[k] = {}
            target = target[k]
        target[keys[-1]] = value
    
    def reset_to_defaults(self):
        """Reset all preferences to defaults"""
        self.preferences = self.DEFAULT_PREFERENCES.copy()


class PreferencesGUI:
    """GUI for editing PII Guard preferences"""
    
    def __init__(self):
        self.prefs_manager = PreferencesManager()
        self.root = tk.Tk()
        self.root.title("PII Guard - Preferences")
        self.root.geometry("600x700")
        self.root.resizable(True, True)
        
        # Variables for checkboxes
        self.vars = {}
        
        self._create_ui()
        self._load_current_preferences()
    
    def _create_ui(self):
        """Create the user interface"""
        # Create notebook for tabs
        notebook = ttk.Notebook(self.root)
        notebook.pack(fill=tk.BOTH, expand=True, padx=10, pady=10)
        
        # Tab 1: Detection Settings
        tab_detection = ttk.Frame(notebook)
        notebook.add(tab_detection, text="Detection")
        self._create_detection_tab(tab_detection)
        
        # Tab 2: Entity Types
        tab_entities = ttk.Frame(notebook)
        notebook.add(tab_entities, text="Entity Types")
        self._create_entities_tab(tab_entities)
        
        # Tab 3: Sources
        tab_sources = ttk.Frame(notebook)
        notebook.add(tab_sources, text="Sources")
        self._create_sources_tab(tab_sources)
        
        # Tab 4: Whitelist
        tab_whitelist = ttk.Frame(notebook)
        notebook.add(tab_whitelist, text="Whitelist")
        self._create_whitelist_tab(tab_whitelist)
        
        # Tab 5: Notifications
        tab_notifications = ttk.Frame(notebook)
        notebook.add(tab_notifications, text="Notifications")
        self._create_notifications_tab(tab_notifications)
        
        # Bottom buttons
        button_frame = ttk.Frame(self.root)
        button_frame.pack(fill=tk.X, padx=10, pady=10)
        
        ttk.Button(button_frame, text="Save", command=self._save_preferences).pack(side=tk.LEFT, padx=5)
        ttk.Button(button_frame, text="Cancel", command=self.root.destroy).pack(side=tk.LEFT, padx=5)
        ttk.Button(button_frame, text="Reset to Defaults", command=self._reset_to_defaults).pack(side=tk.RIGHT, padx=5)
    
    def _create_detection_tab(self, parent):
        """Create detection settings tab"""
        frame = ttk.Frame(parent, padding=15)
        frame.pack(fill=tk.BOTH, expand=True)
        
        ttk.Label(frame, text="Detection Engines", font=('Segoe UI', 12, 'bold')).pack(anchor=tk.W, pady=(0, 10))
        
        # Regex detector
        self.vars['detector_regex'] = tk.BooleanVar()
        ttk.Checkbutton(frame, text="Regex Pattern Matching (Fast, ~1-5ms)", 
                       variable=self.vars['detector_regex']).pack(anchor=tk.W, pady=5)
        ttk.Label(frame, text="  Detects: Emails, phones, SSNs, credit cards, IPs, URLs",
                 foreground='gray').pack(anchor=tk.W)
        
        # spaCy detector
        self.vars['detector_spacy'] = tk.BooleanVar()
        ttk.Checkbutton(frame, text="spaCy NER (Fast, ~30-50ms)", 
                       variable=self.vars['detector_spacy']).pack(anchor=tk.W, pady=(15, 5))
        ttk.Label(frame, text="  Detects: Person names, locations, organizations",
                 foreground='gray').pack(anchor=tk.W)
        
        # Transformer detector
        self.vars['detector_transformer'] = tk.BooleanVar()
        ttk.Checkbutton(frame, text="Transformer Model (Accurate, ~200-400ms, requires GPU)", 
                       variable=self.vars['detector_transformer']).pack(anchor=tk.W, pady=(15, 5))
        ttk.Label(frame, text="  Context-aware detection, best accuracy (slower)",
                 foreground='gray').pack(anchor=tk.W)
        
        ttk.Separator(frame, orient=tk.HORIZONTAL).pack(fill=tk.X, pady=20)
        
        # Advanced settings
        ttk.Label(frame, text="Advanced Settings", font=('Segoe UI', 12, 'bold')).pack(anchor=tk.W, pady=(0, 10))
        
        # Confidence threshold
        conf_frame = ttk.Frame(frame)
        conf_frame.pack(fill=tk.X, pady=5)
        ttk.Label(conf_frame, text="Confidence Threshold:").pack(side=tk.LEFT)
        self.vars['confidence_threshold'] = tk.DoubleVar()
        ttk.Scale(conf_frame, from_=0.0, to=1.0, variable=self.vars['confidence_threshold'],
                 orient=tk.HORIZONTAL, length=200).pack(side=tk.LEFT, padx=10)
        self.confidence_label = ttk.Label(conf_frame, text="0.5")
        self.confidence_label.pack(side=tk.LEFT)
        self.vars['confidence_threshold'].trace_add('write', self._update_confidence_label)
    
    def _create_entities_tab(self, parent):
        """Create entity types tab"""
        frame = ttk.Frame(parent, padding=15)
        frame.pack(fill=tk.BOTH, expand=True)
        
        ttk.Label(frame, text="Select which types of PII to detect and obfuscate:", 
                 font=('Segoe UI', 10)).pack(anchor=tk.W, pady=(0, 15))
        
        # Create checkboxes for each entity type
        entities = [
            ('EMAIL', 'Email Addresses', 'john@email.com'),
            ('PHONE', 'Phone Numbers', '(555) 123-4567'),
            ('SSN', 'Social Security Numbers', '123-45-6789'),
            ('CREDIT_CARD', 'Credit Card Numbers', '4532-0151-1283-0366'),
            ('PERSON', 'Person Names', 'John Smith'),
            ('LOCATION', 'Locations', 'Seattle, WA'),
            ('ORGANIZATION', 'Organizations', 'Microsoft Corporation'),
            ('DATE', 'Dates', '01/15/2024'),
            ('IP_ADDRESS', 'IP Addresses', '192.168.1.1'),
            ('URL', 'URLs', 'https://example.com'),
            ('ID_NUMBER', 'ID Numbers', 'EMP-12345')
        ]
        
        for entity_type, label, example in entities:
            var_name = f'entity_{entity_type}'
            self.vars[var_name] = tk.BooleanVar()
            
            cb_frame = ttk.Frame(frame)
            cb_frame.pack(fill=tk.X, pady=5)
            
            ttk.Checkbutton(cb_frame, text=label, variable=self.vars[var_name]).pack(side=tk.LEFT)
            ttk.Label(cb_frame, text=f"  (e.g., {example})", foreground='gray').pack(side=tk.LEFT)
    
    def _create_sources_tab(self, parent):
        """Create sources tab"""
        frame = ttk.Frame(parent, padding=15)
        frame.pack(fill=tk.BOTH, expand=True)
        
        ttk.Label(frame, text="Enable PII protection for:", 
                 font=('Segoe UI', 10)).pack(anchor=tk.W, pady=(0, 15))
        
        # Clipboard
        self.vars['source_clipboard'] = tk.BooleanVar()
        ttk.Checkbutton(frame, text="Clipboard (Copy/Paste)", 
                       variable=self.vars['source_clipboard']).pack(anchor=tk.W, pady=5)
        ttk.Label(frame, text="  Automatically obfuscates PII when you copy text",
                 foreground='gray').pack(anchor=tk.W, padx=20)
        
        # Typing
        self.vars['source_typing'] = tk.BooleanVar()
        ttk.Checkbutton(frame, text="Typing (Desktop Apps)", 
                       variable=self.vars['source_typing']).pack(anchor=tk.W, pady=(15, 5))
        ttk.Label(frame, text="  Monitors typing in Slack, Teams, Outlook, Discord",
                 foreground='gray').pack(anchor=tk.W, padx=20)
    
    def _create_whitelist_tab(self, parent):
        """Create whitelist tab"""
        frame = ttk.Frame(parent, padding=15)
        frame.pack(fill=tk.BOTH, expand=True)
        
        ttk.Label(frame, text="Whitelist trusted applications and domains:", 
                 font=('Segoe UI', 10)).pack(anchor=tk.W, pady=(0, 15))
        
        # Trusted apps
        ttk.Label(frame, text="Trusted Applications:", font=('Segoe UI', 10, 'bold')).pack(anchor=tk.W, pady=(10, 5))
        ttk.Label(frame, text="PII protection will be disabled in these apps (one per line):",
                 foreground='gray').pack(anchor=tk.W)
        
        apps_frame = ttk.Frame(frame)
        apps_frame.pack(fill=tk.BOTH, expand=True, pady=5)
        
        self.apps_text = tk.Text(apps_frame, height=6, width=50)
        self.apps_text.pack(side=tk.LEFT, fill=tk.BOTH, expand=True)
        
        apps_scroll = ttk.Scrollbar(apps_frame, command=self.apps_text.yview)
        apps_scroll.pack(side=tk.RIGHT, fill=tk.Y)
        self.apps_text.config(yscrollcommand=apps_scroll.set)
        
        ttk.Label(frame, text="Examples: notepad++.exe, code.exe, sublime_text.exe",
                 foreground='gray', font=('Segoe UI', 8)).pack(anchor=tk.W)
        
        # Trusted domains
        ttk.Label(frame, text="Trusted Email Domains:", font=('Segoe UI', 10, 'bold')).pack(anchor=tk.W, pady=(20, 5))
        ttk.Label(frame, text="Email addresses from these domains won't be obfuscated:",
                 foreground='gray').pack(anchor=tk.W)
        
        domains_frame = ttk.Frame(frame)
        domains_frame.pack(fill=tk.BOTH, expand=True, pady=5)
        
        self.domains_text = tk.Text(domains_frame, height=6, width=50)
        self.domains_text.pack(side=tk.LEFT, fill=tk.BOTH, expand=True)
        
        domains_scroll = ttk.Scrollbar(domains_frame, command=self.domains_text.yview)
        domains_scroll.pack(side=tk.RIGHT, fill=tk.Y)
        self.domains_text.config(yscrollcommand=domains_scroll.set)
        
        ttk.Label(frame, text="Examples: company.com, mycorp.org",
                 foreground='gray', font=('Segoe UI', 8)).pack(anchor=tk.W)
    
    def _create_notifications_tab(self, parent):
        """Create notifications tab"""
        frame = ttk.Frame(parent, padding=15)
        frame.pack(fill=tk.BOTH, expand=True)
        
        ttk.Label(frame, text="Notification Settings", font=('Segoe UI', 12, 'bold')).pack(anchor=tk.W, pady=(0, 15))
        
        # Enable notifications
        self.vars['notifications_enabled'] = tk.BooleanVar()
        ttk.Checkbutton(frame, text="Show notifications when PII is detected", 
                       variable=self.vars['notifications_enabled']).pack(anchor=tk.W, pady=5)
        
        # Show preview
        self.vars['notifications_show_preview'] = tk.BooleanVar()
        ttk.Checkbutton(frame, text="Show preview of detected PII in notifications", 
                       variable=self.vars['notifications_show_preview']).pack(anchor=tk.W, pady=5)
        
        # Auto-dismiss
        dismiss_frame = ttk.Frame(frame)
        dismiss_frame.pack(fill=tk.X, pady=(15, 5))
        ttk.Label(dismiss_frame, text="Auto-dismiss after:").pack(side=tk.LEFT)
        
        self.vars['auto_dismiss'] = tk.IntVar()
        ttk.Spinbox(dismiss_frame, from_=0, to=60, textvariable=self.vars['auto_dismiss'],
                   width=5).pack(side=tk.LEFT, padx=10)
        ttk.Label(dismiss_frame, text="seconds (0 = never)").pack(side=tk.LEFT)
    
    def _update_confidence_label(self, *args):
        """Update confidence threshold label"""
        value = self.vars['confidence_threshold'].get()
        self.confidence_label.config(text=f"{value:.2f}")
    
    def _load_current_preferences(self):
        """Load current preferences into UI"""
        prefs = self.prefs_manager.preferences
        
        # Detectors
        self.vars['detector_regex'].set(prefs['detectors']['regex'])
        self.vars['detector_spacy'].set(prefs['detectors']['spacy'])
        self.vars['detector_transformer'].set(prefs['detectors']['transformer'])
        
        # Sources
        self.vars['source_clipboard'].set(prefs['sources']['clipboard'])
        self.vars['source_typing'].set(prefs['sources']['typing'])
        
        # Entity types
        for entity_type, enabled in prefs['entity_types'].items():
            var_name = f'entity_{entity_type}'
            if var_name in self.vars:
                self.vars[var_name].set(enabled)
        
        # Notifications
        self.vars['notifications_enabled'].set(prefs['notifications']['enabled'])
        self.vars['notifications_show_preview'].set(prefs['notifications']['show_preview'])
        self.vars['auto_dismiss'].set(prefs['notifications']['auto_dismiss_seconds'])
        
        # Advanced
        self.vars['confidence_threshold'].set(prefs['advanced']['confidence_threshold'])
        
        # Whitelist
        self.apps_text.delete('1.0', tk.END)
        self.apps_text.insert('1.0', '\n'.join(prefs['whitelist']['apps']))
        
        self.domains_text.delete('1.0', tk.END)
        self.domains_text.insert('1.0', '\n'.join(prefs['whitelist']['domains']))
    
    def _save_preferences(self):
        """Save preferences from UI"""
        prefs = self.prefs_manager.preferences
        
        # Detectors
        prefs['detectors']['regex'] = self.vars['detector_regex'].get()
        prefs['detectors']['spacy'] = self.vars['detector_spacy'].get()
        prefs['detectors']['transformer'] = self.vars['detector_transformer'].get()
        
        # Sources
        prefs['sources']['clipboard'] = self.vars['source_clipboard'].get()
        prefs['sources']['typing'] = self.vars['source_typing'].get()
        
        # Entity types
        for entity_type in prefs['entity_types'].keys():
            var_name = f'entity_{entity_type}'
            if var_name in self.vars:
                prefs['entity_types'][entity_type] = self.vars[var_name].get()
        
        # Notifications
        prefs['notifications']['enabled'] = self.vars['notifications_enabled'].get()
        prefs['notifications']['show_preview'] = self.vars['notifications_show_preview'].get()
        prefs['notifications']['auto_dismiss_seconds'] = self.vars['auto_dismiss'].get()
        
        # Advanced
        prefs['advanced']['confidence_threshold'] = self.vars['confidence_threshold'].get()
        
        # Whitelist
        apps_text = self.apps_text.get('1.0', tk.END).strip()
        prefs['whitelist']['apps'] = [line.strip() for line in apps_text.split('\n') if line.strip()]
        
        domains_text = self.domains_text.get('1.0', tk.END).strip()
        prefs['whitelist']['domains'] = [line.strip() for line in domains_text.split('\n') if line.strip()]
        
        # Save to file
        if self.prefs_manager.save():
            messagebox.showinfo("Success", "Preferences saved successfully!\n\nRestart monitors for changes to take effect.")
            self.root.destroy()
        else:
            messagebox.showerror("Error", "Failed to save preferences.")
    
    def _reset_to_defaults(self):
        """Reset preferences to defaults"""
        if messagebox.askyesno("Reset to Defaults", "Are you sure you want to reset all preferences to defaults?"):
            self.prefs_manager.reset_to_defaults()
            self._load_current_preferences()
            messagebox.showinfo("Reset Complete", "Preferences have been reset to defaults.")
    
    def run(self):
        """Run the GUI"""
        self.root.mainloop()


if __name__ == "__main__":
    print("Starting PII Guard Preferences...")
    gui = PreferencesGUI()
    gui.run()