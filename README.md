# Cyber-Neural Forensic Dashboard & GenAI Evidence Reasoning System

**Multi-Modal Evidence Reasoning System for Crime Investigation Using GenAI**

An intelligent and highly concurrent local Generative AI system that ingests diverse digital evidence (documents, images, raw texts, logs, and audio) to reconstruct timelines, detect inconsistencies, generate scenarios, and provide deterministic, evidence-based conclusions for crime investigation.

---

## 📌 What the Project Does

Modern cyber-crimes and complex physical evidence trails require correlating massively unstructured data formats. This pipeline acts as a digital detective assistant:
- **Correlates Disparate Formats:** Fuses data from audio confessions, server logs, financial transactions, chats, and image/document content.
- **Identifies Culprits:** Uses AI reasoning to point out the most likely suspect based on weighted clues across multiple files.
- **Explains Reasoning:** Instead of just guessing, the LLM provides bullet-proof "Key Evidence" points, deep logical explanations, and justifies eliminating other suspects.
- **Visualizes Analytics:** Translates text data into comprehensive visual insights both in the terminal (via ASCII charts) and on a rich web-based frontend dashboard.

---

## ⚙️ How It Does It (The Workflow)

1. **Multi-Modal Intake & Storage:** Investigators upload a batch of raw evidence files through the FastAPI endpoints. Files are mapped to specific parsers based on extension (`.txt`, `.csv`, `.pdf`, `.wav`, `.jpg`, etc.).
2. **Concurrent Text Extraction:** To drastically reduce loading times, a ThreadPoolExecutor concurrent pipeline processes multiple heavy files at once (e.g., using Whisper for Audio transcription, Tesseract for OCR).
3. **Cross-Evidence Reasoning Engine (LLM):** All extracted context is bundled (up to specific token limits) and passed to a locally hosted **Llama 3** agent through **Ollama**. The system uses a strict forensic persona prompt enforcing deterministic extraction.
4. **Deterministic Auditing & Scoring:** LLM outputs are prone to hallucinations, so this system runs a secondary heuristic scoring pass. It measures confidence directly based on modal diversity and the presence of high-risk keywords (e.g. "bribe", "murder", "transaction") to guarantee transparent score generation. 
5. **Data Visualization:** The results are rendered securely to a full HTML/JS/CSS client-side dashboard offering insights like Modality Spread, Risk Factors, and Text Richness, while simultaneously throwing visual, dynamic `plotext` graphs into the server terminal.

---

## 🛠️ Technologies Used

### Core Framework & Backend
* **Python 3.10+** - Core data manipulation layer
* **FastAPI & Uvicorn** - High-performance asynchronous API
* **Loguru** - Advanced CLI pipeline logging

### AI & Machine Learning
* **Ollama (Llama 3)** - Local LLM deployment for privacy-safe criminal reasoning
* **OpenAI Whisper** - Advanced audio transcription directly from evidence media
* **OpenCV & PyTesseract** - Optical Character Recognition for image & PDF processing
* **NLP Stacks** - Space, SentencePiece, HuggingFace Transformers (available for future embeddings tracking)

### Data Handling & Visualization 
* **Pandas & NumPy** - Preprocessing tabular logs and datasets
* **Plotext** - Terminal-based charting for real-time backend visibility
* **HTML5/Vanilla JS/Vanilla CSS** - Fully custom investigative UI (Chart.js compliant via API responses)

---

## 🚀 Getting Started

### 1. Prerequisites
- [Python 3.10+](https://www.python.org/)
- [Ollama](https://ollama.com/) installed and running locally.
- Tesseract-OCR installed on your system (added to PATH for image extraction).

### 2. Setup the Environment
```bash
# Clone the repository
git clone <your-repo-url>
cd multi-modal-evidence-reasoning-system-for-crime-investigation-using-genai

# Create a virtual environment and activate it
python -m venv venv
source venv/bin/activate  # On Windows use: venv\Scripts\activate

# Install dependencies
pip install -r requirements.txt
```

### 3. Initialize AI Models
Make sure your Ollama daemon is running, then pull the required Llama engine:
```bash
ollama pull llama3
```

### 4. Run the Pipeline
```bash
python server.py
```

The unified interface will now be available at: **http://localhost:8000**
You can interact with the API endpoints natively via **http://localhost:8000/docs**
