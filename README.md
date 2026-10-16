# RoboMANTAP TKA — Vercel student portal

Paket FastAPI + Jinja2/HTMX untuk portal siswa TKA. Runtime ini memakai `tka_engine.py` dan `ai_engine.py` yang juga menjadi mesin inti generator TKA. Sumber `tka_studio.py` dan `tka_docx.py` disertakan di `studio_reference/` sebagai referensi integrasi Studio guru; folder tersebut tidak diimpor oleh function Vercel.

## Ketentuan yang dipertahankan

- Latihan Mandiri: 15 soal, 75 menit.
- Komposisi latihan mandiri: PG, MCMA, dan KATEGORI, masing-masing 5 soal (diperiksa oleh validator generator).
- Stimulus/gambar opsional; ketiadaan gambar tidak menggagalkan generator.
- Paket GuruMANTAP dibaca dari tabel `tka_custom` yang dipublikasikan oleh TKA Studio.
- Template siswa berada di `templates-tka/` dan dipakai oleh `tka_main.py`.

## Deploy ke Vercel

1. Ekstrak ZIP dan push seluruh isi folder ini ke root repository GitHub yang dituju.
2. Buat project Vercel dari repository itu. **Root Directory harus folder ini**, bukan `api/` atau `templates-tka/`.
3. Tambahkan environment variables di Vercel → Settings → Environment Variables:
   - `GEMINI_API_KEY` (wajib; atau `GEMINI_API_KEYS`)
   - `DATABASE_URL` (wajib, PostgreSQL yang dapat diakses Vercel; pakai URL pooled/provider yang sesuai)
   - `STREAMLIT_URL` (opsional, tujuan tombol review)
4. Redeploy setelah variabel diatur.
5. Uji `https://DOMAIN-ANDA/healthz`. JSON harus menunjukkan `status: ok`, `database_configured: true`, `gemini_configured: true`.
6. Uji halaman `/`, kemudian buat latihan mandiri MTs Bahasa Indonesia dan Matematika, serta MA Bahasa Indonesia/Matematika/Bahasa Inggris. Uji juga kode paket GuruMANTAP yang sudah diterbitkan dari Studio.

## Database

`ensure_tka_tables()` membuat tabel `tka_custom` dan `tka_image_library` bila koneksi tersedia. Pencatatan hasil/session tetap memakai tabel `sesi_ujian` yang digunakan RoboMANTAP. Database yang dipakai harus sudah mempunyai struktur `sesi_ujian` kompatibel dengan RoboMANTAP; jangan jalankan SQL DROP/RESET.

## Pemeriksaan yang sudah dilakukan pada paket

- Python syntax compilation untuk semua modul runtime dan entrypoint.
- Pemeriksaan file template, route entrypoint, dan konfigurasi Vercel.
- Perbaikan konstanta label opsi MTs/MA yang sebelumnya dipanggil namun tidak didefinisikan.
- Pemulihan sesi dari `sesi_ujian` ditambahkan untuk membantu menghadapi cold start/instance baru Vercel, menggunakan payload `quiz_data` dan `user_answers` yang disimpan oleh engine.

## Catatan penting sebelum dipakai siswa secara luas

Paket ini belum dapat diuji end-to-end terhadap database dan API Gemini milik Anda dari lingkungan build ini karena kredensial/provider tersebut tidak tersedia di sini. Jalankan checklist deploy di atas dan satu ujian simulasi sebelum membagikan link ke semua siswa. Pemulihan sesi menggunakan metadata yang tersedia di `sesi_ujian`; beberapa data tampilan yang tidak disimpan schema lama (misalnya kelas/absen dan mode asal) akan kembali sebagai nilai default setelah cold start. Untuk pemulihan sesi penuh tanpa kehilangan metadata, schema payload sesi perlu menyimpan seluruh konfigurasi peserta.

## Struktur utama

- `api/index.py` — entrypoint Vercel
- `vercel.json` — routing seluruh path ke FastAPI
- `tka_main.py` — route portal siswa
- `tka_engine.py` — generator, validator, library stimulus, publish/load paket, pencatatan sesi
- `ai_engine.py` — Gemini, label opsi, database connection, hint siswa
- `templates-tka/` — tampilan login, ujian, dan hasil
- `studio_reference/` — snapshot sumber Studio dan DOCX untuk penyelarasan
