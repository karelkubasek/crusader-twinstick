# SPDX-License-Identifier: GPL-3.0-or-later
"""First-run installation and play page for the existing controller launcher."""
from pathlib import Path
import math
import tkinter as tk
from tkinter import filedialog, ttk

from .diagram import ACCENT, BG, CARD, LINE, MUTED, TEXT
from . import core


class GamePage(ttk.Frame):
    def __init__(self, parent, app):
        super().__init__(parent, padding=(0, 4, 0, 0))
        self.app = app
        self.source = tk.StringVar()
        self.heading = tk.StringVar()
        self.description = tk.StringVar()
        self.default_message = "Your original files stay untouched. Saves and settings are kept separately."
        self.message = tk.StringVar(value=self.default_message)
        self._art_stamp = None
        self._portrait = self._scaled_portrait = self._portrait_factor = None
        self._show_import = False
        self.columnconfigure(0, weight=1)
        self.rowconfigure(0, weight=1, minsize=180)

        hero = ttk.Frame(self, style="Card.TFrame")
        hero.grid(row=0, column=0, sticky="nsew")
        hero.columnconfigure(1, weight=1)
        hero.rowconfigure(0, weight=1)
        self.art = tk.Canvas(hero, background="#000000", highlightthickness=0, width=250, height=210)
        self.art.grid(row=0, column=0, sticky="ns")
        self.art.bind("<Configure>", lambda _event: self._draw_art())
        information = ttk.Frame(hero, style="Card.TFrame", padding=(28, 18, 22, 18))
        information.grid(row=0, column=1, sticky="ew")
        information.columnconfigure(0, weight=1)
        self.title_label = ttk.Label(information, text="Crusader", style="HeroTitle.TLabel")
        self.title_label.grid(row=0, column=0, sticky="w")
        self.subtitle_label = ttk.Label(information, text="No Remorse", style="HeroSubtitle.TLabel")
        self.subtitle_label.grid(row=1, column=0, sticky="w", pady=(0, 18))
        ttk.Label(information, textvariable=self.heading, style="Ready.TLabel").grid(row=2, column=0, sticky="w")
        self.description_label = ttk.Label(information, textvariable=self.description, style="CardMuted.TLabel",
                                           wraplength=540, justify="left")
        self.description_label.grid(row=3, column=0, sticky="ew", pady=(5, 0))
        information.bind("<Configure>", lambda event: self.description_label.configure(wraplength=max(1, event.width-50)))

        self.ready_panel = ttk.Frame(self)
        self.ready_panel.grid(row=1, column=0, sticky="ew", pady=(20, 0))
        for column, weight in enumerate((4, 4, 3)):
            self.ready_panel.columnconfigure(column, weight=weight, uniform="actions")
        self.play = ttk.Button(self.ready_panel, text="Play Crusader", command=app.start, style="HubPrimary.TButton")
        self.play.grid(row=0, column=0, sticky="ew", padx=(0, 10))
        self.controls = ttk.Button(self.ready_panel, text="Controller layout", command=lambda: app.notebook.select(1), style="Hub.TButton")
        self.controls.grid(row=0, column=1, sticky="ew", padx=(0, 10))
        self.settings_button = ttk.Button(self.ready_panel, text="Settings", command=lambda: app.notebook.select(2), style="Hub.TButton")
        self.settings_button.grid(row=0, column=2, sticky="ew")

        self.launch_options = ttk.Frame(self)
        self.launch_options.grid(row=2, column=0, sticky="ew", pady=(12, 0))
        app.fullscreen_check = ttk.Checkbutton(self.launch_options, text="Fullscreen", variable=app.fullscreen)
        app.fullscreen_check.pack(side="left", padx=(0, 26))
        app.skip_intro_check = ttk.Checkbutton(self.launch_options, text="Skip opening movies", variable=app.skip_intro)
        app.skip_intro_check.pack(side="left")
        app.editable.extend((app.fullscreen_check, app.skip_intro_check))

        utility = ttk.Frame(self)
        utility.grid(row=3, column=0, sticky="ew", pady=(5, 0))
        self.change = ttk.Button(utility, text="Choose game files…", command=self.show_import, style="Quiet.TButton")
        self.change.pack(side="left", padx=(0, 12))
        self.about_button = ttk.Button(utility, text="About…", command=app.about, style="Quiet.TButton")
        self.about_button.pack(side="left")

        self.import_panel = ttk.Frame(self)
        self.import_panel.grid(row=1, column=0, rowspan=2, sticky="ew", pady=(14, 0))
        buttons = self.source_buttons = ttk.Frame(self.import_panel)
        buttons.pack(fill="x", pady=(0, 8))
        self.installer = ttk.Button(buttons, text="GOG installer…", command=self.choose_installer)
        self.installer.pack(side="left", padx=(0, 10))
        self.folder = ttk.Button(buttons, text="Game folder…", command=self.choose_folder)
        self.folder.pack(side="left")
        self.source_label = ttk.Label(self.import_panel, textvariable=self.source, style="Muted.TLabel", wraplength=800)
        self.source_label.pack(fill="x", pady=(0, 8))
        install_actions = self.install_actions = ttk.Frame(self.import_panel)
        install_actions.pack(fill="x")
        self.install = ttk.Button(install_actions, text="Install No Remorse", command=lambda: app.begin_import(self.source.get()), style="Primary.TButton")
        self.install.pack(side="left", padx=(0, 12))
        self.back = ttk.Button(install_actions, text="Back to Play", command=self.show_import)
        self.progress = ttk.Progressbar(self.import_panel, maximum=100)
        self.cancel = ttk.Button(self.import_panel, text="Cancel installation", command=app.cancel_import)
        self.message_label = ttk.Label(self, textvariable=self.message, style="Muted.TLabel", wraplength=880, justify="left")
        self.message_label.grid(row=4, column=0, sticky="ew", pady=(8, 0))
        self.bind("<Configure>", self._fit_text)
        self.source.trace_add("write", lambda *_args: self.refresh())

    def _fit_text(self, event):
        width = max(1, event.width)
        for label in (self.source_label, self.message_label):
            if int(label.cget("wraplength")) != width:
                label.configure(wraplength=width)

    def choose_installer(self):
        selected = filedialog.askopenfilename(parent=self.app.root, title="Choose your GOG offline installer",
                                              filetypes=[("GOG installer", "*.exe"), ("All files", "*")])
        if selected:
            self.source.set(selected)

    def choose_folder(self):
        selected = filedialog.askdirectory(parent=self.app.root, title="Choose your No Remorse game folder")
        if selected:
            self.source.set(selected)

    def show_import(self):
        self._show_import = not self._show_import
        self.refresh()
        self.focus_primary()

    def focus_primary(self):
        if self.app.is_installing():
            target = self.cancel
        elif not self.app.install_state.ready or self._show_import:
            target = self.install if self.source.get() else self.installer
        else:
            target = self.play
        target.focus_set()

    def refresh(self):
        state = self.app.install_state
        busy = self.app.is_installing() or (self.app.process is not None and self.app.process.poll() is None)
        runtime = self.app.runtime_available()
        importing = not state.ready or self._show_import or self.app.is_installing()
        phase = self.app.install_phase
        show_message = not (state.ready and not importing and runtime and
                            (self.message.get() == self.default_message or phase == "complete"))
        compact = importing or show_message
        self.title_label.configure(style="ImportTitle.TLabel" if compact else "HeroTitle.TLabel")
        self.subtitle_label.configure(style="ImportSubtitle.TLabel" if compact else "HeroSubtitle.TLabel")
        self.subtitle_label.grid_configure(pady=(0, 10 if compact else 18))
        if self.app.is_installing():
            heading = "Cancelling installation" if phase == "cancelling" else "Installing game files"
        elif importing:
            heading = {"failed": "Installation failed", "cancelled": "Installation cancelled"}.get(
                phase, "Reinstall game files" if state.ready else "Install your copy")
        else:
            heading = "Installation complete" if phase == "complete" else "Ready to play" if runtime else "Runtime missing"
        self.heading.set(heading)
        if state.ready and not importing:
            mode = "Twin-stick controls enabled" if self.app.enabled.get() else "Classic controls"
            self.description.set(f"{state.edition} · {mode}")
            self.ready_panel.grid()
            self.launch_options.grid()
        else:
            self.description.set("Choose a replacement copy. Your saves and controller settings stay here." if state.ready else
                                 "Choose a GOG offline installer or a complete game folder.")
            self.ready_panel.grid_remove()
            self.launch_options.grid_remove()
        if importing:
            self.import_panel.grid()
        else:
            self.import_panel.grid_remove()
        for widget in (self.installer, self.folder, self.change):
            widget.state(["disabled"] if busy else ["!disabled"])
        self.install.state(["!disabled"] if self.source.get() and not busy else ["disabled"])
        self.play.state(["!disabled"] if state.ready and runtime and not busy and getattr(self.app, "_settings_valid", True) else ["disabled"])
        if self.app.is_installing():
            self.source_buttons.pack_forget()
            self.install_actions.pack_forget()
            self.progress.pack(fill="x", pady=(12, 6))
            self.cancel.pack(anchor="w")
        else:
            self.progress.pack_forget()
            self.cancel.pack_forget()
            self.source_buttons.pack(fill="x", before=self.source_label, pady=(0, 8))
            self.install_actions.pack(fill="x", after=self.source_label)
        if state.ready and importing and not busy:
            self.back.pack(side="left")
        else:
            self.back.pack_forget()
        if not runtime and not self.app.is_installing():
            self.message.set("The game runtime is missing from this source checkout. Use a complete release bundle or follow README.md to prepare it.")
        if show_message:
            self.message_label.grid()
        else:
            self.message_label.grid_remove()
        if importing:
            self.change.pack_forget()
        else:
            self.change.pack(side="left", before=self.about_button, padx=(0, 12))
        self._load_artwork(state.artwork)
        self._draw_art()

    def _load_artwork(self, imported):
        candidates = [core.STATE / "artwork/launcher.png"]
        if imported:
            candidates.append(Path(imported))
        stamp = []
        for path in candidates:
            try:
                stat = path.stat()
                stamp.append((path, stat.st_mtime_ns, stat.st_size))
            except OSError:
                continue
        if stamp == self._art_stamp:
            return
        self._art_stamp = stamp
        self._portrait = self._scaled_portrait = self._portrait_factor = None
        for path, _, _ in stamp:
            try:
                self._portrait = tk.PhotoImage(file=str(path))
                break
            except (tk.TclError, OSError):
                continue

    def _draw_art(self):
        canvas = self.art
        canvas.delete("all")
        width, height = canvas.winfo_width(), canvas.winfo_height()
        if self._portrait:
            factor = max(1, math.ceil(self._portrait.width() / max(1, width - 24)),
                         math.ceil(self._portrait.height() / max(1, height - 24)))
            if factor != self._portrait_factor:
                self._portrait_factor = factor
                self._scaled_portrait = self._portrait.subsample(factor)
            canvas.create_image(width / 2, height / 2, image=self._scaled_portrait)
        else:
            canvas.create_text(width / 2, height / 2 - 36, text="CRUSADER", fill=ACCENT, font=("Noto Sans", 23, "bold"))
            canvas.create_text(width / 2, height / 2 + 3, text="NO REMORSE", fill=TEXT, font=("Noto Sans", 14))
            canvas.create_line(width * .2, height / 2 + 35, width * .8, height / 2 + 35, fill=LINE)
            canvas.create_text(width / 2, height - 42, text="Your game. Twin-stick controls.", fill=MUTED, font=("Noto Sans", 9))
