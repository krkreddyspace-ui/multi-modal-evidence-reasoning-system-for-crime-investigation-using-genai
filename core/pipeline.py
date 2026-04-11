from typing import Dict
from loguru import logger

from core.extraction import extract_evidence
from core.reasoning import reason_over_evidence

# logger = logging.getLogger("pipeline") # Removed in favor of loguru


def run_pipeline(file_path: str) -> Dict:
    """
    Runs the complete evidence analysis pipeline:
    extraction -> reasoning -> decision
    """
    filename = file_path.split('/')[-1]
    logger.info(f"--- Starting Pipeline for: <yellow>{filename}</yellow> ---")

    # Step 1: Extract evidence
    logger.info("Initializing <bold>[Agent: Extractor]</bold>...")
    evidence = extract_evidence(file_path)
    logger.success("<green>Agent [Extractor] extraction complete.</green>")

    # Step 2: Reason over extracted evidence
    logger.info("Initializing <bold>[Agent: Reasoning]</bold>...")
    decision = reason_over_evidence(evidence)
    logger.success("<green>Agent [Reasoning] analysis complete.</green>")

    # Step 3: Combine results
    logger.info(f"Pipeline finished for: {filename}")
    return {
        "evidence": evidence,
        "analysis": decision
    }
