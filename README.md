# DaSheet_BOT 🤖
**Asisten AI untuk Analisis Datasheet Komponen Elektronik**

Tugas ini adalah aplikasi berbasis Web menggunakan **Streamlit** dan **Google Gemini API** yang dirancang untuk membantu teknisi atau pelajar dalam menganalisis dokumen PDF (datasheet) secara cepat.

## Fitur Utama
- **Long Context Processing**: Mampu membaca seluruh isi dokumen PDF tanpa potongan (chunking) tradisional, sehingga hasil analisis lebih akurat.
- **REST API Integration**: Menggunakan protokol REST untuk berkomunikasi langsung dengan model Gemini terbaru (2.0/2.5).
- **Multi-Document Support**: Bisa mengunggah beberapa PDF sekaligus untuk dianalisis secara bersamaan.
- **Auto-Fallback Model**: Sistem secara otomatis mencoba model lain (seperti Gemini 2.0 Flash Lite) jika model utama sedang sibuk.

## Teknologi yang Digunakan
- **Python 3.14** (Versi terbaru untuk performa maksimal)
- **Streamlit**: Framework untuk antarmuka web.
- **PyPDF**: Untuk ekstraksi teks dari dokumen PDF.
- **Google Gemini API**: Sebagai otak AI untuk pemrosesan bahasa alami.

## Cara Menggunakan
1. Buka aplikasi melalui browser.
2. Masukkan **Google API Key** Anda di panel samping (Sidebar).
3. Unggah file PDF datasheet yang ingin dianalisis.
4. Klik tombol **Proses Dokumen Sekarang**.
5. Setelah teks berhasil dimuat, Anda bisa mulai bertanya apa saja mengenai isi dokumen tersebut di kolom chat.

## Keamanan Data
Aplikasi ini tidak menyimpan API Key Anda. API Key hanya digunakan selama sesi berlangsung untuk berkomunikasi dengan Google API.
