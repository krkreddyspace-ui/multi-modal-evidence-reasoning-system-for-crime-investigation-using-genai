# core/correlation_engine.py

from typing import List, Dict
from collections import Counter
from datetime import datetime
from core.entity_extraction import extract_entities


WEIGHTS = {
    "suspicious_density": 3,
    "location_overlap": 2,
    "time_window": 2,
    "date_presence": 1
}


def parse_time(t: str):
    try:
        return datetime.strptime(t, "%H:%M")
    except:
        return None


def detect_time_window_overlap(times: List[str]) -> bool:
    parsed_times = [parse_time(t) for t in times if parse_time(t)]

    if len(parsed_times) < 2:
        return False

    parsed_times.sort()

    for i in range(len(parsed_times) - 1):
        diff = abs((parsed_times[i+1] - parsed_times[i]).total_seconds())
        if diff <= 3600:  # within 1 hour
            return True

    return False


def correlate_entities(evidence_results: List[Dict]) -> Dict:

    aggregated = {
        "times": [],
        "dates": [],
        "locations": [],
        "suspicious_actions": []
    }

    for result in evidence_results:
        text = result["evidence"]["content"]
        entities = extract_entities(text)

        for key in aggregated:
            aggregated[key].extend(entities[key])

    entity_counts = {
        key: Counter(aggregated[key])
        for key in aggregated
    }

    correlation_score = 0
    reasoning_signals = []

    # -------------------
    # Suspicious Density
    # -------------------
    suspicious_total = len(aggregated["suspicious_actions"])

    if suspicious_total >= 3:
        correlation_score += WEIGHTS["suspicious_density"]
        reasoning_signals.append(
            f"High suspicious activity density detected ({suspicious_total} indicators)"
        )

    # -------------------
    # Location Overlap
    # -------------------
    location_overlap = [
        item for item, count in entity_counts["locations"].items()
        if count > 1
    ]

    if location_overlap:
        correlation_score += len(location_overlap) * WEIGHTS["location_overlap"]
        reasoning_signals.append(
            f"Repeated locations detected: {location_overlap}"
        )

    # -------------------
    # Time Window Matching
    # -------------------
    if detect_time_window_overlap(aggregated["times"]):
        correlation_score += WEIGHTS["time_window"]
        reasoning_signals.append(
            "Time references fall within same incident window"
        )

    # -------------------
    # Date Presence
    # -------------------
    if len(entity_counts["dates"]) > 0:
        correlation_score += WEIGHTS["date_presence"]
        reasoning_signals.append("Date reference detected")

    return {
        "correlation_score": correlation_score,
        "entity_counts": entity_counts,
        "reasoning_signals": reasoning_signals
    }


def generate_case_decision(correlation_result: Dict) -> Dict:

    score = correlation_result["correlation_score"]

    if score >= 8:
        decision = "High likelihood of coordinated criminal activity"
        confidence = "High"
    elif score >= 4:
        decision = "Moderate cross-evidence suspicious correlation"
        confidence = "Medium"
    else:
        decision = "Low cross-evidence correlation"
        confidence = "Low"

    return {
        "final_decision": decision,
        "confidence": confidence,
        "details": correlation_result
    }


def run_case_correlation(evidence_results: List[Dict]) -> Dict:
    correlation_result = correlate_entities(evidence_results)
    return generate_case_decision(correlation_result)
