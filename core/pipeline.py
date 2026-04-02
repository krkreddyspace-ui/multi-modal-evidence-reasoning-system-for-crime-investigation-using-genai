# core/pipeline.py

from typing import Dict
import logging

from core.extraction import extract_evidence
from core.reasoning import reason_over_evidence

logger = logging.getLogger("pipeline")


def run_pipeline(file_path: str) -> Dict:
    """
    Runs the complete evidence analysis pipeline:
    extraction -> reasoning -> decision
    """

    # Step 1: Extract evidence
    logger.info("Initializing Agent [Extractor]...")
    evidence = extract_evidence(file_path)
    logger.info("Agent [Extractor] complete.")

    # Step 2: Reason over extracted evidence
    logger.info("Initializing Agent [Reasoning]...")
    decision = reason_over_evidence(evidence)
    logger.info("Agent [Reasoning] complete.")

    # Step 3: Combine results
    logger.info(f"Pipeline finished for: {file_path}")
    return {
        "evidence": evidence,
        "analysis": decision
    }
