"""
DaSheet_BOT - Professional AI Document Assistant
Versi Terintegrasi dengan Google Search.
"""

import streamlit as st
import tempfile
import os
import requests
import time
from pypdf import PdfReader

# 1. KONFIGURASI HALAMAN
st.set_page_config(
    page_title="DaSheet_BOT Professional", 
    page_icon="🤖", 
    layout="wide",
    initial_sidebar_state="expanded"
)

# Custom CSS
st.markdown("""
    <style>
    .stButton>button {
        width: 100%;
        border-radius: 5px;
        background-color: #007bff;
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

def hapus_chat():
    st.session_state.messages = []

# 3. SIDEBAR
with st.sidebar:
    st.title("DaSheet_BOT 🤖")
    st.caption("AI Assistant with Web Search")
    st.markdown("---")
    
    with st.expander("Konfigurasi", expanded=True):
        google_api_key = st.text_input("Google API Key", type="password")
        # FITUR BARU: Toggle untuk pencarian web
        aktifkan_web = st.checkbox("Aktifkan Pencarian Web", value=True, help="Jika dicentang, AI bisa mencari informasi tambahan dari internet.")
    
    st.markdown("---")
    st.header("Unggah Dokumen")
    files_upload = st.file_uploader("Upload PDF", type="pdf", accept_multiple_files=True, label_visibility="collapsed")
    
    if st.button("Mulai Proses Dokumen", type="primary"):
        if not google_api_key:
            st.error("Silakan masukkan API Key.")
        elif not files_upload:
            st.warning("Pilih file PDF terlebih dahulu.")
        else:
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
                st.session_state.teks_dokumen = gabungan_teks
                st.session_state.nama_file = nama_file_list
                status.update(label="Proses Selesai!", state="complete", expanded=False)
    
    st.markdown("---")
    if st.button("Hapus Riwayat Chat"):
        hapus_chat()
        st.rerun()

    # --- BAGIAN BARU: DAFTAR DOKUMEN TERDAFTAR ---
    if st.session_state.nama_file:
        st.markdown("---")
        st.subheader("Dokumen Terdaftar")
        for file_aktif in st.session_state.nama_file:
            st.success(f"📄 {file_aktif}")
        
        if st.button("Hapus Semua Dokumen", type="secondary"):
            st.session_state.teks_dokumen = ""
            st.session_state.nama_file = []
            st.rerun()

# 4. FUNGSI REQUEST API DENGAN GOOGLE SEARCH
def request_gemini(prompt, system, api_key, pakai_web=False):
    # Gunakan Gemini 2.0 Flash untuk dukungan pencarian web yang stabil
    models = ["gemini-2.0-flash", "gemini-2.0-flash-lite"]
    
    payload = {
        "contents": [{"role": "user", "parts": [{"text": f"{system}\n\n{prompt}"}]}],
        "generationConfig": {"temperature": 0.2}
    }
    
    # TAMBAHKAN TOOL GOOGLE SEARCH JIKA DIAKTIFKAN
    if pakai_web:
        payload["tools"] = [{"google_search_retrieval": {}}]

    for m_name in models:
        url = f"https://generativelanguage.googleapis.com/v1/models/{m_name}:generateContent?key={api_key}"
        try:
            for attempt in range(2):
                r = requests.post(url, json=payload, timeout=90)
                if r.status_code == 200:
                    return r.json()["candidates"][0]["content"]["parts"][0]["text"]
                if r.status_code == 429:
                    time.sleep(5)
                    continue
                break
        except:
            continue
    return "Maaf, sistem sedang sibuk atau API Key bermasalah."

# 5. ANTARMUKA UTAMA
api_key_clean = google_api_key.strip() if google_api_key else ""

tab_chat, tab_preview = st.tabs(["💬 Percakapan AI", "📄 Preview Dokumen"])

with tab_chat:
    if st.session_state.teks_dokumen:
        col_a, col_b, col_c = st.columns(3)
        col_a.metric("Dokumen", len(st.session_state.nama_file))
        col_b.metric("Karakter", f"{len(st.session_state.teks_dokumen):,}")
        col_c.metric("Web Search", "Aktif" if aktifkan_web else "Mati")
    
    for m in st.session_state.messages:
        with st.chat_message(m["role"]):
            st.markdown(m["content"])

    if prompt := st.chat_input("Tanyakan sesuatu..."):
        st.session_state.messages.append({"role": "user", "content": prompt})
        with st.chat_message("user"):
            st.markdown(prompt)

        with st.chat_message("assistant"):
            with st.spinner("Sedang menganalisis..." + (" (Mencari di Web)" if aktifkan_web else "")):
                sys_inst = (
                    "Anda adalah DaSheet_BOT. Gunakan data dokumen jika tersedia.\n"
                    "Jika 'Google Search' diaktifkan, Anda boleh menggunakan informasi dari internet "
                    "untuk melengkapi jawaban Anda, terutama jika data di datasheet kurang lengkap."
                )
                
                # Masukkan data dokumen ke dalam prompt
                konteks = f"DATA DOKUMEN:\n{st.session_state.teks_dokumen}\n\n" if st.session_state.teks_dokumen else "Tidak ada dokumen yang diunggah.\n\n"
                query_lengkap = konteks + f"PERTANYAAN: {prompt}"
                
                try:
                    response = request_gemini(query_lengkap, sys_inst, api_key_clean, pakai_web=aktifkan_web)
                    st.markdown(response)
                    st.session_state.messages.append({"role": "assistant", "content": response})
                except Exception as e:
                    st.error(f"Error: {e}")

with tab_preview:
    if st.session_state.teks_dokumen:
        st.text_area("Konten Dokumen", st.session_state.teks_dokumen, height=500)
    else:
        st.write("Belum ada data dokumen.")
