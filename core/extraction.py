import os
import PyPDF2
import pandas as pd
import whisper
import pytesseract
from PIL import Image


# ----------------------------------
# Whisper Model Loader (Cached)
# ----------------------------------

_whisper_model = None


def load_whisper_model(model_size="base"):
    global _whisper_model

    if _whisper_model is None:
        try:
            _whisper_model = whisper.load_model(model_size)
        except Exception as e:
            raise RuntimeError(f"Failed to load Whisper model: {e}")

    return _whisper_model


# ----------------------------------
# TEXT EXTRACTION
# ----------------------------------

def extract_from_text(file_path: str) -> dict:
    try:
        with open(file_path, "r", encoding="utf-8", errors="ignore") as f:
            text = f.read()

        return {
            "modality": "text",
            "content": text.strip(),
            "metadata": {"source_file": file_path}
        }

    except Exception as e:
        return {
            "modality": "text",
            "content": "",
            "metadata": {"error": str(e), "source_file": file_path}
        }


# ----------------------------------
# IMAGE OCR
# ----------------------------------

def extract_from_image(file_path: str) -> dict:

    try:
        image = Image.open(file_path)

        custom_config = r"--oem 3 --psm 6"

        text = pytesseract.image_to_string(image, config=custom_config)

        return {
            "modality": "image",
            "content": text.strip(),
            "metadata": {"source_file": file_path}
        }

    except Exception as e:

        return {
            "modality": "image",
            "content": "",
            "metadata": {"error": str(e), "source_file": file_path}
        }


# ----------------------------------
# PDF EXTRACTION
# ----------------------------------

def extract_from_pdf(file_path: str) -> dict:

    text = ""

    try:

        with open(file_path, "rb") as file:

            reader = PyPDF2.PdfReader(file)

            for page in reader.pages:

                page_text = page.extract_text()

                if page_text:
                    text += page_text

        return {
            "modality": "pdf",
            "content": text.strip(),
            "metadata": {"source_file": file_path}
        }

    except Exception as e:

        return {
            "modality": "pdf",
            "content": "",
            "metadata": {"error": str(e), "source_file": file_path}
        }


# ----------------------------------
# CSV EXTRACTION
# ----------------------------------

def extract_from_csv(file_path: str) -> dict:

    try:

        df = pd.read_csv(file_path)

        text_representation = ""

        for index, row in df.iterrows():
            row_text = ", ".join([f"{col}: {row[col]}" for col in df.columns])
            text_representation += row_text + "\n"

        return {
            "modality": "csv",
            "content": text_representation.strip(),
            "metadata": {
                "rows": len(df),
                "columns": list(df.columns),
                "source_file": file_path
            }
        }

    except Exception as e:

        return {
            "modality": "csv",
            "content": "",
            "metadata": {"error": str(e), "source_file": file_path}
        }


# ----------------------------------
# AUDIO TRANSCRIPTION (SAFE)
# ----------------------------------

def extract_from_audio(file_path: str) -> dict:

    try:

        if not os.path.exists(file_path):
            return {
                "modality": "audio",
                "content": "Audio file not found",
                "metadata": {"source_file": file_path}
            }

        if os.path.getsize(file_path) == 0:
            return {
                "modality": "audio",
                "content": "Audio file is empty",
                "metadata": {"source_file": file_path}
            }

        model = load_whisper_model()

        result = model.transcribe(file_path)

        text = result.get("text", "").strip()

        if text == "":
            text = "No speech detected"

        return {
            "modality": "audio",
            "content": text,
            "metadata": {
                "language": result.get("language", "unknown"),
                "source_file": file_path
            }
        }

    except Exception as e:

        return {
            "modality": "audio",
            "content": "Audio transcription failed",
            "metadata": {"error": str(e), "source_file": file_path}
        }


# ----------------------------------
# MAIN EVIDENCE ROUTER
# ----------------------------------

def extract_evidence(file_path: str) -> dict:

    ext = os.path.splitext(file_path)[1].lower()

    if ext == ".txt":
        return extract_from_text(file_path)

    elif ext in [".jpg", ".png", ".jpeg"]:
        return extract_from_image(file_path)

    elif ext in [".wav", ".mp3", ".m4a"]:
        return extract_from_audio(file_path)

    elif ext == ".pdf":
        return extract_from_pdf(file_path)

    elif ext == ".csv":
        return extract_from_csv(file_path)

    elif ext in [".mp4", ".avi"]:
        return {
             "modality": "video",
             "content": "Video processing is temporarily disabled.",
             "metadata": {"error": "NotImplementedError", "source_file": file_path}
        }

    else:
        # Fallback for code/log files that can be read as text
        if ext in [".json", ".md", ".xml", ".log", ".html"]:
            return extract_from_text(file_path)
            
        return {
             "modality": "unknown",
             "content": f"Unsupported file type: {ext}. Could not extract text.",
             "metadata": {"error": "Unsupported file type", "source_file": file_path}
        }