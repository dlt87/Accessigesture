import tkinter as tk
from tkinter import ttk
import threading

class ModernSlider(ttk.Frame):
    # ... (Your ModernSlider class is perfect and unchanged) ...
    """Custom slider widget with better visuals and controls."""
    def __init__(self, parent, label, default_value, min_val, max_val, 
                 resolution, callback, description="", unit="", **kwargs):
        super().__init__(parent, **kwargs)
        
        self.min_val = min_val
        self.max_val = max_val
        self.resolution = resolution
        self.callback = callback
        self.unit = unit
        
        # Container frame
        container = ttk.Frame(self)
        container.pack(fill=tk.BOTH, expand=True, padx=5, pady=5)
        
        # Header with label and value
        header_frame = ttk.Frame(container)
        header_frame.pack(fill=tk.X, pady=(0, 5))
        
        label_widget = ttk.Label(header_frame, text=label, 
                                 font=('Segoe UI', 10, 'bold'))
        label_widget.pack(side=tk.LEFT)
        
        self.value_var = tk.StringVar(value=self._format_value(default_value))
        value_label = ttk.Label(header_frame, textvariable=self.value_var, 
                                font=('Segoe UI', 10), foreground='#0066cc')
        value_label.pack(side=tk.RIGHT)
        
        # Slider frame with buttons
        slider_frame = ttk.Frame(container)
        slider_frame.pack(fill=tk.X, pady=(0, 3))
        
        # Decrease button
        dec_btn = ttk.Button(slider_frame, text="−", width=3,
                             command=lambda: self._adjust_value(-resolution))
        dec_btn.pack(side=tk.LEFT, padx=(0, 5))
        
        # Slider
        self.slider = ttk.Scale(slider_frame, from_=min_val, to=max_val, 
                                orient=tk.HORIZONTAL, command=self._on_change)
        self.slider.set(default_value)
        self.slider.pack(side=tk.LEFT, fill=tk.X, expand=True)
        
        # Increase button
        inc_btn = ttk.Button(slider_frame, text="+", width=3,
                             command=lambda: self._adjust_value(resolution))
        inc_btn.pack(side=tk.LEFT, padx=(5, 0))
        
        # Description
        if description:
            desc_label = ttk.Label(container, text=description, 
                                   font=('Segoe UI', 8), foreground='#666666')
            desc_label.pack(anchor=tk.W, pady=(0, 5))
    
    def _format_value(self, value):
        """Format value for display."""
        if self.resolution < 1:
            formatted = f"{value:.2f}"
        else:
            formatted = f"{int(value)}"
        return f"{formatted} {self.unit}".strip()
    
    def _on_change(self, val):
        """Handle slider change."""
        float_val = float(val)
        rounded_val = round(float_val / self.resolution) * self.resolution
        self.value_var.set(self._format_value(rounded_val))
        self.callback(rounded_val)
    
    def _adjust_value(self, delta):
        """Adjust value by delta using buttons."""
        current = self.slider.get()
        new_value = max(self.min_val, min(self.max_val, current + delta))
        self.slider.set(new_value)
        self._on_change(new_value)
    
    def get(self):
        """Get current slider value."""
        return self.slider.get()
    
    def set(self, value):
        """Set slider value."""
        self.slider.set(value)
        self._on_change(value)


class SettingsWindow:
    # --- NEW: Added 'on_quit' callback ---
    def __init__(self, on_quit=None):
        self.window = None
        self.thread = None
        self.on_quit_callback = on_quit # Store the quit function
        
        # Default settings
        self.smoothing_factor = 0.2
        self.fist_cooldown = 1.0
        self.pinch_threshold = 0.05
        self.min_detection_confidence = 0.7
        self.min_tracking_confidence = 0.5
        self.roi_x_min = 0.5
        self.roi_x_max = 0.9
        self.roi_y_min = 0.5
        self.roi_y_max = 0.9
        self.scroll_speed = 3
        
        # --- REVERSED MAPPING ---
        self.gesture_names = ["None", "PINCH", "PINCH_MID", "THUMBS_UP", "THUMBS_DOWN", "OPEN", "TOGGLE"]
        self.action_names = ["Move Cursor", "Left Click (Hold)", "Right Click (Once)", "Scroll Up", "Scroll Down"]
        self.action_mappings = {} 
        
        self.on_settings_changed = None
        
    def create_window(self):
        """Create the settings window in a separate thread."""
        self.thread = threading.Thread(target=self._run_window, daemon=True)
        self.thread.start()
    
    def _run_window(self):
        """Run the tkinter window in a separate thread."""
        self.window = tk.Tk()
        self.window.title("✋ Gesture Control Settings")
        self.window.geometry("580x950") 
        self.window.resizable(False, False)
        
        # --- NEW: Handle window close ('X' button) ---
        self.window.protocol("WM_DELETE_WINDOW", self._quit_app)
        
        # ... (Styling code is unchanged) ...
        self.window.configure(bg='#f0f0f0')
        self.window.attributes('-topmost', True)
        style = ttk.Style()
        style.theme_use('clam')
        style.configure('Title.TLabel', font=('Segoe UI', 16, 'bold'), background='#f0f0f0', foreground='#2c3e50')
        style.configure('Section.TLabel', font=('Segoe UI', 12, 'bold'), background='#f0f0f0', foreground='#34495e')
        style.configure('TFrame', background='#f0f0f0')
        style.configure('Card.TFrame', background='#ffffff', relief='flat')
        style.configure('TButton', font=('Segoe UI', 9), padding=8)
        style.map('TButton', background=[('active', '#3498db')])
        
        # ... (Scrollable canvas code is unchanged) ...
        canvas = tk.Canvas(self.window, bg='#f0f0f0', highlightthickness=0)
        scrollbar = ttk.Scrollbar(self.window, orient="vertical", command=canvas.yview)
        scrollable_frame = ttk.Frame(canvas)
        scrollable_frame.bind("<Configure>", lambda e: canvas.configure(scrollregion=canvas.bbox("all")))
        canvas.create_window((0, 0), window=scrollable_frame, anchor="nw")
        canvas.configure(yscrollcommand=scrollbar.set)
        scrollbar.pack(side="right", fill="y")
        canvas.pack(side="left", fill="both", expand=True)
        def _on_mousewheel(event):
            canvas.yview_scroll(int(-1*(event.delta/120)), "units")
        canvas.bind_all("<MouseWheel>", _on_mousewheel)
        
        # ... (Main frame and Title code is unchanged) ...
        main_frame = ttk.Frame(scrollable_frame, padding="15")
        main_frame.pack(fill=tk.BOTH, expand=True)
        title_frame = ttk.Frame(main_frame)
        title_frame.pack(fill=tk.X, pady=(0, 20))
        title = ttk.Label(title_frame, text="✋ Gesture Control Settings", style='Title.TLabel')
        title.pack()
        subtitle = ttk.Label(title_frame, text="Adjust parameters in real-time", font=('Segoe UI', 9), foreground='#7f8c8d')
        subtitle.pack()

        # ... (All Slider/Card code for Thresholds is unchanged) ...
        cursor_card = self._create_card(main_frame, "🖱️ Cursor Settings")
        self.smoothing_slider = ModernSlider(cursor_card, "Smoothing Factor", self.smoothing_factor, 0.0, 1.0, 0.05, lambda v: setattr(self, 'smoothing_factor', v), "Higher = more responsive • Lower = smoother")
        self.smoothing_slider.pack(fill=tk.X)
        preset_frame = ttk.Frame(cursor_card)
        preset_frame.pack(fill=tk.X, pady=(0, 10), padx=5)
        ttk.Label(preset_frame, text="Presets:", font=('Segoe UI', 8), foreground='#666666').pack(side=tk.LEFT, padx=(0, 5))
        for name, value in [("Smooth", 0.2), ("Balanced", 0.5), ("Responsive", 0.8)]:
            ttk.Button(preset_frame, text=name, command=lambda v=value: self.smoothing_slider.set(v), width=10).pack(side=tk.LEFT, padx=2)
        ttk.Separator(cursor_card, orient='horizontal').pack(fill=tk.X, pady=10)
        ttk.Label(cursor_card, text="Tracking Area (ROI)", font=('Segoe UI', 9, 'bold')).pack(anchor=tk.W, padx=5)
        self.roi_x_min_slider = ModernSlider(cursor_card, "ROI Left Edge", self.roi_x_min, 0.0, 0.8, 0.05, lambda v: setattr(self, 'roi_x_min', v), "Left boundary of hand tracking area")
        self.roi_x_min_slider.pack(fill=tk.X)
        self.roi_x_max_slider = ModernSlider(cursor_card, "ROI Right Edge", self.roi_x_max, 0.2, 1.0, 0.05, lambda v: setattr(self, 'roi_x_max', v), "Right boundary of hand tracking area")
        self.roi_x_max_slider.pack(fill=tk.X)
        self.roi_y_min_slider = ModernSlider(cursor_card, "ROI Top Edge", self.roi_y_min, 0.0, 0.8, 0.05, lambda v: setattr(self, 'roi_y_min', v), "Top boundary of hand tracking area")
        self.roi_y_min_slider.pack(fill=tk.X)
        self.roi_y_max_slider = ModernSlider(cursor_card, "ROI Bottom Edge", self.roi_y_max, 0.2, 1.0, 0.05, lambda v: setattr(self, 'roi_y_max', v), "Bottom boundary of hand tracking area")
        self.roi_y_max_slider.pack(fill=tk.X)
        gesture_card = self._create_card(main_frame, "👆 Gesture Thresholds")
        self.pinch_slider = ModernSlider(gesture_card, "Pinch Threshold", self.pinch_threshold, 0.01, 0.15, 0.01, lambda v: setattr(self, 'pinch_threshold', v), "Distance between fingers to trigger pinch")
        self.pinch_slider.pack(fill=tk.X)
        self.fist_cooldown_slider = ModernSlider(gesture_card, "Fist Cooldown", self.fist_cooldown, 0.1, 3.0, 0.1, lambda v: setattr(self, 'fist_cooldown', v), "Time between repeated fist actions", unit="s")
        self.fist_cooldown_slider.pack(fill=tk.X)
        self.scroll_speed_slider = ModernSlider(gesture_card, "Scroll Speed", self.scroll_speed, 1, 10, 1, lambda v: setattr(self, 'scroll_speed', int(v)), "Speed of scroll gestures")
        self.scroll_speed_slider.pack(fill=tk.X)
        
        # ... (Action Mapping card is unchanged) ...
        mapping_card = self._create_card(main_frame, "🔄 Action Mapping")
        ttk.Label(mapping_card, text="Assign a hand gesture to a computer action.", font=('Segoe UI', 8), foreground='#666666').pack(anchor=tk.W, padx=5, pady=(0, 10))
        for action in self.action_names:
            frame = ttk.Frame(mapping_card, style='Card.TFrame') 
            frame.pack(fill=tk.X, padx=5, pady=2)
            tk.Label(frame, text=f"{action}:", width=15, anchor="w", font=('Segoe UI', 10), background='white').pack(side=tk.LEFT, padx=(5, 0))
            var = tk.StringVar(self.window)
            if action == "Left Click (Hold)": var.set("PINCH")
            elif action == "Right Click (Once)": var.set("PINCH_MID")
            elif action == "Scroll Up": var.set("THUMBS_UP")
            elif action == "Scroll Down": var.set("THUMBS_DOWN")
            elif action == "Move Cursor": var.set("OPEN")
            else: var.set("None")
            dropdown = ttk.OptionMenu(frame, var, var.get(), *self.gesture_names)
            dropdown.pack(side=tk.LEFT, fill=tk.X, expand=True, padx=(5, 10), pady=5)
            self.action_mappings[action] = var 
        
        # ... (Detection Settings card is unchanged) ...
        detection_card = self._create_card(main_frame, "🔍 Hand Detection")
        self.detection_conf_slider = ModernSlider(detection_card, "Detection Confidence", self.min_detection_confidence, 0.3, 1.0, 0.05, lambda v: setattr(self, 'min_detection_confidence', v), "Minimum confidence to detect hand initially")
        self.detection_conf_slider.pack(fill=tk.X)
        self.tracking_conf_slider = ModernSlider(detection_card, "Tracking Confidence", self.min_tracking_confidence, 0.3, 1.0, 0.05, lambda v: setattr(self, 'min_tracking_confidence', v), "Minimum confidence to track hand continuously")
        self.tracking_conf_slider.pack(fill=tk.X)
        
        # === BUTTONS ===
        button_card = ttk.Frame(main_frame)
        button_card.pack(fill=tk.X, pady=(15, 10))
        button_container = ttk.Frame(button_card)
        button_container.pack()
        
        reset_btn = ttk.Button(button_container, text="🔄 Reset to Defaults", 
                                 command=self._reset_defaults)
        reset_btn.pack(side=tk.LEFT, padx=5)
        
        # --- NEW: Quit Button ---
        # Add a style for the quit button
        style.configure('Quit.TButton', font=('Segoe UI', 9, 'bold'), foreground='white', background='#e74c3c')
        style.map('Quit.TButton', background=[('active', '#c0392b')])
        
        quit_btn = ttk.Button(button_container, text="❌ Quit Program", 
                                command=self._quit_app, style='Quit.TButton')
        quit_btn.pack(side=tk.LEFT, padx=5)
        # --- END NEW ---
        
        # ... (Info label is unchanged) ...
        info_frame = ttk.Frame(main_frame)
        info_frame.pack(fill=tk.X, pady=(10, 0))
        info_label = ttk.Label(info_frame, text="💡 Tip: Changes apply immediately", font=('Segoe UI', 8), foreground='#27ae60', background='#e8f5e9', relief='flat', padding=8)
        info_label.pack(fill=tk.X)
        
        self.window.mainloop()
    
    # --- NEW: Quit Function ---
    def _quit_app(self):
        """Signals the main thread to stop and closes the UI."""
        if self.on_quit_callback:
            self.on_quit_callback() # Signal main.py to stop
        self.window.destroy() # Close this settings window
    # --- END NEW ---

    def _create_card(self, parent, title):
        # ... (This helper function is unchanged) ...
        card = ttk.Frame(parent, style='Card.TFrame', relief='solid', borderwidth=1)
        card.pack(fill=tk.X, pady=(0, 15), padx=2)
        header = ttk.Frame(card, style='Card.TFrame') 
        header.pack(fill=tk.X, pady=(10, 5), padx=15)
        title_label = ttk.Label(header, text=title, style='Section.TLabel', background='white')
        title_label.pack(side=tk.LEFT)
        content = ttk.Frame(card, style='Card.TFrame') 
        content.pack(fill=tk.BOTH, expand=True, padx=10, pady=(5, 15))
        return content
    
    def _reset_defaults(self):
        """Reset all settings to default values."""
        # ... (Resetting values is unchanged) ...
        self.smoothing_factor = 0.2
        self.fist_cooldown = 1.0
        self.pinch_threshold = 0.05
        self.min_detection_confidence = 0.7
        self.min_tracking_confidence = 0.5
        self.roi_x_min = 0.5
        self.roi_x_max = 0.9
        self.roi_y_min = 0.5
        self.roi_y_max = 0.9
        self.scroll_speed = 3
        
        # Update sliders and mappings
        try:
            self.smoothing_slider.set(self.smoothing_factor)
            self.pinch_slider.set(self.pinch_threshold)
            self.fist_cooldown_slider.set(self.fist_cooldown)
            self.scroll_speed_slider.set(self.scroll_speed)
            self.detection_conf_slider.set(self.min_detection_confidence)
            self.tracking_conf_slider.set(self.min_tracking_confidence)
            self.roi_x_min_slider.set(self.roi_x_min)
            self.roi_x_max_slider.set(self.roi_x_max)
            self.roi_y_min_slider.set(self.roi_y_min)
            self.roi_y_max_slider.set(self.roi_y_max)
            
            if self.action_mappings:
                self.action_mappings["Left Click (Hold)"].set("PINCH")
                self.action_mappings["Right Click (Once)"].set("PINCH_MID")
                self.action_mappings["Scroll Up"].set("THUMBS_UP")
                self.action_mappings["Scroll Down"].set("THUMBS_DOWN")
                self.action_mappings["Move Cursor"].set("OPEN")
                
        except:
            pass
        
        if self.on_settings_changed:
            self.on_settings_changed()
    
    def get_settings(self):
        # ... (This function is unchanged) ...
        settings = {
            'smoothing_factor': self.smoothing_factor,
            'fist_cooldown': self.fist_cooldown,
            'pinch_threshold': self.pinch_threshold,
            'min_detection_confidence': self.min_detection_confidence,
            'min_tracking_confidence': self.min_tracking_confidence,
            'roi_x_min': self.roi_x_min,
            'roi_x_max': self.roi_x_max,
            'roi_y_min': self.roi_y_min,
            'roi_y_max': self.roi_y_max,
            'scroll_speed': self.scroll_speed,
            'mappings': {}
        }
        if self.action_mappings:
            for action, var in self.action_mappings.items():
                settings['mappings'][action] = var.get()
        return settings