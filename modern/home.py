# SPDX-License-Identifier: GPL-3.0-or-later
"""First-run installation and play page for the existing controller launcher."""
from pathlib import Path
import tkinter as tk
from tkinter import filedialog, ttk

from .diagram import ACCENT, BG, CARD, LINE, MUTED, TEXT


class GamePage(ttk.Frame):
    def __init__(self, parent, app):
        super().__init__(parent, padding=(8, 18, 8, 8))
        self.app = app
        self.source = tk.StringVar()
        self.heading = tk.StringVar()
        self.description = tk.StringVar()
        self.message = tk.StringVar(value="Your original files stay untouched. Saves and settings are kept separately.")
        self._art_path = None
        self._portrait = None
        self._show_import = False
        self.columnconfigure(0, weight=4)
        self.columnconfigure(1, weight=6)
        self.rowconfigure(0, weight=1)

        self.art = tk.Canvas(self, background=CARD, highlightthickness=1, highlightbackground=LINE,
                             width=310, height=330)
        self.art.grid(row=0, column=0, sticky="nsew", padx=(0, 24))
        self.art.bind("<Configure>", lambda _event: self._draw_art())
        panel = ttk.Frame(self)
        panel.grid(row=0, column=1, sticky="nsew")
        panel.columnconfigure(0, weight=1)
        ttk.Label(panel, textvariable=self.heading, style="Heading.TLabel", font=("Noto Sans", 20, "bold")).grid(
            row=0, column=0, sticky="w", pady=(2, 10))
        ttk.Label(panel, textvariable=self.description, style="Muted.TLabel", wraplength=440, justify="left").grid(
            row=1, column=0, sticky="w", pady=(0, 16))

        self.ready_panel = ttk.Frame(panel)
        self.ready_panel.grid(row=2, column=0, sticky="ew")
        ttk.Button(self.ready_panel, text="Play Crusader", command=app.start, style="Primary.TButton").pack(anchor="w")
        self.play = self.ready_panel.winfo_children()[0]
        ttk.Button(self.ready_panel, text="Configure controller…", command=lambda: app.notebook.select(app.controls_tab)).pack(
            anchor="w", pady=(10, 0))
        self.change = ttk.Button(self.ready_panel, text="Reinstall / choose another copy…", command=self.show_import)
        self.change.pack(anchor="w", pady=(10, 0))

        self.import_panel = ttk.Frame(panel)
        self.import_panel.grid(row=3, column=0, sticky="ew", pady=(8, 0))
        buttons = ttk.Frame(self.import_panel)
        buttons.pack(anchor="w", pady=(0, 8))
        self.installer = ttk.Button(buttons, text="GOG installer…", command=self.choose_installer)
        self.installer.pack(side="left", padx=(0, 8))
        self.folder = ttk.Button(buttons, text="Game folder…", command=self.choose_folder)
        self.folder.pack(side="left")
        ttk.Label(self.import_panel, textvariable=self.source, style="Muted.TLabel", wraplength=420).pack(anchor="w", pady=(0, 8))
        self.install = ttk.Button(self.import_panel, text="Install No Remorse", command=lambda: app.begin_import(self.source.get()),
                                  style="Primary.TButton")
        self.install.pack(anchor="w")
        self.progress = ttk.Progressbar(self.import_panel, maximum=100)
        self.progress.pack(fill="x", pady=(12, 6))
        self.cancel = ttk.Button(self.import_panel, text="Cancel installation", command=app.cancel_import)
        self.cancel.pack(anchor="w")
        self.back = ttk.Button(self.import_panel, text="Back to Play", command=self.show_import)
        ttk.Label(panel, textvariable=self.message, style="Muted.TLabel", wraplength=440, justify="left").grid(
            row=4, column=0, sticky="sw", pady=(12, 0))
        self.source.trace_add("write", lambda *_args: self.refresh())

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

    def refresh(self):
        state = self.app.install_state
        busy = self.app.is_installing() or (self.app.process is not None and self.app.process.poll() is None)
        runtime = self.app.runtime_available()
        importing = not state.ready or self._show_import or self.app.is_installing()
        self.heading.set("Ready to play" if not importing else "Reinstall game files" if state.ready else "Install your copy")
        if state.ready and not importing:
            controls = "Twin-stick movement and aiming are enabled. Your controller layout is ready to configure." if self.app.enabled.get() else \
                       "Twin-stick controls are turned off. Enable them in Movement & feel, or play with classic controls."
            self.description.set(f"Crusader: No Remorse · {state.edition}\n{controls}")
            self.ready_panel.grid()
        else:
            self.description.set("Select your GOG installer or a complete game folder to replace the imported files. Your saves and controller settings will be kept." if state.ready else
                                 "Bring your own Crusader: No Remorse. Select the GOG offline installer or a complete game folder; the launcher will prepare it for twin-stick play.")
            self.ready_panel.grid_remove()
        if importing:
            self.import_panel.grid()
        else:
            self.import_panel.grid_remove()
        for widget in (self.installer, self.folder, self.change):
            widget.state(["disabled"] if busy else ["!disabled"])
        self.install.state(["!disabled"] if self.source.get() and not busy else ["disabled"])
        self.play.state(["!disabled"] if state.ready and runtime and not busy and getattr(self.app, "_settings_valid", True) else ["disabled"])
        if self.app.is_installing():
            self.progress.pack(fill="x", pady=(12, 6))
            self.cancel.pack(anchor="w")
        else:
            self.progress.pack_forget()
            self.cancel.pack_forget()
        if state.ready and importing and not busy:
            self.back.pack(anchor="w", pady=(8, 0))
        else:
            self.back.pack_forget()
        if not runtime and not self.app.is_installing():
            self.message.set("The game runtime is missing from this source checkout. Use a complete release bundle or follow README.md to prepare it.")
        path = state.artwork
        if path != self._art_path:
            self._art_path = path
            try:
                self._portrait = tk.PhotoImage(file=str(path)) if path else None
            except (tk.TclError, OSError):
                self._portrait = None
        self._draw_art()

    def _draw_art(self):
        canvas = self.art
        canvas.delete("all")
        width, height = canvas.winfo_width(), canvas.winfo_height()
        canvas.create_rectangle(0, 0, 5, height, fill=ACCENT, outline="")
        if self._portrait:
            canvas.create_image(width / 2, height / 2 - 22, image=self._portrait)
            canvas.create_text(width / 2, height - 35, text="THE SILENCER", fill=MUTED, font=("Noto Sans", 10, "bold"))
        else:
            canvas.create_text(width / 2, height / 2 - 36, text="CRUSADER", fill=ACCENT, font=("Noto Sans", 23, "bold"))
            canvas.create_text(width / 2, height / 2 + 3, text="NO REMORSE", fill=TEXT, font=("Noto Sans", 14))
            canvas.create_line(width * .2, height / 2 + 35, width * .8, height / 2 + 35, fill=LINE)
            canvas.create_text(width / 2, height - 42, text="Your game. Twin-stick controls.", fill=MUTED, font=("Noto Sans", 9))
