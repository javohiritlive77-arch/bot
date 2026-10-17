import asyncio
import logging
import re
from aiogram import Bot, Dispatcher, types, F
from aiogram.filters import Command
from aiogram.enums import ParseMode

# =================== SOZLAMALAR ===================
BOT_TOKEN = "8731776190:AAEOTQMGaclvDEXYoGb2ixoaMd4YbQJQhck"      # @BotFather dan olingan token
KANAL_ID = "@Luckasuzb"           # Masalan: @kanalim yoki -100123456789 (ID formatida)
ADMIN_PAROL = "/admin 7877"
# ==================================================

logging.basicConfig(level=logging.INFO)
bot = Bot(token=BOT_TOKEN)
dp = Dispatcher()

# Tasdiqlangan adminlar ro'yxati (xotirada)
authenticated_admins = set()

# Adminlarning navbatdagi posti (draft xotira)
admin_posts = {}


# Matndan @username va har qanday havolalarni (link) olib tashlash funksiyasi
def clean_text(text: str) -> str:
    if not text:
        return ""
    
    # 1. Havolalarni (https://..., http://..., t.me/..., www....) o'chirish
    url_pattern = r'(https?://\S+|www\.\S+|t\.me/\S+)'
    cleaned = re.sub(url_pattern, '', text)
    
    # 2. @username larni o'chirish
    mention_pattern = r'@[a-zA-Z0-9_]+'
    cleaned = re.sub(mention_pattern, '', cleaned)
    
    # 3. Ortiqcha bo'sh qatorlar va bo'shliqlarni tozalash
    lines = [line.strip() for line in cleaned.splitlines()]
    lines = [line for line in lines if line]  # Bo'sh qatorlarni tashlab ketish
    return "\n".join(lines).strip()


# Foydalanuvchi kanalda admin ekanligini tekshirish
async def is_channel_admin(user_id: int) -> bool:
    try:
        member = await bot.get_chat_member(chat_id=KANAL_ID, user_id=user_id)
        return member.status in ["administrator", "creator"]
    except Exception as e:
        logging.error(f"Kanal a'zosi tekshirishda xatolik: {e}")
        return False


# /start buyrug'i
@dp.message(Command("start"))
async def start_cmd(message: types.Message):
    await message.answer(
        "Assalomu alaykum!\nAdmin sifatida kirish uchun parolni yuboring (Masalan: <code>/admin 1091</code>)",
        parse_mode=ParseMode.HTML
    )


# /admin 1091 tekshiruvi
@dp.message(F.text == ADMIN_PAROL)
async def admin_auth(message: types.Message):
    user_id = message.from_user.id

    # Kanalda admin ekanligini tekshirish
    if await is_channel_admin(user_id):
        authenticated_admins.add(user_id)
        await message.answer(
            "✅ <b>Tabriklaymiz! Siz muvaffaqiyatli admin bo'ldingiz.</b>\n\n"
            "Endi istalgan narsani (matn, rasm, video yoki <b>Premium stiker</b>) yuboring.\n"
            "Post kanalga yuborilishi uchun oxirida <b>send</b> so'zini yozing.",
            parse_mode=ParseMode.HTML
        )
    else:
        await message.answer(
            f"❌ Parol to‘g‘ri, ammo siz <b>{KANAL_ID}</b> kanalida <b>admin emassiz</b>!\n"
            f"Avval botni ham, o‘zingizni ham kanalga admin qiling.",
            parse_mode=ParseMode.HTML
        )


# "send" buyrug'i kelganda postni kanalga chiqarish
@dp.message(F.text.lower() == "send")
async def send_to_channel(message: types.Message):
    user_id = message.from_user.id

    if user_id not in authenticated_admins:
        await message.answer("❌ Siz admin emassiz! Avval <code>/admin 1091</code> buyrug‘ini bering.", parse_mode=ParseMode.HTML)
        return

    post: types.Message = admin_posts.get(user_id)

    if not post:
        await message.answer("⚠️ Yuborish uchun hech qanday post topilmadi! Avval biror narsa tashlang.")
        return

    try:
        # 1. Agar stiker bo'lsa (Barcha Premium stikerlar to'g'ridan-to'g'ri o'tadi)
        if post.sticker:
            await bot.send_sticker(chat_id=KANAL_ID, sticker=post.sticker.file_id)

        # 2. Agar oddiy matn bo'lsa
        elif post.text:
            cleaned_content = clean_text(post.text)
            if not cleaned_content:
                cleaned_content = " "  # Agar hamma narsa link bo'lib o'chib ketgan bo'lsa
            await bot.send_message(chat_id=KANAL_ID, text=cleaned_content)

        # 3. Rasm bo'lsa
        elif post.photo:
            cleaned_caption = clean_text(post.caption)
            await bot.send_photo(
                chat_id=KANAL_ID,
                photo=post.photo[-1].file_id,
                caption=cleaned_caption if cleaned_caption else None
            )

        # 4. Video bo'lsa
        elif post.video:
            cleaned_caption = clean_text(post.caption)
            await bot.send_video(
                chat_id=KANAL_ID,
                video=post.video.file_id,
                caption=cleaned_caption if cleaned_caption else None
            )

        # 5. GIF / Animatsiya bo'lsa
        elif post.animation:
            cleaned_caption = clean_text(post.caption)
            await bot.send_animation(
                chat_id=KANAL_ID,
                animation=post.animation.file_id,
                caption=cleaned_caption if cleaned_caption else None
            )

        # 6. Fayl / Audio yoki boshqa format bo'lsa
        elif post.document:
            cleaned_caption = clean_text(post.caption)
            await bot.send_document(
                chat_id=KANAL_ID,
                document=post.document.file_id,
                caption=cleaned_caption if cleaned_caption else None
            )

        await message.answer("🚀 <b>Post tozalanib, kanalga muvaffaqiyatli joylandi!</b>", parse_mode=ParseMode.HTML)
        # Xotirani tozalaymiz
        del admin_posts[user_id]

    except Exception as e:
        await message.answer(f"❌ Kanalga yuborishda xatolik yuz berdi:\n<code>{e}</code>", parse_mode=ParseMode.HTML)


# Admin tashlagan barcha materiallarni (stiker, rasm, matn va h.k.) qabul qilib saqlash
@dp.message()
async def receive_post(message: types.Message):
    user_id = message.from_user.id

    if user_id not in authenticated_admins:
        return  # Admin bo'lmaganlarga e'tibor bermaydi

    # Postni xotiraga saqlaymiz
    admin_posts[user_id] = message

    # Foydalanuvchiga xabar beramiz
    info_text = "📥 <b>Post qabul qilindi!</b>\n"
    if message.caption or message.text:
        info_text += "<i>Matndagi barcha @ va havolalar avtomatik olib tashlanadi.</i>\n"
    info_text += "\nKanalga chiqarish uchun <b>send</b> deb yozib yuboring."

    await message.reply(info_text, parse_mode=ParseMode.HTML)


async def main():
    print("Bot muvaffaqiyatli ishga tushirildi...")
    await dp.start_polling(bot)

if __name__ == "__main__":
    asyncio.run(main())
