# main.py
import os
import time
import uuid
import requests
import logging
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import Application, CommandHandler, MessageHandler, CallbackQueryHandler, ContextTypes, filters

# استيراد الوحدات
from config import BOT_TOKEN, FREE_IMAGES_LIMIT, CURRENCY
from database import db
from admin_panel import (
    ADMIN_IDS, admin_panel, admin_balance_menu, admin_add_balance_start,
    admin_deduct_balance_start, admin_handle_balance_input,
    admin_subscriptions_menu, admin_activate_sub_start, admin_deactivate_sub_start,
    admin_handle_subscription_input, admin_payment_methods_menu,
    admin_toggle_payment_method, admin_stats_menu, admin_find_user_start,
    admin_handle_find_user
)
from subscription import (
    force_subscription_middleware, check_subscription_callback,
    subscription_menu, buy_balance_menu, buy_subscription_menu,
    payment_methods_menu, process_payment, complete_payment
)

# إعداد اللوق
logging.basicConfig(format='%(asctime)s - %(levelname)s - %(message)s', level=logging.INFO)
logger = logging.getLogger(__name__)

# إنشاء المجلدات
os.makedirs("images", exist_ok=True)
os.makedirs("results", exist_ok=True)

# ================== معالج الصور ==================
try:
    from PIL import Image
    PIL_AVAILABLE = True
except ImportError:
    PIL_AVAILABLE = False
    print("⚠️ Pillow غير متاحة")

class ImageOptimizer:
    @staticmethod
    def optimize_image(input_path, output_path, quality=90):
        if not PIL_AVAILABLE:
            try:
                with open(input_path, 'rb') as f_in, open(output_path, 'wb') as f_out:
                    f_out.write(f_in.read())
                return True
            except:
                return False
        try:
            img = Image.open(input_path)
            if img.mode in ('RGBA', 'LA', 'P'):
                rgb_img = Image.new('RGB', img.size, (255, 255, 255))
                if img.mode == 'P':
                    img = img.convert('RGBA')
                if img.mode == 'RGBA':
                    rgb_img.paste(img, mask=img.split()[3])
                else:
                    rgb_img.paste(img)
                img = rgb_img
            max_size = 2000
            if img.size[0] > max_size or img.size[1] > max_size:
                img.thumbnail((max_size, max_size), Image.Resampling.LANCZOS)
            img.save(output_path, 'JPEG', quality=quality, optimize=True)
            return True
        except Exception as e:
            logger.error(f"خطأ في تحسين الصورة: {e}")
            return False

class Processor:
    URL = "https://pornworks.com/api/v2"

    def upload(self, path):
        try:
            with open(path, 'rb') as f:
                files = {'file': (os.path.basename(path), f, 'image/jpeg')}
                headers = {'User-Agent': 'Mozilla/5.0', 'Accept': 'application/json'}
                r = requests.put(f"{self.URL}/uploads/undress", headers=headers, files=files, timeout=60)
            if r.status_code == 400 and ("child" in r.text.lower() or "adolescent" in r.text.lower()):
                return "CHILD_DETECTED"
            if r.status_code in [200, 201, 202]:
                try:
                    data = r.json()
                    return data.get("url") or data.get("data", {}).get("url")
                except:
                    return None
        except Exception as e:
            logger.error(f"خطأ في الرفع: {e}")
        return None

    def generate(self, url):
        try:
            r = requests.post(f"{self.URL}/generate/undress", headers={'User-Agent': 'Mozilla/5.0', 'Content-Type': 'application/json'}, json={"image": url, "gender": "auto"}, timeout=60)
            if r.status_code in [200, 201, 202]:
                try:
                    data = r.json()
                    return data.get("id") or data.get("data", {}).get("id")
                except:
                    return None
        except Exception as e:
            logger.error(f"خطأ في التوليد: {e}")
        return None

    def wait_done(self, gen_id):
        for _ in range(60):
            try:
                r = requests.get(f"{self.URL}/generations/{gen_id}/state", headers={'User-Agent': 'Mozilla/5.0'}, timeout=30)
                if r.status_code == 200:
                    try:
                        data = r.json()
                        state = data.get("state") or data.get("data", {}).get("state", "")
                        if state in ["done", "completed", "success", "finished", "succeeded"]:
                            return True
                    except:
                        pass
                time.sleep(2)
            except:
                time.sleep(2)
        return False

    def result(self, gen_id):
        try:
            r = requests.get(f"{self.URL}/generations/{gen_id}", headers={'User-Agent': 'Mozilla/5.0'}, timeout=60)
            if r.status_code == 200:
                try:
                    data = r.json()
                    results = data.get("results") or data.get("data", {}).get("results", {})
                    image_url = results.get("image") or results.get("output") or results.get("url") or results.get("result")
                    if image_url:
                        if not image_url.startswith("http"):
                            if image_url.startswith("//"):
                                image_url = f"https:{image_url}"
                            elif image_url.startswith("/"):
                                image_url = f"https://pornworks.com{image_url}"
                        return image_url
                except:
                    return None
        except Exception as e:
            logger.error(f"خطأ في جلب النتيجة: {e}")
        return None

processor = Processor()
optimizer = ImageOptimizer()

# ================== أوامر البوت ==================

async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not await force_subscription_middleware(update, context):
        return
    
    user_id = update.effective_user.id
    user = db.get_user(user_id)
    db.update_user(user_id, {"username": update.effective_user.username, "first_name": update.effective_user.first_name})
    
    remaining = user.get('images_limit', FREE_IMAGES_LIMIT) - user.get('images_used', 0)
    if remaining < 0:
        remaining = 0
    
    keyboard = [
        [InlineKeyboardButton("📷 رفع صورة", callback_data="upload")],
        [InlineKeyboardButton("💰 الرصيد والاشتراك", callback_data="subscription_menu")],
        [InlineKeyboardButton("ℹ️ معلومات", callback_data="info")],
    ]
    
    if user_id in ADMIN_IDS:
        keyboard.insert(2, [InlineKeyboardButton("🔐 لوحة التحكم", callback_data="admin_panel")])
    
    await update.message.reply_text(
        f"👋 أهلاً بك {update.effective_user.first_name}!\n\n💰 رصيدك: {user.get('balance', 0)} {CURRENCY}\n🎁 صور مجانية متبقية: {remaining}\n\nأرسل صورة للمعالجة:",
        reply_markup=InlineKeyboardMarkup(keyboard)
    )

async def handle_media(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not await force_subscription_middleware(update, context):
        return
    
    user_id = update.effective_user.id
    
    if not db.can_use_image(user_id):
        await update.message.reply_text(f"❌ لا يمكنك الاستخدام\n💰 رصيدك: {db.get_balance(user_id)} {CURRENCY}\nاشتر الآن من قائمة الرصيد")
        return
    
    wait_msg = await update.message.reply_text("⏳ جاري المعالجة...")
    
    try:
        uid = str(uuid.uuid4())[:8]
        image_path = f"images/{uid}.jpg"
        
        if update.message.photo:
            file = await update.message.photo[-1].get_file()
        elif update.message.document and update.message.document.mime_type.startswith('image/'):
            file = await update.message.document.get_file()
        else:
            await wait_msg.edit_text("❌ أرسل صورة فقط")
            return
        
        await file.download_to_drive(image_path)
        
        upload_result = processor.upload(image_path)
        if upload_result == "CHILD_DETECTED":
            await wait_msg.edit_text("❌ تم رفض الصورة (محتوى غير مناسب)")
            return
        if not upload_result:
            await wait_msg.edit_text("❌ فشل الرفع")
            return
        
        gen_id = processor.generate(upload_result)
        if not gen_id:
            await wait_msg.edit_text("❌ فشل بدء المعالجة")
            return
        
        if not processor.wait_done(gen_id):
            await wait_msg.edit_text("❌ انتهت المهلة")
            return
        
        result_url = processor.result(gen_id)
        if not result_url:
            await wait_msg.edit_text("❌ فشل جلب النتيجة")
            return
        
        result_response = requests.get(result_url, timeout=60)
        temp_path = f"results/temp_{uid}.jpg"
        final_path = f"results/final_{uid}.jpg"
        
        with open(temp_path, "wb") as f:
            f.write(result_response.content)
        
        optimizer.optimize_image(temp_path, final_path)
        db.use_image(user_id)
        
        with open(final_path, "rb") as f:
            await update.message.reply_document(document=f, filename=f"result_{uid}.jpg", caption="✅ تمت المعالجة!")
        
        await wait_msg.delete()
        
        for path in [image_path, temp_path, final_path]:
            try:
                if os.path.exists(path):
                    os.remove(path)
            except:
                pass
                
    except Exception as e:
        logger.error(f"خطأ: {e}")
        await wait_msg.edit_text("❌ حدث خطأ")

async def handle_text(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text("❌ أرسل صورة فقط\nاستخدم /start")

async def buttons(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    data = query.data
    
    if data == "upload":
        await query.edit_message_text("📤 أرسل الصورة الآن")
    elif data == "info":
        await query.edit_message_text("ℹ️ بوت معالجة الصور\nيدعم JPG/PNG\nالمدة: 30-60 ثانية")
    elif data == "back_to_main":
        user_id = query.from_user.id
        user = db.get_user(user_id)
        remaining = user.get('images_limit', FREE_IMAGES_LIMIT) - user.get('images_used', 0)
        keyboard = [
            [InlineKeyboardButton("📷 رفع صورة", callback_data="upload")],
            [InlineKeyboardButton("💰 الرصيد والاشتراك", callback_data="subscription_menu")],
        ]
        if user_id in ADMIN_IDS:
            keyboard.insert(1, [InlineKeyboardButton("🔐 لوحة التحكم", callback_data="admin_panel")])
        await query.edit_message_text(f"💰 رصيدك: {user.get('balance', 0)} {CURRENCY}\n🎁 صور متبقية: {remaining}", reply_markup=InlineKeyboardMarkup(keyboard))
    elif data == "admin_panel":
        context.user_data.clear()
        await admin_panel(update, context)
    elif data == "admin_balance":
        await admin_balance_menu(update, context)
    elif data == "admin_add_balance":
        await admin_add_balance_start(update, context)
    elif data == "admin_deduct_balance":
        await admin_deduct_balance_start(update, context)
    elif data == "admin_find_user":
        await admin_find_user_start(update, context)
    elif data == "admin_subscriptions":
        await admin_subscriptions_menu(update, context)
    elif data == "admin_activate_sub":
        await admin_activate_sub_start(update, context)
    elif data == "admin_deactivate_sub":
        await admin_deactivate_sub_start(update, context)
    elif data == "admin_payment_methods":
        await admin_payment_methods_menu(update, context)
    elif data.startswith("admin_toggle_method_"):
        await admin_toggle_payment_method(update, context)
    elif data == "admin_stats":
        await admin_stats_menu(update, context)
    elif data == "subscription_menu":
        await subscription_menu(update, context)
    elif data == "buy_balance":
        await buy_balance_menu(update, context)
    elif data == "buy_subscription":
        await buy_subscription_menu(update, context)
    elif data == "payment_methods":
        await payment_methods_menu(update, context)
    elif data.startswith("buy_balance_") or data.startswith("buy_sub_"):
        await process_payment(update, context)
    elif data.startswith("pay_method_"):
        await process_payment(update, context)
    elif data.startswith("payment_complete_"):
        await complete_payment(update, context)
    elif data == "check_subscription":
        await check_subscription_callback(update, context)

async def cancel(update: Update, context: ContextTypes.DEFAULT_TYPE):
    context.user_data.clear()
    await update.message.reply_text("✅ تم الإلغاء")

async def error_handler(update: Update, context: ContextTypes.DEFAULT_TYPE):
    logger.error(f"خطأ: {context.error}")

# ================== التشغيل ==================
def main():
    if not BOT_TOKEN:
        print("❌ التوكن غير موجود!")
        return
    
    print("=" * 50)
    print("🤖 البوت يعمل على Kuberns")
    print(f"👥 عدد المشرفين: {len(ADMIN_IDS)}")
    print("=" * 50)
    
    app = Application.builder().token(BOT_TOKEN).build()
    
    app.add_handler(CommandHandler("start", start))
    app.add_handler(CommandHandler("cancel", cancel))
    app.add_handler(CallbackQueryHandler(buttons))
    app.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, admin_handle_balance_input))
    app.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, admin_handle_subscription_input))
    app.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, admin_handle_find_user))
    app.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, handle_text))
    app.add_handler(MessageHandler(filters.PHOTO | filters.Document.IMAGE, handle_media))
    app.add_error_handler(error_handler)
    
    app.run_polling()

if __name__ == "__main__":
    main()
