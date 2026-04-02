# core/entity_extraction.py

import re
from typing import Dict, List


TIME_PATTERN = r"\b\d{1,2}:\d{2}\b"
DATE_PATTERN = r"\b\d{1,2}[/-]\d{1,2}[/-]\d{2,4}\b"

LOCATION_KEYWORDS = [
    "street", "avenue", "road", "crossing",
    "apartment", "building", "warehouse",
    "station", "highway", "market"
]

SUSPICIOUS_ACTIONS = [
    "rob", "steal", "attack", "hit",
    "cut", "masked", "flee", "block",
    "threat", "illegal", "weapon",
    "unconscious", "escape"
]


def extract_entities(text: str) -> Dict:
    text_lower = text.lower()

    # Time detection
    times = re.findall(TIME_PATTERN, text_lower)
    dates = re.findall(DATE_PATTERN, text_lower)

    # Location detection (keyword-based)
    locations = [word for word in LOCATION_KEYWORDS if word in text_lower]

    # Suspicious action detection
    suspicious = [word for word in SUSPICIOUS_ACTIONS if word in text_lower]

    return {
        "times": times,
        "dates": dates,
        "locations": locations,
        "suspicious_actions": suspicious
    }
