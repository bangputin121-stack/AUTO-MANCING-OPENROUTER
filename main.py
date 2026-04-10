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
def extract_question_and_choices(message: Message):
    """
    Kembalikan (teks_soal, list_button_objects, list_teks_pilihan).
    button_objects diperlukan untuk request_callback (klik button).
    """
    text = (message.text or "") + (message.caption or "")

    buttons     = []  # object button asli (untuk di-klik)
    choices_txt = []  # teks dari button (untuk dikirim ke AI)

    if message.reply_markup:
        try:
            for row in message.reply_markup.inline_keyboard:
                for btn in row:
                    buttons.append(btn)
                    choices_txt.append(btn.text.strip())
        except Exception:
            pass

    return text.strip(), buttons, choices_txt


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
#  Helper: klik inline button (cara benar jawab captcha)
# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
async def click_button(client: Client, message: Message, btn_text: str, buttons: list) -> bool:
    """
    Cari button dengan teks = btn_text lalu klik (request_callback).
    Return True kalau berhasil, False kalau gagal.
    """
    # Cari button yang cocok (exact atau strip)
    target_btn = None
    for btn in buttons:
        if btn.text.strip() == btn_text.strip():
            target_btn = btn
            break

    if not target_btn:
        log("CLICK", f"⚠️ Button '{btn_text}' tidak ditemukan di markup")
        return False

    try:
        await client.request_callback_answer(
            chat_id    = message.chat.id,
            message_id = message.id,
            callback_data = target_btn.callback_data
        )
        log("CLICK", f"✅ Berhasil klik button: '{btn_text}'")
        return True
    except Exception as e:
        log("CLICK", f"❌ Gagal klik button: {e}")
        return False


# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
#  Helper: kirim pesan teks aman (handle FloodWait)
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
    question, buttons, choices = extract_question_and_choices(message)

    # ── Captcha terdeteksi ──────────────────────────────────
    if is_captcha(question):
        log("CAPTCHA", f"🚨 Captcha terdeteksi!")
        log("CAPTCHA", f"📝 Soal: {question[:120]}")
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

        # Kalau tidak ada button sama sekali, coba parse angka dari teks
        if not choices:
            log("CAPTCHA", "⚠️ Tidak ada inline button, parse dari teks...")
            numbers = re.findall(r"\d+", question)
            if numbers:
                choices = numbers[-4:]

        answer = None

        # ── STEP 1: Python math solver (instant, tanpa AI) ──
        is_math_question = any(k in question.lower() for k in [
            "berapa hasil", "hitung", "hasil dari", "tambah", "kurang",
            "kali", "bagi", "pangkat", "akar", "kuadrat", "mod", "sisa",
            "+ ", "- ", "x ", "× ", "÷ ", "= ?", "=?"
        ])
        if not img_b64 and is_math_question:
            log("MATH", "🧮 Coba Python solver...")
            answer = solve_math(question, choices)
            if answer:
                log("MATH", f"✅ Python solver: '{answer}'")

        # ── STEP 2: OpenRouter AI (untuk emoji, gambar, pola) ──
        if not answer:
            log("AI", "🤖 Kirim ke OpenRouter AI...")
            answer = await call_openrouter(question, choices, img_b64)

        if not answer:
            log("CAPTCHA", "❌ Tidak bisa jawab captcha!")
            return

        log("CAPTCHA", f"💡 Jawaban: '{answer}'")
        await asyncio.sleep(1.5)

        # ── STEP 3: Klik button kalau ada, fallback kirim teks ──
        if buttons:
            clicked = await click_button(client, message, answer, buttons)
            if not clicked:
                # Kalau klik gagal, kirim teks sebagai fallback
                log("CAPTCHA", "⚠️ Klik gagal, kirim teks sebagai fallback...")
                await safe_send(client, FISHING_BOT, answer)
        else:
            await safe_send(client, FISHING_BOT, answer)
        return

    # ── Hasil mancing ──────────────────────────────────────
    if "berhasil menangkap" in question.lower():
        fish_match = re.search(r"menangkap (.+?)!", question)
        fish_name = fish_match.group(1) if fish_match else "ikan"
        is_rare = any(e in question for e in ["🦑", "🐋", "🐬", "🦈", "🐊", "🐢"])
        flag = "⭐ RARE!" if is_rare else ""
        log("HASIL", f"🐟 Dapat: {fish_name} {flag}")
        return

    # ── Pesan lain ─────────────────────────────────────────
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
