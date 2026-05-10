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
import google.genai as genai

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
def get_embedding(text: str, api_key: str, model: str = "text-embedding-004") -> list:
    """Memanggil Google Generative Language REST API v1 secara langsung untuk embedding."""
    url = (
        f"https://generativelanguage.googleapis.com/v1/models/"
        f"{model}:embedContent?key={api_key}"
    )
    payload = {
        "model": f"models/{model}",
        "content": {"parts": [{"text": text}]}
    }
    resp = requests.post(url, json=payload, timeout=30)
    resp.raise_for_status()
    return resp.json()["embedding"]["values"]


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
                errors = 0
                for i, chunk in enumerate(all_chunks):
                    try:
                        emb = get_embedding(chunk, api_key_clean)
                        store.add_texts([chunk], [emb])
                    except Exception as e:
                        errors += 1
                    progress.progress((i + 1) / len(all_chunks), text=f"Embedding {i+1}/{len(all_chunks)}...")
                    time.sleep(0.05)  # Hindari rate limit

                progress.empty()
                st.session_state.vector_store = store

                if errors == 0:
                    st.sidebar.success(f"✅ {len(all_chunks)} bagian berhasil diindeks!")
                else:
                    st.sidebar.warning(f"⚠️ Selesai dengan {errors} error. {len(store.texts)} bagian berhasil diindeks.")


# ==========================================
# CHAT INTERFACE
# ==========================================
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
                        st.warning(f"Gagal mencari konteks: {e}")

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
                        f"(Tidak ada dokumen yang diunggah atau tidak ditemukan konteks yang relevan.)\n\n"
                        f"Pertanyaan: {prompt}"
                    )

                try:
                    client = genai.Client(api_key=api_key_clean)
                    response = client.models.generate_content(
                        model="gemini-1.5-flash",
                        contents=user_message,
                        config=genai.types.GenerateContentConfig(
                            system_instruction=system_instruction,
                            temperature=0.2,
                        )
                    )
                    final_answer = response.text
                    st.markdown(final_answer)
                    st.session_state.messages.append({"role": "assistant", "content": final_answer})

                except Exception as e:
                    st.error(f"Terjadi kesalahan saat memanggil Gemini: {e}")
