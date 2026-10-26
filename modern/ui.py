# SPDX-License-Identifier: GPL-3.0-or-later
"""Gamepad controls reference and movement settings."""
import ctypes as C
import math
from pathlib import Path
import subprocess
import queue
import threading
import time
import tkinter as tk
from tkinter import filedialog, messagebox, ttk

from . import core
from .install import import_game, installation_status, InstallCancelled
from .home import GamePage
from .session import detect_session, SessionMode
from .navigation import Navigation
from .diagram import ACCENT, BG, CARD, LINE, MUTED, TEAL, TEXT, controller_scene


class TwinStickApp:
    def __init__(self, root):
        self.root = root
        self.preview_stick = tk.StringVar(value="left")
        self.process = None
        self.install_state = installation_status()
        self._install_thread = None
        self.install_phase = "idle"
        self.install_result = None
        self._install_cancel = threading.Event()
        self._install_events = queue.Queue()
        self._closing = False
        self.saved = core.load_settings()
        self.enabled = tk.BooleanVar(value=self.saved["enabled"])
        self.fullscreen = tk.BooleanVar(value=self.saved["fullscreen"])
        self.skip_intro = tk.BooleanVar(value=self.saved["skip_intro"])
        tuning_keys = ("deadzone", "aim_deadzone", "hysteresis")
        self.values = {key: tk.StringVar(value=str(self.saved[key])) for key in tuning_keys}
        self.scales = {key: tk.DoubleVar(value=self.saved[key]) for key in self.values}
        self.badge = tk.StringVar(value="Saved")
        self.status = tk.StringVar(value="Ready to play. Settings apply on the next launch.")
        self.stick_status = tk.StringVar(value="Centered · keep facing")
        self.stick_hint = tk.StringVar(value="Drag the dot to try the zones.")
        self.layout_hint = tk.StringVar()
        self.editable = []
        self.pad = self.controller = None
        self.navigation = Navigation()
        self._reconnect_at = 0
        self._dragging = False
        self._axes = (0.0, 0.0)
        self._active = self._walking = False
        self._heading = (0.0, -1.0)
        self._suspend_refresh = False
        self._valid_preview = dict(self.saved)

        self._style()
        root.title("Crusader · Twin Stick")
        root.geometry("1080x720")
        root.minsize(940, 680)
        root.configure(background=BG)
        root.protocol("WM_DELETE_WINDOW", self.close)
        root.bind("<Control-s>", lambda _event: self.save())

        self._page_index = 0
        self.page_title = tk.StringVar(value="Crusader Twin Stick")
        body = ttk.Frame(root, padding=(26, 18))
        body.pack(fill="both", expand=True)
        body.columnconfigure(0, weight=1)
        body.rowconfigure(1, weight=1)
        header = ttk.Frame(body)
        header.grid(row=0, column=0, sticky="ew", pady=(0, 12))
        header.columnconfigure(1, weight=1)
        self.back_button = ttk.Button(header, text="Back", command=lambda: self.notebook.select(0))
        self.back_button.grid(row=0, column=0, padx=(0, 14))
        self.back_button.grid_remove()
        ttk.Label(header, textvariable=self.page_title, style="Heading.TLabel").grid(row=0, column=1, sticky="w")
        ttk.Label(header, textvariable=self.badge, style="Badge.TLabel", padding=(12, 6)).grid(row=0, column=2)
        self.about_button = ttk.Button(header, text="About…", command=self.about)
        self.about_button.grid(row=0, column=3, padx=(10, 0))
        self.about_button.grid_remove()

        notebook = self.notebook = ttk.Notebook(body, style="Hub.TNotebook", takefocus=False)
        notebook.grid(row=1, column=0, sticky="nsew")
        self.home = GamePage(notebook, self)
        controls = ttk.Frame(notebook, padding=(0, 10, 0, 0))
        self.controls_tab = controls
        movement = ttk.Frame(notebook, padding=(0, 10, 0, 0))
        notebook.add(self.home, text="Game")
        notebook.add(controls, text="Controller layout")
        notebook.add(movement, text="Settings")
        self._controls_page(controls)
        self._movement_page(movement)

        self.session_mode = detect_session()
        self.notice = ttk.Frame(body, style="Card.TFrame", padding=(14, 9))
        if self.session_mode is not SessionMode.GAMING:
            self.notice.grid(row=2, column=0, sticky="ew", pady=(12, 10))
        ttk.Label(self.notice, text="Desktop Mode", style="Notice.TLabel").pack(side="left", padx=(0, 14))
        ttk.Label(self.notice, text="Hold Menu to select Gamepad controls.", style="Card.TLabel").pack(side="left")

        footer = ttk.Frame(body)
        footer.grid(row=3, column=0, sticky="ew", pady=(5, 0))
        footer.columnconfigure(0, weight=1)
        self.status_label = ttk.Label(footer, textvariable=self.status, style="Muted.TLabel", wraplength=700)
        self.status_label.grid(row=0, column=0, sticky="ew", padx=(0, 14))
        self.status_label.bind("<Configure>", lambda event: self.status_label.configure(wraplength=max(160, event.width)))
        actions = ttk.Frame(footer)
        actions.grid(row=0, column=1)
        self.save_button = ttk.Button(actions, text="Save changes", command=self.save)
        self.save_button.pack(side="left", padx=(0, 10))
        self.play_button = ttk.Button(actions, text="Play", command=self.start, style="Primary.TButton")
        ttk.Label(footer, text="D-pad navigate · A select · B back · LB / RB pages", style="Muted.TLabel",
                  font=("Noto Sans", 9)).grid(row=1, column=0, columnspan=2, sticky="w", pady=(6, 0))
        notebook.bind("<<NotebookTabChanged>>", self._tab_changed)

        for variable in (*self.values.values(), self.enabled, self.fullscreen, self.skip_intro):
            variable.trace_add("write", self._refresh)
        self._refresh_layout()
        self._refresh()
        self._open_pad()
        self.home.refresh()
        root.after(150, self.home.focus_primary)
        root.after(100, self._poll_stick)

    def _style(self):
        style = ttk.Style(self.root)
        style.theme_use("clam")
        style.configure(".", background=BG, foreground=TEXT, font=("Noto Sans", 10, "normal"))
        style.configure("TFrame", background=BG)
        style.configure("Card.TFrame", background=CARD)
        style.configure("TLabel", background=BG, foreground=TEXT)
        style.configure("Muted.TLabel", foreground=MUTED)
        style.configure("Title.TLabel", font=("Noto Sans", 19, "bold"))
        style.configure("Heading.TLabel", font=("Noto Sans", 12, "bold"))
        style.configure("Badge.TLabel", background=CARD, foreground=ACCENT, font=("Noto Sans", 10, "bold"))
        style.configure("Card.TLabel", background=CARD, foreground=TEXT)
        style.configure("HeroTitle.TLabel", background=CARD, foreground=TEXT, font=("Noto Sans", 42, "bold"))
        style.configure("ImportTitle.TLabel", background=CARD, foreground=TEXT, font=("Noto Sans", 30, "bold"))
        style.configure("ImportSubtitle.TLabel", background=CARD, foreground=TEXT, font=("Noto Sans", 18))
        style.configure("HeroSubtitle.TLabel", background=CARD, foreground=TEXT, font=("Noto Sans", 26))
        style.configure("Ready.TLabel", background=CARD, foreground=ACCENT, font=("Noto Sans", 11, "bold"))
        style.configure("CardMuted.TLabel", background=CARD, foreground=MUTED, font=("Noto Sans", 11))
        style.configure("Hub.TNotebook", background=BG, borderwidth=0, tabmargins=0)
        style.layout("Hub.TNotebook.Tab", [])
        style.configure("Notice.TLabel", background=CARD, foreground=ACCENT, font=("Noto Sans", 9, "bold"))
        style.configure("Error.TLabel", foreground="#ffb2a5")
        style.configure("TNotebook", background=BG, borderwidth=0, tabmargins=0,
                        bordercolor=BG, lightcolor=BG, darkcolor=BG)
        style.configure("TNotebook.Tab", background=CARD, foreground=MUTED, padding=(14, 10),
                        font=("Noto Sans", 11, "bold"), borderwidth=0,
                        bordercolor=BG, lightcolor=BG, darkcolor=BG)
        style.map("TNotebook.Tab", background=[("selected", "#592c24")], foreground=[("selected", TEXT)],
                  lightcolor=[("selected", BG), ("!selected", BG)], padding=[("selected", (14, 10))])
        style.configure("TButton", background="#3d2923", foreground=TEXT, padding=(14, 13),
                        borderwidth=0, font=("Noto Sans", 10, "bold"), focuscolor=ACCENT)
        style.map("TButton", background=[("active", "#59382c"), ("disabled", CARD)],
                  foreground=[("disabled", "#a38c7e")])
        style.configure("Primary.TButton", background=ACCENT, foreground="#1a100c", padding=(23, 11),
                        focuscolor="#1a100c", focusthickness=2)
        style.map("Primary.TButton", background=[("active", "#ffa764"), ("disabled", "#603c29")],
                  foreground=[("disabled", MUTED)])
        style.configure("Hub.TButton", background="#3d2923", foreground=TEXT, padding=(18, 23),
                        font=("Noto Sans", 14, "bold"), borderwidth=2, focuscolor=TEXT, focusthickness=2,
                        bordercolor=LINE, lightcolor=LINE, darkcolor=LINE)
        style.configure("HubPrimary.TButton", background="#a73928", foreground=TEXT, padding=(18, 23),
                        font=("Noto Sans", 16, "bold"), borderwidth=2, focuscolor=TEXT, focusthickness=2,
                        bordercolor="#a73928", lightcolor="#a73928", darkcolor="#a73928")
        style.map("Hub.TButton", bordercolor=[("focus", ACCENT), ("!focus", LINE)],
                  lightcolor=[("focus", ACCENT), ("!focus", LINE)], darkcolor=[("focus", ACCENT), ("!focus", LINE)])
        style.map("HubPrimary.TButton", background=[("disabled", CARD), ("active", "#bd4932"), ("!disabled", "#a73928")],
                  foreground=[("disabled", MUTED)], bordercolor=[("focus", ACCENT), ("!focus", "#a73928")],
                  lightcolor=[("focus", ACCENT), ("!focus", "#a73928")],
                  darkcolor=[("focus", ACCENT), ("!focus", "#a73928")])
        style.configure("Quiet.TButton", background=BG, foreground=MUTED, padding=(10, 12), borderwidth=0)
        style.configure("TCheckbutton", background=BG, foreground=TEXT, padding=(6, 12), font=("Noto Sans", 11),
                        indicatorbackground=CARD, indicatorforeground=ACCENT,
                        focuscolor=ACCENT, focusthickness=2, focussolid=False)
        style.map("TCheckbutton", background=[("active", BG)], foreground=[("disabled", MUTED)])
        style.configure("TSpinbox", fieldbackground=CARD, foreground=TEXT, background="#3d2923",
                        arrowcolor=TEXT, padding=(6, 12), bordercolor=LINE, insertcolor=TEXT)
        style.map("TSpinbox", bordercolor=[("focus", ACCENT), ("!focus", LINE)],
                  lightcolor=[("focus", ACCENT), ("!focus", LINE)], darkcolor=[("focus", ACCENT), ("!focus", LINE)])
        style.configure("Horizontal.TScale", background=ACCENT, troughcolor="#432b24", bordercolor=BG,
                        lightcolor=BG, darkcolor=BG, arrowsize=44, sliderlength=38,
                        gripcount=0, borderwidth=2)
        style.map("Horizontal.TScale", background=[("disabled", "#8f6b58")],
                  bordercolor=[("focus", ACCENT), ("!disabled", BG)],
                  lightcolor=[("focus", ACCENT), ("!disabled", BG)], darkcolor=[("focus", ACCENT), ("!disabled", BG)])

    def _controls_page(self, parent):
        parent.columnconfigure(0, weight=1)
        parent.rowconfigure(1, weight=1)
        heading = ttk.Frame(parent)
        heading.grid(row=0, column=0, sticky="ew", padx=4, pady=(0, 2))
        heading.columnconfigure(0, weight=1)
        ttk.Label(heading, textvariable=self.layout_hint, style="Muted.TLabel").grid(row=0, column=0, sticky="w")
        self.remap_button = ttk.Button(heading, text="Remap buttons…", command=lambda: self.start(True))
        self.remap_button.grid(row=0, column=1, padx=(10, 0))
        ttk.Button(heading, text="Export SVG…", command=self.export_diagram).grid(row=0, column=2, padx=(10, 0))
        self.diagram = tk.Canvas(parent, background=BG, highlightthickness=0, width=1000, height=390)
        self.diagram.grid(row=1, column=0, sticky="nsew")
        self.diagram.bind("<Configure>", lambda _event: self.scene.draw(self.diagram))

    def _movement_page(self, parent):
        parent.columnconfigure(0, weight=5)
        parent.columnconfigure(1, weight=6)
        parent.rowconfigure(0, weight=1)
        preview = ttk.Frame(parent, padding=(4, 0, 20, 0))
        preview.grid(row=0, column=0, sticky="nsew")
        preview.columnconfigure(0, weight=1)
        preview.rowconfigure(1, weight=1)
        preview_header = ttk.Frame(preview)
        preview_header.grid(row=0, column=0, sticky="w")
        ttk.Label(preview_header, text="Preview", style="Heading.TLabel").pack(side="left")
        for text, value in (("Move (L)", "left"), ("Aim (R)", "right")):
            ttk.Button(preview_header, text=text, command=lambda name=value: self._select_preview(name)).pack(side="left", padx=(8, 0))
        self.zone = tk.Canvas(preview, background=BG, highlightthickness=0, width=330, height=245)
        self.zone.grid(row=1, column=0, sticky="nsew", pady=(4, 0))
        self.zone.bind("<Configure>", lambda _event: self._draw_zone())
        self.zone.bind("<ButtonPress-1>", self._drag_stick)
        self.zone.bind("<B1-Motion>", self._drag_stick)
        self.zone.bind("<ButtonRelease-1>", self._release_stick)
        ttk.Label(preview, textvariable=self.stick_status, style="Heading.TLabel").grid(row=2, column=0, sticky="w", pady=(0, 6))
        ttk.Label(preview, textvariable=self.stick_hint, style="Muted.TLabel", wraplength=360).grid(row=3, column=0, sticky="w")
        legend = ttk.Frame(preview)
        legend.grid(row=4, column=0, sticky="w", pady=(12, 0))
        legend_rows = ((MUTED, "Aim centered: follow movement"), (TEAL, "Left stick: move after deadzone"),
                       (ACCENT, "Right stick: aim independently"))
        for color, text in legend_rows:
            row = ttk.Frame(legend)
            row.pack(anchor="w", pady=2)
            swatch = tk.Canvas(row, width=12, height=12, background=BG, highlightthickness=0)
            swatch.create_oval(2, 2, 10, 10, fill=color, outline=color)
            swatch.pack(side="left", padx=(0, 8))
            ttk.Label(row, text=text, style="Muted.TLabel").pack(side="left")

        settings = ttk.Frame(parent, padding=(20, 0, 4, 0))
        settings.grid(row=0, column=1, sticky="nsew")
        settings.columnconfigure(0, weight=1)
        enabled = self.enable_check = ttk.Checkbutton(settings, text="Enable twin-stick controls", variable=self.enabled)
        enabled.grid(row=0, column=0, sticky="w", pady=(0, 8))
        self.editable.append(enabled)
        rows = (("deadzone", "Move deadzone", "Move immediately beyond this threshold.", 1, 98),
                ("aim_deadzone", "Aim deadzone", "Center the right stick to face movement again.", 1, 98),
                ("hysteresis", "Boundary cushion", "A small buffer prevents jitter at each boundary.", 0, 49))
        for index, (key, title, help_text, low, high) in enumerate(rows):
            row = ttk.Frame(settings)
            row.grid(row=index+1, column=0, sticky="ew", pady=(0, 3))
            row.columnconfigure(0, minsize=158)
            row.columnconfigure(1, weight=1)
            ttk.Label(row, text=title, style="Heading.TLabel").grid(row=0, column=0, sticky="w")
            ttk.Label(row, text=help_text, style="Muted.TLabel", font=("Noto Sans", 9),
                      wraplength=155).grid(row=1, column=0, sticky="w", pady=(2, 3))
            scale = ttk.Scale(row, from_=low, to=high, variable=self.scales[key],
                              command=lambda value, name=key: self.values[name].set(str(round(float(value)))))
            scale.grid(row=0, column=1, rowspan=2, sticky="ew", padx=(12, 10), pady=(3, 3))
            entry = ttk.Spinbox(row, from_=low, to=high, textvariable=self.values[key], width=4, justify="center")
            entry.grid(row=0, column=2, rowspan=2, padx=(0, 4))
            ttk.Label(row, text="%", style="Muted.TLabel").grid(row=0, column=3, rowspan=2)
            self.editable.extend((entry, scale))
        self.release_hint = tk.StringVar()
        ttk.Label(settings, textvariable=self.release_hint, style="Muted.TLabel", wraplength=430).grid(row=4, column=0, sticky="w")
        defaults = ttk.Button(settings, text="Restore movement defaults", command=self.restore_defaults)
        defaults.grid(row=5, column=0, sticky="w", pady=(8, 0))
        self.editable.append(defaults)

    def settings(self):
        try:
            settings = {key: int(variable.get()) for key, variable in self.values.items()}
        except ValueError:
            raise ValueError("Use whole percentages for the stick settings.") from None
        return core.validate({**core.DEFAULTS, **settings, "enabled": self.enabled.get(),
                              "fullscreen": self.fullscreen.get(), "skip_intro": self.skip_intro.get()})

    def _refresh(self, *_args):
        if self._suspend_refresh:
            return
        valid = True
        try:
            settings = self.settings()
            self._valid_preview = dict(settings)
            for key in self.values:
                self.scales[key].set(settings[key])
            cushion = settings["hysteresis"]
            self.release_hint.set(f"Movement stops below {settings['deadzone'] - cushion}%. "
                                  f"Aim releases below {settings['aim_deadzone'] - cushion}%.")
            dirty = settings != self.saved
            self.status.set("Unsaved changes. Save or play to apply them." if dirty else
                            self.install_result if self.install_result else
                            "Ready to play. Settings apply on the next launch." if self.install_state.ready else
                            "Choose your game files to get started.")
            self.status_label.configure(style="Muted.TLabel")
        except ValueError as error:
            dirty, valid = True, False
            self.status.set(str(error))
            self.status_label.configure(style="Error.TLabel")
            self.release_hint.set("Adjust the thresholds to update the preview.")
        running = self.is_installing() or (self.process is not None and self.process.poll() is None)
        if self.is_installing():
            cancelling = self.install_phase == "cancelling"
            self.status.set("Cancelling installation and cleaning temporary files…" if cancelling else
                            "Installing game files. Your saves and controller settings are preserved.")
            badge = "Cancelling" if cancelling else "Installing"
        else:
            badge = "Running" if running else "Unsaved changes" if dirty else {
                "failed": "Import failed", "cancelled": "Cancelled", "complete": "Installed"}.get(self.install_phase, "Saved")
        self.badge.set(badge)
        for widget in self.editable:
            widget.state(["disabled"] if running else ["!disabled"])
        self.save_button.state(["!disabled"] if valid and not running and dirty else ["disabled"])
        ready = self.install_state.ready and self.runtime_available()
        self._settings_valid = valid
        for widget in (self.play_button, self.remap_button):
            widget.state(["!disabled"] if valid and not running and ready else ["disabled"])
        self.play_button.configure(text="Running…" if running else "Save & play" if dirty else "Play")
        self._active = self._walking = False
        self._update_stick(*self._axes)
        self.home.refresh()

    def _tab_changed(self, _event=None):
        index = self.notebook.index("current")
        previous = self._page_index
        self._page_index = index
        if index == 0:
            self.page_title.set("Crusader Twin Stick")
            self.back_button.grid_remove()
            self.about_button.grid_remove()
            self.play_button.pack_forget()
            if self.install_state.ready and not self.home._show_import and previous in (1, 2):
                (self.home.controls if previous == 1 else self.home.settings_button).focus_set()
            else:
                self.home.focus_primary()
        else:
            self.page_title.set("Controller layout" if index == 1 else "Settings")
            self.back_button.grid()
            self.about_button.grid()
            self.play_button.pack(side="left")
            (self.remap_button if index == 1 else self.enable_check).focus_set()

    def runtime_available(self):
        return core.BINARY.is_file()

    def about(self):
        if getattr(self, "about_window", None) is not None and self.about_window.winfo_exists():
            self.about_window.lift()
            return
        previous_focus = self.root.focus_get()
        dialog = self.about_window = tk.Toplevel(self.root)

        def dismiss():
            if not dialog.winfo_exists():
                return
            dialog.destroy()
            if previous_focus is not None and previous_focus.winfo_exists() and previous_focus.winfo_ismapped():
                previous_focus.focus_set()
            else:
                self.home.focus_primary()

        dialog.protocol("WM_DELETE_WINDOW", dismiss)
        dialog.title("About Crusader Twin Stick")
        dialog.transient(self.root)
        dialog.resizable(False, False)
        dialog.configure(background=BG)
        body = ttk.Frame(dialog, padding=24)
        body.pack(fill="both", expand=True)
        ttk.Label(body, text="Crusader Twin Stick", font=("Noto Sans", 18, "bold")).pack(anchor="w")
        ttk.Label(body, text="An unofficial controller launcher for Crusader: No Remorse.",
                  style="Muted.TLabel", wraplength=440, justify="left").pack(anchor="w", pady=(6, 18))
        for title, text in (
            ("ScummVM engine", "Powered by a locally modified ScummVM engine."),
            ("GNU GPL version 3 or later", "Applies to the launcher and engine changes. License texts, credits and source information are included with the application."),
            ("Game resources", "Crusader game files and artwork belong to their original rights holders and are supplied by you."),
        ):
            ttk.Label(body, text=title, style="Heading.TLabel").pack(anchor="w", pady=(0, 5))
            ttk.Label(body, text=text, style="Muted.TLabel", wraplength=440, justify="left").pack(
                anchor="w", pady=(0, 16))
        close = ttk.Button(body, text="Close", command=dismiss, style="Primary.TButton")
        close.pack(anchor="e", pady=(4, 0))
        dialog.bind("<Escape>", lambda _event: dismiss())
        dialog.bind("<Return>", lambda _event: dismiss())
        dialog.update_idletasks()
        x = self.root.winfo_rootx() + (self.root.winfo_width() - dialog.winfo_reqwidth()) // 2
        y = self.root.winfo_rooty() + (self.root.winfo_height() - dialog.winfo_reqheight()) // 2
        dialog.geometry(f"+{max(0, x)}+{max(0, y)}")
        close.focus_set()

    def is_installing(self):
        return self._install_thread is not None

    def begin_import(self, source):
        if not source or self.is_installing() or (self.process and self.process.poll() is None):
            return
        if not self.save():
            return
        self._install_cancel.clear()
        self.install_phase = "installing"
        self.install_result = None
        self.home.progress["value"] = 0

        def work():
            try:
                state = import_game(source, lambda percent, message: self._install_events.put(("progress", percent, message)),
                                    self._install_cancel)
                self._install_events.put(("complete", state))
            except Exception as error:
                self._install_events.put(("error", error))

        self._install_thread = threading.Thread(target=work, daemon=True)
        self._install_thread.start()
        self._refresh()
        self.home.focus_primary()
        self.root.after(100, self._poll_install)

    def cancel_import(self):
        self.install_phase = "cancelling"
        self._install_cancel.set()
        self.home.message.set("Cancelling and cleaning temporary files…")
        self._refresh()

    def _poll_install(self):
        finished = False
        while True:
            try:
                event = self._install_events.get_nowait()
            except queue.Empty:
                break
            if event[0] == "progress":
                self.home.progress["value"] = event[1]
                self.home.message.set(event[2])
            elif event[0] == "complete":
                self.install_state = event[1]
                self.home._show_import = False
                self.home.message.set("Installed. Your source files, saves and controller settings are preserved.")
                self.install_phase = "complete"
                self.install_result = "Installation complete. Ready to play."
                finished = True
            elif event[0] == "error":
                self.install_state = installation_status()
                self.home.message.set(str(event[1]))
                cancelled = isinstance(event[1], InstallCancelled)
                self.install_phase = "cancelled" if cancelled else "failed"
                self.install_result = "Installation cancelled. Your previous files are intact." if cancelled else \
                                      "Installation failed. Choose your game files to try again."
                if not self.home.message.get():
                    self.home.message.set(self.install_result)
                finished = True
        if self._install_thread is not None and self._install_thread.is_alive():
            self.root.after(100, self._poll_install)
            return
        self._install_thread = None
        self._refresh()
        if self.notebook.select() == str(self.home):
            self.home.focus_primary()
        if self._closing:
            self.close()

    def _refresh_layout(self):
        self.scene = controller_scene(core.controller_labels())
        enabled = core.load_settings()["enabled"]
        mode = "Twin-stick" if enabled else "Classic"
        self.layout_hint.set(f"Gamepad · {mode} layout · labels follow saved button mappings")
        self.scene.draw(self.diagram)

    def restore_defaults(self):
        self._suspend_refresh = True
        for key, variable in self.values.items():
            variable.set(str(core.DEFAULTS[key]))
        self.enabled.set(True)
        self._suspend_refresh = False
        self._refresh()

    def save(self):
        if self.is_installing() or (self.process and self.process.poll() is None):
            return False
        try:
            settings = self.settings()
            core.save_settings(settings)
            self.saved = dict(settings)
            self._refresh_layout()
            self._refresh()
            self.status.set("Saved. Your custom button mappings are preserved.")
            return True
        except (ValueError, OSError) as error:
            self.status.set(str(error))
            self.status_label.configure(style="Error.TLabel")
            return False

    def start(self, launcher=False):
        self.install_state = installation_status()
        if not self.install_state.ready or not self.runtime_available():
            self.notebook.select(self.home)
            self.home.refresh()
            return
        if not self.save():
            return
        self.install_phase = "idle"
        self.install_result = None
        self.home.message.set(self.home.default_message)
        self.status.set("Starting the controller remapping screen…" if launcher else "Starting Crusader…")
        self.root.update_idletasks()
        try:
            self.process = core.launch(launcher)
        except (ValueError, OSError, RuntimeError, subprocess.SubprocessError) as error:
            self.status.set(str(error))
            self.status_label.configure(style="Error.TLabel")
            return
        self._refresh()
        self.status.set("Select the game → Game Options → Keymaps. Close ScummVM when done." if launcher else
                        "Game running. Close it to change settings.")
        self.root.iconify()
        self.root.after(500, self._poll_process)

    def _poll_process(self):
        if self.process is None:
            return
        result = self.process.poll()
        if result is None:
            self.root.after(500, self._poll_process)
            return
        self.process = None
        self.root.deiconify()
        self.root.lift()
        try:
            self.saved = core.load_settings()
            self._suspend_refresh = True
            for key, variable in self.values.items():
                variable.set(str(self.saved[key]))
            self.enabled.set(self.saved["enabled"])
            self.fullscreen.set(self.saved["fullscreen"])
            self.skip_intro.set(self.saved["skip_intro"])
            self._suspend_refresh = False
            self._refresh_layout()
            self._refresh()
        except (ValueError, OSError) as error:
            self._suspend_refresh = False
            self.status.set(str(error))
            self.status_label.configure(style="Error.TLabel")
        if result:
            self.status.set(f"The game closed with an error. See {core.LOG}.")
            self.status_label.configure(style="Error.TLabel")

    def export_diagram(self):
        filename = filedialog.asksaveasfilename(parent=self.root, title="Export controller diagram",
                                              initialfile="crusader-controller.svg", defaultextension=".svg",
                                              filetypes=[("SVG vector image", "*.svg")])
        if filename:
            try:
                Path(filename).write_text(self.scene.svg(), encoding="utf-8")
                self.status.set("Controller diagram exported as SVG.")
            except OSError as error:
                messagebox.showerror("Export diagram", str(error), parent=self.root)

    def _zone_geometry(self):
        width, height = self.zone.winfo_width(), self.zone.winfo_height()
        return width / 2, height / 2, max(20, min(width / 2 - 35, height / 2 - 22))

    def _draw_zone(self):
        canvas = self.zone
        canvas.delete("all")
        x, y, radius = self._zone_geometry()
        settings = self._valid_preview
        threshold = settings["aim_deadzone"] if self.preview_stick.get() == "right" else settings["deadzone"]
        zones = ((100, "#3c211b", "#ae6751"), (threshold, "#30211c", "#b18d79"))
        for percent, fill, stroke in zones:
            r = radius * percent / 100
            canvas.create_oval(x-r, y-r, x+r, y+r, fill=fill, outline=stroke, width=1.5)
        exits = (threshold - settings["hysteresis"],)
        for percent in exits:
            r = radius * percent / 100
            canvas.create_oval(x-r, y-r, x+r, y+r, outline="#b09b85", dash=(2, 4))
        canvas.create_line(x-radius, y, x+radius, y, fill="#805447", dash=(2, 5))
        canvas.create_line(x, y-radius, x, y+radius, fill="#805447", dash=(2, 5))
        canvas.create_text(x, y-radius-13, text="SCREEN UP", fill=MUTED, font=("Noto Sans", 8))
        vx, vy = self._axes
        magnitude = math.hypot(vx, vy)
        divisor = max(1, magnitude)
        px, py = x + vx / divisor * radius, y + vy / divisor * radius
        tint = TEAL if self._walking else ACCENT if self._active else MUTED
        if self._active:
            hx, hy = self._heading
            length = radius * min(1, magnitude)
            canvas.create_line(x, y, x+hx*length, y+hy*length, fill=tint, width=3, arrow="last")
        else:
            hx, hy = self._heading
            canvas.create_line(x, y, x+hx*radius*.6, y+hy*radius*.6, fill="#ab8a76", dash=(3, 4), arrow="last")
        canvas.create_oval(px-7, py-7, px+7, py+7, fill=TEXT, outline=tint, width=3)

    def _update_stick(self, x, y):
        self._axes = (x, y)
        settings = self._valid_preview
        strength = math.hypot(x, y) * 100
        cushion = settings["hysteresis"]
        aiming = self.preview_stick.get() == "right"
        threshold = settings["aim_deadzone"] if aiming else settings["deadzone"]
        self._active = settings["enabled"] and strength >= threshold - (cushion if self._active else 0)
        self._walking = self._active and not aiming
        if self._active:
            direction = math.atan2(y, x)
            self._heading = math.cos(direction), math.sin(direction)
        mode = ("Aim" if self._active else "Centered · follow movement") if aiming else \
               ("Move" if self._active else "Centered · stopped")
        self.stick_status.set(f"{mode} · {min(100, round(strength))}%" if strength >= 1 else mode)
        if not settings["enabled"]:
            self.stick_status.set("Twin-stick controls are off")
        self._draw_zone()

    def _select_preview(self, stick):
        self.preview_stick.set(stick)
        self._active = self._walking = False
        self._update_stick(0, 0)

    def _drag_stick(self, event):
        self._dragging = True
        x, y, radius = self._zone_geometry()
        vx, vy = (event.x-x) / radius, (event.y-y) / radius
        divisor = max(1, math.hypot(vx, vy))
        self._update_stick(vx / divisor, vy / divisor)

    def _release_stick(self, _event):
        self._dragging = False
        self._update_stick(0, 0)

    def _open_pad(self):
        try:
            from .gamepad import Gamepad
            self.pad = Gamepad()
            signatures = {
                "SDL_GameControllerOpen": (C.c_void_p, [C.c_int]),
                "SDL_GameControllerClose": (None, [C.c_void_p]),
                "SDL_GameControllerGetAxis": (C.c_int16, [C.c_void_p, C.c_int]),
                "SDL_GameControllerGetAttached": (C.c_int, [C.c_void_p]),
                "SDL_GameControllerGetButton": (C.c_uint8, [C.c_void_p, C.c_int]),
            }
            for name, (result, arguments) in signatures.items():
                function = getattr(self.pad.sdl, name)
                function.restype, function.argtypes = result, arguments
            self._connect_pad()
        except (OSError, RuntimeError, AttributeError):
            self.stick_hint.set("Drag the dot to try the zones. Live controller preview is unavailable.")
            if self.pad:
                self.pad.close()
                self.pad = None

    def _connect_pad(self):
        self.navigation = Navigation()
        self.pad.refresh()
        self.controller = self.pad.sdl.SDL_GameControllerOpen(self.pad.index) if self.pad.index is not None else None
        if self.controller:
            self.stick_hint.set("Move either stick, or drag the dot to preview.")
        else:
            self.stick_hint.set("Connect a controller for live input, or drag the dot.")

    def _poll_stick(self):
        if self.pad:
            self.pad.sdl.SDL_PumpEvents()
            self.pad.sdl.SDL_JoystickUpdate()
            if self.controller and not self.pad.sdl.SDL_GameControllerGetAttached(self.controller):
                self.pad.sdl.SDL_GameControllerClose(self.controller)
                self.controller = None
                self._update_stick(0, 0)
            if not self.controller and time.monotonic() >= self._reconnect_at:
                self._connect_pad()
                self._reconnect_at = time.monotonic() + 1
            if self.controller and not self._dragging:
                numbers = (2, 3) if self.preview_stick.get() == "right" else (0, 1)
                axes = tuple(self.pad.sdl.SDL_GameControllerGetAxis(self.controller, number) / 32768 for number in numbers)
                if axes != self._axes:
                    self._update_stick(*axes)
            buttons = {i for i in (*Navigation.BUTTONS, *Navigation.DIRECTIONS)
                       if self.controller and self.pad.sdl.SDL_GameControllerGetButton(self.controller, i)}
            axes = tuple(self.pad.sdl.SDL_GameControllerGetAxis(self.controller, i) / 32768 for i in (0, 1)) if self.controller else (0, 0)
            try:
                focused = self.root.focus_displayof()
                window = focused.winfo_toplevel() if focused else None
                context = (str(window), self.notebook.select()) if window and not self.process and not self.root.grab_current() else None
            except (KeyError, tk.TclError):
                context = None
            # The movement page reserves both sticks for its live preview.
            if self.notebook.index("current") == 2:
                axes = (0, 0)
            for action in self.navigation.update(buttons, axes, context, time.monotonic()):
                self._navigate(action)
        self.root.after(33, self._poll_stick)

    def _navigate(self, action):
        focused = self.root.focus_get()
        window = focused.winfo_toplevel() if focused else self.root
        if action == "back":
            if window is not self.root:
                window.event_generate("<Escape>")
            elif self.is_installing():
                self.cancel_import()
            elif self.notebook.select() != str(self.home):
                self.notebook.select(self.home)
            elif self.home._show_import:
                self.home.show_import()
            else:
                self.home.focus_primary()
        elif action in ("previous_page", "next_page") and window is self.root:
            index = (self.notebook.index("current") + (1 if action == "next_page" else -1)) % len(self.notebook.tabs())
            self.notebook.select(index)
        elif action == "confirm" and focused is not None:
            if isinstance(focused, (ttk.Button, ttk.Checkbutton)) and focused.winfo_ismapped() and not focused.instate(["disabled"]):
                focused.invoke()
        elif action in ("left", "right") and isinstance(focused, (ttk.Scale, ttk.Spinbox)):
            keys = ("<Left>", "<Right>") if isinstance(focused, ttk.Scale) else ("<Down>", "<Up>")
            focused.event_generate(keys[action == "right"])
        elif action in ("up", "down", "left", "right"):
            focused = focused or self.home.play
            next_widget = focused.tk_focusPrev() if action in ("up", "left") else focused.tk_focusNext()
            if next_widget:
                next_widget.focus_set()

    def close(self):
        if self.is_installing():
            self._closing = True
            self.cancel_import()
            return
        if self.pad:
            if self.controller:
                self.pad.sdl.SDL_GameControllerClose(self.controller)
            self.pad.close()
        self.root.destroy()


def gui():
    root = tk.Tk()
    TwinStickApp(root)
    root.mainloop()
