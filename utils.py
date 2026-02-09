import zipfile
from pathlib import Path
import tempfile
import shutil

def prepare_input_generic(input_path):
    """
    Prepares input for any parser:
    - If zip: extracts to temporary folder
    - If folder: returns folder
    - If single text file: returns file parent as folder
    Returns:
        input_folder: Path to folder containing text/media
        media_folder: Path to folder containing media files (usually same as input folder)
    """
    input_path = Path(input_path).resolve()

    # Case 1: zip file
    if input_path.is_file() and input_path.suffix.lower() in {".zip", ".wbu"}:
        temp_dir = Path(tempfile.mkdtemp(prefix="bubbly_"))
        try:
            with zipfile.ZipFile(input_path, "r") as zip_ref:
                zip_ref.extractall(temp_dir)
        except zipfile.BadZipFile:
            data = input_path.read_bytes()
            sig = data.find(b"PK\x03\x04")
            if sig == -1:
                raise
            fixed_zip = temp_dir / input_path.name
            fixed_zip.write_bytes(data[sig:])
            with zipfile.ZipFile(fixed_zip, "r") as zip_ref:
                zip_ref.extractall(temp_dir)
        # Assume first folder inside zip is the chat folder
        extracted_items = list(temp_dir.iterdir())
        if len(extracted_items) == 1 and extracted_items[0].is_dir():
            input_folder = extracted_items[0]
        else:
            input_folder = temp_dir
        media_folder = input_folder
        return input_folder, media_folder

    # Case 2: folder
    elif input_path.is_dir():
        return input_path, input_path

    # Case 3: single text file
    elif input_path.is_file() and input_path.suffix.lower() == ".txt":
        return input_path.parent, input_path.parent

    else:
        raise ValueError(f"Unsupported input type: {input_path}")
