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
