"""
DaSheet_BOT — Asisten AI untuk analisis dokumen PDF menggunakan Google Gemini.
Versi 2026: Menggunakan Long Context Window (Tanpa Embedding/Vector DB).
Sangat stabil untuk Python 3.14 dan menghindari error 404 embedding.
"""

import streamlit as st
import tempfile
import os
import requests
import time

from pypdf import PdfReader

# ==========================================
# KONFIGURASI HALAMAN
# ==========================================
st.set_page_config(page_title="DaSheet_BOT", page_icon="🤖", layout="wide")
st.title("DaSheet_BOT 🤖")
st.write("Asisten AI untuk menganalisis dokumen PDF menggunakan Long Context Gemini.")

# ==========================================
# SIDEBAR — INPUT API KEY & UPLOAD PDF
# ==========================================
with st.sidebar:
    st.header("⚙️ Konfigurasi API")
    google_api_key = st.text_input(
        "Google API Key",
        type="password",
        help="Dapatkan di aistudio.google.com"
    )
    st.markdown("---")
    st.header("📄 Unggah Dokumen PDF")
    uploaded_files = st.file_uploader(
        "Unggah PDF (bisa lebih dari 1)",
        type="pdf",
        accept_multiple_files=True
    )
    process_btn = st.button("🔄 Proses Dokumen")

# Sanitasi API Key
api_key_clean = google_api_key.strip() if google_api_key else ""

# ==========================================
# STATE INITIALIZATION
# ==========================================
if "messages" not in st.session_state:
    st.session_state.messages = []
if "full_context" not in st.session_state:
    st.session_state.full_context = ""

# ==========================================
# FUNGSI CHAT: REST API v1 LANGSUNG
# ==========================================
def generate_response(prompt: str, system: str, api_key: str) -> str:
    """Memanggil Google Generative Language REST API v1 dengan fallback model."""
    models_to_try = ["gemini-2.0-flash-lite", "gemini-2.0-flash", "gemini-2.5-flash-lite"]
    
    # Gabungkan instruksi sistem dan pesan user
    full_prompt = f"{system}\n\n{prompt}"
    payload = {
        "contents": [{"role": "user", "parts": [{"text": full_prompt}]}],
        "generationConfig": {"temperature": 0.2}
    }

    last_error = ""
    for model in models_to_try:
        url = f"https://generativelanguage.googleapis.com/v1/models/{model}:generateContent?key={api_key}"
        try:
            for attempt in range(3):
                resp = requests.post(url, json=payload, timeout=90)
                if resp.status_code == 200:
                    return resp.json()["candidates"][0]["content"]["parts"][0]["text"]
                elif resp.status_code == 429:
                    time.sleep(5)
                    continue
                else:
                    break
            
            err_msg = resp.json().get("error", {}).get("message", resp.text)
            last_error = f"Model {model}: {err_msg}"
        except Exception as e:
            last_error = str(e)
            continue
            
    raise Exception(f"Chat gagal. Error terakhir: {last_error}")

# ==========================================
# PROSES PDF: EKSTRAK TEKS LANGSUNG
# ==========================================
if process_btn:
    if not api_key_clean:
        st.sidebar.error("❌ Masukkan Google API Key.")
    elif not uploaded_files:
        st.sidebar.warning("⚠️ Unggah PDF terlebih dahulu.")
    else:
        with st.spinner("Mengekstrak teks dokumen..."):
            all_text = ""
            for uploaded_file in uploaded_files:
                try:
                    with tempfile.NamedTemporaryFile(delete=False, suffix=".pdf") as tmp:
                        tmp.write(uploaded_file.getvalue())
                        tmp_path = tmp.name
                    
                    reader = PdfReader(tmp_path)
                    file_text = f"\n--- ISI DOKUMEN: {uploaded_file.name} ---\n"
                    for page in reader.pages:
                        file_text += (page.extract_text() or "") + "\n"
                    
                    all_text += file_text
                    os.remove(tmp_path)
                except Exception as e:
                    st.sidebar.error(f"Gagal membaca {uploaded_file.name}: {e}")
            
            if all_text:
                st.session_state.full_context = all_text
                st.sidebar.success(f"✅ Berhasil memuat {len(all_text)} karakter teks!")

# ==========================================
# CHAT INTERFACE
# ==========================================
if st.session_state.full_context:
    st.info(f"📚 **Dokumen Aktif**: {len(st.session_state.full_context)} karakter teks dimuat ke memori AI.")
else:
    st.warning("⚠️ Belum ada dokumen yang diproses. Silakan unggah PDF di sidebar.")

for msg in st.session_state.messages:
    with st.chat_message(msg["role"]):
        st.markdown(msg["content"])

if prompt := st.chat_input("Tanyakan sesuatu tentang dokumen..."):
    st.session_state.messages.append({"role": "user", "content": prompt})
    with st.chat_message("user"):
        st.markdown(prompt)

    if not api_key_clean:
        st.error("❌ Google API Key diperlukan.")
    else:
        with st.chat_message("assistant"):
            with st.spinner("Menganalisis dokumen..."):
                system_instruction = (
                    "Kamu adalah DaSheet_BOT, asisten ahli analisis komponen elektronik.\n"
                    "Gunakan isi dokumen yang diberikan untuk menjawab pertanyaan pengguna.\n"
                    "Jika informasi tidak ada, katakan sejujurnya.\n"
                    "Jawab dalam Bahasa Indonesia yang profesional."
                )
                
                # Masukkan seluruh dokumen ke dalam pesan
                context_prefix = f"Berikut adalah isi dokumen yang diunggah:\n{st.session_state.full_context}\n\n"
                full_user_query = context_prefix + f"Pertanyaan: {prompt}"

                try:
                    answer = generate_response(full_user_query, system_instruction, api_key_clean)
                    st.markdown(answer)
                    st.session_state.messages.append({"role": "assistant", "content": answer})
                except Exception as e:
                    st.error(f"Terjadi kesalahan: {e}")
