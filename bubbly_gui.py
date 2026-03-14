"""GUI launcher for Bubbly report generation."""

import os
import queue
import threading
from types import SimpleNamespace
from pathlib import Path
import tkinter as tk
import tkinter.font as tkfont
from tkinter import filedialog, messagebox
from tkinter import ttk
import subprocess
import sys
import shutil

from bubbly_launcher import PARSERS, run_with_args


LOG_LEVELS = ["debug", "info", "warning", "error", "critical"]


class TextRedirector:
    def __init__(self, event_queue):
        self.event_queue = event_queue

    def write(self, message):
        if message:
            self.event_queue.put(("log", message))

    def flush(self):
        return None


class BubblyGui(tk.Tk):
    def __init__(self, prefill=None):
        super().__init__()
        self.title("Bubbly Launcher")
        self.minsize(900, 600)
        self._configure_style()

        self.parser_var = tk.StringVar(value="")
        self.input_path = tk.StringVar()
        self.output_path = tk.StringVar()
        self.creator = tk.StringVar()
        self.case = tk.StringVar()
        self.logo_path = tk.StringVar()
        self.log_level = tk.StringVar(value="info")
        self.split_by_chat = tk.BooleanVar(value=True)

        self.parser_arg_vars = {}
        self.parser_arg_required = set()
        self.event_queue = queue.Queue()
        self._run_thread = None
        self.last_output_folder = None

        self._build_layout()
        if prefill:
            self._apply_prefill(prefill)
        self._poll_events()

    def _configure_style(self):
        style = ttk.Style(self)
        try:
            style.theme_use("clam")
        except tk.TclError:
            pass

        base_font = tkfont.nametofont("TkDefaultFont")
        base_font.configure(size=10)
        heading_font = base_font.copy()
        heading_font.configure(weight="bold")

        bg = "#e9edf3"
        self.configure(background=bg)
        style.configure(".", background=bg)
        style.configure("TFrame", background=bg)
        style.configure("TLabel", background=bg)
        style.configure("TLabelframe", background=bg)
        style.configure("TLabelframe.Label", background=bg, font=heading_font)

        style.configure("TNotebook", background=bg, borderwidth=0)
        style.configure("TNotebook.Tab", padding=(12, 6))
        style.map("TNotebook.Tab", padding=[("selected", (12, 8)), ("!selected", (12, 6))])

        style.configure("TButton", padding=(12, 6))
        style.configure("TEntry", padding=(6, 4))
        style.configure("TCombobox", padding=(6, 2))

        style.configure(
            "Treeview",
            background="#ffffff",
            fieldbackground="#ffffff",
            rowheight=24,
        )
        style.configure("Treeview.Heading", font=heading_font)

    def _build_layout(self):
        container = ttk.Frame(self, padding=16)
        container.pack(fill=tk.BOTH, expand=True)

        header = ttk.Frame(container)
        header.pack(fill=tk.X)
        ttk.Label(header, text="Bubbly GUI Launcher", font=("TkDefaultFont", 14, "bold")).pack(side=tk.LEFT)

        notebook = ttk.Notebook(container)
        notebook.pack(fill=tk.BOTH, expand=True, pady=(12, 0))

        setup_tab = ttk.Frame(notebook, padding=12)
        parser_tab = ttk.Frame(notebook, padding=12)
        run_tab = ttk.Frame(notebook, padding=12)

        notebook.add(setup_tab, text="Setup")
        notebook.add(parser_tab, text="Parser Args")
        notebook.add(run_tab, text="Run")

        self._build_setup_tab(setup_tab)
        self._build_parser_tab(parser_tab)
        self._build_run_tab(run_tab)

        footer = ttk.Frame(self, padding=(16, 8, 16, 12))
        footer.pack(fill=tk.X, side=tk.BOTTOM)

        self.status_label = ttk.Label(footer, text="Fill in the required fields to run.")
        self.status_label.pack(side=tk.LEFT, fill=tk.X, expand=True)

        self.open_output_button = ttk.Button(
            footer,
            text="Open Output",
            command=self._open_output_folder,
            state="disabled",
        )
        self.open_output_button.pack(side=tk.RIGHT, padx=(8, 0))

        self.progress = ttk.Progressbar(footer, mode="indeterminate", length=140)
        self.progress.pack(side=tk.RIGHT, padx=(8, 0))

        self.run_button = ttk.Button(footer, text="Run Bubbly", command=self._start_run)
        self.run_button.pack(side=tk.RIGHT)

    def _build_setup_tab(self, parent):
        setup_frame = ttk.LabelFrame(parent, text="Core Settings", padding=12)
        setup_frame.pack(fill=tk.X)

        grid = ttk.Frame(setup_frame)
        grid.pack(fill=tk.X)

        ttk.Label(grid, text="Parser *").grid(row=0, column=0, sticky="w", pady=4)
        parser_combo = ttk.Combobox(
            grid,
            textvariable=self.parser_var,
            values=sorted(PARSERS.keys()),
            state="readonly",
        )
        parser_combo.grid(row=0, column=1, sticky="ew", padx=(8, 0), pady=4)
        parser_combo.bind("<<ComboboxSelected>>", self._on_parser_change)

        input_row = ttk.Frame(grid)
        input_row.grid(row=1, column=1, sticky="ew", padx=(8, 0), pady=4)
        ttk.Entry(input_row, textvariable=self.input_path).pack(side=tk.LEFT, fill=tk.X, expand=True)
        ttk.Button(input_row, text="Browse File", command=self._choose_input_file).pack(side=tk.LEFT, padx=(8, 0))
        ttk.Button(input_row, text="Browse Folder", command=self._choose_input_folder).pack(side=tk.LEFT, padx=(8, 0))
        ttk.Label(grid, text="Input path *").grid(row=1, column=0, sticky="w")

        output_row = ttk.Frame(grid)
        output_row.grid(row=2, column=1, sticky="ew", padx=(8, 0), pady=4)
        ttk.Entry(output_row, textvariable=self.output_path).pack(side=tk.LEFT, fill=tk.X, expand=True)
        ttk.Button(output_row, text="Browse Folder", command=self._choose_output_folder).pack(side=tk.LEFT, padx=(8, 0))
        ttk.Label(grid, text="Output folder *").grid(row=2, column=0, sticky="w")

        ttk.Label(grid, text="Creator *").grid(row=3, column=0, sticky="w", pady=4)
        ttk.Entry(grid, textvariable=self.creator).grid(row=3, column=1, sticky="ew", padx=(8, 0), pady=4)

        ttk.Label(grid, text="Case *").grid(row=4, column=0, sticky="w", pady=4)
        ttk.Entry(grid, textvariable=self.case).grid(row=4, column=1, sticky="ew", padx=(8, 0), pady=4)

        ttk.Label(grid, text="Logo (optional)").grid(row=5, column=0, sticky="w", pady=4)
        logo_row = ttk.Frame(grid)
        logo_row.grid(row=5, column=1, sticky="ew", padx=(8, 0), pady=4)
        ttk.Entry(logo_row, textvariable=self.logo_path).pack(side=tk.LEFT, fill=tk.X, expand=True)
        ttk.Button(logo_row, text="Browse", command=self._choose_logo).pack(side=tk.LEFT, padx=(8, 0))

        ttk.Label(grid, text="Log level").grid(row=6, column=0, sticky="w", pady=4)
        ttk.Combobox(grid, textvariable=self.log_level, values=LOG_LEVELS, state="readonly").grid(
            row=6, column=1, sticky="w", padx=(8, 0), pady=4
        )

        ttk.Checkbutton(grid, text="Split by chat (default)", variable=self.split_by_chat).grid(
            row=7, column=1, sticky="w", padx=(8, 0), pady=(6, 0)
        )

        grid.columnconfigure(1, weight=1)

        tool_row = ttk.Frame(setup_frame)
        tool_row.pack(fill=tk.X, pady=(12, 0))
        ttk.Label(tool_row, text="Need to create a generic JSON first?").pack(side=tk.LEFT)
        ttk.Button(tool_row, text="Open Input-to-JSON", command=self._open_input_to_json).pack(
            side=tk.LEFT, padx=(8, 0)
        )

    def _build_parser_tab(self, parent):
        parser_frame = ttk.LabelFrame(parent, text="Parser-specific arguments", padding=12)
        parser_frame.pack(fill=tk.BOTH, expand=True)

        self.parser_args_container = ttk.Frame(parser_frame)
        self.parser_args_container.pack(fill=tk.BOTH, expand=True)

        self.parser_hint = ttk.Label(self.parser_args_container, text="Select a parser to configure its arguments.")
        self.parser_hint.pack(anchor="w")

    def _build_run_tab(self, parent):
        log_frame = ttk.LabelFrame(parent, text="Run output", padding=12)
        log_frame.pack(fill=tk.BOTH, expand=True)

        self.log_text = tk.Text(log_frame, height=16, wrap="word", state="disabled", background="#ffffff")
        self.log_text.pack(fill=tk.BOTH, expand=True)

    def _apply_prefill(self, prefill):
        parser_value = prefill.get("parser")
        if parser_value:
            self.parser_var.set(parser_value)
            self._render_parser_args()

        for key, target in (
            ("input", self.input_path),
            ("output", self.output_path),
            ("creator", self.creator),
            ("case", self.case),
            ("logo", self.logo_path),
        ):
            value = prefill.get(key)
            if value:
                target.set(value)

    def _on_parser_change(self, _event=None):
        self._render_parser_args()

    def _render_parser_args(self):
        for child in self.parser_args_container.winfo_children():
            child.destroy()

        parser_key = self.parser_var.get().strip()
        parser_class = PARSERS.get(parser_key)
        parser_args = getattr(parser_class, "PARSER_ARGS", {}) if parser_class else {}

        if not parser_args:
            ttk.Label(self.parser_args_container, text="No parser-specific arguments.").pack(anchor="w")
            self.parser_arg_vars = {}
            self.parser_arg_required = set()
            return

        grid = ttk.Frame(self.parser_args_container)
        grid.pack(fill=tk.X)

        self.parser_arg_vars = {}
        self.parser_arg_required = set()
        for row_index, (key, description) in enumerate(parser_args.items()):
            is_required = "required" in description.lower()
            label_text = f"{key} *" if is_required else key
            ttk.Label(grid, text=label_text).grid(row=row_index, column=0, sticky="w", pady=4)
            var = tk.StringVar()

            if parser_key == "whatsapp_export" and key == "platform":
                entry = ttk.Combobox(grid, textvariable=var, values=["ios", "android"], state="readonly")
            else:
                entry = ttk.Entry(grid, textvariable=var)
            entry.grid(row=row_index, column=1, sticky="ew", padx=(8, 0), pady=4)
            ttk.Label(grid, text=description).grid(row=row_index, column=2, sticky="w", padx=(8, 0))
            self.parser_arg_vars[key] = var
            if is_required:
                self.parser_arg_required.add(key)

        grid.columnconfigure(1, weight=1)

    def _choose_input_file(self):
        path = filedialog.askopenfilename(
            title="Select input file",
            filetypes=[("All files", "*")],
        )
        if path:
            self.input_path.set(path)

    def _choose_input_folder(self):
        path = filedialog.askdirectory(title="Select input folder")
        if path:
            self.input_path.set(path)

    def _choose_output_folder(self):
        path = filedialog.askdirectory(title="Select output folder")
        if path:
            self.output_path.set(path)

    def _choose_logo(self):
        path = filedialog.askopenfilename(
            title="Select logo image",
            filetypes=[("Image files", "*.png *.jpg *.jpeg *.gif *.bmp"), ("All files", "*")],
        )
        if path:
            self.logo_path.set(path)

    def _validate(self):
        if not self.parser_var.get().strip():
            return False, "Parser is required."
        if not self.input_path.get().strip():
            return False, "Input path is required."
        if not Path(self.input_path.get().strip()).exists():
            return False, "Input path does not exist."
        if not self.output_path.get().strip():
            return False, "Output folder is required."
        if not self.creator.get().strip():
            return False, "Creator is required."
        if not self.case.get().strip():
            return False, "Case is required."
        for key in self.parser_arg_required:
            var = self.parser_arg_vars.get(key)
            if not var or not var.get().strip():
                return False, f"Parser arg '{key}' is required."
        return True, ""

    def _start_run(self):
        if self._run_thread and self._run_thread.is_alive():
            messagebox.showinfo("Run in progress", "A run is already in progress.")
            return

        valid, message = self._validate()
        if not valid:
            messagebox.showerror("Missing input", message)
            return

        self._append_log("Starting run...\n")
        self.status_label.configure(text="Running...")
        self.run_button.configure(state="disabled")
        self.progress.start(12)
        self.open_output_button.configure(state="disabled")

        self._run_thread = threading.Thread(target=self._run_job, daemon=True)
        self._run_thread.start()

    def _run_job(self):
        import sys

        args = self._build_args()
        stdout = sys.stdout
        stderr = sys.stderr
        sys.stdout = TextRedirector(self.event_queue)
        sys.stderr = TextRedirector(self.event_queue)
        try:
            result = run_with_args(args)
            self.event_queue.put(("result", result))
            self.event_queue.put(("status", "Run complete."))
        except Exception as exc:
            self.event_queue.put(("status", f"Run failed: {exc}"))
        finally:
            sys.stdout = stdout
            sys.stderr = stderr
            self.event_queue.put(("done", ""))

    def _build_args(self):
        parser_args = []
        for key, var in self.parser_arg_vars.items():
            value = var.get().strip()
            if value:
                parser_args.append(f"{key}={value}")

        return SimpleNamespace(
            parser=self.parser_var.get().strip(),
            input=self.input_path.get().strip(),
            output=self.output_path.get().strip(),
            creator=self.creator.get().strip(),
            case=self.case.get().strip(),
            logo=self.logo_path.get().strip() or None,
            log_level=self.log_level.get().strip() or "info",
            split_by_chat=self.split_by_chat.get(),
            parser_args=parser_args,
            _config={},
            _banner_shown=True,
        )

    def _poll_events(self):
        try:
            while True:
                event, payload = self.event_queue.get_nowait()
                if event == "log":
                    self._append_log(payload)
                elif event == "status":
                    self.status_label.configure(text=payload)
                elif event == "result":
                    self._handle_run_result(payload)
                elif event == "done":
                    self.run_button.configure(state="normal")
                    self.progress.stop()
        except queue.Empty:
            pass

        self.after(100, self._poll_events)

    def _append_log(self, text):
        self.log_text.configure(state="normal")
        self.log_text.insert(tk.END, text)
        self.log_text.see(tk.END)
        self.log_text.configure(state="disabled")

    def _handle_run_result(self, result):
        if not isinstance(result, dict):
            return
        self.last_output_folder = result.get("output_folder")
        if self.last_output_folder:
            self.open_output_button.configure(state="normal")
        message_count = result.get("message_count")
        if message_count is not None and self.last_output_folder:
            self.status_label.configure(
                text=f"Run complete. Messages: {message_count}. Output: {self.last_output_folder}"
            )

    def _open_path(self, path):
        if not path:
            return
        target = str(path)
        if sys.platform.startswith("win"):
            # pylint: disable=no-member
            os.startfile(target)
        elif sys.platform == "darwin":
            subprocess.run(["open", target], check=False)
        else:
            opener = None
            for candidate in ("xdg-open", "gio", "gnome-open", "kde-open"):
                if shutil.which(candidate):
                    opener = candidate
                    break
            if not opener:
                messagebox.showerror(
                    "Open failed",
                    "Could not find a system opener (xdg-open/gio/gnome-open/kde-open).",
                )
                return
            if opener == "gio":
                subprocess.run([opener, "open", target], check=False)
            else:
                subprocess.run([opener, target], check=False)

    def _open_output_folder(self):
        if not self.last_output_folder:
            messagebox.showinfo("No output", "No output folder available yet.")
            return
        self._open_path(self.last_output_folder)

    def _open_input_to_json(self):
        try:
            if getattr(sys, "frozen", False):
                exe_dir = Path(sys.executable).resolve().parent
                candidates = list(exe_dir.glob("input_to_bubbly_gui*"))
                if sys.platform.startswith("win"):
                    candidates = [p for p in candidates if p.suffix.lower() == ".exe"]
                candidates = [p for p in candidates if p.is_file()]
                if not candidates:
                    raise FileNotFoundError(
                        f"No Input-to-JSON executable found next to {sys.executable}"
                    )
                subprocess.Popen([str(candidates[0])])
            else:
                script_path = Path(__file__).resolve().parent / "input_to_bubbly_gui.py"
                subprocess.Popen([sys.executable, str(script_path)])
        except Exception as exc:
            messagebox.showerror("Launch failed", f"Could not open Input-to-JSON tool: {exc}")



if __name__ == "__main__":
    app = BubblyGui()
    app.mainloop()
