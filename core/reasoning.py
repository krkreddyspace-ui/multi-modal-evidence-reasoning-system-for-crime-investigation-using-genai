# core/reasoning.py

from typing import Dict, List


# -----------------------------
# Rule-based signal extraction
# -----------------------------
def apply_rules(evidence: Dict) -> List[str]:
    """
    Applies simple rule-based checks to extracted evidence
    and returns reasoning signals.
    """
    signals = []

    text = evidence.get("content", "").lower()
    modality = evidence.get("modality", "unknown")

    if not text:
        signals.append("No textual content extracted")
        return signals

    # Basic keyword-based rules
    if "suspect" in text:
        signals.append("Suspect mentioned in evidence")

    if "saw" in text or "seen" in text:
        signals.append("Eyewitness-style statement detected")

    if any(time in text for time in ["pm", "am", "night", "morning"]):
        signals.append("Time reference detected")

    if modality == "audio":
        signals.append("Source is spoken testimony")

    if modality == "image":
        signals.append("Source is handwritten or image-based evidence")

    if modality == "text":
        signals.append("Source is textual document")

    return signals


# -----------------------------
# GenAI-style reasoning (mocked)
# -----------------------------
def genai_reason(evidence: Dict, signals: List[str]) -> Dict:
    """
    Performs reasoning over evidence using GenAI-style logic.
    (LLM integration can be added later)
    """

    decision = "Insufficient evidence"
    confidence = "Low"

    if "Suspect mentioned in evidence" in signals:
        decision = "Evidence indicates suspect involvement"
        confidence = "Medium"

    if (
        "Suspect mentioned in evidence" in signals
        and "Time reference detected" in signals
        and "Eyewitness-style statement detected" in signals
    ):
        decision = "Evidence strongly supports suspect presence at the scene"
        confidence = "High"

    return {
        "decision": decision,
        "confidence": confidence,
        "justification": signals
    }


# -----------------------------
# Main reasoning function
# -----------------------------
def reason_over_evidence(evidence: Dict) -> Dict:
    """
    Full reasoning pipeline.
    """
    signals = apply_rules(evidence)
    result = genai_reason(evidence, signals)

    return result
