"""
DaSheet_BOT Professional - Powered by Gemini & Exa AI
UI yang lebih bersih dengan Metrik di Sidebar.
"""

import streamlit as st
import tempfile
import os
import requests
import time
from pypdf import PdfReader

# 1. KONFIGURASI HALAMAN
st.set_page_config(page_title="DaSheet_BOT Pro", page_icon="🤖", layout="wide")

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

# 3. FUNGSI PENCARIAN EXA AI
def cari_internet_exa(query, exa_key):
    if not exa_key:
        return "Info: Exa API Key kosong, pencarian internet dilewati."
    
    url = "https://api.exa.ai/search"
    headers = {"accept": "application/json", "content-type": "application/json", "x-api-key": exa_key}
    payload = {
        "query": query,
        "useAutoprompt": True,
        "numResults": 3,
        "contents": {"text": {"maxCharacters": 1000}}
    }
    try:
        response = requests.post(url, json=payload, headers=headers, timeout=15)
        if response.status_code == 200:
            results = response.json().get("results", [])
            if not results: return "Info: Tidak ditemukan hasil relevan di internet."
            teks_hasil = "\n--- HASIL PENCARIAN INTERNET (EXA AI) ---\n"
            for res in results:
                teks_hasil += f"\nSumber: {res.get('url')}\nJudul: {res.get('title')}\nKonten: {res.get('text')[:500]}...\n"
            return teks_hasil
        else:
            return f"Info: Exa API Error {response.status_code} - {response.text}"
    except Exception as e:
        return f"Info: Gagal terhubung ke Exa AI: {str(e)}"

# 4. FUNGSI REQUEST GEMINI
def request_gemini(prompt, system, api_key):
    models = ["gemini-2.0-flash", "gemini-2.0-flash-lite"]
    payload = {
        "contents": [{"role": "user", "parts": [{"text": f"{system}\n\n{prompt}"}]}],
        "generationConfig": {"temperature": 0.2}
    }
    error_asli = ""
    for m_name in models:
        url = f"https://generativelanguage.googleapis.com/v1beta/models/{m_name}:generateContent?key={api_key}"
        try:
            for attempt in range(2):
                r = requests.post(url, json=payload, timeout=120)
                if r.status_code == 200:
                    return r.json()["candidates"][0]["content"]["parts"][0]["text"]
                if r.status_code == 429:
                    time.sleep(8); continue
                error_asli = r.json().get("error", {}).get("message", r.text)
                break 
        except Exception as e:
            error_asli = str(e); continue
    return f"Gagal mendapatkan respon. Detail: {error_asli}"

# 5. SIDEBAR
with st.sidebar:
    st.title("DaSheet_BOT 🤖")
    st.caption("Advanced AI Analysis")
    st.markdown("---")
    
    with st.expander("Konfigurasi API", expanded=True):
        gemini_key = st.text_input("Gemini API Key", type="password")
        exa_key = st.text_input("Exa API Key", type="password")
        pakai_exa = st.checkbox("Gunakan Pencarian Internet", value=False, help="Hanya gunakan jika Anda sudah memasukkan Exa API Key.")
    
    st.markdown("---")
    st.header("Unggah Dokumen")
    files_upload = st.file_uploader("Upload PDF", type="pdf", accept_multiple_files=True, label_visibility="collapsed")
    
    if st.button("Mulai Proses Dokumen", type="primary"):
        if not gemini_key:
            st.error("Masukkan Gemini API Key.")
        elif not files_upload:
            st.warning("Pilih file PDF.")
        else:
            with st.status("Memproses dokumen...", expanded=True) as status:
                gabungan_teks = ""; nama_file_list = []
                for file in files_upload:
                    with tempfile.NamedTemporaryFile(delete=False, suffix=".pdf") as tmp:
                        tmp.write(file.getvalue()); path = tmp.name
                    reader = PdfReader(path)
                    t = f"\n[DOKUMEN: {file.name}]\n"
                    for p in reader.pages: t += (p.extract_text() or "") + "\n"
                    gabungan_teks += t; nama_file_list.append(file.name); os.remove(path)
                st.session_state.teks_dokumen = gabungan_teks
                st.session_state.nama_file = nama_file_list
                status.update(label="Selesai!", state="complete", expanded=False)

    # PINDAHKAN METRIK KE SIDEBAR
    if st.session_state.nama_file:
        st.markdown("---")
        st.subheader("Statistik Dokumen")
        st.metric("Total Dokumen", len(st.session_state.nama_file))
        st.metric("Ukuran Teks", f"{len(st.session_state.teks_dokumen):,} char")
        
        with st.expander("Daftar File", expanded=False):
            for f in st.session_state.nama_file:
                st.caption(f"📄 {f}")
        
        if st.button("Hapus Semua Dokumen"):
            st.session_state.teks_dokumen = ""; st.session_state.nama_file = []; st.rerun()

    st.markdown("---")
    if st.button("Hapus Riwayat Chat"):
        st.session_state.messages = []; st.rerun()

# 6. MAIN INTERFACE
tab_chat, tab_preview = st.tabs(["💬 Chat dengan AI", "📄 Preview Teks"])

with tab_chat:
    for m in st.session_state.messages:
        with st.chat_message(m["role"]): st.markdown(m["content"])

    if prompt := st.chat_input("Tanyakan sesuatu tentang datasheet..."):
        st.session_state.messages.append({"role": "user", "content": prompt})
        with st.chat_message("user"): st.markdown(prompt)

        with st.chat_message("assistant"):
            with st.spinner("Sedang menganalisis..."):
                hasil_web = ""
                # HANYA JALANKAN EXA JIKA DICENTANG DAN KEY ADA
                if pakai_exa and exa_key.strip():
                    with st.status("Mencari di internet via Exa AI...", expanded=False) as s_exa:
                        hasil_web = cari_internet_exa(prompt, exa_key.strip())
                        if "Error" in hasil_web:
                            s_exa.update(label="Gagal mencari di web", state="error")
                        else:
                            s_exa.update(label="Pencarian web selesai", state="complete")
                
                sys_inst = "Anda adalah DaSheet_BOT. Jawab berdasarkan dokumen PDF yang diberikan. Jika ada data dari web, gunakan untuk melengkapi jawaban."
                konteks_lengkap = f"DOKUMEN PDF:\n{st.session_state.teks_dokumen}\n\n{hasil_web}\n\nPERTANYAAN: {prompt}"
                
                try:
                    res = request_gemini(konteks_lengkap, sys_inst, gemini_key.strip())
                    st.markdown(res)
                    st.session_state.messages.append({"role": "assistant", "content": res})
                except Exception as e:
                    st.error(f"Terjadi kesalahan: {e}")

with tab_preview:
    if st.session_state.teks_dokumen:
        st.text_area("Konten yang dibaca AI", st.session_state.teks_dokumen, height=500)
    else: st.write("Belum ada dokumen.")
