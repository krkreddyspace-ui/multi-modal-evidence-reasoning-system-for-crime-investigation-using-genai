import os
import PyPDF2
import pandas as pd
import whisper
import pytesseract
from PIL import Image
from loguru import logger


# ----------------------------------
# Whisper Model Loader (Cached)
# ----------------------------------

_whisper_model = None


def load_whisper_model(model_size="tiny"):
    global _whisper_model

    if _whisper_model is None:
        logger.info(f"<cyan>Loading Whisper model ({model_size})...</cyan>")
        try:
            _whisper_model = whisper.load_model(model_size)
            logger.success("<green>Whisper model loaded successfully.</green>")
        except Exception as e:
            logger.error(f"Failed to load Whisper model: {e}")
            raise RuntimeError(f"Failed to load Whisper model: {e}")

    return _whisper_model


# ----------------------------------
# TEXT EXTRACTION
# ----------------------------------

def extract_from_text(file_path: str) -> dict:
    logger.info(f"MODALITY [TEXT] -> Processing: {os.path.basename(file_path)}")
    try:
        with open(file_path, "r", encoding="utf-8", errors="ignore") as f:
            text = f.read()

        logger.debug(f"Read {len(text)} characters from text file.")
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
    logger.info(f"MODALITY [IMAGE] -> Processing: {os.path.basename(file_path)}")
    try:
        image = Image.open(file_path)
        logger.debug(f"Image opened: {image.size} {image.format}")

        custom_config = r"--oem 3 --psm 6"
        logger.info("Running Tesseract OCR engine...")
        text = pytesseract.image_to_string(image, config=custom_config)

        logger.debug(f"OCR Complete. Extracted {len(text)} characters.")
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
    logger.info(f"MODALITY [PDF] -> Processing: {os.path.basename(file_path)}")
    text = ""
    try:
        with open(file_path, "rb") as file:
            reader = PyPDF2.PdfReader(file)
            num_pages = len(reader.pages)
            logger.debug(f"PDF contains {num_pages} pages.")

            for i, page in enumerate(reader.pages):
                logger.debug(f"Extracting text from page {i+1}/{num_pages}...")
                page_text = page.extract_text()
                if page_text:
                    text += page_text

        logger.info(f"PDF Extraction complete. Total characters: {len(text)}")
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
    logger.info(f"MODALITY [CSV] -> Processing: {os.path.basename(file_path)}")
    try:
        df = pd.read_csv(file_path)
        logger.debug(f"CSV Loaded. Shape: {df.shape}")

        text_representation = ""
        for index, row in df.iterrows():
            row_text = ", ".join([f"{col}: {row[col]}" for col in df.columns])
            text_representation += row_text + "\n"

        logger.info(f"CSV Flattened. Extracted {len(text_representation)} characters.")
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
    logger.info(f"MODALITY [AUDIO] -> Processing: {os.path.basename(file_path)}")
    try:
        if not os.path.exists(file_path):
            logger.warning(f"Audio file missing: {file_path}")
            return {
                "modality": "audio",
                "content": "Audio file not found",
                "metadata": {"source_file": file_path}
            }

        if os.path.getsize(file_path) == 0:
            logger.warning(f"Audio file is empty: {file_path}")
            return {
                "modality": "audio",
                "content": "Audio file is empty",
                "metadata": {"source_file": file_path}
            }

        model = load_whisper_model()
        logger.info("Initializing transcription via Whisper...")
        result = model.transcribe(file_path)

        text = result.get("text", "").strip()
        if text == "":
            logger.warning("No speech detected in audio file.")
            text = "No speech detected"

        logger.success(f"Transcription complete. Language: {result.get('language')}")
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
    logger.info(f"Routing file: <cyan>{os.path.basename(file_path)}</cyan>")

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