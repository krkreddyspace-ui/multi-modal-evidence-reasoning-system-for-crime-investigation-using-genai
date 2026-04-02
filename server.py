import os
import re
import logging
from fastapi import FastAPI, UploadFile, File
from fastapi.responses import JSONResponse, RedirectResponse, Response
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles
from typing import List
import ollama

from core.pipeline import run_pipeline

logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(name)s - %(levelname)s - %(message)s')
logger = logging.getLogger("server")

app = FastAPI(title="AI Crime Investigation API")

# Mount static files to serve the frontend and media assets
os.makedirs("frontend", exist_ok=True)
os.makedirs("data/raw", exist_ok=True)

# CORS config
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

def clean_text(text):
    text = re.sub(r"[^a-zA-Z0-9₹.,:@\n ]", " ", text)
    text = re.sub(r"\s+", " ", text)
    return text.strip()

def calculate_confidence_score(results, all_text):
    score = 50  # Increased Base Score from 20 to 50
    
    # Diversity Bonus
    unique_types = set()
    for r in results:
        ctype = r.get("file_type", "")
        if "audio" in ctype: unique_types.add("audio")
        elif "image" in ctype: unique_types.add("image")
        elif "pdf" in ctype or "text" in ctype: unique_types.add("text")
    
    score += min(30, len(unique_types) * 15)  # Increased from 10 to 15 per type
    
    text_lower = all_text.lower()
    
    # High-impact keywords
    high_keywords = ["confess", "kill", "murder", "stole", "bribe", "admit", "hacked", "guilty", "blood", "weapon"]
    high_matches = sum(1 for kw in high_keywords if kw in text_lower)
    score += min(30, high_matches * 20)  # Increased from 15 to 20 per match
    
    # Medium-impact keywords
    medium_keywords = ["threat", "fraud", "illegal", "secret", "suspicious", "transfer", "log", "deleted", "transaction", "access"]
    med_matches = sum(1 for kw in medium_keywords if kw in text_lower)
    score += min(20, med_matches * 10)  # Increased from 5 to 10 per match
    
    score = min(98, score) # Cap at 98%
    return f"{score}%"

def parse_output(text):
    text = text.replace("**", "")  

    sections = {
        "culprit": "Not Detected",
        "confidence": "N/A",
        "evidence": "Not Available",
        "reasoning": "Not Available",
        "eliminated": "Not Available"
    }

    try:
        # 1. Standard Match
        c = re.search(r"(?:Culprit|Suspect|Most Likely Culprit)[^\n:]*:\s*([^\n]+)", text, re.IGNORECASE)
        if c: 
            sections["culprit"] = c.group(1).strip()
            
        # 2. Fallback: Check if it was pushed to the next line
        if sections["culprit"] == "Not Detected" or "[" in sections["culprit"] or "goes here" in sections["culprit"]:
            c_fallback = re.search(r"(?:Culprit|Suspect)[^\n:]*:\s*\n+\s*([^\n]+)", text, re.IGNORECASE)
            if c_fallback: 
                sections["culprit"] = c_fallback.group(1).strip()

        # 3. Extreme Fallback: Grab the block before Key Evidence and extract the last meaningful line
        if sections["culprit"] == "Not Detected":
            before_ev = re.search(r"^(.*?)(?:Key Evidence|Evidence):", text, re.S | re.IGNORECASE)
            if before_ev:
                chunk = before_ev.group(1).strip()
                # Clean up intro text
                chunk = re.sub(r'(?i)(output format:?|the most likely culprit is|based on the evidence,?)', '', chunk)
                lines = [l.strip() for l in chunk.split('\n') if len(l.strip()) > 2]
                if lines:
                    sections["culprit"] = lines[-1]

        # Clean off any literal brackets the AI might have repeated
        sections["culprit"] = re.sub(r'\[.*?\]|<.*?>', '', sections["culprit"]).strip()

        ev = re.search(r"Key Evidence:(.*?)(Reasoning:)", text, re.S | re.IGNORECASE)
        if ev: sections["evidence"] = ev.group(1).strip()

        r = re.search(r"Reasoning:(.*?)(Eliminated Suspects:)", text, re.S | re.IGNORECASE)
        if r: sections["reasoning"] = r.group(1).strip()

        el = re.search(r"Eliminated Suspects:(.*)", text, re.S | re.IGNORECASE)
        if el: sections["eliminated"] = el.group(1).strip()

    except:
        pass

    return sections

@app.post("/api/analyze")
async def analyze_evidence(files: List[UploadFile] = File(...)):
    logger.info(f"Received request to analyze {len(files)} files.")
    results = []
    
    for file in files:
        path = os.path.join("data/raw", file.filename)
        # Read file contents and save
        content = await file.read()
        with open(path, "wb") as f:
            f.write(content)
            
        result = run_pipeline(path)
        result["file_name"] = file.filename
        
        # Determine content type manually if missing from UploadFile obj
        ctype = file.content_type if file.content_type else "unknown"
        if not file.content_type:
            ext = str(file.filename).split('.')[-1].lower()
            if ext in ['png','jpg','jpeg']: ctype = f"image/{ext}"
            elif ext in ['wav','mp3']: ctype = f"audio/{ext}"
            elif ext == 'pdf': ctype = "application/pdf"
            elif ext in ['txt','csv']: ctype = f"text/{ext}"
            
        result["file_type"] = ctype
        logger.info(f"Finished processing file: {file.filename} (Type: {ctype})")
        results.append(result)

    all_text = ""
    for r in results:
        content = r.get("evidence", {}).get("content", "")
        if content:
            all_text += "\n" + clean_text(content)

    prompt = f"""
You are an expert digital forensic investigator.

Analyze the following MULTI-MODAL evidence and identify the MOST LIKELY CULPRIT.

IMPORTANT:
- You MUST identify a culprit
- Do NOT say "insufficient data"
- Ignore OCR errors and noisy text
- Focus on meaningful signals
- Perform cross-evidence reasoning

PRIORITY ORDER:
1. Audio confession
2. System logs
3. Financial transactions
4. Access control
5. Chats and emails

EVIDENCE:
{all_text}

OUTPUT FORMAT EXACT HEADINGS:

Culprit: Name goes here

Key Evidence:
- bullet points

Reasoning:
- clear logical explanation

Eliminated Suspects:
- Name → reason
"""

    logger.info("Sending extracted evidence block to Llama 3 for reasoning...")
    try:
        response = ollama.chat(
            model="llama3",
            messages=[{"role": "user", "content": prompt}],
            options={"temperature": 0.2}
        )
        result_text = response["message"]["content"]
    except Exception as e:
        print(f"Error communicating with Ollama: {e}")
        result_text = f"Error communicating with AI model: {str(e)}"

    print(f"\n--- LLM RAW OUTPUT ---\n{result_text}\n----------------------\n")

    sections = parse_output(result_text)
    
    # Override confidence with our deterministic score
    sections["confidence"] = calculate_confidence_score(results, all_text)

    logger.info(f"Analysis complete. Identified Culprit: {sections['culprit']}")

    return JSONResponse(content={
        "summary": sections,
        "raw_evidence": results
    })

# Mount endpoints AFTER all route definitions to avoid catching /api calls
app.mount("/data/raw", StaticFiles(directory="data/raw"), name="raw_data")
app.mount("/frontend", StaticFiles(directory="frontend", html=True), name="frontend")

@app.get("/")
def redirect_to_frontend():
    return RedirectResponse(url="/frontend/index.html")

@app.get("/favicon.ico", include_in_schema=False)
async def favicon():
    return Response(status_code=204)

if __name__ == "__main__":
    import uvicorn
    uvicorn.run("server:app", host="0.0.0.0", port=8000, reload=True)
