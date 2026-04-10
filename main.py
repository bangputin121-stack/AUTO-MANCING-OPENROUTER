"""
AUTO MANCING v3.0 — OPENROUTER AI CAPTCHA SOLVER
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
Support semua tipe captcha:
  ✅ Hitung emoji ikan di gambar
  ✅ Pilih emoji ikan yang benar (button)
  ✅ Soal matematika (10 + 12 = ?)
  ✅ Lanjutkan pola angka (2, 4, 6, 8, ?)
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
ENV VARS yang dibutuhkan:
  API_ID            → Telegram API ID
  API_HASH          → Telegram API Hash
  SESSION_STRING    → Pyrogram session string
  OPENROUTER_KEY    → sk-or-v1-... (dari openrouter.ai)
  FISHING_BOT       → username bot (default: fish_it_vip_bot)
  MANCING_INTERVAL  → jeda antar cast dalam detik (default: 310)
  OPENROUTER_MODEL  → model AI (default: google/gemini-2.0-flash-exp)
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
"""

import os
import re
import time
import base64
import asyncio
import aiohttp
from pyrogram import Client, filters, idle
from pyrogram.errors import FloodWait
from pyrogram.types import Message

# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
#  CONFIG — ambil dari environment variable
# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
API_ID           = int(os.environ.get("API_ID", "0"))
API_HASH         = os.environ.get("API_HASH", "")
SESSION_STRING   = os.environ.get("SESSION_STRING", "")
FISHING_BOT      = os.environ.get("FISHING_BOT", "fish_it_vip_bot").lstrip("@")
MANCING_INTERVAL = int(os.environ.get("MANCING_INTERVAL", "310"))
OPENROUTER_KEY   = os.environ.get("OPENROUTER_KEY", "")

# Model vision terbaik di OpenRouter untuk captcha gambar
# Ganti kalau mau pakai model lain
OPENROUTER_MODEL = os.environ.get("OPENROUTER_MODEL", "google/gemini-2.0-flash-exp:free")

# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
#  Pyrogram client
# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
app = Client(
    "mancing_session",
    api_id=API_ID,
    api_hash=API_HASH,
    session_string=SESSION_STRING
)

# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
#  Helper: logging
# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
def log(tag: str, msg: str):
    print(f"[{time.strftime('%H:%M:%S')}] [{tag}] {msg}", flush=True)

# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
#  OpenRouter AI — jawab captcha
# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
SYSTEM_PROMPT = """Kamu adalah solver captcha Telegram otomatis untuk bot mancing.

Tugasmu: jawab captcha dengan TEPAT sesuai pilihan yang tersedia.

Aturan penting:
1. Jawab HANYA dengan teks/angka yang persis sama dengan salah satu pilihan.
2. JANGAN tambah kata lain, tanda baca, spasi, atau penjelasan apapun.
3. Kalau captcha berupa gambar emoji, hitung jumlahnya dan pilih angka yang sesuai.
4. Kalau pola angka, lanjutkan polanya lalu pilih angka yang cocok.
5. Kalau suruh "pilih emoji IKAN" atau "pilih hewan air/laut", pilih emoji yang merupakan
   hewan yang hidup di air (laut, sungai, danau, dll).

Daftar emoji HEWAN AIR / LAUT yang valid (pilih salah satu dari pilihan kalau ada ini):
🐟 🐠 🐡 🦈 🐙 🦑 🦐 🦞 🦀 🐚 🐋 🐳 🐬 🐊 🐢 🦦 🦭 🫧 🎣 🐸 🐍 🦎
(hewan yang hidup di air, sungai, laut, rawa — semua termasuk)

Emoji yang BUKAN hewan air (jangan pilih ini untuk captcha hewan air):
🌸 🌺 🌻 🌹 🍀 🎮 ⚽ 🏀 🎱 🎯 🎪 🎭 🚗 🚀 ✈️ 🏠 💻 📱 🎸 🎵
(bunga, bola, kendaraan, teknologi, dll)

Contoh jawaban:
- "Hitung berapa ikan: 🐟🐟🐟" | Pilihan: [3, 5, 6, 4] → Jawab: 3
- "Pilih emoji IKAN yang benar" | Pilihan: [🌸, 🐙, 🎮, ⚽] → Jawab: 🐙
- "Pilih emoji IKAN yang benar" | Pilihan: [🌻, 🎯, 🦑, 🏀] → Jawab: 🦑
- "Pilih emoji IKAN yang benar" | Pilihan: [🐊, 🌸, 🎮, 🎱] → Jawab: 🐊
- "Pilih emoji IKAN yang benar" | Pilihan: [🎭, 🐢, 🚗, 🌹] → Jawab: 🐢
- "2, 4, 6, 8, __?" | Pilihan: [11, 8, 10, 14] → Jawab: 10
"""

# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
#  Python Math Solver — hitung sendiri tanpa AI
#  Support semua variasi:
#    Simbol  : + - × ÷ ^ √ ² ³ % mod
#    Kata ID : tambah, kurang, kali, dibagi, pangkat, akar, mod, sisa
#    Bertingkat: (3+4)×2 - 1
# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

def normalize_math(text: str) -> str:
    """
    Ubah teks soal matematika (semua format) → ekspresi Python.
    Urutan penggantian SANGAT PENTING — jangan ubah urutannya!
    """
    expr = text.strip()

    # ── 1. Kata-kata Indonesia → operator (HARUS sebelum potong prefix) ──
    word_ops = [
        # kata lebih panjang dulu agar tidak bentrok
        (r'\bdikurang(?:i)?\b',   '-'),
        (r'\bditambah(?:i)?\b',   '+'),
        (r'\bdibagi\b',           '/'),
        (r'\bdikali\b',           '*'),
        (r'\bpangkat\b',          '**'),
        (r'\bkuadrat\b',          '**2'),
        (r'\bkubik\b',            '**3'),
        (r'\bmodulo\b',           '%'),
        (r'\bmod\b',              '%'),
        (r'\bsisa\b',             '%'),
        (r'\btambah\b',           '+'),
        (r'\bkurang\b',           '-'),
        (r'\bkali\b',             '*'),
        (r'\bbagi\b',             '/'),
    ]
    for pattern, repl in word_ops:
        expr = re.sub(pattern, repl, expr, flags=re.IGNORECASE)

    # ── 2. Akar sebelum cleanup (supaya angka di dalam tidak hilang) ──
    # "akar(9+16)" → "((9+16)**0.5)"
    expr = re.sub(r'akar\s*\(([^)]+)\)', r'((\1)**0.5)', expr, flags=re.IGNORECASE)
    # "akar 144" atau "akar144" → "(144**0.5)"
    expr = re.sub(r'akar\s*(\d+)', r'(\1**0.5)', expr, flags=re.IGNORECASE)
    # "√(9+16)" → "((9+16)**0.5)"
    expr = re.sub(r'√\(([^)]+)\)', r'((\1)**0.5)', expr)
    # "√144" → "(144**0.5)"
    expr = re.sub(r'√(\d+)', r'(\1**0.5)', expr)

    # ── 3. Simbol matematika → Python ──
    symbol_ops = [
        (r'[×xX]',           '*'),     # × x X → *
        (r'[÷]',             '/'),     # ÷ → /
        (r'²',               '**2'),   # superscript kuadrat
        (r'³',               '**3'),   # superscript kubik
        (r'(?<!\*)\^(?!\*)', '**'),    # ^ → ** (kalau belum jadi **)
    ]
    for pattern, repl in symbol_ops:
        expr = re.sub(pattern, repl, expr)

    # ── 4. Hapus teks non-math di DEPAN ("Berapa hasil dari:", dll) ──
    # Cari digit / kurung / % pertama
    m = re.search(r'[\d\(%\(]', expr)
    if m:
        expr = expr[m.start():]

    # ── 5. Hapus "= ?" dan teks sisa, tapi JAGA operator %, *, /, +, - ──
    expr = re.sub(r'[=?]', '', expr)
    # Hanya izinkan: angka, operator, titik desimal, spasi, kurung
    expr = re.sub(r'[^0-9\+\-\*\/\%\.\(\)\s]', '', expr)
    expr = expr.strip()

    return expr


def solve_math(text: str, choices: list) -> str | None:
    """
    Selesaikan soal matematika dari teks.
    Return string pilihan yang cocok, atau None kalau gagal.

    Didukung:
      Simbol   : 10+12, 6×9, 100÷4, 2^5, √144, 3²
      Kata ID  : tambah, kurang, kali, bagi, pangkat, akar, mod, sisa
      Bertingkat: (3+4)×2-1, akar(9+16), 50-(3×7)
    """
    if not re.search(r'\d', text):
        return None

    expr = normalize_math(text)
    log("MATH", f"🧮 Expr: '{expr}'")

    if not expr or not re.search(r'\d', expr):
        return None

    try:
        result      = eval(expr, {"__builtins__": {}})
        result_float = float(result)
        result_int   = int(round(result_float))

        log("MATH", f"🧮 Hasil: {result_float}")

        for ch in choices:
            ch_str = str(ch).strip()
            try:
                if abs(float(ch_str) - result_float) < 0.01:
                    return ch_str
            except ValueError:
                pass
            if ch_str == str(result_int):
                return ch_str

    except Exception as e:
        log("MATH", f"⚠️ Gagal eval '{expr}': {e}")

    return None
async def call_openrouter(prompt: str, choices: list, img_base64: str = None) -> str | None:
    """
    Panggil OpenRouter untuk jawab captcha.
    
    Args:
        prompt    : teks soal captcha
        choices   : list pilihan jawaban dari button
        img_base64: gambar captcha (base64) kalau ada
    
    Returns:
        string jawaban yang cocok dengan salah satu choices
    """
    if not OPENROUTER_KEY:
        log("AI", "❌ OPENROUTER_KEY kosong! Set env var dulu.")
        return None

    url = "https://openrouter.ai/api/v1/chat/completions"
    headers = {
        "Authorization": f"Bearer {OPENROUTER_KEY}",
        "Content-Type": "application/json",
        "HTTP-Referer": "https://github.com/auto-mancing",
        "X-Title": "Auto Mancing Bot"
    }

    # Susun user message
    choices_str = " | ".join(str(c) for c in choices)
    user_text = f"Soal: {prompt}\nPilihan yang tersedia: [{choices_str}]\nJawab HANYA dengan salah satu pilihan di atas."

    content = [{"type": "text", "text": user_text}]

    # Kalau ada gambar, sertakan
    if img_base64:
        content.insert(0, {
            "type": "image_url",
            "image_url": {"url": f"data:image/jpeg;base64,{img_base64}"}
        })

    payload = {
        "model": OPENROUTER_MODEL,
        "messages": [
            {"role": "system", "content": SYSTEM_PROMPT},
            {"role": "user",   "content": content}
        ],
        "temperature": 0,
        "max_tokens": 10
    }

    try:
        async with aiohttp.ClientSession() as session:
            async with session.post(
                url, headers=headers, json=payload,
                timeout=aiohttp.ClientTimeout(total=25)
            ) as resp:
                if resp.status == 200:
                    data = await resp.json()
                    raw = data["choices"][0]["message"]["content"].strip()
                    log("AI", f"🤖 AI jawab: '{raw}'")

                    # Cocokkan jawaban AI dengan pilihan yang ada
                    matched = match_answer(raw, choices)
                    if matched:
                        log("AI", f"✅ Matched ke pilihan: '{matched}'")
                        return matched

                    log("AI", f"⚠️ Jawaban AI '{raw}' tidak cocok dengan pilihan {choices}")
                    return raw  # tetap kirim raw sebagai fallback

                body = await resp.text()
                log("AI", f"⚠️ HTTP {resp.status}: {body[:300]}")

    except asyncio.TimeoutError:
        log("AI", "❌ Timeout OpenRouter (25s)")
    except Exception as e:
        log("AI", f"❌ Exception: {e}")

    return None


def match_answer(ai_answer: str, choices: list) -> str | None:
    """
    Cocokkan jawaban AI dengan list pilihan.
    Case-insensitive, strip whitespace.
    """
    ai_clean = ai_answer.strip().lower()
    for ch in choices:
        ch_str = str(ch).strip()
        if ch_str.lower() == ai_clean:
            return ch_str
        # coba exact match angka
        if re.fullmatch(r'\d+', ai_clean) and re.fullmatch(r'\d+', ch_str):
            if int(ai_clean) == int(ch_str):
                return ch_str
    return None


# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
#  Parser: ekstrak teks soal & button dari pesan
# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
def extract_question_and_choices(message: Message) -> tuple[str, list]:
    """
    Kembalikan (teks_soal, list_pilihan_dari_button).
    Kalau tidak ada button, choices = [].
    """
    text = (message.text or "") + (message.caption or "")

    choices = []
    if message.reply_markup:
        try:
            for row in message.reply_markup.inline_keyboard:
                for btn in row:
                    choices.append(btn.text.strip())
        except Exception:
            pass

    return text.strip(), choices


def is_captcha(text: str) -> bool:
    """Deteksi apakah pesan ini adalah captcha/verifikasi."""
    keywords = [
        "verifikasi", "captcha", "hitung berapa", "hitung ",
        "pilih emoji", "berapa hasil", "lanjutkan pola",
        "jawab pertanyaan", "pilih dalam"
    ]
    low = text.lower()
    return any(k in low for k in keywords)


# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
#  Helper: kirim pesan aman (handle FloodWait)
# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
async def safe_send(client: Client, chat_id, text: str):
    try:
        await client.send_message(chat_id, text)
    except FloodWait as e:
        log("FLOOD", f"⏳ FloodWait {e.value}s...")
        await asyncio.sleep(e.value + 1)
        await client.send_message(chat_id, text)
    except Exception as e:
        log("SEND", f"❌ Gagal kirim: {e}")


# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
#  Handler utama pesan dari fishing bot
# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
@app.on_message(filters.chat(FISHING_BOT))
async def handle_bot_msg(client: Client, message: Message):
    question, choices = extract_question_and_choices(message)

    # ── Captcha terdeteksi ──────────────────────────────────
    if is_captcha(question):
        log("CAPTCHA", f"🚨 Captcha terdeteksi!")
        log("CAPTCHA", f"📝 Soal: {question[:100]}")
        log("CAPTCHA", f"🔘 Pilihan: {choices}")

        # Download foto kalau ada (untuk captcha gambar/emoji)
        img_b64 = None
        if message.photo:
            log("CAPTCHA", "📸 Download foto captcha...")
            try:
                photo_bytes = await message.download(in_memory=True)
                img_b64 = base64.b64encode(photo_bytes.getvalue()).decode()
                log("CAPTCHA", f"✅ Foto di-encode ({len(img_b64)} chars)")
            except Exception as e:
                log("CAPTCHA", f"⚠️ Gagal download foto: {e}")

        # Kalau tidak ada pilihan dari button, coba parse dari teks
        if not choices:
            log("CAPTCHA", "⚠️ Tidak ada inline button, parse dari teks...")
            numbers = re.findall(r'\b\d+\b', question)
            if numbers:
                choices = numbers[-4:]  # ambil 4 angka terakhir sebagai pilihan

        answer = None

        # ── STEP 1: Coba selesaikan matematika pakai Python dulu (instant, gratis) ──
        is_math_question = any(k in question.lower() for k in [
            "berapa hasil", "hitung", "hasil dari", "+ ", "- ", "x ", "kali",
            "dibagi", "kurang", "tambah", "= ?", "=?", "pangkat", "akar", "kuadrat", "mod"
        ])
        if not img_b64 and is_math_question:
            log("MATH", "🧮 Coba selesaikan pakai Python solver...")
            answer = solve_math(question, choices)
            if answer:
                log("MATH", f"✅ Python solver berhasil: '{answer}' (hemat token AI!)")

        # ── STEP 2: Fallback ke OpenRouter AI kalau math solver gagal / ada gambar ──
        if not answer:
            log("AI", "🤖 Kirim ke OpenRouter AI...")
            answer = await call_openrouter(question, choices, img_b64)

        if answer:
            log("CAPTCHA", f"📤 Kirim jawaban: '{answer}'")
            await asyncio.sleep(1.5)  # delay biar kelihatan manusiawi
            await safe_send(client, FISHING_BOT, answer)
        else:
            log("CAPTCHA", "❌ AI tidak bisa jawab captcha ini!")
        return

    # ── Hasil mancing ──────────────────────────────────────
    if "berhasil menangkap" in question.lower():
        fish_match = re.search(r"menangkap (.+?)!", question)
        fish_name = fish_match.group(1) if fish_match else "ikan"
        is_rare = any(e in question for e in ["🦑", "🐋", "🐬", "🦈", "🐊", "🐢"])
        flag = "⭐ RARE!" if is_rare else ""
        log("HASIL", f"🐟 Dapat: {fish_name} {flag}")
        return

    # ── Pesan lain (opsional log) ───────────────────────────
    if question:
        log("MSG", question[:80])


# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
#  Loop mancing otomatis
# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
async def mancing_loop(client: Client):
    await asyncio.sleep(3)  # tunggu bot fully start
    cast_count = 0
    while True:
        cast_count += 1
        log("LOOP", f"🎣 Cast #{cast_count} — kirim /mancing")
        await safe_send(client, FISHING_BOT, "/mancing")
        log("LOOP", f"⏳ Tunggu {MANCING_INTERVAL}s sebelum cast berikutnya...")
        await asyncio.sleep(MANCING_INTERVAL)


# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
#  Entry point
# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
async def main():
    log("INIT", "🚀 Starting Auto Mancing Bot v3.0...")
    log("INIT", f"📡 Fishing bot target : @{FISHING_BOT}")
    log("INIT", f"⏱️  Interval           : {MANCING_INTERVAL}s")
    log("INIT", f"🤖 AI Model           : {OPENROUTER_MODEL}")
    log("INIT", f"🔑 OpenRouter Key     : {'✅ SET' if OPENROUTER_KEY else '❌ KOSONG!'}")

    await app.start()
    me = await app.get_me()
    log("INIT", f"✅ Login sebagai: {me.first_name} (@{me.username})")

    asyncio.create_task(mancing_loop(app))
    log("INIT", "💤 Bot berjalan... tinggal tidur aja bro!")
    await idle()
    await app.stop()


if __name__ == "__main__":
    asyncio.run(main())
