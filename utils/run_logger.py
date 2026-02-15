"""Run logging utilities for teeing CLI output into per-run log files."""

import json
import logging
import sys
from datetime import datetime
from pathlib import Path


class _LoggingStream:
    """File-like stream wrapper that forwards writes to a logger level."""

    def __init__(self, logger, level):
        """Initialize stream redirection target."""
        self.logger = logger
        self.level = level
        self.buffer = ""

    def write(self, data):
        """Write stream data by logging complete lines."""
        if not data:
            return 0
        text = str(data)
        self.buffer += text
        while "\n" in self.buffer:
            line, self.buffer = self.buffer.split("\n", 1)
            if line:
                self.logger.log(self.level, line)
        return len(text)

    def flush(self):
        """Flush pending buffered text to the logger."""
        if self.buffer:
            self.logger.log(self.level, self.buffer)
            self.buffer = ""

    def isatty(self):
        """Return False because this is a virtual stream."""
        return False


class RunLogger:
    """Context manager that configures run logging for console and file output."""

    def __init__(self, output_base, args, config_parser_args, cli_parser_args, parser_kwargs):
        """Store run metadata and output location for logger setup."""
        self.output_base = Path(output_base)
        self.args = args
        self.config_parser_args = config_parser_args
        self.cli_parser_args = cli_parser_args
        self.parser_kwargs = parser_kwargs
        self.logger = None
        self.file_handler = None
        self.log_path = None
        self.original_stdout = None
        self.original_stderr = None

    def __enter__(self):
        """Set up logging handlers and redirect stdout/stderr through logging."""
        log_dir = self.output_base / "log"
        log_dir.mkdir(parents=True, exist_ok=True)
        self.log_path = log_dir / f"bubbly_run_{datetime.now().strftime('%Y%m%d_%H%M%S')}.log"

        self.original_stdout = sys.stdout
        self.original_stderr = sys.stderr

        logger_name = f"bubbly.run.{datetime.now().strftime('%Y%m%d_%H%M%S_%f')}"
        self.logger = logging.getLogger(logger_name)
        self.logger.setLevel(logging.INFO)
        self.logger.propagate = False

        formatter = logging.Formatter("%(asctime)s [%(levelname)s] %(message)s")
        console_handler = logging.StreamHandler(self.original_stdout)
        console_handler.setFormatter(formatter)
        file_handler = logging.FileHandler(self.log_path, encoding="utf-8")
        file_handler.setFormatter(formatter)
        self.logger.addHandler(console_handler)
        self.logger.addHandler(file_handler)
        self.file_handler = file_handler

        sys.stdout = _LoggingStream(self.logger, logging.INFO)
        sys.stderr = _LoggingStream(self.logger, logging.ERROR)

        args_snapshot = {k: v for k, v in vars(self.args).items() if k != "_config"}
        run_context = {
            "timestamp": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
            "argv": sys.argv[1:],
            "cli_args_resolved": args_snapshot,
            "config_values": self.args._config if isinstance(getattr(self.args, "_config", None), dict) else {},
            "config_parser_args": self.config_parser_args,
            "cli_parser_args": self.cli_parser_args,
            "merged_parser_args": self.parser_kwargs,
        }
        self.logger.info("Run log: %s", self.log_path)
        if self.file_handler is not None:
            self.file_handler.stream.write("=== Run context ===\n")
            self.file_handler.stream.write(json.dumps(run_context, ensure_ascii=False, indent=2))
            self.file_handler.stream.write("\n")
            self.file_handler.flush()
        return self

    def __exit__(self, exc_type, exc, tb):
        """Restore original streams and close logger handlers."""
        if sys.stdout is not None and hasattr(sys.stdout, "flush"):
            sys.stdout.flush()
        if sys.stderr is not None and hasattr(sys.stderr, "flush"):
            sys.stderr.flush()
        sys.stdout = self.original_stdout
        sys.stderr = self.original_stderr
        if self.logger is not None:
            for handler in list(self.logger.handlers):
                handler.close()
                self.logger.removeHandler(handler)
        return False
