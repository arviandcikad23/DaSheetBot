"""
DaSheet_BOT Professional - Powered by Gemini & Exa AI
Fitur: Auto-Load Dokumen dari folder 'database_pdf'
"""

import streamlit as st
import tempfile
import os
import requests
import time
import glob
from pypdf import PdfReader

# 1. KONFIGURASI HALAMAN
st.set_page_config(page_title="DaSheet_BOT Pro", page_icon="dashetbot24x24.ico", layout="wide")

# Custom CSS
st.markdown("""
    <style>
    .stButton>button { width: 100%; border-radius: 5px; background-color: #007bff; color: white; }
    </style>
    """, unsafe_allow_html=True)

# 2. INISIALISASI STATE
if "messages" not in st.session_state:
    st.session_state.messages = []
if "teks_dokumen" not in st.session_state:
    st.session_state.teks_dokumen = ""
if "nama_file" not in st.session_state:
    st.session_state.nama_file = []
if "dokumen_dict" not in st.session_state:
    st.session_state.dokumen_dict = {}
if "is_data_loaded" not in st.session_state:
    st.session_state.is_data_loaded = False

# 3. FUNGSI UNTUK MEMBACA PDF
def ekstrak_teks_pdf(file_path, nama_file):
    try:
        reader = PdfReader(file_path)
        teks = f"\n[DOKUMEN: {nama_file}]\n"
        for page in reader.pages:
            teks += (page.extract_text() or "") + "\n"
        return teks
    except Exception as e:
        return f"\n[Gagal membaca {nama_file}: {e}]\n"

# 4. OTOMATIS MUAT DOKUMEN DARI ROOT (HALAMAN UTAMA)
# Mencari semua file .pdf yang Anda upload langsung ke GitHub
BASE_DIR = os.path.dirname(os.path.abspath(__file__))

if not st.session_state.is_data_loaded:
    # Cari file .pdf dan .PDF langsung di folder utama
    files = glob.glob(os.path.join(BASE_DIR, "*.pdf")) + \
            glob.glob(os.path.join(BASE_DIR, "*.PDF"))
    
    if files:
        with st.spinner(f"Mendeteksi {len(files)} dokumen di repositori..."):
            gabungan = ""
            nama_list = []
            for f_path in files:
                f_name = os.path.basename(f_path)
                # Hindari memproses file sementara jika ada
                if not f_name.startswith("~"):
                    teks_ekstrak = ekstrak_teks_pdf(f_path, f_name)
                    gabungan += teks_ekstrak
                    nama_list.append(f_name)
                    st.session_state.dokumen_dict[f_name] = teks_ekstrak
            st.session_state.teks_dokumen = gabungan
            st.session_state.nama_file = nama_list
    
    st.session_state.is_data_loaded = True

# 5. FUNGSI PENCARIAN EXA AI
def cari_internet_exa(query, exa_key):
    if not exa_key: return ""
    url = "https://api.exa.ai/search"
    headers = {"accept": "application/json", "content-type": "application/json", "x-api-key": exa_key}
    payload = {"query": query, "useAutoprompt": True, "numResults": 3, "contents": {"text": {"maxCharacters": 1000}}}
    try:
        response = requests.post(url, json=payload, headers=headers, timeout=15)
        if response.status_code == 200:
            results = response.json().get("results", [])
            teks_hasil = "\n--- DATA TAMBAHAN DARI INTERNET ---\n"
            for res in results:
                teks_hasil += f"\nSumber: {res.get('url')}\nKonten: {res.get('text')[:500]}...\n"
            return teks_hasil
        return ""
    except: return ""

# 6. FUNGSI REQUEST GEMINI
def request_gemini(prompt, system, api_key):
    # Mencoba berbagai model dari yang terbaru hingga yang paling stabil
    models = [
        "gemini-2.5-flash",
        "gemini-2.0-flash", 
        "gemini-2.0-flash-lite",
        "gemini-1.5-flash"
    ]
    payload = {"contents": [{"role": "user", "parts": [{"text": f"{system}\n\n{prompt}"}]}], "generationConfig": {"temperature": 0.2}}
    err_msg = ""
    for m_name in models:
        url = f"https://generativelanguage.googleapis.com/v1beta/models/{m_name}:generateContent?key={api_key}"
        try:
            r = requests.post(url, json=payload, timeout=120)
            if r.status_code == 200: return r.json()["candidates"][0]["content"]["parts"][0]["text"]
            err_msg = r.json().get("error", {}).get("message", r.text)
        except: continue
    return f"Gagal merespon. Detail: {err_msg}"

# 7. SIDEBAR
with st.sidebar:
    st.image("DasheetBOT.png", use_container_width=True)
    st.caption("AI Assistant with Auto-Database")
    st.markdown("---")
    
    with st.expander("Konfigurasi API", expanded=True):
        gemini_key = st.text_input("Gemini API Key", type="password")
        exa_key = st.text_input("Exa API Key", type="password")
        pakai_exa = st.checkbox("Gunakan Pencarian Internet", value=False)
    
    st.markdown("---")
    st.header("Tambah Dokumen")
    files_upload = st.file_uploader("Upload PDF Tambahan", type="pdf", accept_multiple_files=True, label_visibility="collapsed")
    
    if st.button("Proses Dokumen Tambahan", type="primary"):
        if files_upload:
            with st.status("Menambah dokumen...", expanded=False):
                for file in files_upload:
                    with tempfile.NamedTemporaryFile(delete=False, suffix=".pdf") as tmp:
                        tmp.write(file.getvalue()); p = tmp.name
                    teks_ekstrak = ekstrak_teks_pdf(p, file.name)
                    st.session_state.teks_dokumen += teks_ekstrak
                    st.session_state.nama_file.append(file.name)
                    st.session_state.dokumen_dict[file.name] = teks_ekstrak
                    os.remove(p)
                st.rerun()

    if st.session_state.nama_file:
        st.markdown("---")
        st.subheader("Database Aktif")
        st.metric("Total Dokumen", len(st.session_state.nama_file))
        with st.expander("Daftar File", expanded=False):
            for f in st.session_state.nama_file: st.caption(f"📄 {f}")
        if st.button("Kosongkan Database"):
            st.session_state.teks_dokumen = ""
            st.session_state.nama_file = []
            st.session_state.dokumen_dict = {}
            st.rerun()

# 8. MAIN INTERFACE
tab_chat, tab_preview = st.tabs(["💬 Chat dengan AI", "📄 Preview Data"])

with tab_chat:
    for m in st.session_state.messages:
        with st.chat_message(m["role"]): st.markdown(m["content"])

    if prompt := st.chat_input("Tanyakan sesuatu..."):
        st.session_state.messages.append({"role": "user", "content": prompt})
        with st.chat_message("user"): st.markdown(prompt)

        with st.chat_message("assistant"):
            with st.spinner("Menganalisis..."):
                h_web = cari_internet_exa(prompt, exa_key.strip()) if (pakai_exa and exa_key.strip()) else ""
                sys = "Anda adalah DaSheet_BOT. Jawab berdasarkan DATA DOKUMEN dan INTERNET yang diberikan."
                ctx = f"DATA DOKUMEN:\n{st.session_state.teks_dokumen}\n\n{h_web}\n\nPERTANYAAN: {prompt}"
                try:
                    res = request_gemini(ctx, sys, gemini_key.strip())
                    st.markdown(res); st.session_state.messages.append({"role": "assistant", "content": res})
                except Exception as e: st.error(f"Error: {e}")

with tab_preview:
    if st.session_state.dokumen_dict:
        st.subheader("📚 Daftar Dokumen Aktif")
        st.write("Klik pada nama dokumen untuk melihat seluruh teks yang dibaca oleh AI.")
        
        for f_name, text in st.session_state.dokumen_dict.items():
            # Tampilkan sedikit ringkasan teks sebagai preview (200 karakter pertama)
            snippet = text.replace("\n", " ")[:200] + "..."
            
            # Membuat kotak (expander) yang bisa diklik
            with st.expander(f"📄 {f_name}"):
                st.caption("Ringkasan isi:")
                st.write(snippet)
                st.markdown("---")
                st.text_area("Teks Lengkap", text, height=300, key=f"preview_{f_name}")
    else:
        st.write("Belum ada dokumen yang dimuat.")
