# Catatan Baseline dan Pengujian

## Sumber yang dipakai

Paket runtime disusun dari arsip `RoboMANTAP_HTMX_TKA_Fix_OPTION_LABELS.zip` yang tersedia di Library percakapan. Snapshot `tka_studio.py` dan `tka_docx.py` disertakan terpisah dari arsip lengkap RoboMANTAP yang tersedia, untuk membantu pemeriksaan keselarasan Studio. Kode yang hanya pernah ditempel sebagai pesan teks dan tidak tersedia sebagai file sumber utuh tidak dapat diverifikasi baris demi baris dari arsip ini.

## Perbedaan penting terhadap deskripsi baseline pesan terbaru

Arsip runtime yang tersedia memakai prompt generator yang berada di `tka_engine.py`; arsip tersebut **tidak** berisi `tka_prompts.py` terpisah. Karena itu paket ini tidak mengklaim sebagai salinan byte-per-byte dari versi terbaru yang disebut memakai `tka_prompts.py`. Jangan menimpa baseline GitHub yang sudah benar sebelum melakukan review diff.

## Hasil pemeriksaan lokal

- `py_compile`: lulus untuk modul runtime, entrypoint Vercel, dan snapshot Studio.
- `check_package.py`: lulus untuk konstanta 15 soal, opsi MTs/MA, template, dan Vercel entrypoint.
- Smoke test import FastAPI dan registrasi route: lulus dengan stub lokal untuk modul Gemini; API Gemini sungguhan tidak dipanggil.
- Tidak ada tes end-to-end ke PostgreSQL atau Gemini karena kredensial lingkungan pengguna tidak tersedia.

## Hal yang wajib diverifikasi sebelum siswa mengakses

1. Environment variables `GEMINI_API_KEY`/`GEMINI_API_KEYS` dan `DATABASE_URL` aktif di Vercel Production.
2. PostgreSQL memiliki tabel `sesi_ujian` dengan kolom yang diharapkan engine RoboMANTAP.
3. Uji satu latihan mandiri sampai submit, lalu uji satu kode GuruMANTAP yang diterbitkan dari Studio.
4. Uji ulang sesi setelah reload/cold start. Pemulihan dari schema lama tidak bisa mengembalikan metadata peserta yang memang tidak tersimpan (contoh kelas dan nomor absen).
