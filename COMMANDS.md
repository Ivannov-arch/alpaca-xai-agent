# ⚡ Execution & Service Startup Commands Quick Reference

Ringkasan seluruh perintah (*commands*) untuk inisialisasi lingkungan, pengujian modul/fase, menjalankan backend & frontend, serta verifikasi API.

---

## 1. ⚙️ Setup Lingkungan & Dependensi

### A. Python Backend (Virtual Environment)
```powershell
# Create virtual environment
python -m venv venv

# Activate virtual environment (Windows PowerShell)
.\venv\Scripts\activate

# Activate virtual environment (Windows CMD)
.\venv\Scripts\activate.bat

# Activate virtual environment (Linux / macOS)
source venv/bin/activate

# Install all Python dependencies
pip install -r requirements.txt

# Copy environment template
copy .env.example .env
```

### B. Next.js Frontend Setup
```cmd
cd frontend
npm install
```

---

## 2. 🚀 Menjalankan Layanan (Start Services)

### A. Start Agent API Backend & Background Audit Worker
Menjalankan server FastAPI di port `8000` (termasuk background audit scheduler 15 menit):
```powershell
# Jalankan dari root direktori proyek (dengan venv aktif)
uvicorn agent.api.main:app --reload --port 8000
```

### B. Start Next.js Frontend Dashboard
Menjalankan antarmuka Next.js di `http://localhost:3000`:
```cmd
# Jalankan dari folder frontend/
cd frontend
npm run dev
```

---

## 3. 🧪 Pengujian Unit & Fase (Independent Phase Testing)

Jalankan pengujian secara mandiri untuk setiap node State Machine:

```powershell
# 1. Test Supabase Database Connection
.\venv\Scripts\python.exe test_supabase.py

# 2. Test Network Connectivity
.\venv\Scripts\python.exe test_network.py

# 3. Test Alpaca Market Data Feed
.\venv\Scripts\python.exe test_feed.py

# 4. Phase 1: Test LLM Hypothesis Generation (Gemini 3.6 Flash)
.\venv\Scripts\python.exe test_phase1.py

# 5. Phase 2: Test Alpaca Paper Trading Order Execution
.\venv\Scripts\python.exe test_phase2.py

# 6. Phase 3: Test Position Audit Logic (Hold / Close Verdict)
.\venv\Scripts\python.exe test_phase3.py

# 7. Phase 4: Test Post-Mortem Synthesis & 3072-dim pgvector Embedding
.\venv\Scripts\python.exe test_phase4.py
```

---

## 4. 🗄️ Database Setup (Supabase SQL Editor)

Jalankan skrip SQL berikut secara berurutan pada **Supabase SQL Editor**:

1. **`database/schema.sql`**  
   *Mengaktifkan ekstensi `pgvector` & membuat tabel `accounts`, `hypotheses`, `audit_logs`, `post_mortems`.*
2. **`database/rls_policies.sql`**  
   *Menerapkan Row Level Security (RLS) & membuat fungsi RPC `match_post_mortems()`.*
3. **`database/seed.sql`** *(Opsional)*  
   *Menambahkan data dev account sampel.*

---

## 5. 📡 Verifikasi REST API (cURL / HTTP)

Perintah pengujian endpoint API backend dari terminal:

```bash
# 1. Check API Health status
curl http://localhost:8000/

# 2. Trigger Trade (Phase 1 -> Phase 2)
curl -X POST http://localhost:8000/trade/start \
  -H "Content-Type: application/json" \
  -d "{\"symbol\": \"AAPL\"}"

# 3. Get All Hypotheses
curl http://localhost:8000/trade/hypotheses

# 4. Get Live Portfolio & Account Summary
curl http://localhost:8000/portfolio

# 5. Get All Vector Memories (Post-Mortems)
curl http://localhost:8000/memory

# 6. Trigger Manual Audit for Hypothesis (Ganti {hypothesis_id})
curl -X POST http://localhost:8000/trade/{hypothesis_id}/audit
```
