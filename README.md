# DaSheet_BOT
**Asisten AI untuk Analisis Dokumen Datasheet**

Aplikasi ini dibuat untuk membantu proses pembacaan dan analisis dokumen teknis dalam format PDF, khususnya datasheet komponen elektronik. Dengan menggunakan Google Gemini API, aplikasi ini mampu memahami isi dokumen secara mendalam dan menjawab pertanyaan teknis secara otomatis.

## Link Aplikasi
Aplikasi dapat diakses melalui link berikut:  
**[Buka DaSheet_BOT](https://dasheetbot-8jint3j2h55bsn3u9hfbvm.streamlit.app)**
*(Membutuhkan Google API Key untuk menjalankan fungsi chat)*

## Panduan Penggunaan
Bagi Anda yang ingin menguji aplikasi ini, berikut adalah langkah-langkahnya:

1. **Buka Link Aplikasi**: Klik link yang tertera di atas.
2. **Input API Key**: Pada panel sidebar di sebelah kiri, masukkan Google API Key Anda. Anda bisa mendapatkannya secara gratis melalui Google AI Studio.
3. **Database Otomatis**: Aplikasi ini sudah dilengkapi dengan beberapa file PDF contoh yang tersimpan di repositori GitHub. File-file tersebut akan otomatis terdeteksi dan siap untuk dianalisis (cek bagian "Database Aktif").
4. **Unggah File Lain**: Jika ingin menganalisis file PDF Anda sendiri, gunakan fitur "Tambah Dokumen" di sidebar.
5. **Mulai Chat**: Ketik pertanyaan teknis Anda di kolom chat yang tersedia.

## Fitur Utama
* **Long Context Window**: Aplikasi mengirimkan seluruh teks dokumen ke AI sehingga jawaban yang dihasilkan lebih akurat dan menyeluruh.
* **Integrasi Pencarian Web**: Dilengkapi dengan opsi pencarian internet melalui Exa AI untuk melengkapi data yang tidak ada di datasheet.
* **Auto-Load Database**: File PDF yang ada di repositori GitHub otomatis dimuat saat aplikasi pertama kali dijalankan.
* **Interface Sederhana**: Didesain agar mudah digunakan tanpa banyak konfigurasi rumit.

## Teknologi Utama
* Python 3.14
* Streamlit (Interface)
* Google Gemini API (AI Engine)
* Exa AI (Web Search)
* PyPDF (PDF Parsing)

---

