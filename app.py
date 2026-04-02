import streamlit as st
import os
import re
import ollama

from core.pipeline import run_pipeline

os.makedirs("data/raw", exist_ok=True)

st.set_page_config(
    page_title="AI Crime Investigation Dashboard",
    page_icon="🚔",
    layout="wide"
)

# -------------------------------
# 🎨 CUSTOM CSS
# -------------------------------
st.markdown("""
<style>
.main {
    background-color: #0E1117;
}
.block-container {
    padding-top: 2rem;
}

.card {
    background: #161B22;
    padding: 20px;
    border-radius: 12px;
    border: 1px solid #30363D;
    margin-bottom: 20px;
    box-shadow: 0px 4px 10px rgba(0,0,0,0.4);
}

.card-title {
    font-size: 1rem;
    color: #8B949E;
    margin-bottom: 5px;
}

.card-value {
    font-size: 1.6rem;
    font-weight: bold;
}

.success {
    color: #3FB950;
}

.warning {
    color: #F85149;
}

.section-title {
    font-size: 1.3rem;
    margin-top: 25px;
    margin-bottom: 10px;
    font-weight: 600;
}
</style>
""", unsafe_allow_html=True)

# -------------------------------
# HEADER
# -------------------------------
st.title("🚔 AI Crime Investigation Dashboard")
st.markdown("*AI-powered multi-modal evidence reasoning system*")
st.divider()

# -------------------------------
# CLEAN TEXT
# -------------------------------
def clean_text(text):
    text = re.sub(r"[^a-zA-Z0-9₹.,:@\n ]", " ", text)
    text = re.sub(r"\s+", " ", text)
    return text.strip()

# -------------------------------
# PARSE OUTPUT
# -------------------------------
def parse_output(text):
    text = text.replace("**", "")  # remove markdown noise

    sections = {
        "culprit": "Not Detected",
        "confidence": "N/A",
        "evidence": "Not Available",
        "reasoning": "Not Available",
        "eliminated": "Not Available"
    }

    try:
        c = re.search(r"Culprit:\s*(.*)", text)
        if c: sections["culprit"] = c.group(1).strip()

        conf = re.search(r"Confidence.*?(\d+%)", text)
        if conf: sections["confidence"] = conf.group(1)

        ev = re.search(r"Key Evidence:(.*?)(Reasoning:)", text, re.S)
        if ev: sections["evidence"] = ev.group(1).strip()

        r = re.search(r"Reasoning:(.*?)(Eliminated Suspects:)", text, re.S)
        if r: sections["reasoning"] = r.group(1).strip()

        el = re.search(r"Eliminated Suspects:(.*)", text, re.S)
        if el: sections["eliminated"] = el.group(1).strip()

    except:
        pass

    return sections

# -------------------------------
# SIDEBAR
# -------------------------------
with st.sidebar:
    st.header("📂 Evidence Input")
    uploaded_files = st.file_uploader(
        "Upload Evidence Files",
        type=["txt", "png", "jpg", "jpeg", "wav", "mp3", "pdf", "csv"],
        accept_multiple_files=True
    )
    analyze_btn = st.button("🔍 Analyze Evidence", use_container_width=True)

# -------------------------------
# MAIN
# -------------------------------
if uploaded_files and analyze_btn:

    results = []

    with st.spinner("Processing evidence..."):
        for file in uploaded_files:
            path = os.path.join("data/raw", file.name)
            with open(path, "wb") as f:
                f.write(file.getbuffer())

            result = run_pipeline(path)
            result["file_name"] = file.name
            result["file_type"] = file.type
            results.append(result)

    st.sidebar.success("✅ Evidence processed")

    # -------------------------------
    # COMBINE EVIDENCE
    # -------------------------------
    all_text = ""
    for r in results:
        content = r["evidence"].get("content", "")
        all_text += "\n" + clean_text(content)

    # -------------------------------
    # PROMPT
    # -------------------------------
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

OUTPUT FORMAT:

Culprit:
Confidence (0-100%):

Key Evidence:
- bullet points

Reasoning:
- clear logical explanation

Eliminated Suspects:
- Name → reason
"""

    # -------------------------------
    # LLM CALL
    # -------------------------------
    with st.spinner("Analyzing case with AI..."):
        try:
            response = ollama.chat(
                model="llama3",
                messages=[{"role": "user", "content": prompt}],
                options={"temperature": 0.2}
            )
            result_text = response["message"]["content"]

        except Exception as e:
            st.error(f"Error: {e}")
            result_text = ""

    sections = parse_output(result_text)

    # -------------------------------
    # SUMMARY
    # -------------------------------
    st.markdown("## 📊 Investigation Summary")

    col1, col2 = st.columns(2)

    with col1:
        st.markdown(f"""
        <div class="card">
            <div class="card-title">🚨 Culprit</div>
            <div class="card-value warning">🚨 {sections['culprit']}</div>
        </div>
        """, unsafe_allow_html=True)

    with col2:
        st.markdown(f"""
        <div class="card">
            <div class="card-title">📊 Confidence</div>
            <div class="card-value success">{sections['confidence']}</div>
        </div>
        """, unsafe_allow_html=True)

    # -------------------------------
    # KEY EVIDENCE
    # -------------------------------
    st.markdown("### 🔍 Key Evidence")
    st.markdown(f"""
    <div class="card"><pre>{sections['evidence']}</pre></div>
    """, unsafe_allow_html=True)

    # -------------------------------
    # REASONING
    # -------------------------------
    st.markdown("### 🧠 AI Reasoning")
    st.markdown(f"""
    <div class="card"><pre>{sections['reasoning']}</pre></div>
    """, unsafe_allow_html=True)

    # -------------------------------
    # ELIMINATED
    # -------------------------------
    st.markdown("### ❌ Eliminated Suspects")
    st.markdown(f"""
    <div class="card"><pre>{sections['eliminated']}</pre></div>
    """, unsafe_allow_html=True)

    # -------------------------------
    # RAW EVIDENCE + MEDIA PREVIEW 🔥
    # -------------------------------
    st.markdown("### 📄 Evidence Breakdown")

    for r in results:
        filename = r.get("file_name", "file")
        content = r["evidence"].get("content", "No content")
        file_type = r.get("file_type", "")

        st.markdown(f"""
        <div class="card">
            <div class="card-title">📁 {filename}</div>
        """, unsafe_allow_html=True)

        # Show media if applicable
        if "image" in file_type:
            st.image(f"data/raw/{filename}", use_container_width=True)

        elif "audio" in file_type:
            st.audio(f"data/raw/{filename}")

        st.markdown(f"""
            <div style="white-space: pre-wrap; font-size: 0.9rem;">
{content}
            </div>
        </div>
        """, unsafe_allow_html=True)

else:
    st.markdown("""
    <div class="card">
        <div class="card-title">👈 Awaiting Input</div>
        <div class="card-value">Upload evidence files to begin investigation</div>
    </div>
    """, unsafe_allow_html=True)