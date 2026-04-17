import ollama
from core.correlation_engine import run_case_correlation




# Use sample input
sample_input = [
    {
        "evidence": {
            "content": "Suspicious meeting at 14:30 near Warehouse A on 12/02/2026 involving weapon exchange"
        }
    },
    {
        "evidence": {
            "content": "Another activity at 15:00 near Warehouse A with illegal transaction"
        }
    }
]


symbolic_output = run_case_correlation(sample_input)

system_prompt = """
You are a forensic AI.
Return ONLY valid JSON.
No explanations.
"""

user_prompt = f"""
Based on this symbolic output:

{symbolic_output}

Generate JSON with exactly this structure:

{{
  "risk_level": "Low | Moderate | High",
  "reasoning_summary": "single concise paragraph",
  "confidence_score": float between 0 and 1
}}

Rules:
- reasoning_summary must be a single string (not a list)
- confidence_score must be decimal like 0.75
- No extra fields
- Output valid JSON only

"""

response = ollama.chat(
    model="llama3",
    messages=[
        {"role": "system", "content": system_prompt},
        {"role": "user", "content": user_prompt}
    ],
    options={"temperature": 0.2}
)

print(response["message"]["content"])
