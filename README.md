# DaSheetBOT
**Asisten Pintar Analisis Datasheet & Karakteristik Hardware**

DaSheetBOT adalah aplikasi AI berbasis *Long-Context* yang dirancang khusus untuk membantu mahasiswa dan insinyur teknik dalam menganalisis dokumen datasheet komponen elektronik secara cepat dan akurat.

---

##  Struktur File Utama
Untuk mempermudah pemeriksaan kode, berikut adalah file-file inti dari proyek ini:
*   **`app.py`**: File utama yang berisi seluruh logika program, desain antarmuka (UI), dan integrasi API.
*   **`requirements.txt`**: Daftar pustaka (library) Python yang wajib diinstal agar aplikasi berjalan lancar.
*   **`README.md`**: Dokumen panduan penggunaan dan penjelasan fitur aplikasi.
*   **`DasheetBOT.png` & `dashetbot24x24.ico`**: Aset visual (Logo dan Favicon) untuk identitas aplikasi.

---

##  Link Aplikasi
Aplikasi dapat langsung diakses melalui tautan berikut:  
 **[Buka DaSheetBOT](https://dasheetbot-8jint3j2h55bsn3u9hfbvm.streamlit.app)**  
*(Pastikan Anda telah menyiapkan Google Gemini API Key untuk memulai percakapan)*

---

##  Fitur Unggulan Terbaru
*   ** Hardware Expert Personality**: AI telah dioptimasi untuk berpikir seperti pakar hardware, mampu mengidentifikasi Pinout, Batas Maksimal (Safety), dan karakteristik fisik komponen secara otomatis.
*   ** Analisis Cepat (Quick Actions)**: Dilengkapi tombol pintasan di sidebar untuk melakukan perintah kompleks hanya dengan satu klik:
    *   **Ringkasan Pinout**: Langsung mengekstrak fungsi kaki-kaki komponen.
    *   **Cek Batas Aman**: Menampilkan tabel *Absolute Maximum Ratings* untuk keamanan hardware.
    *   **Cari Padanan (Equivalent)**: Mencari alternatif komponen melalui internet jika stok tidak tersedia.
*   ** Smart Auto-Database**: Semua file PDF datasheet yang tersimpan di repositori GitHub akan otomatis terdeteksi dan siap dianalisis tanpa perlu upload manual satu per satu.
*   ** Exa AI Web Search**: Integrasi pencarian internet canggih untuk melengkapi informasi datasheet dengan data terbaru dari web.
*   ** UI/UX Premium**: Tampilan profesional dengan tema *Bone White & Cyan*, ikon Material, dan layout yang responsif untuk kenyamanan analisis data.

---

##  Panduan Penggunaan Singkat
1.  **Buka Aplikasi**: Klik link di atas.
2.  **Konfigurasi API**: Masukkan Google API Key Anda pada bagian "Pengaturan Kunci API" di sidebar.
3.  **Gunakan Quick Actions**: Klik tombol **"Ringkasan Pinout"** atau **"Cek Batas Aman"** untuk langsung melihat keajaiban analisis otomatis.
4.  **Eksplorasi Data**: Gunakan tab **"Eksplorasi Data"** untuk melihat teks mentah dokumen yang sedang dianalisis.
5.  **Tambah Dokumen**: Anda tetap bisa mengunggah file PDF tambahan dari komputer lokal jika diperlukan.

---

##  Contoh Pertanyaan untuk Dicoba
Anda bisa menguji kecerdasan DaSheetBOT dengan mencoba beberapa perintah berikut:
1.  **Perbandingan Komponen**: *"Bandingkan spesifikasi teknis antara XL4005 dan XL4015 dalam bentuk tabel. Mana yang lebih efisien untuk arus 4A?"*
2.  **Analisis Pinout**: *"Sebutkan konfigurasi pin untuk komponen BC547 dan jelaskan fungsi masing-masing kakinya."*
3.  **Cek Keamanan**: *"Berapa suhu operasional maksimal dan tegangan input tertinggi untuk XL4016 agar tidak terbakar?"*
4.  **Cari Alternatif**: *"Jika saya tidak memiliki transistor BC547, carikan komponen pengganti (equivalent) yang serupa melalui internet."*

---

##  Teknologi yang Digunakan
*   **Bahasa**: Python 3.14
*   **Framework**: Streamlit (Modern Web App)
*   **AI Engine**: Google Generative AI (Gemini Flash Series)
*   **Search Engine**: Exa AI API (Neural Search)
*   **PDF Library**: PyPDF (Fast Extraction)

---
*Dikembangkan dengan ❤️ oleh **Arviandcikad** - 2026*
*Dibuat untuk memudahkan eksplorasi teknologi dan inovasi sistem hardware.*
