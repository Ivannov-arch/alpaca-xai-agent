# 🛠️ Debug Log: XAI Trading Agent Troubleshooting

Dokumen ini mencatat ringkasan kendala (bugs/errors) yang dihadapi selama setup awal dan pengujian Phase 1, beserta penyebab dan solusinya.

---

## 1. PowerShell Parameter Parsing Syntax Error
*   **Penyebab:** Eksekusi script loop PowerShell untuk pembuatan folder struktur di CLI/sandbox Antigravity gagal karena shell parser mendeteksi karakter unescaped.
*   **Solusi:** Menggunakan command sederhana direct shell native `mkdir` dan `type nul >` via `cmd /c` untuk men-scaffold project.

## 2. API v1beta Gemini Embedding Error (text-embedding-004)
*   **Penyebab:** Class `GoogleGenerativeAIEmbeddings` bawaan `langchain-google-genai` memanggil API endpoint `v1beta` Google yang tidak mendukung model `text-embedding-004` untuk API key standard.
*   **Solusi:** Menulis ulang fungsi `embed_text()` di `agent/llm.py` menggunakan official SDK `google-genai` terbaru (`client.models.embed_content()`) dengan model `gemini-embedding-001` (3072 dimensi).

## 3. Supabase pgvector Size Mismatch (1536 vs 3072)
*   **Penyebab:** Perubahan model embedding ke `gemini-embedding-001` mengubah output dimensi vector menjadi 3072, sementara di SQL schema awal diatur sebesar 1536 (OpenAI standard).
*   **Solusi:** Mengupdate kolom `embedding` di `schema.sql` dan parameter fungsi `match_post_mortems()` di `rls_policies.sql` menjadi `VECTOR(3072)` lalu menjalankan migrasi ulang di Supabase.

## 4. Windows Terminal CP1252 Encoding Error
*   **Penyebab:** Karakter box-drawing unicode (`──`) pada `print()` statement di file test merusak eksekusi python di console Windows yang menggunakan encoding default CP1252.
*   **Solusi:** Mengganti semua pemisah karakter unicode dengan karakter ASCII biasa (`---`).

## 5. Alpaca Market Data Return Null on Weekends
*   **Penyebab:** Endpoint `/v2/stocks/{symbol}/bars` dipanggil tanpa parameter `start`/`end`. Alpaca secara default mencocokkan waktu saat ini (weekend/sabtu-minggu saat market tutup) sehingga mengembalikan array kosong/null.
*   **Solusi:** Memperbarui `get_market_data()` di `agent/tools/alpaca_tools.py` agar otomatis menghitung dan menyertakan parameter `"start": (current_time - 45 days)`.

## 6. Deprecated Gemini 2.0 Model Endpoint
*   **Penyebab:** Google API memblokir pemanggilan model `gemini-2.0-flash` dan merespon dengan status `404` serta rekomendasi beralih ke `gemini-3.6-flash`.
*   **Solusi:** Memperbarui parameter model di `agent/llm.py` menjadi `gemini-3.6-flash`.

## 7. Supabase DNS Resolution (getaddrinfo failed)
*   **Penyebab:** File `.env` masih menggunakan domain placeholder `your-project-ref.supabase.co` sehingga sistem operasi gagal me-resolve alamat IP hosting database.
*   **Solusi:** Memperbarui parameter `SUPABASE_URL` di file `.env` dengan URL asli project Supabase.

## 8. Relational Foreign Key Constraint Violation (23503)
*   **Penyebab:** `ACCOUNT_ID` hardcoded pada file test unit tidak terdaftar di tabel `accounts` Supabase, memicu error constraint saat insert data ke tabel `hypotheses`.
*   **Solusi:** Melakukan insert data user baru ke tabel `accounts` di Supabase, lalu mengganti `ACCOUNT_ID` di file `test_phase1.py` dengan UUID `id` akun yang baru terbuat.
