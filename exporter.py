import shutil
from pathlib import Path
from datetime import datetime
import json
import mimetypes
from bubbly_version import BUBBLY_VERSION

class BubblyExporter:
    def __init__(self, messages, media_folder, output_folder, metadata, logo_path=None):
        self.messages = messages
        self.media_folder = Path(media_folder)
        self.output_folder = Path(output_folder)
        self.metadata = metadata
        self.templates_folder = Path(__file__).resolve().parent / "templates"
        if not self.templates_folder.is_dir():
            raise FileNotFoundError(f"Templates folder not found: {self.templates_folder}")
        self.logo_path = Path(logo_path) if logo_path else None
        self.output_folder.mkdir(parents=True, exist_ok=True)
        (self.output_folder / "media").mkdir(exist_ok=True)

    # ----------------------
    # Load template file
    # ----------------------
    def _load_template(self, file_name: str):
        path = self.templates_folder / file_name
        if not path.exists():
            raise FileNotFoundError(f"Template not found: {path}")
        return path.read_text(encoding="utf-8")

    # ----------------------
    # Copy media files
    # ----------------------
    def _copy_media(self):
        copied_count = 0
        copied_targets = set()
        for msg in self.messages:
            media_name = msg.get("media")
            if not media_name:
                continue

            if isinstance(media_name, str) and media_name.startswith("missing:"):
                # Already marked by parser, keep as-is.
                continue

            src = self.media_folder / media_name
            if not src.exists():
                msg["media"] = f"missing:{media_name}"
                msg.pop("media_mime", None)
                continue

            media_mime = msg.get("media_mime") or self._detect_mime_from_magic(src) or mimetypes.guess_type(str(src))[0]
            if media_mime and not msg.get("media_mime"):
                msg["media_mime"] = media_mime

            output_media_name = msg.get("media_output") or media_name
            if not Path(output_media_name).suffix:
                ext = self._extension_for_mime(media_mime)
                if ext:
                    output_media_name = f"{output_media_name}.{ext}"

            dest = self.output_folder / "media" / output_media_name
            dest.parent.mkdir(parents=True, exist_ok=True)
            if str(dest) not in copied_targets:
                shutil.copy(src, dest)
                copied_targets.add(str(dest))
                copied_count += 1

            # Keep final media path in messages so frontend uses the copied file name.
            msg["media"] = output_media_name
        return copied_count

    def _detect_mime_from_magic(self, path: Path):
        try:
            header = path.read_bytes()[:64]
        except Exception:
            return None
        if not header:
            return None

        if header.startswith(b"\xFF\xD8\xFF"):
            return "image/jpeg"
        if header.startswith(b"\x89PNG\r\n\x1A\n"):
            return "image/png"
        if header.startswith((b"GIF87a", b"GIF89a")):
            return "image/gif"
        if header.startswith(b"RIFF") and len(header) >= 12 and header[8:12] == b"WEBP":
            return "image/webp"
        if header.startswith(b"%PDF-"):
            return "application/pdf"
        if header.startswith(b"OggS"):
            return "audio/ogg"
        if header.startswith(b"ID3"):
            return "audio/mpeg"
        if len(header) >= 2 and header[0] == 0xFF and (header[1] & 0xE0) == 0xE0:
            return "audio/mpeg"
        if header.startswith(b"RIFF") and len(header) >= 12 and header[8:12] == b"WAVE":
            return "audio/wav"
        if len(header) >= 12 and header[4:8] == b"ftyp":
            brand = header[8:12]
            suffix = path.suffix.lower()
            if brand == b"M4A ":
                return "audio/mp4"
            # `isom/mp41/mp42` are common for both audio and video MP4 containers.
            # Prefer extension-based disambiguation to avoid classifying videos as audio.
            if brand in {b"isom", b"mp41", b"mp42"}:
                if suffix in {".m4a", ".aac"}:
                    return "audio/mp4"
                return "video/mp4"
            if brand in {b"qt  "}:
                return "video/quicktime"
            return "video/mp4"
        if header.startswith(b"\x1A\x45\xDF\xA3"):
            return "video/webm"
        return None

    def _extension_for_mime(self, mime):
        mime = (mime or "").lower().strip()
        mapping = {
            "image/jpeg": "jpg",
            "image/png": "png",
            "image/gif": "gif",
            "image/webp": "webp",
            "video/mp4": "mp4",
            "video/quicktime": "mov",
            "video/webm": "webm",
            "audio/mpeg": "mp3",
            "audio/mp4": "m4a",
            "audio/ogg": "ogg",
            "audio/wav": "wav",
            "application/pdf": "pdf",
        }
        if mime in mapping:
            return mapping[mime]
        guessed = mimetypes.guess_extension(mime) if mime else None
        if guessed:
            return guessed.lstrip(".")
        return None

    # ----------------------
    # Export messages as JSON
    # ----------------------
    def _export_json(self):
        json_path = self.output_folder / "chat.json"
        messages_json = []
        for msg in self.messages:
            chat_name = msg.get("chat") or self.metadata.get("chat_name")
            messages_json.append({
                "sender": msg["sender"],
                "content": msg["content"],
                "timestamp": msg["timestamp"],
                "media": msg.get("media"),
                "is_owner": msg.get("is_owner"),
                "chat": chat_name
            })
        with open(json_path, "w", encoding="utf-8") as f:
            json.dump(messages_json, f, ensure_ascii=False, indent=2)
        return json_path.name

    def _copy_logo(self):
        if not self.logo_path:
            return None
        if not self.logo_path.exists() or not self.logo_path.is_file():
            return None
        branding_dir = self.output_folder / "branding"
        branding_dir.mkdir(exist_ok=True)
        ext = self.logo_path.suffix or ".png"
        target_name = f"branding_logo{ext.lower()}"
        target = branding_dir / target_name
        shutil.copy(self.logo_path, target)
        return str(Path("branding") / target_name)

    # ----------------------
    # Export HTML
    # ----------------------
    def export_html(self, output_html_name="chat.html"):
        copied_count = self._copy_media()
        json_file = self._export_json()
        logo_file = self._copy_logo()
        generated_time = datetime.now().strftime("%Y-%m-%d %H:%M:%S")

        # ----------------------
        # Metadata header
        # ----------------------
        meta = self.metadata
        header_lines = [
            ("Report generated by", meta.get("user")),
            ("Report generated at", generated_time),
            ("Case number", meta.get("case")),
            ("Chat name", meta.get("chat_name")),
            ("Source", meta.get("source")),
            ("WhatsApp account name", meta.get("wa_account_name")),
            ("WhatsApp account number", meta.get("wa_account_number")),
            ("Telegram account name", meta.get("tg_account_name")),
            ("Wire account name", meta.get("wire_account_name")),
            ("Platform", meta.get("platform")),
            ("Media files copied", copied_count),
        ]
        header_html = ['<div class="report-header"><div class="report-grid">']
        for label, value in header_lines:
            if value is None:
                continue
            header_html.append(
                f"<div class=\"report-item\"><div class=\"report-label\">{label}</div>"
                f"<div class=\"report-value\">{value}</div></div>"
            )
        header_html.append("</div></div>")
        header_html = "\n".join(header_html)

        signature_html = (
            f'<div class="signature">Created with Bubbly v{BUBBLY_VERSION}</div>'
        )
        branding_html = ""
        if logo_file:
            branding_html = (
                '<div id="brandingLogo" class="branding-logo">'
                f'<img src="{logo_file}" alt="Brand logo">'
                "</div>"
            )

        # ----------------------
        # Load templates
        # ----------------------
        html_template = self._load_template("chat.html")
        css_content = self._load_template("style.css")
        js_content = self._load_template("chat.js")

        # ----------------------
        # Inline CSS & JS
        # ----------------------
        messages_for_html = []
        for msg in self.messages:
            chat_name = msg.get("chat") or self.metadata.get("chat_name")
            enriched = dict(msg)
            enriched["chat"] = chat_name
            messages_for_html.append(enriched)

        html_content = html_template.replace(
            '<link rel="stylesheet" href="style.css">',
            f"<style>{css_content}</style>"
        ).replace(
            '<script src="chat.js"></script>',
            f"<script>{js_content}</script>"
        ).replace(
            "{{header}}", header_html
        ).replace(
            "{{signature}}", signature_html
        ).replace(
            "{{branding_logo}}", branding_html
        ).replace(
            #"{{messages_json_path}}", json_file
            "{{messages_json_content}}", json.dumps(messages_for_html, ensure_ascii=False)
        )

        # ----------------------
        # Write final HTML
        # ----------------------
        output_html_path = self.output_folder / output_html_name
        with open(output_html_path, "w", encoding="utf-8") as f:
            f.write(html_content)

        print(f"HTML saved to {output_html_path} with inline CSS/JS")
