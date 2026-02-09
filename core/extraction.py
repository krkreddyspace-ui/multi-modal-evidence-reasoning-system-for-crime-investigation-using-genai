import os
import whisper
import pytesseract
from PIL import Image


_whisper_model = None


def load_whisper_model(model_size="base"):
    global _whisper_model
    if _whisper_model is None:
        _whisper_model = whisper.load_model(model_size)
    return _whisper_model


def extract_from_text(file_path: str) -> dict:
    with open(file_path, "r", encoding="utf-8", errors="ignore") as f:
        text = f.read()

    return {
        "modality": "text",
        "content": text.strip(),
        "metadata": {
            "source_file": file_path
        }
    }


def extract_from_image(file_path: str) -> dict:
    image = Image.open(file_path)

    # Explicit Tesseract configuration to avoid PRN device issue
    custom_config = r"--oem 3 --psm 6"

    text = pytesseract.image_to_string(image, config=custom_config)

    return {
        "modality": "image",
        "content": text.strip(),
        "metadata": {
            "source_file": file_path
        }
    }


def extract_from_audio(file_path: str) -> dict:
    model = load_whisper_model()
    result = model.transcribe(file_path)

    return {
        "modality": "audio",
        "content": result["text"].strip(),
        "metadata": {
            "language": result.get("language", "unknown"),
            "source_file": file_path
        }
    }





def extract_evidence(file_path: str) -> dict:
    ext = os.path.splitext(file_path)[1].lower()

    if ext in [".txt"]:
        return extract_from_text(file_path)

    elif ext in [".jpg", ".png", ".jpeg"]:
        return extract_from_image(file_path)

    elif ext in [".wav", ".mp3", ".m4a"]:
        return extract_from_audio(file_path)

    elif ext in [".mp4", ".avi"]:
        raise NotImplementedError("Video processing is temporarily disabled")

    else:
        raise ValueError(f"Unsupported file type: {ext}")


