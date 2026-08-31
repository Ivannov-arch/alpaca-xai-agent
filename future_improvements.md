# 🚀 Future Improvements & Roadmap: XAI Trading Agent

Dokumen ini memuat rencana pengembangan tingkat lanjut (roadmap) untuk menyempurnakan agen trading otonom XAI di masa mendatang.

---

## 1. 💰 Dynamic Portfolio Risk & Position Sizing Control
* **Deskripsi:** Menambahkan kontrol alokasi modal berbasis persentase risiko (misal: maksimum 2% dari total ekuitas portofolio per transaksi) daripada menggunakan fixed range unit.
* **Fitur UI:** Input bidang "Max Allocation ($ / %)" pada dashboard frontend agar pengguna dapat menyesuaikan batas maksimum dana per transaksi.

## 2. 🔍 Automated Multi-Asset Scanner (Auto-Discovery)
* **Deskripsi:** Membuat background scanner yang memindai daftar 50+ pasangan saham & crypto berpotensi secara berkala (misal tiap jam). Agen secara otomatis akan memilih aset terbaik yang membentuk setup teknikal ideal untuk dianalisis di Phase 1 tanpa perlu input manual.

## 3. 🎯 Dynamic Trailing Stop & Partial Profit Taking (Scale-Out)
* **Deskripsi:** Mengembangkan Phase 3 Audit agar mendukung penutupan parsial (misal: Take Profit 50% posisi saat mencapai risk-to-reward 1:1, lalu menaikkan Stop Loss ke titik breakeven untuk sisa 50% posisi).

## 4. ⚡ Real-time WebSocket Streaming Feed
* **Deskripsi:** Mengganti mekanisme REST API polling (15 detik) dengan Alpaca WebSocket Data Streaming (`wss://stream.data.alpaca.markets`). Hal ini memungkinkan evaluasi audit (Phase 3) berjalan secara sub-detik saat terjadi lonjakan harga ekstrem (*flash crash* / *breakout*).

## 5. 📰 Sentiment Analysis & News Integration
* **Deskripsi:** Menggabungkan data sentimen berita finansial real-time (via Finnhub / CryptoPanic API / X) ke dalam prompt LLM Phase 1. Agen tidak hanya menganalisis grafik OHLCV tetapi juga memperhitungkan *catalyst* berita terkini.

## 6. 🤝 Multi-LLM Ensemble Voting
* **Deskripsi:** Memperluas pembuat hipotesis dengan menggabungkan hasil analisis dari beberapa LLM sekaligus (misal: Gemini 3.6 Flash + Claude 3.5 Sonnet + DeepSeek V3). Transaksi hanya dieksekusi jika minimal 2 dari 3 LLM memberikan konfirmasi sinyal searah.

## 7. 📊 Quantitative Backtesting Engine
* **Deskripsi:** Membangun modul backtesting berbasis histori data 1-3 tahun terakhir untuk menguji performa state machine LangGraph dan kualitas hipotesis sebelum diterapkan di akun live trading sesungguhnya.

## 8. 🏢 Multi-Account & Portfolio Scenario Isolation
* **Deskripsi:** Mendukung pengelolaan banyak akun (*multi-account*) dan sub-portofolio dengan skenario independen. 
* **Implementasi:** Arsitektur database kita sudah 80% siap karena memiliki relasi `account_id` pada setiap tabel (`accounts`, `hypotheses`, `audit_logs`, `post_mortems`). Pengguna dapat membuat akun terpisah untuk skenario *High-Risk Speculative Crypto* dan *Low-Risk Retirement Stock Portfolio*.
* **Fitur UI:** *Account Switcher Dropdown* pada header terminal untuk memilah analitik & riwayat transaksi per akun secara terpisah.

## 9. 🧠 Multi-Strategy Archetypes (Aggressive, Swing, Conservative)
* **Deskripsi:** Menyediakan pilihan kepribadian & profil risiko strategi bagi agen sebelum memicu transaksi:
  * ⚡ **Scalping Mode (Agresif):** Timeframe 1-5 menit, Stop Loss sangat ketat (0.5–1%), frekuensi audit sub-menit.
  * 📈 **Swing Trading Mode (Standar):** Timeframe H1–1Day, Risk-to-Reward 2:1+, frekuensi audit 15 menit.
  * 🛡️ **Conservative / Long-Term Mode:** Timeframe Weekly, Stop Loss lebar (5–10%), fokus pada akumulasi aset & fundamental, frekuensi audit harian.
* **Implementasi:** Parameter `strategy_profile` disuntikkan ke dalam *System Prompt* Gemini pada Phase 1 & Phase 3, sehingga LLM secara otomatis menyesuaikan kalkulasi Stop Loss, Target Profit, dan Invalidation Triggers sesuai kepribadian mode yang dipilih.

