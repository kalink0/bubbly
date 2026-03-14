"""GUI wrapper for converting input datasets into Bubbly-compatible JSON."""

import json
import os
from pathlib import Path
import tkinter as tk
import tkinter.font as tkfont
from tkinter import filedialog, messagebox
from tkinter import ttk

from input_to_bubbly_json import (
    ALLOWED_MESSAGE_FIELDS,
    REQUIRED_MESSAGE_FIELDS,
    build_messages,
    normalize_timestamp,
)


def _normalize_header(header):
    return str(header or "").strip().lower()


COMMON_HEADER_ALIASES = {
    "sender": {"sender", "from", "author", "user", "name"},
    "timestamp": {"timestamp", "time", "date", "datetime", "ts"},
    "content": {"content", "message", "body", "text"},
    "media": {"media", "attachment", "attachments", "file"},
    "url": {"url", "link"},
    "is_owner": {"is_owner", "owner", "is_me", "me", "self"},
    "chat": {"chat", "conversation", "thread"},
}

TOOLTIPS = {
    "delimiter": "Character separating columns, e.g. ',' or ';'.",
    "encoding": "Text encoding used by the CSV file. Common: utf-8.",
    "strict": "If enabled, fail on any row missing required values.",
    "messenger": "Platform name shown in the report header.",
    "source": "Where the data came from, shown in the report header.",
    "chat_name": "Optional chat name displayed in the report header.",
}


class CsvToBubblyGui(tk.Tk):
    """Tkinter UI for CSV -> Bubbly JSON conversion."""

    def __init__(self):
        super().__init__()
        self.title("Bubbly CSV Converter")
        self.minsize(760, 520)
        self._configure_style()

        self.csv_path = tk.StringVar()
        self.output_path = tk.StringVar()
        self.messenger = tk.StringVar(value="")
        self.source = tk.StringVar(value="")
        self.chat_name = tk.StringVar(value="")
        self.delimiter = tk.StringVar(value=",")
        self.encoding = tk.StringVar(value="utf-8")
        self.strict = tk.BooleanVar(value=False)
        self.timestamp_format = tk.StringVar(value="")
        self.timestamp_timezone = tk.StringVar(value="")

        self._headers = []
        self._preview_rows = []
        self._mapping_vars = {}
        self._mapping_boxes = {}

        self._build_layout()

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
        style.configure("TLabelframe.Label", background=bg)
        style.configure("TLabelframe.Label", font=heading_font)

        style.configure("TNotebook", background=bg, borderwidth=0)
        style.configure("TNotebook.Tab", padding=(12, 6))
        style.map(
            "TNotebook.Tab",
            padding=[("selected", (12, 8)), ("!selected", (12, 6))],
        )

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

    def _attach_tooltip(self, widget, text):
        tip = tk.Toplevel(self)
        tip.withdraw()
        tip.overrideredirect(True)
        label = ttk.Label(tip, text=text, relief=tk.SOLID, borderwidth=1, padding=(6, 4))
        label.pack()

        def show_tip(_event):
            x = widget.winfo_rootx() + 12
            y = widget.winfo_rooty() + widget.winfo_height() + 8
            tip.geometry(f"+{x}+{y}")
            tip.deiconify()

        def hide_tip(_event):
            tip.withdraw()

        widget.bind("<Enter>", show_tip)
        widget.bind("<Leave>", hide_tip)

    def _build_layout(self):
        container = ttk.Frame(self, padding=16)
        container.pack(fill=tk.BOTH, expand=True)

        header = ttk.Frame(container)
        header.pack(fill=tk.X)
        ttk.Label(header, text="Input to Bubbly JSON", font=("TkDefaultFont", 14, "bold")).pack(
            side=tk.LEFT
        )

        file_frame = ttk.LabelFrame(container, text="Input / Output", padding=12)
        file_frame.pack(fill=tk.X, pady=(12, 0))

        self._build_file_row(file_frame, "CSV file", self.csv_path, self._choose_csv)
        self._build_file_row(file_frame, "Output JSON", self.output_path, self._choose_output)

        notebook = ttk.Notebook(container)
        notebook.pack(fill=tk.BOTH, expand=True, pady=(12, 0))

        settings_tab = ttk.Frame(notebook, padding=12)
        mapping_tab = ttk.Frame(notebook, padding=12)
        notebook.add(settings_tab, text="Settings")
        notebook.add(mapping_tab, text="Field Mapping")

        input_frame = ttk.LabelFrame(settings_tab, text="Input file settings", padding=12)
        input_frame.pack(fill=tk.X)
        ttk.Label(input_frame, text="These control how we read the CSV file.").pack(anchor="w")

        input_grid = ttk.Frame(input_frame)
        input_grid.pack(fill=tk.X, pady=(8, 0))

        delimiter_entry = self._build_entry(input_grid, 0, "Delimiter", self.delimiter)
        delimiter_entry.configure(width=6)
        encoding_entry = self._build_entry(input_grid, 1, "Encoding", self.encoding)
        encoding_entry.configure(width=12)

        strict_check = ttk.Checkbutton(input_grid, text="Strict mode (fail on missing required values)", variable=self.strict)
        strict_check.grid(row=2, column=0, columnspan=2, sticky="w", pady=(6, 0))

        reload_button = ttk.Button(input_grid, text="Reload Headers", command=self._reload_headers)
        reload_button.grid(row=2, column=2, sticky="e", padx=(8, 0), pady=(6, 0))

        meta_frame = ttk.LabelFrame(settings_tab, text="Report metadata (appears in output header)", padding=12)
        meta_frame.pack(fill=tk.X, pady=(12, 0))
        ttk.Label(meta_frame, text="These values show up in the Bubbly report header.").pack(anchor="w")

        meta_grid = ttk.Frame(meta_frame)
        meta_grid.pack(fill=tk.X, pady=(8, 0))

        messenger_entry = self._build_entry(meta_grid, 0, "Messenger / platform *", self.messenger)
        source_entry = self._build_entry(meta_grid, 1, "Source *", self.source)
        chat_entry = self._build_entry(meta_grid, 2, "Chat name (optional)", self.chat_name)

        self._add_tooltip_icon(input_grid, 0, 2, "delimiter")
        self._add_tooltip_icon(input_grid, 1, 2, "encoding")
        self._add_tooltip_icon(input_grid, 2, 3, "strict")

        self._add_tooltip_icon(meta_grid, 0, 2, "messenger")
        self._add_tooltip_icon(meta_grid, 1, 2, "source")
        self._add_tooltip_icon(meta_grid, 2, 2, "chat_name")

        mapping_pane = ttk.PanedWindow(mapping_tab, orient=tk.VERTICAL)
        mapping_pane.pack(fill=tk.BOTH, expand=True)

        preview_notebook = ttk.Notebook(mapping_pane)
        preview_csv_frame = ttk.Frame(preview_notebook, padding=8)
        preview_ts_frame = ttk.Frame(preview_notebook, padding=8)
        preview_skipped_frame = ttk.Frame(preview_notebook, padding=8)
        preview_notebook.add(preview_csv_frame, text="CSV Preview")
        preview_notebook.add(preview_ts_frame, text="Timestamp Preview")
        preview_notebook.add(preview_skipped_frame, text="Skipped Rows")
        self._build_preview(preview_csv_frame)
        self._build_timestamp_preview(preview_ts_frame)
        self._build_skipped_preview(preview_skipped_frame)

        mapping_container = ttk.Frame(mapping_pane)
        mapping_canvas = tk.Canvas(mapping_container, highlightthickness=0)
        mapping_scroll = ttk.Scrollbar(mapping_container, orient=tk.VERTICAL, command=mapping_canvas.yview)
        self.mapping_body = ttk.Frame(mapping_canvas)

        self.mapping_body.bind(
            "<Configure>",
            lambda event: mapping_canvas.configure(scrollregion=mapping_canvas.bbox("all")),
        )

        mapping_canvas.create_window((0, 0), window=self.mapping_body, anchor="nw")
        mapping_canvas.configure(yscrollcommand=mapping_scroll.set)

        mapping_canvas.pack(side=tk.LEFT, fill=tk.BOTH, expand=True)
        mapping_scroll.pack(side=tk.RIGHT, fill=tk.Y)

        ordered_fields = list(REQUIRED_MESSAGE_FIELDS) + sorted(
            field for field in ALLOWED_MESSAGE_FIELDS if field not in REQUIRED_MESSAGE_FIELDS
        )
        for row_index, field in enumerate(ordered_fields):
            label_text = field
            if field in REQUIRED_MESSAGE_FIELDS:
                label_text = f"{field} *"
            label = ttk.Label(self.mapping_body, text=label_text)
            label.grid(row=row_index, column=0, sticky="w", padx=(0, 12), pady=4)

            var = tk.StringVar(value="")
            values = ["—"]
            combo = ttk.Combobox(self.mapping_body, textvariable=var, values=values, state="readonly")
            combo.grid(row=row_index, column=1, sticky="ew", pady=4)
            combo.set("—")
            combo.bind("<<ComboboxSelected>>", self._on_mapping_change)

            self._mapping_vars[field] = var
            self._mapping_boxes[field] = combo

        self.mapping_body.columnconfigure(1, weight=1)

        mapping_pane.add(preview_notebook, weight=1)
        mapping_pane.add(mapping_container, weight=3)

        footer = ttk.Frame(self, padding=(16, 8, 16, 12))
        footer.pack(fill=tk.X, side=tk.BOTTOM)

        self.status = ttk.Label(footer, text="Pick a CSV file to begin.")
        self.status.pack(side=tk.LEFT, fill=tk.X, expand=True)

        convert_button = ttk.Button(footer, text="Convert CSV -> Bubbly JSON", command=self._convert)
        convert_button.pack(side=tk.RIGHT)

    def _build_preview(self, parent):
        toolbar = ttk.Frame(parent)
        toolbar.pack(fill=tk.X)

        ttk.Label(toolbar, text="Showing first rows of the CSV file.").pack(side=tk.LEFT)
        self.preview_rows_var = tk.IntVar(value=10)
        ttk.Label(toolbar, text="Rows:").pack(side=tk.LEFT, padx=(12, 4))
        preview_rows_entry = ttk.Entry(toolbar, textvariable=self.preview_rows_var, width=5)
        preview_rows_entry.pack(side=tk.LEFT)
        ttk.Button(toolbar, text="Refresh Preview", command=self._reload_headers).pack(
            side=tk.LEFT, padx=(8, 0)
        )

        tree_container = ttk.Frame(parent)
        tree_container.pack(fill=tk.BOTH, expand=True, pady=(8, 0))

        self.preview_tree = ttk.Treeview(tree_container, columns=(), show="headings", height=6)
        preview_scroll_y = ttk.Scrollbar(tree_container, orient=tk.VERTICAL, command=self.preview_tree.yview)
        preview_scroll_x = ttk.Scrollbar(tree_container, orient=tk.HORIZONTAL, command=self.preview_tree.xview)
        self.preview_tree.configure(yscrollcommand=preview_scroll_y.set, xscrollcommand=preview_scroll_x.set)

        self.preview_tree.pack(side=tk.LEFT, fill=tk.BOTH, expand=True)
        preview_scroll_y.pack(side=tk.RIGHT, fill=tk.Y)
        preview_scroll_x.pack(side=tk.BOTTOM, fill=tk.X)

    def _build_timestamp_preview(self, parent):
        settings_row = ttk.Frame(parent)
        settings_row.pack(fill=tk.X)

        ttk.Label(settings_row, text="Timestamp format").grid(row=0, column=0, sticky="w")
        timestamp_format_values = [
            "",
            "%Y-%m-%d %H:%M:%S",
            "%Y-%m-%d %H:%M",
            "%Y-%m-%dT%H:%M:%S",
            "%d/%m/%Y %H:%M",
            "%m/%d/%Y %H:%M",
            "%d.%m.%Y, %H:%M",
        ]
        timestamp_format_entry = ttk.Combobox(
            settings_row,
            textvariable=self.timestamp_format,
            values=timestamp_format_values,
            state="normal",
        )
        timestamp_format_entry.grid(row=0, column=1, sticky="ew", padx=(8, 16))

        ttk.Label(settings_row, text="Timezone").grid(row=0, column=2, sticky="w")
        timezone_combo = ttk.Combobox(
            settings_row,
            textvariable=self.timestamp_timezone,
            values=["", "utc", "local"],
            state="readonly",
            width=10,
        )
        timezone_combo.grid(row=0, column=3, sticky="w", padx=(8, 0))

        settings_row.columnconfigure(1, weight=1)

        toolbar = ttk.Frame(parent)
        toolbar.pack(fill=tk.X, pady=(8, 0))
        ttk.Label(toolbar, text="Preview parsed timestamps from the mapped column.").pack(side=tk.LEFT)
        ttk.Button(toolbar, text="Auto-detect Format", command=self._auto_detect_timestamp_format).pack(
            side=tk.RIGHT, padx=(8, 0)
        )
        ttk.Button(toolbar, text="Refresh Timestamp Preview", command=self._update_timestamp_preview).pack(
            side=tk.RIGHT
        )

        tree_container = ttk.Frame(parent)
        tree_container.pack(fill=tk.BOTH, expand=True, pady=(8, 0))

        self.timestamp_tree = ttk.Treeview(
            tree_container,
            columns=("raw", "iso"),
            show="headings",
            height=4,
        )
        self.timestamp_tree.heading("raw", text="Raw timestamp")
        self.timestamp_tree.heading("iso", text="ISO 8601 output")
        self.timestamp_tree.column("raw", width=220, minwidth=160, stretch=True)
        self.timestamp_tree.column("iso", width=220, minwidth=160, stretch=True)

        scroll_y = ttk.Scrollbar(tree_container, orient=tk.VERTICAL, command=self.timestamp_tree.yview)
        scroll_x = ttk.Scrollbar(tree_container, orient=tk.HORIZONTAL, command=self.timestamp_tree.xview)
        self.timestamp_tree.configure(yscrollcommand=scroll_y.set, xscrollcommand=scroll_x.set)

        self.timestamp_tree.pack(side=tk.LEFT, fill=tk.BOTH, expand=True)
        scroll_y.pack(side=tk.RIGHT, fill=tk.Y)
        scroll_x.pack(side=tk.BOTTOM, fill=tk.X)

        self.timestamp_hint = ttk.Label(parent, text="")
        self.timestamp_hint.pack(fill=tk.X, pady=(6, 0))

    def _build_skipped_preview(self, parent):
        toolbar = ttk.Frame(parent)
        toolbar.pack(fill=tk.X)
        self.skipped_hint = ttk.Label(toolbar, text="Skipped rows will appear after conversion.")
        self.skipped_hint.pack(side=tk.LEFT)

        tree_container = ttk.Frame(parent)
        tree_container.pack(fill=tk.BOTH, expand=True, pady=(8, 0))

        self.skipped_tree = ttk.Treeview(
            tree_container,
            columns=("row", "reason"),
            show="headings",
            height=6,
        )
        self.skipped_tree.heading("row", text="Row")
        self.skipped_tree.heading("reason", text="Reason")
        self.skipped_tree.column("row", width=80, minwidth=60, stretch=False)
        self.skipped_tree.column("reason", width=360, minwidth=200, stretch=True)

        scroll_y = ttk.Scrollbar(tree_container, orient=tk.VERTICAL, command=self.skipped_tree.yview)
        scroll_x = ttk.Scrollbar(tree_container, orient=tk.HORIZONTAL, command=self.skipped_tree.xview)
        self.skipped_tree.configure(yscrollcommand=scroll_y.set, xscrollcommand=scroll_x.set)

        self.skipped_tree.pack(side=tk.LEFT, fill=tk.BOTH, expand=True)
        scroll_y.pack(side=tk.RIGHT, fill=tk.Y)
        scroll_x.pack(side=tk.BOTTOM, fill=tk.X)

    def _build_file_row(self, parent, label_text, var, browse_command):
        row = ttk.Frame(parent)
        row.pack(fill=tk.X, pady=4)

        label = ttk.Label(row, text=label_text, width=14)
        label.pack(side=tk.LEFT)
        entry = ttk.Entry(row, textvariable=var)
        entry.pack(side=tk.LEFT, fill=tk.X, expand=True, padx=(8, 8))
        button = ttk.Button(row, text="Browse", command=browse_command)
        button.pack(side=tk.LEFT)

    def _build_entry(self, parent, row, label_text, var):
        label = ttk.Label(parent, text=label_text)
        label.grid(row=row, column=0, sticky="w", pady=4)
        entry = ttk.Entry(parent, textvariable=var)
        entry.grid(row=row, column=1, sticky="ew", padx=(8, 0), pady=4)
        parent.columnconfigure(1, weight=1)
        return entry

    def _add_tooltip_icon(self, parent, row, column, tooltip_key):
        icon = ttk.Label(parent, text="?", foreground="#444", padding=(6, 0))
        icon.grid(row=row, column=column, sticky="w")
        tooltip_text = TOOLTIPS.get(tooltip_key, "")
        if tooltip_text:
            self._attach_tooltip(icon, tooltip_text)

    def _choose_csv(self):
        path = filedialog.askopenfilename(
            title="Select CSV file",
            filetypes=[("CSV files", "*.csv"), ("All files", "*")],
        )
        if not path:
            return
        self.csv_path.set(path)

        if not self.output_path.get():
            base = Path(path)
            self.output_path.set(str(base.with_suffix("")) + "_bubbly.json")

        self._reload_headers()

    def _choose_output(self):
        path = filedialog.asksaveasfilename(
            title="Save output JSON",
            defaultextension=".json",
            filetypes=[("JSON files", "*.json"), ("All files", "*")],
        )
        if path:
            self.output_path.set(path)

    def _reload_headers(self):
        path = self.csv_path.get().strip()
        if not path:
            messagebox.showwarning("Missing CSV", "Please choose a CSV file first.")
            return

        csv_path = Path(path)
        if not csv_path.is_file():
            messagebox.showerror("CSV not found", f"CSV file not found: {csv_path}")
            return

        try:
            headers, rows = self._load_headers(csv_path)
        except Exception as exc:
            messagebox.showerror("Unable to read CSV", str(exc))
            return

        self._headers = headers
        self._preview_rows = rows
        self._update_mapping_options()
        self._update_preview()
        self._update_timestamp_preview()
        self.status.configure(text=f"Loaded {len(headers)} column(s) from CSV.")

    def _load_headers(self, csv_path):
        delimiter = self.delimiter.get() or ","
        encoding = self.encoding.get() or "utf-8"
        preview_limit = self._safe_preview_limit()
        import csv

        with csv_path.open("r", encoding=encoding, newline="") as handle:
            reader = csv.DictReader(handle, delimiter=delimiter)
            headers = reader.fieldnames or []
            rows = []
            for _, row in zip(range(preview_limit), reader):
                rows.append(row)

        headers = [h for h in headers if h is not None]
        if not headers:
            raise ValueError("CSV file has no header row.")
        return headers, rows

    def _safe_preview_limit(self):
        try:
            value = int(self.preview_rows_var.get())
        except Exception:
            value = 10
        if value <= 0:
            return 10
        return min(value, 200)

    def _update_mapping_options(self):
        values = ["—"] + self._headers
        normalized = {_normalize_header(h): h for h in self._headers}

        for field, combo in self._mapping_boxes.items():
            combo.configure(values=values)
            auto_value = self._auto_map_value(field, normalized)
            if auto_value:
                combo.set(auto_value)
            else:
                combo.set("—")

    def _update_preview(self):
        if not self._headers:
            return
        # Reset columns
        self.preview_tree.delete(*self.preview_tree.get_children())
        self.preview_tree["columns"] = self._headers
        for header in self._headers:
            self.preview_tree.heading(header, text=header)
            self.preview_tree.column(header, width=120, minwidth=80, stretch=True)

        for row in self._preview_rows:
            values = [row.get(header, "") for header in self._headers]
            self.preview_tree.insert("", tk.END, values=values)

    def _on_mapping_change(self, _event):
        self._update_timestamp_preview()

    def _update_timestamp_preview(self):
        if not hasattr(self, "timestamp_tree"):
            return
        self.timestamp_tree.delete(*self.timestamp_tree.get_children())

        timestamp_column = self._mapping_vars.get("timestamp")
        if not timestamp_column:
            return
        column_name = timestamp_column.get().strip()
        if not column_name or column_name == "—":
            self.timestamp_tree.insert("", tk.END, values=("Map the timestamp column to preview.", ""))
            return
        if not self._preview_rows:
            self.timestamp_tree.insert("", tk.END, values=("No preview rows loaded.", ""))
            return

        fmt = self.timestamp_format.get().strip() or None
        tz_hint = self.timestamp_timezone.get().strip() or None

        errors = 0
        for row in self._preview_rows[:5]:
            raw_value = row.get(column_name, "")
            try:
                iso_value = normalize_timestamp(raw_value, fmt=fmt, timezone_hint=tz_hint)
            except Exception as exc:
                errors += 1
                iso_value = f"Error: {exc}"
            self.timestamp_tree.insert("", tk.END, values=(raw_value, iso_value))

        if hasattr(self, "timestamp_hint"):
            if errors:
                self.timestamp_hint.configure(text="Some timestamps failed to parse. Adjust the format.")
            else:
                self.timestamp_hint.configure(text="All preview timestamps parsed successfully.")

    def _auto_detect_timestamp_format(self):
        timestamp_column = self._mapping_vars.get("timestamp")
        if not timestamp_column:
            messagebox.showinfo("Missing mapping", "Map the timestamp column first.")
            return
        column_name = timestamp_column.get().strip()
        if not column_name or column_name == "—":
            messagebox.showinfo("Missing mapping", "Map the timestamp column first.")
            return
        if not self._preview_rows:
            messagebox.showinfo("No preview rows", "Load a CSV preview first.")
            return

        candidate_formats = [
            "%Y-%m-%d %H:%M:%S",
            "%Y-%m-%d %H:%M",
            "%Y-%m-%dT%H:%M:%S",
            "%Y-%m-%dT%H:%M",
            "%d/%m/%Y %H:%M:%S",
            "%d/%m/%Y %H:%M",
            "%m/%d/%Y %H:%M:%S",
            "%m/%d/%Y %H:%M",
            "%d.%m.%Y, %H:%M:%S",
            "%d.%m.%Y, %H:%M",
            "%d.%m.%Y %H:%M:%S",
            "%d.%m.%Y %H:%M",
            "%Y/%m/%d %H:%M:%S",
            "%Y/%m/%d %H:%M",
            "%Y.%m.%d %H:%M:%S",
            "%Y.%m.%d %H:%M",
        ]

        sample_values = [
            str(row.get(column_name, "")).strip()
            for row in self._preview_rows
            if str(row.get(column_name, "")).strip()
        ][:20]
        if not sample_values:
            messagebox.showinfo("No timestamps", "No timestamp values found to analyze.")
            return

        best_format = None
        best_score = -1
        for fmt in candidate_formats:
            score = 0
            for value in sample_values:
                try:
                    normalize_timestamp(value, fmt=fmt, timezone_hint=self.timestamp_timezone.get().strip() or None)
                except Exception:
                    continue
                score += 1
            if score > best_score:
                best_score = score
                best_format = fmt

        if best_format and best_score > 0:
            self.timestamp_format.set(best_format)
            self._update_timestamp_preview()
            if hasattr(self, "timestamp_hint"):
                self.timestamp_hint.configure(
                    text=f"Detected format {best_format} (matched {best_score}/{len(sample_values)} samples)."
                )
        else:
            messagebox.showinfo(
                "Auto-detect failed",
                "Could not detect a matching timestamp format. Try entering one manually.",
            )

    def _auto_map_value(self, field, normalized_headers):
        aliases = COMMON_HEADER_ALIASES.get(field, {field})
        for alias in aliases:
            mapped = normalized_headers.get(alias)
            if mapped:
                return mapped
        return ""

    def _validate_inputs(self):
        csv_path = self.csv_path.get().strip()
        output_path = self.output_path.get().strip()
        messenger = self.messenger.get().strip()
        source = self.source.get().strip()

        if not csv_path:
            return False, "CSV file is required."
        if not Path(csv_path).is_file():
            return False, f"CSV file not found: {csv_path}"
        if not output_path:
            return False, "Output JSON path is required."
        if not messenger:
            return False, "Messenger / platform is required."
        if not source:
            return False, "Source is required."

        mapping = self._build_mapping()
        missing_required = [field for field in REQUIRED_MESSAGE_FIELDS if field not in mapping]
        if missing_required:
            return False, f"Missing required mapping(s): {', '.join(sorted(missing_required))}"

        return True, ""

    def _build_mapping(self):
        mapping = {}
        for field, var in self._mapping_vars.items():
            value = var.get().strip()
            if not value or value == "—":
                continue
            mapping[field] = value
        return mapping

    def _convert(self):
        valid, message = self._validate_inputs()
        if not valid:
            messagebox.showerror("Missing input", message)
            return

        csv_path = Path(self.csv_path.get().strip())
        output_path = Path(self.output_path.get().strip())
        messenger = self.messenger.get().strip()
        source = self.source.get().strip()
        chat_name = self.chat_name.get().strip()
        mapping = self._build_mapping()
        timestamp_format = self.timestamp_format.get().strip() or None
        timestamp_timezone = self.timestamp_timezone.get().strip() or None

        try:
            messages, skipped, skipped_rows = build_messages(
                csv_path=csv_path,
                mapping=mapping,
                delimiter=self.delimiter.get() or ",",
                encoding=self.encoding.get() or "utf-8",
                strict=self.strict.get(),
                timestamp_format=timestamp_format,
                timestamp_timezone=timestamp_timezone,
            )
        except Exception as exc:
            messagebox.showerror("Conversion failed", str(exc))
            return

        payload = {
            "source": source,
            "platform": messenger,
            "messages": messages,
        }
        if chat_name:
            payload["chat_name"] = chat_name

        try:
            output_path.parent.mkdir(parents=True, exist_ok=True)
            with output_path.open("w", encoding="utf-8") as handle:
                json.dump(payload, handle, indent=2, ensure_ascii=False)
                handle.write("\n")
        except Exception as exc:
            messagebox.showerror("Save failed", str(exc))
            return

        log_path = None
        if skipped_rows:
            log_path = output_path.with_suffix(".skipped.log")
            try:
                with log_path.open("w", encoding="utf-8") as handle:
                    for row_index, missing_fields in skipped_rows:
                        handle.write(f"Row {row_index}: missing required values {missing_fields}\n")
            except Exception as exc:
                messagebox.showwarning("Skip log failed", f"Unable to write skipped log: {exc}")

        if hasattr(self, "skipped_tree"):
            self.skipped_tree.delete(*self.skipped_tree.get_children())
            if skipped_rows:
                for row_index, missing_fields in skipped_rows:
                    reason = f"Missing required values: {', '.join(missing_fields)}"
                    self.skipped_tree.insert("", tk.END, values=(row_index, reason))
                if hasattr(self, "skipped_hint"):
                    hint = f"Skipped {len(skipped_rows)} row(s)."
                    if log_path:
                        hint += f" Log: {log_path}"
                    self.skipped_hint.configure(text=hint)
            else:
                if hasattr(self, "skipped_hint"):
                    self.skipped_hint.configure(text="No rows were skipped.")

        self.status.configure(
            text=f"Wrote {len(messages)} message(s) to {output_path}. Skipped rows: {skipped}."
        )
        messagebox.showinfo(
            "Conversion complete",
            f"Wrote {len(messages)} message(s) to {output_path}.\nSkipped rows: {skipped}.",
        )


if __name__ == "__main__":
    app = CsvToBubblyGui()
    app.mainloop()
