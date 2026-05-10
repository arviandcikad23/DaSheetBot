"""
DaSheet_BOT — Asisten AI untuk analisis dokumen PDF menggunakan Google Gemini.
Stack: google-genai SDK (langsung), FAISS (in-memory vector store), Streamlit.
Tidak menggunakan langchain-google-genai atau chromadb yang tidak kompatibel Python 3.14.
"""

import streamlit as st
import tempfile
import os
import time
import shutil
import json
import requests
import numpy as np

from pypdf import PdfReader
from langchain_text_splitters import RecursiveCharacterTextSplitter
from langchain_core.documents import Document
from langchain_core.embeddings import Embeddings
from langchain_core.messages import HumanMessage, AIMessage

# ==========================================
# KONFIGURASI HALAMAN
# ==========================================
st.set_page_config(page_title="DaSheet_BOT", page_icon="🤖", layout="wide")
st.title("DaSheet_BOT 🤖")
st.write("Asisten AI untuk menganalisis dokumen PDF menggunakan Google Gemini.")


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
os.environ["GOOGLE_API_KEY"] = api_key_clean


# ==========================================
# EMBEDDING: REST API v1 LANGSUNG (tanpa SDK wrapper)
# ==========================================
def get_embedding(text: str, api_key: str) -> list:
    """Memanggil Google Generative Language REST API v1 dengan fallback model."""
    # Daftar model embedding yang akan dicoba
    embedding_models = ["text-embedding-004", "text-embedding-005", "embedding-001"]
    
    last_err = ""
    for model in embedding_models:
        url = f"https://generativelanguage.googleapis.com/v1/models/{model}:embedContent?key={api_key}"
        payload = {
            "model": f"models/{model}",
            "content": {"parts": [{"text": text}]}
        }
        try:
            for attempt in range(2):
                resp = requests.post(url, json=payload, timeout=30)
                if resp.status_code == 200:
                    return resp.json()["embedding"]["values"]
                elif resp.status_code == 429:
                    time.sleep(2)
                    continue
                else:
                    break
            
            # Jika sampai sini berarti gagal untuk model ini
            err_data = resp.json().get("error", {}).get("message", resp.text)
            last_err = f"Model {model}: {err_data}"
        except Exception as e:
            last_err = str(e)
            continue
            
    raise Exception(f"Semua model embedding gagal. Error terakhir: {last_err}")

# ==========================================
# VECTOR STORE SEDERHANA (In-Memory, tanpa chromadb)
# ==========================================
class SimpleVectorStore:
    """Vector store sederhana berbasis numpy, tanpa dependensi chromadb."""
    def __init__(self):
        self.texts = []
        self.embeddings = []

    def add_texts(self, texts: list, embeddings: list):
        self.texts.extend(texts)
        self.embeddings.extend(embeddings)

    def similarity_search(self, query_embedding: list, k: int = 3) -> list:
        if not self.embeddings:
            return []
        q = np.array(query_embedding)
        scores = []
        for i, emb in enumerate(self.embeddings):
            e = np.array(emb)
            score = np.dot(q, e) / (np.linalg.norm(q) * np.linalg.norm(e) + 1e-10)
            scores.append((score, self.texts[i]))
        scores.sort(key=lambda x: x[0], reverse=True)
        return [text for _, text in scores[:k]]


# ==========================================
# STATE INITIALIZATION
# ==========================================
if "messages" not in st.session_state:
    st.session_state.messages = []
if "vector_store" not in st.session_state:
    st.session_state.vector_store = None


# ==========================================
# RAG PIPELINE: PROSES PDF
# ==========================================
if process_btn:
    if not api_key_clean:
        st.sidebar.error("❌ Silakan masukkan Google API Key terlebih dahulu.")
    elif not uploaded_files:
        st.sidebar.warning("⚠️ Silakan unggah minimal 1 file PDF.")
    else:
        with st.spinner("Memproses dan mengindeks dokumen..."):
            splitter = RecursiveCharacterTextSplitter(chunk_size=1000, chunk_overlap=200)
            all_chunks = []

            for uploaded_file in uploaded_files:
                try:
                    with tempfile.NamedTemporaryFile(delete=False, suffix=".pdf") as tmp:
                        tmp.write(uploaded_file.getvalue())
                        tmp_path = tmp.name

                    reader = PdfReader(tmp_path)
                    full_text = "\n".join(
                        page.extract_text() or "" for page in reader.pages
                    )
                    os.remove(tmp_path)

                    chunks = splitter.split_text(full_text)
                    all_chunks.extend(chunks)
                    st.sidebar.write(f"✅ {uploaded_file.name}: {len(chunks)} bagian")
                except Exception as e:
                    st.sidebar.error(f"Gagal membaca '{uploaded_file.name}': {e}")

            if all_chunks:
                store = SimpleVectorStore()
                progress = st.sidebar.progress(0, text="Membuat embedding...")
                errors_list = []
                
                for i, chunk in enumerate(all_chunks):
                    try:
                        emb = get_embedding(chunk, api_key_clean)
                        store.add_texts([chunk], [emb])
                    except Exception as e:
                        if len(errors_list) < 3: # Hanya simpan 3 error pertama agar tidak penuh
                            errors_list.append(str(e))
                    progress.progress((i + 1) / len(all_chunks), text=f"Embedding {i+1}/{len(all_chunks)}...")
                    time.sleep(0.1)

                progress.empty()
                st.session_state.vector_store = store

                if not errors_list:
                    st.sidebar.success(f"✅ {len(all_chunks)} bagian berhasil diindeks!")
                else:
                    st.sidebar.error(f"❌ Gagal mengindeks: {errors_list[0]}")
                    if len(store.texts) > 0:
                        st.sidebar.warning(f"⚠️ Hanya {len(store.texts)} dari {len(all_chunks)} bagian yang berhasil.")


# ==========================================
# FUNGSI CHAT: REST API v1 LANGSUNG
# ==========================================
def generate_response(prompt: str, system: str, api_key: str) -> str:
    """
    Memanggil Google Generative Language REST API v1.
    Mencoba beberapa model secara berurutan jika ada yang gagal.
    """
    # Urutan model: dari yang terbaru hingga yang paling stabil
    # Urutan: flash-lite punya rate limit 30 RPM (lebih tinggi), flash 15 RPM
    models_to_try = [
        "gemini-2.0-flash-lite",
        "gemini-2.0-flash",
        "gemini-2.5-flash-lite",
    ]
    full_prompt = f"{system}\n\n{prompt}"
    payload = {
        "contents": [{"role": "user", "parts": [{"text": full_prompt}]}],
        "generationConfig": {"temperature": 0.2}
    }

    last_error = ""
    for model in models_to_try:
        url = (
            f"https://generativelanguage.googleapis.com/v1/models/"
            f"{model}:generateContent?key={api_key}"
        )
        # Retry 3x dengan backoff untuk rate limit
        for attempt in range(3):
            resp = requests.post(url, json=payload, timeout=60)
            if resp.status_code == 200:
                return resp.json()["candidates"][0]["content"]["parts"][0]["text"]
            elif resp.status_code == 429:
                wait = 3 * (attempt + 1)  # 3, 6, 9 detik
                time.sleep(wait)
                last_error = f"429 Rate limit pada model `{model}`"
                continue
            else:
                # Error lain (404, 400, dll) — coba model berikutnya
                try:
                    err_msg = resp.json().get("error", {}).get("message", resp.text)
                except Exception:
                    err_msg = resp.text
                last_error = f"Model `{model}` error {resp.status_code}: {err_msg}"
                break  # Keluar dari retry, coba model berikutnya

    raise Exception(
        f"Semua model gagal. Error terakhir: {last_error}\n\n"
        "Pastikan API Key valid dan memiliki akses ke Gemini API."
    )


# ==========================================
# CHAT INTERFACE
# ==========================================

# Status dokumen
if st.session_state.vector_store and st.session_state.vector_store.texts:
    n = len(st.session_state.vector_store.texts)
    st.info(f"📚 **{n} bagian dokumen** siap digunakan. Silakan ajukan pertanyaan!")
else:
    st.warning("⚠️ Belum ada dokumen yang diproses. Unggah PDF dan klik **Proses Dokumen** di sidebar terlebih dahulu.")

for msg in st.session_state.messages:
    with st.chat_message(msg["role"]):
        st.markdown(msg["content"])

if prompt := st.chat_input("Tanyakan sesuatu tentang dokumen yang diunggah..."):
    st.session_state.messages.append({"role": "user", "content": prompt})
    with st.chat_message("user"):
        st.markdown(prompt)

    if not api_key_clean:
        st.error("❌ Google API Key diperlukan untuk merespons percakapan.")
    else:
        with st.chat_message("assistant"):
            with st.spinner("Sedang berpikir..."):

                # Cari konteks dari dokumen jika ada
                context = ""
                if st.session_state.vector_store and st.session_state.vector_store.texts:
                    try:
                        query_emb = get_embedding(prompt, api_key_clean)
                        relevant_chunks = st.session_state.vector_store.similarity_search(query_emb, k=3)
                        if relevant_chunks:
                            context = "\n\n---\n\n".join(relevant_chunks)
                    except Exception as e:
                        st.error(f"❌ Gagal mencari konteks dokumen: {e}")

                # Bangun pesan ke Gemini
                system_instruction = (
                    "Kamu adalah DaSheet_BOT, asisten AI yang membantu pengguna memahami isi dokumen.\n"
                    "Jawab HANYA berdasarkan konteks dokumen yang diberikan jika relevan.\n"
                    "Jika informasi tidak ada di dokumen, sampaikan dengan jujur.\n"
                    "Selalu jawab dalam Bahasa Indonesia yang jelas dan profesional."
                )

                if context:
                    user_message = (
                        f"Konteks dari dokumen:\n{context}\n\n"
                        f"Pertanyaan: {prompt}"
                    )
                else:
                    user_message = (
                        f"(Tidak ada dokumen yang diunggah atau tidak ditemukan konteks relevan.)\n\n"
                        f"Pertanyaan: {prompt}"
                    )

                try:
                    final_answer = generate_response(
                        prompt=user_message,
                        system=system_instruction,
                        api_key=api_key_clean
                    )
                    st.markdown(final_answer)
                    st.session_state.messages.append({"role": "assistant", "content": final_answer})

                except Exception as e:
                    st.error(f"Terjadi kesalahan saat memanggil Gemini: {e}")
