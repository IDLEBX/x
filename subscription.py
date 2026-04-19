# subscription.py
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import ContextTypes
from database import db
from config import PAYMENT_METHODS, SUBSCRIPTION_PRICE, CURRENCY, FREE_IMAGES_LIMIT, REQUIRED_CHANNELS
import uuid

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
    
    from admin_panel import ADMIN_IDS
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
    
    keyboard = [
        [InlineKeyboardButton("💰 شراء رصيد", callback_data="buy_balance")],
        [InlineKeyboardButton("📅 شراء اشتراك", callback_data="buy_subscription")],
        [InlineKeyboardButton("💳 طرق الدفع", callback_data="payment_methods")],
        [InlineKeyboardButton("🔙 رجوع", callback_data="back_to_main")]
    ]
    
    status = "✅ مفعل" if db.check_subscription(user_id) else "❌ غير مفعل"
    message = f"💎 **الرصيد**\n\n💰 رصيدك: {balance} {CURRENCY}\n📅 الاشتراك: {status}\n🎁 صور مجانية: {FREE_IMAGES_LIMIT}"
    
    if update.callback_query:
        await update.callback_query.edit_message_text(message, reply_markup=InlineKeyboardMarkup(keyboard), parse_mode='Markdown')
    else:
        await update.message.reply_text(message, reply_markup=InlineKeyboardMarkup(keyboard), parse_mode='Markdown')

async def buy_balance_menu(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    
    keyboard = [
        [InlineKeyboardButton("💵 10 صور - 10 ريال", callback_data="buy_balance_10")],
        [InlineKeyboardButton("💵 25 صورة - 20 ريال", callback_data="buy_balance_25")],
        [InlineKeyboardButton("💵 50 صورة - 35 ريال", callback_data="buy_balance_50")],
        [InlineKeyboardButton("🔙 رجوع", callback_data="subscription_menu")],
    ]
    await query.edit_message_text("💰 **شراء رصيد**", reply_markup=InlineKeyboardMarkup(keyboard), parse_mode='Markdown')

async def buy_subscription_menu(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    
    keyboard = [
        [InlineKeyboardButton("📅 شهر واحد", callback_data="buy_sub_1")],
        [InlineKeyboardButton("📅 3 أشهر", callback_data="buy_sub_3")],
        [InlineKeyboardButton("🔙 رجوع", callback_data="subscription_menu")],
    ]
    await query.edit_message_text(f"📅 **اشتراك**\nسعر الشهر: {SUBSCRIPTION_PRICE} {CURRENCY}", reply_markup=InlineKeyboardMarkup(keyboard), parse_mode='Markdown')

async def payment_methods_menu(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    
    keyboard = []
    for method_id, method_data in PAYMENT_METHODS.items():
        if method_data["enabled"]:
            keyboard.append([InlineKeyboardButton(method_data["name"], callback_data=f"pay_method_{method_id}")])
    keyboard.append([InlineKeyboardButton("🔙 رجوع", callback_data="subscription_menu")])
    
    await query.edit_message_text("💳 **طرق الدفع**", reply_markup=InlineKeyboardMarkup(keyboard))

async def process_payment(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    
    data = query.data
    user_id = query.from_user.id
    
    if data.startswith("buy_balance_"):
        amount = int(data.replace("buy_balance_", ""))
        prices = {10: 10, 25: 20, 50: 35}
        price = prices.get(amount, 10)
        context.user_data['pending_payment'] = {'type': 'balance', 'amount': amount, 'price': price, 'item_name': f"{amount} صورة"}
    elif data.startswith("buy_sub_"):
        months = int(data.replace("buy_sub_", ""))
        price = SUBSCRIPTION_PRICE * months
        context.user_data['pending_payment'] = {'type': 'subscription', 'months': months, 'price': price, 'item_name': f"اشتراك {months} شهر"}
    elif data.startswith("pay_method_"):
        method_id = data.replace("pay_method_", "")
        payment_info = context.user_data.get('pending_payment')
        if not payment_info:
            await query.edit_message_text("❌ حدث خطأ")
            return
        
        method_data = PAYMENT_METHODS.get(method_id, {})
        payment_id = str(uuid.uuid4())[:8]
        db.add_payment_request(payment_id, user_id, payment_info['price'], method_id)
        
        keyboard = [[InlineKeyboardButton("✅ تم الدفع", callback_data=f"payment_complete_{payment_id}")]]
        message = f"💳 **طلب دفع**\n\nالمنتج: {payment_info['item_name']}\nالمبلغ: {payment_info['price']} {CURRENCY}\n\n📝 تعليمات: {method_data.get('instructions', '')}\n\n🆔 معرف الطلب: `{payment_id}`"
        await query.edit_message_text(message, reply_markup=InlineKeyboardMarkup(keyboard), parse_mode='Markdown')
        return
    
    # عرض طرق الدفع
    keyboard = [[InlineKeyboardButton(m["name"], callback_data=f"pay_method_{mid}")] for mid, m in PAYMENT_METHODS.items() if m["enabled"]]
    keyboard.append([InlineKeyboardButton("🔙 رجوع", callback_data="subscription_menu")])
    await query.edit_message_text(f"🛒 **المنتج: {context.user_data['pending_payment']['item_name']}**\nالمبلغ: {context.user_data['pending_payment']['price']} {CURRENCY}", reply_markup=InlineKeyboardMarkup(keyboard))

async def complete_payment(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    
    payment_id = query.data.replace("payment_complete_", "")
    db.complete_payment(payment_id)
    payment = db.payments.get(payment_id)
    
    if not payment:
        await query.edit_message_text("❌ لم يتم العثور على الطلب")
        return
    
    user_id = payment['user_id']
    pending = context.user_data.get('pending_payment', {})
    
    if pending.get('type') == 'balance':
        db.add_balance(user_id, pending.get('amount', 0))
        await query.edit_message_text(f"✅ تم الدفع! تمت إضافة {pending.get('amount', 0)} صورة.\nرصيدك: {db.get_balance(user_id)} صورة")
    elif pending.get('type') == 'subscription':
        db.activate_subscription(user_id, days=pending.get('months', 1)*30)
        await query.edit_message_text(f"✅ تم الدفع! تم تفعيل اشتراكك لمدة {pending.get('months', 1)} شهر")
    
    context.user_data.pop('pending_payment', None)
