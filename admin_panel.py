# admin_panel.py
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import ContextTypes
from database import db
from config import PAYMENT_METHODS, SUBSCRIPTION_PRICE, CURRENCY
import re

# ================== معرفات المشرفين ==================
# ⚠️ هام: ضع معرف التليجرام الخاص بك هنا
# اذهب إلى @userinfobot لمعرفة معرفك
ADMIN_IDS = [
    7240148750,  # 👈 غير هذا الرقم إلى معرفك الحقيقي
]

async def admin_panel(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """عرض لوحة تحكم المشرف"""
    user_id = update.effective_user.id
    
    if user_id not in ADMIN_IDS:
        await update.message.reply_text("⛔ غير مصرح لك")
        return
    
    stats = db.get_stats()
    
    keyboard = [
        [InlineKeyboardButton("💰 إدارة الرصيد", callback_data="admin_balance")],
        [InlineKeyboardButton("📅 إدارة الاشتراكات", callback_data="admin_subscriptions")],
        [InlineKeyboardButton("💳 طرق الدفع", callback_data="admin_payment_methods")],
        [InlineKeyboardButton("📊 إحصائيات", callback_data="admin_stats")],
        [InlineKeyboardButton("🔙 رجوع", callback_data="back_to_main")]
    ]
    
    message = (
        f"🔐 **لوحة التحكم**\n\n"
        f"👥 المستخدمين: {stats['total_users']}\n"
        f"✅ اشتراكات نشطة: {stats['active_subscriptions']}\n"
        f"💰 الرصيد الكلي: {stats['total_balance']} {CURRENCY}"
    )
    
    await update.message.reply_text(message, reply_markup=InlineKeyboardMarkup(keyboard), parse_mode='Markdown')

async def admin_balance_menu(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    
    keyboard = [
        [InlineKeyboardButton("➕ إضافة رصيد", callback_data="admin_add_balance")],
        [InlineKeyboardButton("➖ خصم رصيد", callback_data="admin_deduct_balance")],
        [InlineKeyboardButton("🔙 رجوع", callback_data="admin_panel")]
    ]
    
    await query.edit_message_text("💰 **إدارة الرصيد**", reply_markup=InlineKeyboardMarkup(keyboard), parse_mode='Markdown')

async def admin_add_balance_start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    context.user_data['admin_action'] = 'add_balance'
    await query.edit_message_text("➕ أرسل: `معرف_المستخدم المبلغ`\nمثال: `123456789 50`", parse_mode='Markdown')

async def admin_deduct_balance_start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    context.user_data['admin_action'] = 'deduct_balance'
    await query.edit_message_text("➖ أرسل: `معرف_المستخدم المبلغ`\nمثال: `123456789 20`", parse_mode='Markdown')

async def admin_handle_balance_input(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = update.effective_user.id
    if user_id not in ADMIN_IDS:
        return
    
    action = context.user_data.get('admin_action')
    if action not in ['add_balance', 'deduct_balance']:
        return
    
    text = update.message.text.strip()
    match = re.match(r'^(\d+)\s+(\d+(?:\.\d+)?)$', text)
    if not match:
        await update.message.reply_text("❌ تنسيق خاطئ. أرسل: `معرف_المستخدم المبلغ`", parse_mode='Markdown')
        return
    
    target_id = int(match.group(1))
    amount = float(match.group(2))
    
    if action == 'add_balance':
        new_balance = db.add_balance(target_id, amount)
        await update.message.reply_text(f"✅ تمت إضافة {amount} {CURRENCY}\n💰 الرصيد الجديد: {new_balance}")
    else:
        success = db.deduct_balance(target_id, amount)
        if success:
            await update.message.reply_text(f"✅ تم خصم {amount} {CURRENCY}")
        else:
            await update.message.reply_text(f"❌ فشل الخصم. الرصيد الحالي: {db.get_balance(target_id)}")
    
    context.user_data.pop('admin_action', None)

async def admin_subscriptions_menu(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    
    keyboard = [
        [InlineKeyboardButton("✅ تفعيل اشتراك", callback_data="admin_activate_sub")],
        [InlineKeyboardButton("❌ إلغاء اشتراك", callback_data="admin_deactivate_sub")],
        [InlineKeyboardButton("🔙 رجوع", callback_data="admin_panel")]
    ]
    
    await query.edit_message_text("📅 **إدارة الاشتراكات**", reply_markup=InlineKeyboardMarkup(keyboard), parse_mode='Markdown')

async def admin_activate_sub_start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    context.user_data['admin_action'] = 'activate_sub'
    await query.edit_message_text("✅ أرسل: `معرف_المستخدم عدد_الأيام`\nمثال: `123456789 30`", parse_mode='Markdown')

async def admin_deactivate_sub_start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    context.user_data['admin_action'] = 'deactivate_sub'
    await query.edit_message_text("❌ أرسل معرف المستخدم فقط:\n`123456789`", parse_mode='Markdown')

async def admin_handle_subscription_input(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = update.effective_user.id
    if user_id not in ADMIN_IDS:
        return
    
    action = context.user_data.get('admin_action')
    if action not in ['activate_sub', 'deactivate_sub']:
        return
    
    text = update.message.text.strip()
    
    if action == 'activate_sub':
        match = re.match(r'^(\d+)\s+(\d+)$', text)
        if not match:
            await update.message.reply_text("❌ أرسل: `معرف_المستخدم عدد_الأيام`", parse_mode='Markdown')
            return
        target_id = int(match.group(1))
        days = int(match.group(2))
        expiry = db.activate_subscription(target_id, days)
        await update.message.reply_text(f"✅ تم التفعيل\n📅 ينتهي: {expiry.strftime('%Y-%m-%d')}")
    else:
        try:
            target_id = int(text)
            db.deactivate_subscription(target_id)
            await update.message.reply_text(f"✅ تم إلغاء اشتراك {target_id}")
        except ValueError:
            await update.message.reply_text("❌ أرسل معرف المستخدم فقط")
    
    context.user_data.pop('admin_action', None)

async def admin_payment_methods_menu(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    
    keyboard = []
    for method_id, method_data in PAYMENT_METHODS.items():
        status = "✅" if method_data["enabled"] else "❌"
        keyboard.append([InlineKeyboardButton(f"{status} {method_data['name']}", callback_data=f"admin_toggle_method_{method_id}")])
    keyboard.append([InlineKeyboardButton("🔙 رجوع", callback_data="admin_panel")])
    
    await query.edit_message_text("💳 **طرق الدفع**", reply_markup=InlineKeyboardMarkup(keyboard))

async def admin_toggle_payment_method(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    method_id = query.data.replace("admin_toggle_method_", "")
    
    if method_id in PAYMENT_METHODS:
        PAYMENT_METHODS[method_id]["enabled"] = not PAYMENT_METHODS[method_id]["enabled"]
        status = "مفعلة" if PAYMENT_METHODS[method_id]["enabled"] else "معطلة"
        await query.edit_message_text(f"✅ تم {status} طريقة الدفع")
    
    await admin_payment_methods_menu(update, context)

async def admin_stats_menu(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    
    stats = db.get_stats()
    message = (
        f"📊 **الإحصائيات**\n\n"
        f"👥 المستخدمين: {stats['total_users']}\n"
        f"✅ اشتراكات نشطة: {stats['active_subscriptions']}\n"
        f"💰 الرصيد الكلي: {stats['total_balance']} {CURRENCY}\n"
        f"🖼️ صور معالجة: {stats['total_images_processed']}"
    )
    
    keyboard = [[InlineKeyboardButton("🔙 رجوع", callback_data="admin_panel")]]
    await query.edit_message_text(message, reply_markup=InlineKeyboardMarkup(keyboard), parse_mode='Markdown')

async def admin_find_user_start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    context.user_data['admin_action'] = 'find_user'
    await query.edit_message_text("🔍 أرسل معرف المستخدم:\n`123456789`", parse_mode='Markdown')

async def admin_handle_find_user(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = update.effective_user.id
    if user_id not in ADMIN_IDS or context.user_data.get('admin_action') != 'find_user':
        return
    
    try:
        target_id = int(update.message.text.strip())
        user_data = db.get_user(target_id)
        message = (
            f"👤 **المستخدم**\n\n"
            f"🆔 المعرف: `{target_id}`\n"
            f"💰 الرصيد: {user_data.get('balance', 0)} {CURRENCY}\n"
            f"📅 اشتراك: {'✅ مفعل' if db.check_subscription(target_id) else '❌'}\n"
            f"🖼️ صور مستخدمة: {user_data.get('images_used', 0)}"
        )
        await update.message.reply_text(message, parse_mode='Markdown')
    except ValueError:
        await update.message.reply_text("❌ أرسل معرف المستخدم فقط")
    
    context.user_data.pop('admin_action', None)
