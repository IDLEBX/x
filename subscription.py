# subscription.py
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import ContextTypes
from database import db
from config import PAYMENT_METHODS, SUBSCRIPTION_PRICE, CURRENCY, FREE_IMAGES_LIMIT, REQUIRED_CHANNELS, ADMIN_IDS
import uuid
import os

async def check_required_subscriptions(context: ContextTypes.DEFAULT_TYPE, user_id: int) -> tuple:
    if not REQUIRED_CHANNELS:
        return True, []
    not_subscribed = []
    for channel in REQUIRED_CHANNELS:
        try:
            channel_username = channel.replace('@', '')
            chat_member = await context.bot.get_chat_member(f"@{channel_username}", user_id)
            if chat_member.status in ['left', 'kicked']:
                not_subscribed.append(channel_username)
        except:
            pass
    return len(not_subscribed) == 0, not_subscribed

async def force_subscription_middleware(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not update.effective_user:
        return True
    user_id = update.effective_user.id
    if user_id in ADMIN_IDS:
        return True
    is_subscribed, not_subscribed = await check_required_subscriptions(context, user_id)
    if not is_subscribed:
        keyboard = []
        for channel in not_subscribed:
            keyboard.append([InlineKeyboardButton(f"📢 اشترك في {channel}", url=f"https://t.me/{channel}")])
        keyboard.append([InlineKeyboardButton("🔄 تحقق", callback_data="check_subscription")])
        message = "🔒 **اشتراك إجباري**\n\nيجب الاشتراك في:\n" + "\n".join([f"• @{ch}" for ch in not_subscribed])
        if update.callback_query:
            await update.callback_query.answer()
            await update.callback_query.edit_message_text(message, reply_markup=InlineKeyboardMarkup(keyboard), parse_mode='Markdown')
        else:
            await update.message.reply_text(message, reply_markup=InlineKeyboardMarkup(keyboard), parse_mode='Markdown')
        return False
    return True

async def check_subscription_callback(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    user_id = query.from_user.id
    is_subscribed, not_subscribed = await check_required_subscriptions(context, user_id)
    if is_subscribed:
        await query.edit_message_text("✅ تم التحقق! استخدم /start")
    else:
        keyboard = [[InlineKeyboardButton(f"📢 اشترك", url=f"https://t.me/{ch}")] for ch in not_subscribed]
        keyboard.append([InlineKeyboardButton("🔄 تحقق", callback_data="check_subscription")])
        message = "❌ لا تزال غير مشترك:\n" + "\n".join([f"• @{ch}" for ch in not_subscribed])
        await query.edit_message_text(message, reply_markup=InlineKeyboardMarkup(keyboard))

async def subscription_menu(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = update.effective_user.id
    user_data = db.get_user(user_id)
    balance = user_data.get('balance', 0)
    has_subscription = db.check_subscription(user_id)
    
    keyboard = [
        [InlineKeyboardButton("💰 شراء رصيد", callback_data="buy_balance")],
        [InlineKeyboardButton("📅 شراء اشتراك", callback_data="buy_subscription")],
    ]
    if has_subscription:
        keyboard.append([InlineKeyboardButton("📅 اشتراكي", callback_data="my_subscription")])
    keyboard.append([InlineKeyboardButton("💳 طرق الدفع", callback_data="payment_methods")])
    keyboard.append([InlineKeyboardButton("🔙 رجوع", callback_data="back_to_main")])
    
    status = "✅ مفعل" if has_subscription else "❌ غير مفعل"
    remaining = user_data.get('images_limit', FREE_IMAGES_LIMIT) - user_data.get('images_used', 0)
    if remaining < 0:
        remaining = 0
    
    message = (
        f"💎 **الرصيد والاشتراك**\n\n"
        f"💰 رصيدك: {balance} {CURRENCY}\n"
        f"📅 الاشتراك: {status}\n"
        f"🎁 صور مجانية متبقية: {remaining}\n\n"
        f"📌 سعر الاشتراك: {SUBSCRIPTION_PRICE} {CURRENCY}/شهر\n"
        f"✨ كل 1 {CURRENCY} = صورة واحدة"
    )
    
    if update.callback_query:
        await update.callback_query.edit_message_text(message, reply_markup=InlineKeyboardMarkup(keyboard), parse_mode='Markdown')
    else:
        await update.message.reply_text(message, reply_markup=InlineKeyboardMarkup(keyboard), parse_mode='Markdown')

async def my_subscription_info(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    user_id = query.from_user.id
    user_data = db.get_user(user_id)
    if not db.check_subscription(user_id):
        await query.edit_message_text("❌ ليس لديك اشتراك نشط")
        return
    expiry = user_data.get('subscription_expiry', 'غير معروف').split('T')[0]
    message = f"📅 **اشتراكك**\n\n✅ الحالة: مفعل\n⏰ ينتهي: {expiry}\n\n✨ صور غير محدودة!"
    keyboard = [[InlineKeyboardButton("🔙 رجوع", callback_data="subscription_menu")]]
    await query.edit_message_text(message, reply_markup=InlineKeyboardMarkup(keyboard), parse_mode='Markdown')

async def buy_balance_menu(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    keyboard = [
        [InlineKeyboardButton("💵 10 صور - 10 ريال", callback_data="buy_balance_10")],
        [InlineKeyboardButton("💵 25 صورة - 20 ريال", callback_data="buy_balance_25")],
        [InlineKeyboardButton("💵 50 صورة - 35 ريال", callback_data="buy_balance_50")],
        [InlineKeyboardButton("💵 100 صورة - 60 ريال", callback_data="buy_balance_100")],
        [InlineKeyboardButton("🔙 رجوع", callback_data="subscription_menu")],
    ]
    await query.edit_message_text("💰 **شراء رصيد**\nاختر الباقة:", reply_markup=InlineKeyboardMarkup(keyboard), parse_mode='Markdown')

async def buy_subscription_menu(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    keyboard = [
        [InlineKeyboardButton("📅 شهر واحد", callback_data="buy_sub_1")],
        [InlineKeyboardButton("📅 3 أشهر - خصم 10%", callback_data="buy_sub_3")],
        [InlineKeyboardButton("📅 6 أشهر - خصم 20%", callback_data="buy_sub_6")],
        [InlineKeyboardButton("📅 سنة - خصم 30%", callback_data="buy_sub_12")],
        [InlineKeyboardButton("🔙 رجوع", callback_data="subscription_menu")],
    ]
    await query.edit_message_text(
        f"📅 **شراء اشتراك**\nسعر الشهر: {SUBSCRIPTION_PRICE} {CURRENCY}\n"
        f"• 3 أشهر: {int(SUBSCRIPTION_PRICE * 3 * 0.9)} {CURRENCY}\n"
        f"• 6 أشهر: {int(SUBSCRIPTION_PRICE * 6 * 0.8)} {CURRENCY}\n"
        f"• سنة: {int(SUBSCRIPTION_PRICE * 12 * 0.7)} {CURRENCY}",
        reply_markup=InlineKeyboardMarkup(keyboard), parse_mode='Markdown'
    )

async def payment_methods_menu(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    keyboard = []
    for method_id, method_data in PAYMENT_METHODS.items():
        if method_data["enabled"]:
            keyboard.append([InlineKeyboardButton(method_data["name"], callback_data=f"select_method_{method_id}")])
    keyboard.append([InlineKeyboardButton("🔙 رجوع", callback_data="subscription_menu")])
    await query.edit_message_text("💳 **طرق الدفع**", reply_markup=InlineKeyboardMarkup(keyboard))

async def select_payment_method(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    method_id = query.data.replace("select_method_", "")
    method_data = PAYMENT_METHODS.get(method_id, {})
    
    purchase = context.user_data.get('pending_purchase', {})
    if not purchase:
        await query.edit_message_text("❌ حدث خطأ، ابدأ من جديد")
        return
    
    payment_id = str(uuid.uuid4())[:8]
    user_id = query.from_user.id
    
    db.add_payment_request(payment_id, user_id, purchase['price'], method_id)
    db.payments[payment_id]['product_type'] = purchase['type']
    db.payments[payment_id]['product_amount'] = purchase['amount']
    db.payments[payment_id]['product_name'] = purchase['item_name']
    db.save_payments()
    
    context.user_data['current_payment_id'] = payment_id
    
    message = (
        f"💳 **طلب دفع**\n\n"
        f"📦 المنتج: {purchase['item_name']}\n"
        f"💰 المبلغ: {purchase['price']} {CURRENCY}\n"
        f"💳 الطريقة: {method_data.get('name', method_id)}\n\n"
        f"📝 تعليمات الدفع:\n{method_data.get('instructions', 'اتبع التعليمات')}\n\n"
        f"🆔 معرف الطلب: `{payment_id}`\n\n"
        "📸 اضغط على الزر أدناه وأرسل صورة الإيصال"
    )
    
    keyboard = [
        [InlineKeyboardButton("📸 أرسل الإيصال", callback_data="send_receipt")],
        [InlineKeyboardButton("❌ إلغاء", callback_data="subscription_menu")]
    ]
    await query.edit_message_text(message, reply_markup=InlineKeyboardMarkup(keyboard), parse_mode='Markdown')

async def send_receipt_request(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    if not context.user_data.get('current_payment_id'):
        await query.edit_message_text("❌ لا يوجد طلب نشط")
        return
    context.user_data['awaiting_receipt'] = True
    await query.edit_message_text("📸 أرسل صورة الإيصال الآن")

async def handle_receipt(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not context.user_data.get('awaiting_receipt'):
        return
    
    user_id = update.effective_user.id
    payment_id = context.user_data.get('current_payment_id')
    if not payment_id:
        await update.message.reply_text("❌ لا يوجد طلب نشط")
        context.user_data.pop('awaiting_receipt', None)
        return
    
    payment = db.payments.get(payment_id)
    if not payment:
        await update.message.reply_text("❌ طلب غير موجود")
        context.user_data.clear()
        return
    
    if update.message.photo:
        photo = update.message.photo[-1]
        file = await photo.get_file()
        os.makedirs("receipts", exist_ok=True)
        await file.download_to_drive(f"receipts/{payment_id}.jpg")
        
        for admin_id in ADMIN_IDS:
            try:
                with open(f"receipts/{payment_id}.jpg", 'rb') as f:
                    await context.bot.send_photo(
                        admin_id,
                        photo=f,
                        caption=f"📸 **إيصال دفع جديد**\n\n🆔 الطلب: `{payment_id}`\n👤 المستخدم: {update.effective_user.first_name}\n💰 المبلغ: {payment['amount']} {CURRENCY}",
                        parse_mode='Markdown'
                    )
            except:
                pass
        
        await update.message.reply_text(
            "✅ تم استلام الإيصال!\nسيتم مراجعته وتأكيده قريباً."
        )
        context.user_data.clear()
    else:
        await update.message.reply_text("❌ أرسل صورة الإيصال")

async def process_purchase(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    data = query.data
    
    if data.startswith("buy_balance_"):
        amount = int(data.replace("buy_balance_", ""))
        prices = {10: 10, 25: 20, 50: 35, 100: 60}
        price = prices.get(amount, 10)
        context.user_data['pending_purchase'] = {'type': 'balance', 'amount': amount, 'price': price, 'item_name': f"{amount} صورة"}
    elif data.startswith("buy_sub_"):
        months = int(data.replace("buy_sub_", ""))
        prices = {1: SUBSCRIPTION_PRICE, 3: int(SUBSCRIPTION_PRICE * 3 * 0.9), 6: int(SUBSCRIPTION_PRICE * 6 * 0.8), 12: int(SUBSCRIPTION_PRICE * 12 * 0.7)}
        price = prices.get(months, SUBSCRIPTION_PRICE)
        context.user_data['pending_purchase'] = {'type': 'subscription', 'amount': months, 'price': price, 'item_name': f"اشتراك {months} شهر"}
    
    keyboard = [[InlineKeyboardButton(m["name"], callback_data=f"select_method_{mid}")] for mid, m in PAYMENT_METHODS.items() if m["enabled"]]
    keyboard.append([InlineKeyboardButton("🔙 رجوع", callback_data="subscription_menu")])
    await query.edit_message_text(f"🛒 {context.user_data['pending_purchase']['item_name']}\n💰 {context.user_data['pending_purchase']['price']} {CURRENCY}\n\nاختر طريقة الدفع:", reply_markup=InlineKeyboardMarkup(keyboard))

async def cancel_subscription(update: Update, context: ContextTypes.DEFAULT_TYPE):
    context.user_data.clear()
    await update.message.reply_text("✅ تم الإلغاء")
