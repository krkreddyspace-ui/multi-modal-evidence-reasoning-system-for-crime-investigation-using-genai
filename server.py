import os
import re
import sys
import time
import asyncio
from concurrent.futures import ThreadPoolExecutor
from fastapi import FastAPI, UploadFile, File
from fastapi.responses import JSONResponse, RedirectResponse, Response
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles
from typing import List
import ollama
from loguru import logger
import plotext as plt

from core.extraction import extract_evidence

# Configure Loguru with a professional forensic theme
logger.remove()
logger.add(sys.stderr, format="<green>{time:YYYY-MM-DD HH:mm:ss}</green> | <level>{level: <8}</level> | <cyan>{name}</cyan>:<cyan>{function}</cyan>:<cyan>{line}</cyan> - <level>{message}</level>")

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

# Thread pool for concurrent file extraction
_executor = ThreadPoolExecutor(max_workers=4)

def _extract_single_file(path, filename, file_size_kb, content_type):
    """Worker function to extract evidence from a single file (runs in thread)."""
    file_start = time.time()
    evidence = extract_evidence(path)
    file_elapsed = round(time.time() - file_start, 3)
    
    # Determine content type manually if missing
    ctype = content_type if content_type else "unknown"
    if not content_type:
        ext = str(filename).split('.')[-1].lower()
        if ext in ['png','jpg','jpeg']: ctype = f"image/{ext}"
        elif ext in ['wav','mp3']: ctype = f"audio/{ext}"
        elif ext == 'pdf': ctype = "application/pdf"
        elif ext in ['txt','csv']: ctype = f"text/{ext}"
    
    logger.success(f"Successfully processed modality: [cyan]{ctype}[/cyan] in {file_elapsed}s")
    
    result = {
        "evidence": evidence,
        "file_name": filename,
        "file_type": ctype
    }
    
    timing = {
        "file_name": filename,
        "processing_time_sec": file_elapsed,
        "file_size_kb": file_size_kb,
        "modality": ctype.split("/")[0].upper() if "/" in ctype else ctype.upper()
    }
    
    return result, timing

@app.post("/api/analyze")
async def analyze_evidence(files: List[UploadFile] = File(...)):
    pipeline_start = time.time()
    logger.info(f"--- <magenta>INTAKE INITIATED</magenta>: [ {len(files)} ] Evidence Files Received ---")
    
    # Phase 1: Save all files to disk first
    file_infos = []
    for i, file in enumerate(files):
        logger.info(f"Receiving File [{i+1}/{len(files)}]: [yellow]{file.filename}[/yellow]")
        path = os.path.join("data/raw", file.filename)
        content = await file.read()
        file_size_kb = round(len(content) / 1024, 2)
        with open(path, "wb") as f:
            f.write(content)
        logger.debug(f"File saved to disk: {path}")
        file_infos.append((path, file.filename, file_size_kb, file.content_type))
    
    # Phase 2: Process all files concurrently using thread pool
    logger.info(f"Launching concurrent extraction for {len(file_infos)} files...")
    loop = asyncio.get_event_loop()
    futures = [
        loop.run_in_executor(_executor, _extract_single_file, path, fname, fsize, ctype)
        for path, fname, fsize, ctype in file_infos
    ]
    extraction_results = await asyncio.gather(*futures)
    
    results = []
    per_file_timings = []
    for result, timing in extraction_results:
        results.append(result)
        per_file_timings.append(timing)

    all_text = ""
    for r in results:
        content = r.get("evidence", {}).get("content", "")
        if content:
            all_text += "\n" + clean_text(content)

    # Cap context length to speed up LLM processing significantly
    all_text = all_text[:6000]

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

    logger.info("Initializing <bold>[Agent: Reasoner]</bold>... Handing off extracted corpus to Llama 3.")
    reasoning_start = time.time()
    try:
        response = ollama.chat(
            model="llama3",
            messages=[{"role": "user", "content": prompt}],
            options={"temperature": 0.2, "num_predict": 400}
        )
        result_text = response["message"]["content"]
        logger.success("AI Reasoning block received from Llama 3.")
    except Exception as e:
        logger.error(f"Error communicating with Ollama: {e}")
        result_text = f"Error communicating with AI model: {str(e)}"
    reasoning_elapsed = round(time.time() - reasoning_start, 3)

    sections = parse_output(result_text)
    
    # Override confidence with our deterministic score
    sections["confidence"] = calculate_confidence_score(results, all_text)

    # --- ADVANCED TERMINAL ANALYTICS REPORT ---
    try:
        conf_value = int(sections["confidence"].replace("%", ""))
        
        print("\n" + "═"*60)
        print(" " * 15 + "📊 <cyan>FORENSIC ANALYTICS DASHBOARD</cyan>")
        print("═"*60)
        
        # 1. Confidence Gauge (Deterministic ASCII)
        bar_len = 40
        filled_len = int(bar_len * conf_value / 100)
        bar = "█" * filled_len + "░" * (bar_len - filled_len)
        color = "green" if conf_value > 70 else "yellow" if conf_value > 40 else "red"
        print(f"\n <bold>CONFIDENCE SCORE</bold>: [{bar}] <{color}>{conf_value}%</{color}>")
        
        # 2. Modality Distribution Bar Chart
        modality_counts = {}
        for r in results:
            ctype = r.get("file_type", "unknown").split("/")[0].upper()
            modality_counts[ctype] = modality_counts.get(ctype, 0) + 1
        
        if modality_counts:
            print("\n <bold>EVIDENCE MODALITY DISTRIBUTION</bold>:")
            plt.clf()
            plt.bar(list(modality_counts.keys()), list(modality_counts.values()), color="cyan")
            plt.plotsize(60, 12)
            plt.theme("dark")
            plt.show()
            
        # 3. Risk Factor Category Analysis
        risk_keywords = {
            "HACKING": ["hack", "access", "log", "delete", "root", "unauthorized"],
            "FRAUD": ["transaction", "money", "transfer", "bribe", "bank", "account"],
            "VIOLENT": ["kill", "murder", "weapon", "blood", "threat", "gun"],
            "GUILT": ["confess", "admit", "sorry", "guilty", "own", "mistake"]
        }
        
        category_hits = {}
        text_lower = all_text.lower()
        for cat, kws in risk_keywords.items():
            hits = sum(1 for kw in kws if kw in text_lower)
            if hits > 0:
                category_hits[cat] = hits
                
        if category_hits:
            print("\n <bold>RISK FACTOR INTENSITY</bold>:")
            # Sort by hits descending
            sorted_hits = dict(sorted(category_hits.items(), key=lambda item: item[1], reverse=True))
            plt.clf()
            plt.bar(list(sorted_hits.keys()), list(sorted_hits.values()), color="magenta")
            plt.plotsize(60, 10)
            plt.theme("dark")
            plt.show()

    except Exception as e:
        logger.warning(f"Terminal graph rendering failed: {e}")

    # --- FINAL TERMINAL REPORT (The "Editor" request) ---
    print("\n" + "="*60)
    print("       FORENSIC INVESTIGATION SUMMARY REPORT")
    print("="*60)
    print(f" IDENTIFIED CULPRIT  : {sections['culprit']}")
    print(f" CONFIDENCE LEVEL    : {sections['confidence']}")
    print("-" * 60)
    print(" REASONING PREVIEW:")
    # Print first 200 chars of reasoning
    reason_snipped = sections['reasoning'][:300] + "..." if len(sections['reasoning']) > 300 else sections['reasoning']
    print(reason_snipped)
    print("="*60 + "\n")

    logger.info(f"Analysis complete. Identified Culprit: [magenta]{sections['culprit']}[/magenta]")

    # --- Build Analytics Payload for Frontend Graphs ---
    total_pipeline_time = round(time.time() - pipeline_start, 3)
    extraction_time = round(sum(t["processing_time_sec"] for t in per_file_timings), 3)
    
    # Modality distribution counts
    modality_counts = {}
    for r in results:
        ctype = r.get("file_type", "unknown").split("/")[0].upper()
        modality_counts[ctype] = modality_counts.get(ctype, 0) + 1
    
    # Risk category analysis
    risk_keywords = {
        "HACKING": ["hack", "access", "log", "delete", "root", "unauthorized"],
        "FRAUD": ["transaction", "money", "transfer", "bribe", "bank", "account"],
        "VIOLENT": ["kill", "murder", "weapon", "blood", "threat", "gun"],
        "GUILT": ["confess", "admit", "sorry", "guilty", "own", "mistake"],
        "IDENTITY": ["name", "alias", "address", "phone", "email", "id"],
        "DIGITAL": ["ip", "server", "database", "encrypt", "password", "cyber"]
    }
    
    text_lower = all_text.lower()
    risk_scores = {}
    keyword_hits = {}
    for cat, kws in risk_keywords.items():
        hits = sum(1 for kw in kws if kw in text_lower)
        if hits > 0:
            risk_scores[cat] = hits
        # Also track individual keyword hits
        for kw in kws:
            if kw in text_lower:
                keyword_hits[kw] = keyword_hits.get(kw, 0) + text_lower.count(kw)
    
    # Sort keyword hits descending and take top 12
    top_keywords = dict(sorted(keyword_hits.items(), key=lambda x: x[1], reverse=True)[:12])
    
    # Evidence content lengths for each modality (text richness)
    content_lengths = []
    for r in results:
        content = r.get("evidence", {}).get("content", "")
        content_lengths.append({
            "file_name": r.get("file_name", "unknown"),
            "char_count": len(content),
            "modality": r.get("file_type", "unknown").split("/")[0].upper()
        })

    analytics = {
        "timing": {
            "total_pipeline_sec": total_pipeline_time,
            "extraction_sec": extraction_time,
            "reasoning_sec": reasoning_elapsed,
            "per_file": per_file_timings
        },
        "modality_distribution": modality_counts,
        "risk_categories": risk_scores,
        "keyword_hits": top_keywords,
        "content_richness": content_lengths,
        "confidence_value": int(sections["confidence"].replace("%", "")),
        "total_files": len(results),
        "total_chars_extracted": len(all_text)
    }

    return JSONResponse(content={
        "summary": sections,
        "raw_evidence": results,
        "analytics": analytics
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
