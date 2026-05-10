"""
DaSheet_BOT - Professional AI Document Assistant
Didesain dengan UI yang bersih dan fitur Long Context Gemini.
"""

import streamlit as st
import tempfile
import os
import requests
import time
from pypdf import PdfReader

# 1. KONFIGURASI HALAMAN & TEMA CUSTOM
st.set_page_config(
    page_title="DaSheet_BOT Professional", 
    page_icon="🤖", 
    layout="wide",
    initial_sidebar_state="expanded"
)

# Custom CSS untuk mempercantik tampilan
st.markdown("""
    <style>
    .main {
        background-color: #f8f9fa;
    }
    .stButton>button {
        width: 100%;
        border-radius: 5px;
        height: 3em;
        background-color: #007bff;
        color: white;
    }
    .stTextInput>div>div>input {
        border-radius: 5px;
    }
    .sidebar .sidebar-content {
        background-image: linear-gradient(#2e7bcf,#2e7bcf);
        color: white;
    }
    </style>
    """, unsafe_allow_html=True)

# 2. INISIALISASI STATE
if "messages" not in st.session_state:
    st.session_state.messages = []
if "teks_dokumen" not in st.session_state:
    st.session_state.teks_dokumen = ""
if "nama_file" not in st.session_state:
    st.session_state.nama_file = []

# Fungsi untuk menghapus percakapan
def hapus_chat():
    st.session_state.messages = []

# 3. SIDEBAR YANG TERORGANISIR
with st.sidebar:
    st.title("DaSheet_BOT 🤖")
    st.caption("AI Assistant for Electronic Components")
    st.markdown("---")
    
    with st.expander("Konfigurasi API", expanded=True):
        google_api_key = st.text_input(
            "Google API Key",
            type="password",
            placeholder="AIzaSy..."
        )
    
    st.markdown("---")
    st.header("Unggah Dokumen")
    files_upload = st.file_uploader(
        "Pilih file PDF datasheet",
        type="pdf",
        accept_multiple_files=True,
        label_visibility="collapsed"
    )
    
    if st.button("Mulai Proses Dokumen", type="primary"):
        if not google_api_key:
            st.error("Silakan masukkan API Key.")
        elif not files_upload:
            st.warning("Pilih file PDF terlebih dahulu.")
        else:
            # Gunakan status container untuk animasi proses yang keren
            with st.status("Sedang memproses dokumen...", expanded=True) as status:
                st.write("Membaca file PDF...")
                gabungan_teks = ""
                nama_file_list = []
                for file in files_upload:
                    with tempfile.NamedTemporaryFile(delete=False, suffix=".pdf") as tmp:
                        tmp.write(file.getvalue())
                        path = tmp.name
                    
                    reader = PdfReader(path)
                    teks_file = f"\n[DOKUMEN: {file.name}]\n"
                    for page in reader.pages:
                        teks_file += (page.extract_text() or "") + "\n"
                    
                    gabungan_teks += teks_file
                    nama_file_list.append(file.name)
                    os.remove(path)
                    st.write(f"Selesai membaca: {file.name}")
                
                st.session_state.teks_dokumen = gabungan_teks
                st.session_state.nama_file = nama_file_list
                status.update(label="Proses Selesai!", state="complete", expanded=False)
    
    st.markdown("---")
    if st.button("Hapus Riwayat Chat", on_click=hapus_chat):
        st.toast("Percakapan telah dibersihkan")

# 4. AREA UTAMA DENGAN TABS
api_key_clean = google_api_key.strip() if google_api_key else ""

# Header aplikasi
col1, col2 = st.columns([3, 1])
with col1:
    st.title("AI Assistant Panel")
    st.write("Menganalisis dokumen teknis dengan akurasi tinggi.")

# Tampilkan Tabs
tab_chat, tab_preview = st.tabs(["💬 Percakapan AI", "📄 Preview Teks Dokumen"])

with tab_chat:
    # Status Indikator Dokumen
    if st.session_state.teks_dokumen:
        col_a, col_b, col_c = st.columns(3)
        col_a.metric("Dokumen Dimuat", len(st.session_state.nama_file))
        col_b.metric("Total Karakter", f"{len(st.session_state.teks_dokumen):,}")
        col_c.metric("Status", "Siap")
    else:
        st.info("Silakan unggah dan proses dokumen di sidebar untuk memulai analisis.")

    # Tampilkan Chat
    for m in st.session_state.messages:
        with st.chat_message(m["role"]):
            st.markdown(m["content"])

    # Input Chat
    if prompt := st.chat_input("Apa yang ingin Anda ketahui dari dokumen ini?"):
        st.session_state.messages.append({"role": "user", "content": prompt})
        with st.chat_message("user"):
            st.markdown(prompt)

        if not api_key_clean:
            st.error("API Key diperlukan.")
        elif not st.session_state.teks_dokumen:
            st.warning("Mohon proses dokumen terlebih dahulu agar AI memiliki konteks.")
        else:
            with st.chat_message("assistant"):
                with st.spinner("Menganalisis..."):
                    # Fungsi request API (sama seperti sebelumnya tapi lebih rapi)
                    def request_gemini(p, s, k):
                        models = ["gemini-2.0-flash-lite", "gemini-2.0-flash", "gemini-2.5-flash-lite"]
                        full = f"{s}\n\n{p}"
                        payload = {"contents": [{"role": "user", "parts": [{"text": full}]}], "generationConfig": {"temperature": 0.2}}
                        for m_name in models:
                            url = f"https://generativelanguage.googleapis.com/v1/models/{m_name}:generateContent?key={k}"
                            try:
                                r = requests.post(url, json=payload, timeout=90)
                                if r.status_code == 200: return r.json()["candidates"][0]["content"]["parts"][0]["text"]
                                if r.status_code == 429: time.sleep(5); continue
                            except: continue
                        return "Maaf, sistem sedang sibuk. Silakan coba lagi."

                    sys_inst = "Anda adalah DaSheet_BOT, ahli datasheet. Jawab berdasarkan data dokumen yang diberikan secara mendetail."
                    full_query = f"DATA DOKUMEN:\n{st.session_state.teks_dokumen}\n\nPERTANYAAN: {prompt}"
                    
                    try:
                        response = request_gemini(full_query, sys_inst, api_key_clean)
                        st.markdown(response)
                        st.session_state.messages.append({"role": "assistant", "content": response})
                    except Exception as e:
                        st.error(f"Error: {e}")

with tab_preview:
    if st.session_state.teks_dokumen:
        st.header("Isi Teks yang Diekstrak")
        st.text_area("Konten Dokumen", st.session_state.teks_dokumen, height=500, disabled=True)
    else:
        st.write("Belum ada data dokumen untuk ditampilkan.")
