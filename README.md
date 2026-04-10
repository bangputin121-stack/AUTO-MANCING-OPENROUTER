AUTO MANCING v3.0 — Setup Guide
Environment Variables (Railway / VPS)
Variable	Wajib	Contoh	Keterangan
`API_ID`	✅	`12345678`	Dari my.telegram.org
`API_HASH`	✅	`abc123...`	Dari my.telegram.org
`SESSION_STRING`	✅	`BQA...`	Generate pakai script di bawah
`OPENROUTER_KEY`	✅	`sk-or-v1-...`	Dari openrouter.ai
`FISHING_BOT`	❌	`fish_it_vip_bot`	Default sudah diset
`MANCING_INTERVAL`	❌	`310`	Jeda cast dalam detik
`OPENROUTER_MODEL`	❌	`google/gemini-2.0-flash-exp:free`	Model AI
---
Generate SESSION_STRING
Jalankan script ini SEKALI di lokal kamu:
```python
from pyrogram import Client

api_id   = input("API_ID: ")
api_hash = input("API_HASH: ")

with Client("gen_session", api_id=int(api_id), api_hash=api_hash) as app:
    print("SESSION_STRING:", app.export_session_string())
```
Copy hasilnya ke env var `SESSION_STRING`.
---
Install & Jalankan
```bash
pip install -r requirements.txt
python main.py
```
---
Tipe Captcha yang Didukung
Tipe	Contoh	Cara AI Jawab
Hitung emoji	🐟🐟🐟 → pilih 3	Lihat gambar, hitung emoji
Pilih emoji ikan	🌸 🐟 🎮 ⚽	Pilih emoji ikan yang benar
Matematika	10 + 12 = ?	Hitung hasilnya
Pola angka	2, 4, 6, 8, __	Lanjutkan polanya
---
Model OpenRouter yang Direkomendasikan
`google/gemini-2.0-flash-exp:free` — gratis, bagus untuk vision
`google/gemini-flash-1.5-8b` — cepat & murah
`openai/gpt-4o-mini` — akurat tapi lebih mahal
