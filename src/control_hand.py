import customtkinter as ctk
import math
import subprocess
import threading
import sys
import time
import os
import arduino_controller as ac 

# ================= THEME =================
ctk.set_appearance_mode("dark")
ctk.set_default_color_theme("blue")

BG_COLOR = "#0A0E17"
CARD_BG = "#111827"
PURPLE = "#7C3AED"
PURPLE_GLOW = "#A78BFA"
CYAN = "#06B6D4"
CYAN_GLOW = "#22D3EE"
GREEN = "#10B981"
GREEN_GLOW = "#34D399"
RED = "#EF4444"
RED_LIGHT = "#F87171"
AMBER = "#F59E0B"
TEXT_COLOR = "#F1F5F9"
MUTED_TEXT = "#64748B"

# ================= GLOW BUTTON CLASS =================
class GlowingButton(ctk.CTkFrame):
    def __init__(self, master, text, icon, color, glow_color, command=None):
        super().__init__(master, fg_color="transparent")
        self.color = color
        self.glow_color = glow_color
        self.command = command
        self.is_active = False
        self.glow_phase = 0
        self._enabled = True

        self.button = ctk.CTkButton(
            self,
            text=f"{icon}  {text}",
            width=320,
            height=56,
            corner_radius=12,
            fg_color="transparent",
            border_color=color,
            border_width=2,
            text_color=TEXT_COLOR,
            font=("Segoe UI", 14, "bold"),
            hover_color=self._blend(CARD_BG, color, 0.15),
            command=self.on_click
        )
        self.button.pack()

    def on_click(self):
        if self._enabled and self.command:
            self.command()

    def set_enabled(self, state):
        self._enabled = state
        if state:
            self.button.configure(state="normal", border_color=self.color, text_color=TEXT_COLOR)
        else:
            self.button.configure(state="disabled", border_color=MUTED_TEXT, text_color=MUTED_TEXT)
            self.set_active(False)

    def set_active(self, active):
        if not self._enabled: return
        self.is_active = active
        if active:
            self.button.configure(fg_color=self._blend(CARD_BG, self.color, 0.25), border_color=self.glow_color, border_width=3)
            self.animate_glow()
        else:
            self.button.configure(fg_color="transparent", border_color=self.color, border_width=2)

    def animate_glow(self):
        if not self.is_active or not self._enabled: return
        self.glow_phase += 0.15
        glow_strength = (math.sin(self.glow_phase) + 1) / 2
        border_width = 2 + int(glow_strength * 2)
        border_color = self._blend(self.color, self.glow_color, glow_strength)
        self.button.configure(border_color=border_color, border_width=border_width)
        self.after(60, self.animate_glow)

    @staticmethod
    def _blend(c1, c2, f):
        try:
            r1, g1, b1 = int(c1[1:3],16), int(c1[3:5],16), int(c1[5:7],16)
            r2, g2, b2 = int(c2[1:3],16), int(c2[3:5],16), int(c2[5:7],16)
            r = int(r1 + (r2 - r1) * f)
            g = int(g1 + (g2 - g1) * f)
            b = int(b1 + (b2 - b1) * f)
            return f"#{r:02x}{g:02x}{b:02x}"
        except: return c1


# ================= MAIN APP =================
class ControlApp(ctk.CTk):
    def __init__(self):
        super().__init__()

        self.title("REARM Controller")
        self.geometry("900x700")
        self.configure(fg_color=BG_COLOR)
        self.resizable(False, False)

        self.cv_script_name = "hand_track.py" 
        self.arduino_connected = False
        self.monitoring = True
        self.cv_running = False 
        
        # Main Container
        self.container = ctk.CTkFrame(self, fg_color="transparent")
        self.container.pack(expand=True, fill="both", padx=20, pady=20)
        
        # --- BOTTOM BAR ---
        self.bottom_bar = ctk.CTkFrame(self, fg_color="transparent")
        self.bottom_bar.pack(side="bottom", fill="x", pady=15, padx=20)
        
        self.status = ctk.CTkLabel(
            self.bottom_bar, 
            text="Initializing System...", 
            font=("Segoe UI", 12), 
            text_color=MUTED_TEXT,
            anchor="w"
        )
        self.status.pack(side="left", padx=10, fill="x", expand=True)

        self.reconnect_btn = ctk.CTkButton(
            self.bottom_bar,
            text="↻ RECONNECT",
            width=100,
            height=28,
            fg_color=CARD_BG,
            hover_color="#1E293B",
            text_color=AMBER,
            font=("Segoe UI", 11, "bold"),
            command=self.manual_reconnect
        )

        self.show_main_menu()
        self.manual_reconnect()
        self.start_monitor_thread()

    # ================= UI STATE MANAGEMENT =================
    def _update_ui_state(self):
        should_enable = self.arduino_connected and not self.cv_running

        # 1. Main Menu Buttons
        if hasattr(self, 'buttons') and self.buttons:
            try:
                for btn in self.buttons.values(): btn.set_enabled(should_enable)
            except: pass

        # 2. Manual View Controls (Send & Presets)
        if hasattr(self, 'manual_send_btn') and self.manual_send_btn.winfo_exists():
            state = "normal" if should_enable else "disabled"
            color = CYAN if should_enable else MUTED_TEXT
            try:
                self.manual_send_btn.configure(state=state, fg_color=color)
            except: pass
            
        # 3. Status Bar
        if self.cv_running: pass
        elif self.arduino_connected:
            self.status.configure(text="✅ System Ready • Arduino Connected", text_color=GREEN_GLOW)
            self.reconnect_btn.pack_forget()
        else:
            self.status.configure(text="⚠ Arduino Offline • Connect to Operate", text_color=RED_LIGHT)
            self.reconnect_btn.pack(side="right", padx=10)

    # ================= CONNECTION MONITORING =================
    def start_monitor_thread(self):
        thread = threading.Thread(target=self._monitor_loop)
        thread.daemon = True
        thread.start()

    def _monitor_loop(self):
        print("DEBUG: Monitor Started")
        while self.monitoring:
            time.sleep(1.0)
            currently_connected = False
            try:
                if hasattr(ac, 'is_connected'): currently_connected = ac.is_connected()
                else:
                    if hasattr(ac, 'ser') and ac.ser is not None: currently_connected = ac.ser.is_open
            except: currently_connected = False

            #Automatic Reconnection
            # if not currently_connected:
            #     try: currently_connected = ac.connect()
            #     except: pass

            if currently_connected != self.arduino_connected:
                self.arduino_connected = currently_connected
                self.after(0, self._update_ui_state)

    def manual_reconnect(self):
        self.status.configure(text="⟳ Connecting to Arduino...", text_color=AMBER)
        self.reconnect_btn.pack_forget()
        threading.Thread(target=self._connect_logic, daemon=True).start()

    def _connect_logic(self):
        try: success = ac.connect()
        except: success = False
        self.arduino_connected = success
        self.after(0, self._update_ui_state)

    # ================= VIEW MANAGEMENT =================
    def clear_container(self):
        for widget in self.container.winfo_children():
            widget.destroy()
        self.buttons = {} 

    def show_main_menu(self):
        self.clear_container()
        
        ctk.CTkLabel(self.container, text="⚡ REARM CONTROLLER", font=("Segoe UI", 28, "bold"), text_color=TEXT_COLOR).pack(pady=(20, 5))
        ctk.CTkLabel(self.container, text="Advanced Robotic Arm Interface", font=("Segoe UI", 12), text_color=MUTED_TEXT).pack(pady=(0, 30))

        btn_frame = ctk.CTkFrame(self.container, fg_color="transparent")
        btn_frame.pack(expand=True)

        self.buttons = {}
        self.buttons["cv"] = GlowingButton(btn_frame, "COMPUTER VISION", "👁", PURPLE, PURPLE_GLOW, lambda: self.run_cv_sequence())
        self.buttons["cv"].pack(pady=12)
        self.buttons["manual"] = GlowingButton(btn_frame, "MANUAL CONTROL", "🎮", CYAN, CYAN_GLOW, lambda: self.show_manual_view())
        self.buttons["manual"].pack(pady=12)
        self.buttons["ai"] = GlowingButton(btn_frame, "AI MODE", "🧠", GREEN, GREEN_GLOW, lambda: self.run_ai_sequence())
        self.buttons["ai"].pack(pady=12)

        self.exit_btn = ctk.CTkButton(self.container, text="⏻ EXIT", width=200, height=44, fg_color="transparent", border_color=RED, border_width=2, hover_color="#2D1215", text_color=RED_LIGHT, font=("Segoe UI", 12, "bold"), command=self.destroy)
        self.exit_btn.pack(pady=20)
        self._update_ui_state()

    def show_manual_view(self):
        self.clear_container()
        
        # Header
        header = ctk.CTkFrame(self.container, fg_color="transparent")
        header.pack(fill="x", pady=(0, 20))
        ctk.CTkButton(header, text="← Back", width=80, fg_color="transparent", text_color=CYAN, hover_color=CARD_BG, command=self.show_main_menu).pack(side="left")
        ctk.CTkLabel(header, text="MANUAL CONFIGURATION", font=("Segoe UI", 20, "bold"), text_color=TEXT_COLOR).pack(side="left", padx=120)

        # --- PRESETS SECTION ---
        preset_frame = ctk.CTkFrame(self.container, fg_color="transparent")
        preset_frame.pack(fill="x", padx=40, pady=(0, 15))
        
        ctk.CTkLabel(preset_frame, text="QUICK PRESETS:", font=("Segoe UI", 12, "bold"), text_color=MUTED_TEXT).pack(side="left", padx=(0,10))

        # Preset Dictionary: Name -> [Thumb, Index, Middle, Ring, Pinky]
        presets = {
            "✊ Fist": [0, 0, 0, 0, 0],
            "✋ Open": [2, 2, 2, 2, 2],
            "✌ Peace": [0, 2, 2, 0, 0],
            "👌 Okay": [2, 0, 2, 2, 2],
            "👉 Point": [0, 2, 0, 0, 0]
        }

        for name, values in presets.items():
            ctk.CTkButton(
                preset_frame, text=name, width=70, height=28,
                fg_color=CARD_BG, border_color=CYAN, border_width=1,
                text_color=CYAN, hover_color=CYAN, # Hover turns bg cyan
                font=("Segoe UI", 11),
                # When clicked, update variables
                command=lambda v=values: self.apply_preset(v)
            ).pack(side="left", padx=5)

        # --- SLIDERS SECTION ---
        self.finger_vars = []
        fingers = ["Thumb", "Index", "Middle", "Ring", "Pinky"]
        controls_frame = ctk.CTkFrame(self.container, fg_color=CARD_BG, corner_radius=15)
        controls_frame.pack(pady=10, padx=40, fill="x")

        for i, finger in enumerate(fingers):
            row = ctk.CTkFrame(controls_frame, fg_color="transparent")
            row.pack(fill="x", pady=12, padx=20)
            ctk.CTkLabel(row, text=finger.upper(), font=("Segoe UI", 14, "bold"), text_color=CYAN_GLOW, width=80, anchor="w").pack(side="left")
            seg_var = ctk.StringVar(value="Closed") 
            self.finger_vars.append(seg_var)
            ctk.CTkSegmentedButton(row, values=["Open", "Half", "Closed"], variable=seg_var, width=300, selected_color=CYAN, selected_hover_color=CYAN_GLOW, unselected_color=BG_COLOR).pack(side="right")

        self.manual_send_btn = ctk.CTkButton(self.container, text="SEND COMMAND 📡", width=200, height=50, corner_radius=10, fg_color=CYAN, hover_color=CYAN_GLOW, font=("Segoe UI", 15, "bold"), text_color=BG_COLOR, command=self.send_manual_command)
        self.manual_send_btn.pack(pady=30)
        self._update_ui_state()

    def apply_preset(self, values):
        """Updates the SegmentedButtons based on preset list"""
        # Map integer to string
        mapping = {0: "Closed", 1: "Half", 2: "Open"}
        
        for i, val in enumerate(values):
            if i < len(self.finger_vars):
                self.finger_vars[i].set(mapping[val])
        
        # Optional: Auto-Send command when preset is clicked?
        self.send_manual_command() 

    def send_manual_command(self):
        mapping = {"Open": 2, "Half": 1, "Closed": 0}
        result = [mapping[var.get()] for var in self.finger_vars]
        #print(f"Sending: {result}")
        if self.arduino_connected:
            try:
                ac.send_to_arduino(result)
                self.status.configure(text=f"📡 Command Sent: {result}", text_color=CYAN_GLOW)
                self.after(2000, self._update_ui_state)
            except: self.status.configure(text="⚠ Send Failed", text_color=RED)
        else: self._update_ui_state()

    def activate_status(self, mode_name):
        self.status.configure(text=f"● {mode_name} Active", text_color=MUTED_TEXT)

    # ================= CV LOGIC =================
    def run_cv_sequence(self):
        self.cv_running = True 
        self._update_ui_state() 
        self.exit_btn.configure(state="disabled")
        self.buttons["cv"].set_active(True)
        threading.Thread(target=self._cv_thread_logic, daemon=True).start()

    def _cv_thread_logic(self):
        self._update_status_safe("⏳ Initializing REARM...", AMBER)
        time.sleep(6)
        self._update_status_safe("👁 CV Module Running...", PURPLE_GLOW)
        try:
            script_path = os.path.join(os.path.dirname(os.path.abspath(__file__)), self.cv_script_name)
            subprocess.run([sys.executable, script_path], check=True)
            success = True
        except: success = False
        self.after(0, lambda: self._on_cv_finished(success))

    # ================= AI MODE LOGIC =================
    def run_ai_sequence(self):
        self.cv_running = True  # Reuse cv_running flag to disable other buttons
        self._update_ui_state() 
        self.exit_btn.configure(state="disabled")
        self.buttons["ai"].set_active(True)
        threading.Thread(target=self._ai_thread_logic, daemon=True).start()

    def _ai_thread_logic(self):
        self._update_status_safe("⏳ Initializing AI Mode...", AMBER)
        time.sleep(2)
        self._update_status_safe("🧠 AI Mode Running - Gesture Recognition Active", GREEN_GLOW)
        try:
            script_path = os.path.join(os.path.dirname(os.path.abspath(__file__)), "ai_mode.py")
            subprocess.run([sys.executable, script_path], check=True)
            success = True
        except: success = False
        self.after(0, lambda: self._on_ai_finished(success))

    def _on_ai_finished(self, success):
        self.cv_running = False 
        self.exit_btn.configure(state="normal")
        if hasattr(self, 'buttons') and "ai" in self.buttons: 
            self.buttons["ai"].set_active(False)
        self._update_ui_state()
        if not success: 
            self.status.configure(text="⚠ AI Mode Failed", text_color=RED)

    def _update_status_safe(self, text, color):
        self.after(0, lambda: self.status.configure(text=text, text_color=color))

    def _on_cv_finished(self, success):
        self.cv_running = False 
        self.exit_btn.configure(state="normal")
        if hasattr(self, 'buttons') and "cv" in self.buttons: self.buttons["cv"].set_active(False)
        self._update_ui_state()
        if not success: self.status.configure(text="⚠ CV Module Failed", text_color=RED)

    def destroy(self):
        self.monitoring = False
        super().destroy()

if __name__ == "__main__":
    ControlApp().mainloop()