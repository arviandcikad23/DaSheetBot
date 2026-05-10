"""
DaSheet_BOT Professional - Powered by Gemini & Exa AI
Aplikasi ini dikembangkan untuk memudahkan analisis dokumen teknis 
(seperti datasheet elektronik) menggunakan AI.
"""

import os
import glob
import time
import tempfile
import requests
import streamlit as st
from pypdf import PdfReader

# ==========================================
# KONFIGURASI HALAMAN & CSS
# ==========================================
def setup_halaman():
    st.set_page_config(
        page_title="DaSheet_BOT Pro", 
        page_icon="dashetbot24x24.ico", 
        layout="wide"
    )

    # Injeksi CSS untuk mengubah tema warna bawaan Streamlit
    # agar sesuai dengan identitas visual aplikasi (Putih Tulang & Cyan Kebiruan)
    css_kustom = """
    <style>
    /* Latar Belakang (Putih Tulang Terang) */
    .stApp, [data-testid="stSidebar"], [data-testid="stHeader"] {
        background-color: #FDFCF4 !important;
    }
    
    /* Gelembung Chat AI (Cyan Lembut) */
    [data-testid="stChatMessage"] {
        background-color: #E0F7FA !important;
        border-radius: 10px;
        border-left: 5px solid #00BCD4 !important;
        padding: 15px;
        margin-bottom: 10px;
        box-shadow: 0 2px 4px rgba(0,188,212,0.1);
    }
    
    /* Gelembung Chat User (Biru Nila) */
    [data-testid="stChatMessage"]:has([data-testid="chatAvatarIcon-user"]) {
        background-color: #E8EAF6 !important;
        border-left: 5px solid #5C6BC0 !important;
        box-shadow: 0 2px 4px rgba(92,107,192,0.1);
    }
    
    /* Garis Pemisah */
    hr {
        border-top: 2px solid #00BCD4 !important;
    }
    
    /* Modifikasi Tombol (menghilangkan warna merah bawaan) */
    .stButton>button[kind="primary"] {
        background-color: #00BCD4 !important;
        border-color: #00BCD4 !important;
        color: white !important;
        border-radius: 5px;
        width: 100%;
    }
    .stButton>button[kind="primary"]:hover {
        background-color: #4DD0E1 !important;
        border-color: #4DD0E1 !important;
    }
    .stButton>button[kind="secondary"] {
        border-color: #00BCD4 !important;
        color: #0097A7 !important;
        border-radius: 5px;
        width: 100%;
    }
    .stButton>button[kind="secondary"]:hover {
        background-color: #00BCD4 !important;
        color: white !important;
    }

    /* Warna Aktif pada Tab */
    div[data-testid="stTabs"] button[aria-selected="true"] p {
        color: #00BCD4 !important;
        font-weight: bold;
    }
    div[data-testid="stTabs"] div[data-baseweb="tab-list"] div[aria-selected="true"] {
        border-bottom-color: #00BCD4 !important;
    }

    /* Checkbox Transparan */
    .stCheckbox [data-baseweb="checkbox"] div:first-child {
        background-color: transparent;
    }
    </style>
    """
    st.markdown(css_kustom, unsafe_allow_html=True)


# ==========================================
# INISIALISASI VARIABEL SESI (STATE)
# ==========================================
def inisialisasi_sesi():
    if "pesan_chat" not in st.session_state:
        st.session_state.pesan_chat = []
    
    if "teks_gabungan" not in st.session_state:
        st.session_state.teks_gabungan = ""
        
    if "daftar_nama_file" not in st.session_state:
        st.session_state.daftar_nama_file = []
        
    if "data_dokumen" not in st.session_state:
        st.session_state.data_dokumen = {}
        
    if "sudah_dimuat" not in st.session_state:
        st.session_state.sudah_dimuat = False


# ==========================================
# FUNGSI PEMROSESAN DATA
# ==========================================
def ekstrak_teks_dari_pdf(path_file, nama_file):
    """Membaca file PDF dan mengembalikan teks di dalamnya."""
    try:
        pembaca = PdfReader(path_file)
        teks_hasil = f"\n[DOKUMEN: {nama_file}]\n"
        for halaman in pembaca.pages:
            teks_hasil += (halaman.extract_text() or "") + "\n"
        return teks_hasil
    except Exception as error:
        return f"\n[Gagal membaca {nama_file}: {error}]\n"

def muat_dokumen_otomatis():
    """Mencari semua file PDF di folder utama aplikasi saat dijalankan."""
    if st.session_state.sudah_dimuat:
        return

    direktori_utama = os.path.dirname(os.path.abspath(__file__))
    file_pdf_ditemukan = glob.glob(os.path.join(direktori_utama, "*.pdf")) + \
                         glob.glob(os.path.join(direktori_utama, "*.PDF"))
    
    if file_pdf_ditemukan:
        with st.spinner(f"Memuat {len(file_pdf_ditemukan)} dokumen dasar..."):
            teks_sementara = ""
            list_sementara = []
            
            for path_file in file_pdf_ditemukan:
                nama_file = os.path.basename(path_file)
                if not nama_file.startswith("~"):
                    teks_ekstrak = ekstrak_teks_dari_pdf(path_file, nama_file)
                    teks_sementara += teks_ekstrak
                    list_sementara.append(nama_file)
                    st.session_state.data_dokumen[nama_file] = teks_ekstrak
            
            st.session_state.teks_gabungan = teks_sementara
            st.session_state.daftar_nama_file = list_sementara
    
    st.session_state.sudah_dimuat = True


# ==========================================
# FUNGSI INTEGRASI API (GEMINI & EXA)
# ==========================================
def cari_data_di_internet(kata_kunci, kunci_api_exa):
    """Mencari informasi tambahan di internet menggunakan Exa AI."""
    if not kunci_api_exa:
        return ""
        
    url_pencarian = "https://api.exa.ai/search"
    header_pencarian = {
        "accept": "application/json", 
        "content-type": "application/json", 
        "x-api-key": kunci_api_exa
    }
    payload_pencarian = {
        "query": kata_kunci, 
        "useAutoprompt": True, 
        "numResults": 3, 
        "contents": {"text": {"maxCharacters": 1000}}
    }
    
    try:
        respon = requests.post(url_pencarian, json=payload_pencarian, headers=header_pencarian, timeout=15)
        if respon.status_code == 200:
            hasil = respon.json().get("results", [])
            teks_ringkasan = "\n--- INFO TAMBAHAN DARI INTERNET ---\n"
            for item in hasil:
                teks_ringkasan += f"\nSumber: {item.get('url')}\nKonten: {item.get('text')[:500]}...\n"
            return teks_ringkasan
        return ""
    except:
        return ""

def tanya_gemini(pertanyaan, instruksi_sistem, kunci_api_gemini):
    """Mengirim pertanyaan beserta data dokumen ke Google Gemini API."""
    daftar_model = [
        "gemini-2.5-flash",
        "gemini-2.0-flash", 
        "gemini-2.0-flash-lite",
        "gemini-1.5-flash"
    ]
    
    struktur_pesan = {
        "contents": [{"role": "user", "parts": [{"text": f"{instruksi_sistem}\n\n{pertanyaan}"}]}], 
        "generationConfig": {"temperature": 0.2}
    }
    
    pesan_error = ""
    for nama_model in daftar_model:
        url_api = f"https://generativelanguage.googleapis.com/v1beta/models/{nama_model}:generateContent?key={kunci_api_gemini}"
        try:
            respon_api = requests.post(url_api, json=struktur_pesan, timeout=120)
            if respon_api.status_code == 200:
                return respon_api.json()["candidates"][0]["content"]["parts"][0]["text"]
            
            # Jika limit rate tercapai, beri waktu jeda sebentar sebelum ganti model
            if respon_api.status_code == 429:
                time.sleep(5)
                
            pesan_error = respon_api.json().get("error", {}).get("message", respon_api.text)
        except Exception as e:
            pesan_error = str(e)
            continue
            
    return f"Sistem gagal merespon setelah mencoba beberapa model. Detail: {pesan_error}"


# ==========================================
# ANTARMUKA PENGGUNA (USER INTERFACE)
# ==========================================
def tampilkan_sidebar():
    with st.sidebar:
        st.image("DasheetBOT.png", use_container_width=True)
        st.caption("Asisten Pintar Analisis Datasheet")
        st.markdown("---")
        
        # Pengaturan Kunci API
        with st.expander("Pengaturan Kunci API", expanded=True):
            gemini_key = st.text_input("Kunci API Gemini", type="password")
            exa_key = st.text_input("Kunci API Exa (Opsional)", type="password")
            gunakan_internet = st.checkbox("Izinkan Pencarian Web", value=False)
        
        st.markdown("---")
        
        # Fitur Upload Dokumen Tambahan
        st.header("Unggah Dokumen")
        file_diunggah = st.file_uploader(
            "Pilih file PDF tambahan", 
            type="pdf", 
            accept_multiple_files=True, 
            label_visibility="collapsed"
        )
        
        if st.button("Proses Dokumen", type="primary"):
            if file_diunggah:
                with st.status("Sedang memproses file PDF...", expanded=False):
                    for file in file_diunggah:
                        # Membuat file sementara untuk dibaca oleh PyPDF
                        with tempfile.NamedTemporaryFile(delete=False, suffix=".pdf") as file_sementara:
                            file_sementara.write(file.getvalue())
                            path_sementara = file_sementara.name
                            
                        teks_baru = ekstrak_teks_dari_pdf(path_sementara, file.name)
                        st.session_state.teks_gabungan += teks_baru
                        st.session_state.daftar_nama_file.append(file.name)
                        st.session_state.data_dokumen[file.name] = teks_baru
                        
                        os.remove(path_sementara)
                    st.rerun()

        # Menampilkan status database saat ini
        if st.session_state.daftar_nama_file:
            st.markdown("---")
            st.subheader("Informasi Database")
            st.metric("Total Dokumen Aktif", len(st.session_state.daftar_nama_file))
            
            with st.expander("Daftar Nama File", expanded=False):
                for nama in st.session_state.daftar_nama_file:
                    st.caption(f":material/description: {nama}")
                    
            if st.button("Bersihkan Database"):
                st.session_state.teks_gabungan = ""
                st.session_state.daftar_nama_file = []
                st.session_state.data_dokumen = {}
                st.rerun()
                
    return gemini_key, exa_key, gunakan_internet


def tampilkan_layar_utama(gemini_key, exa_key, gunakan_internet):
    tab_percakapan, tab_pratinjau = st.tabs([
        ":material/forum: Percakapan AI", 
        ":material/dataset: Eksplorasi Data"
    ])

    # ---------------- TAB PERCAKAPAN ----------------
    with tab_percakapan:
        # Menempatkan logo di tengah atas agar tidak mengganggu
        kolom_kiri, kolom_tengah, kolom_kanan = st.columns([3, 2, 3])
        with kolom_tengah:
            try:
                st.image("dashetbot2.png", use_container_width=True)
            except:
                pass # Abaikan jika gambar belum diunggah
        
        st.markdown("<br>", unsafe_allow_html=True) # Memberi jarak kosong sedikit
        
        # Menampilkan riwayat chat sebelumnya
        for pesan in st.session_state.pesan_chat:
            avatar_ikon = "dashetbot 32X32.ico" if pesan["role"] == "assistant" else None
            with st.chat_message(pesan["role"], avatar=avatar_ikon): 
                st.markdown(pesan["content"])

        # Menangkap input pengguna
        if input_pengguna := st.chat_input("Ketik pertanyaan Anda tentang datasheet..."):
            st.session_state.pesan_chat.append({"role": "user", "content": input_pengguna})
            
            with st.chat_message("user"): 
                st.markdown(input_pengguna)

            with st.chat_message("assistant", avatar="dashetbot 32X32.ico"):
                with st.spinner("Sedang memformulasikan jawaban..."):
                    # Cek internet jika diizinkan
                    hasil_pencarian = ""
                    if gunakan_internet and exa_key.strip():
                        hasil_pencarian = cari_data_di_internet(input_pengguna, exa_key.strip())
                    
                    # Bangun instruksi dan konteks untuk AI
                    instruksi = (
                        "Anda adalah DaSheet_BOT, asisten ahli teknik elektronika. "
                        "Gunakan data dari dokumen yang disediakan untuk menjawab. "
                        "Jika tidak ada di dokumen, rujuk pada info internet jika tersedia."
                    )
                    konteks_akhir = (
                        f"DATA DOKUMEN:\n{st.session_state.teks_gabungan}\n\n"
                        f"{hasil_pencarian}\n\n"
                        f"PERTANYAAN PENGGUNA: {input_pengguna}"
                    )
                    
                    try:
                        jawaban_ai = tanya_gemini(konteks_akhir, instruksi, gemini_key.strip())
                        st.markdown(jawaban_ai)
                        st.session_state.pesan_chat.append({"role": "assistant", "content": jawaban_ai})
                    except Exception as err:
                        st.error(f"Terjadi kesalahan teknis: {err}")

    # ---------------- TAB PRATINJAU ----------------
    with tab_pratinjau:
        if st.session_state.data_dokumen:
            st.subheader(":material/folder_open: Detail Dokumen yang Tersimpan")
            st.write("Klik pada salah satu nama dokumen di bawah ini untuk membaca teks mentahnya.")
            
            for nama_dokumen, isi_teks in st.session_state.data_dokumen.items():
                cuplikan = isi_teks.replace("\n", " ")[:250] + "..."
                
                with st.expander(f":material/description: {nama_dokumen}"):
                    st.caption("Cuplikan Teks:")
                    st.write(cuplikan)
                    st.markdown("---")
                    st.text_area("Teks Keseluruhan", isi_teks, height=300, key=f"lihat_{nama_dokumen}")
        else:
            st.info("Belum ada dokumen yang dimuat. Silakan unggah dokumen PDF di sidebar.")


# ==========================================
# EKSEKUSI PROGRAM UTAMA
# ==========================================
if __name__ == "__main__":
    setup_halaman()
    inisialisasi_sesi()
    muat_dokumen_otomatis()
    
    kunci_g, kunci_e, izin_web = tampilkan_sidebar()
    tampilkan_layar_utama(kunci_g, kunci_e, izin_web)
