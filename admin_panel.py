# admin_panel.py
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import ContextTypes
from database import db
from config import PAYMENT_METHODS, SUBSCRIPTION_PRICE, CURRENCY
import re

# ================== ⚠️ هام: ضع معرف المشرف هنا ⚠️ ==================
# اذهب إلى @userinfobot في تليجرام لمعرفة معرفك
# ثم اكتب الرقم في المكان المخصص أدناه

ADMIN_IDS = [
    7240148750,  # 👈 امسح هذا الرقم وضع معرفك الحقيقي هنا
]

# مثال: إذا كان معرفك 987654321، اكتبه هكذا:
# ADMIN_IDS = [
#     987654321,
# ]

# ================== باقي الكود ==================

async def admin_panel(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = update.effective_user.id
    if user_id not in ADMIN_IDS:
        await update.message.reply_text("⛔ غير مصرح لك بالدخول إلى لوحة التحكم")
        return
    
    stats = db.get_stats()
    pending_count = len(db.get_pending_payments())
    
    keyboard = [
        [InlineKeyboardButton("👥 إدارة المستخدمين", callback_data="admin_users_menu")],
        [InlineKeyboardButton("💰 إدارة الرصيد", callback_data="admin_balance")],
        [InlineKeyboardButton("📅 إدارة الاشتراكات", callback_data="admin_subscriptions")],
        [InlineKeyboardButton("💳 طرق الدفع", callback_data="admin_payment_methods")],
        [InlineKeyboardButton("📊 الإحصائيات", callback_data="admin_stats")],
        [InlineKeyboardButton(f"💵 طلبات الدفع 📥 ({pending_count})", callback_data="admin_payment_requests")],
        [InlineKeyboardButton("🔙 رجوع", callback_data="back_to_main")]
    ]
    
    message = (
        "🔐 **لوحة تحكم المشرف**\n\n"
        f"👥 إجمالي المستخدمين: {stats['total_users']}\n"
        f"✅ اشتراكات نشطة: {stats['active_subscriptions']}\n"
        f"💰 إجمالي الرصيد: {stats['total_balance']} {CURRENCY}\n"
        f"🖼️ صور تمت معالجتها: {stats['total_images_processed']}\n"
        f"💵 طلبات دفع معلقة: {pending_count}\n\n"
        "اختر الإجراء المطلوب:"
    )
    
    await update.message.reply_text(message, reply_markup=InlineKeyboardMarkup(keyboard), parse_mode='Markdown')

async def admin_users_menu(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    keyboard = [
        [InlineKeyboardButton("🔍 بحث عن مستخدم", callback_data="admin_find_user")],
        [InlineKeyboardButton("📋 قائمة المستخدمين", callback_data="admin_list_users")],
        [InlineKeyboardButton("🔙 رجوع", callback_data="admin_panel")]
    ]
    await query.edit_message_text("👥 **إدارة المستخدمين**", reply_markup=InlineKeyboardMarkup(keyboard), parse_mode='Markdown')

async def admin_list_users(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    users = list(db.users.values())
    page = context.user_data.get('users_page', 0)
    per_page = 10
    total_pages = (len(users) + per_page - 1) // per_page
    start = page * per_page
    end = start + per_page
    current_users = users[start:end]
    
    if not current_users:
        await query.edit_message_text("📭 لا يوجد مستخدمين بعد")
        return
    
    message = "📋 **قائمة المستخدمين**\n\n"
    for user in current_users:
        sub = "✅" if db.check_subscription(user['user_id']) else "❌"
        message += f"🆔 `{user['user_id']}` {sub} 💰 {user.get('balance', 0)}\n"
    message += f"\n📄 الصفحة {page + 1} من {total_pages}"
    
    keyboard = []
    if page > 0:
        keyboard.append(InlineKeyboardButton("⬅️", callback_data="admin_users_prev"))
    if page < total_pages - 1:
        keyboard.append(InlineKeyboardButton("➡️", callback_data="admin_users_next"))
    keyboard.append(InlineKeyboardButton("🔙 رجوع", callback_data="admin_users_menu"))
    
    await query.edit_message_text(message, reply_markup=InlineKeyboardMarkup([keyboard]), parse_mode='Markdown')

async def admin_users_next(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    context.user_data['users_page'] = context.user_data.get('users_page', 0) + 1
    await admin_list_users(update, context)

async def admin_users_prev(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    context.user_data['users_page'] = context.user_data.get('users_page', 0) - 1
    await admin_list_users(update, context)

async def admin_balance_menu(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    keyboard = [
        [InlineKeyboardButton("➕ إضافة رصيد", callback_data="admin_add_balance")],
        [InlineKeyboardButton("➖ خصم رصيد", callback_data="admin_deduct_balance")],
        [InlineKeyboardButton("🔍 البحث عن مستخدم", callback_data="admin_find_user")],
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
        await update.message.reply_text("❌ أرسل: `معرف_المستخدم المبلغ`", parse_mode='Markdown')
        return
    
    target_id = int(match.group(1))
    amount = float(match.group(2))
    user_data = db.get_user(target_id)
    
    if action == 'add_balance':
        new_balance = db.add_balance(target_id, amount)
        await update.message.reply_text(f"✅ تمت إضافة {amount} {CURRENCY}\n💰 الرصيد الجديد: {new_balance}")
        try:
            await context.bot.send_message(target_id, f"🎉 تمت إضافة {amount} {CURRENCY} إلى رصيدك!")
        except:
            pass
    else:
        success = db.deduct_balance(target_id, amount)
        if success:
            await update.message.reply_text(f"✅ تم خصم {amount} {CURRENCY}")
        else:
            await update.message.reply_text(f"❌ فشل الخصم! الرصيد الحالي: {db.get_balance(target_id)}")
    
    context.user_data.pop('admin_action', None)

async def admin_subscriptions_menu(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    keyboard = [
        [InlineKeyboardButton("✅ تفعيل اشتراك", callback_data="admin_activate_sub")],
        [InlineKeyboardButton("❌ إلغاء اشتراك", callback_data="admin_deactivate_sub")],
        [InlineKeyboardButton("📋 قائمة المشتركين", callback_data="admin_list_subs")],
        [InlineKeyboardButton("🔙 رجوع", callback_data="admin_panel")]
    ]
    await query.edit_message_text(f"📅 **إدارة الاشتراكات**\nسعر الاشتراك: {SUBSCRIPTION_PRICE} {CURRENCY}/شهر", reply_markup=InlineKeyboardMarkup(keyboard), parse_mode='Markdown')

async def admin_activate_sub_start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    context.user_data['admin_action'] = 'activate_sub'
    await query.edit_message_text("✅ أرسل: `معرف_المستخدم عدد_الأيام`\nمثال: `123456789 30`", parse_mode='Markdown')

async def admin_deactivate_sub_start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    context.user_data['admin_action'] = 'deactivate_sub'
    await query.edit_message_text("❌ أرسل معرف المستخدم:\n`123456789`", parse_mode='Markdown')

async def admin_list_subs(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    subscribers = []
    for uid, user in db.users.items():
        if user.get('subscription_active', False):
            expiry = user.get('subscription_expiry', '').split('T')[0] if user.get('subscription_expiry') else 'غير معروف'
            subscribers.append(f"🆔 `{uid}` - ينتهي: {expiry}")
    if not subscribers:
        await query.edit_message_text("📭 لا يوجد مشتركين")
        return
    message = "📅 **المشتركين النشطين**\n\n" + "\n".join(subscribers[:30])
    keyboard = [[InlineKeyboardButton("🔙 رجوع", callback_data="admin_subscriptions")]]
    await query.edit_message_text(message, reply_markup=InlineKeyboardMarkup(keyboard), parse_mode='Markdown')

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
        try:
            await context.bot.send_message(target_id, f"🎉 تم تفعيل اشتراكك لمدة {days} يوماً!")
        except:
            pass
    else:
        try:
            target_id = int(text)
            db.deactivate_subscription(target_id)
            await update.message.reply_text(f"✅ تم إلغاء اشتراك {target_id}")
        except:
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
    pending = len(db.get_pending_payments())
    message = (
        f"📊 **الإحصائيات**\n\n"
        f"👥 المستخدمين: {stats['total_users']}\n"
        f"✅ اشتراكات نشطة: {stats['active_subscriptions']}\n"
        f"💰 إجمالي الرصيد: {stats['total_balance']} {CURRENCY}\n"
        f"🖼️ صور معالجة: {stats['total_images_processed']}\n"
        f"💵 طلبات دفع معلقة: {pending}"
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
        sub_status = "✅ مفعل" if db.check_subscription(target_id) else "❌ غير مفعل"
        remaining = user_data.get('images_limit', FREE_IMAGES_LIMIT) - user_data.get('images_used', 0)
        message = (
            f"👤 **المستخدم**\n\n"
            f"🆔 المعرف: `{target_id}`\n"
            f"👤 الاسم: {user_data.get('first_name', 'غير معروف')}\n"
            f"💰 الرصيد: {user_data.get('balance', 0)} {CURRENCY}\n"
            f"📅 الاشتراك: {sub_status}\n"
            f"🎁 صور مجانية متبقية: {remaining}\n"
            f"🖼️ صور مستخدمة: {user_data.get('images_used', 0)}"
        )
        keyboard = [
            [InlineKeyboardButton("➕ إضافة رصيد", callback_data=f"admin_balance_user_{target_id}")],
            [InlineKeyboardButton("✅ تفعيل اشتراك", callback_data=f"admin_sub_user_{target_id}")],
            [InlineKeyboardButton("🔙 رجوع", callback_data="admin_users_menu")]
        ]
        await update.message.reply_text(message, reply_markup=InlineKeyboardMarkup(keyboard), parse_mode='Markdown')
    except:
        await update.message.reply_text("❌ أرسل معرف المستخدم فقط")
    context.user_data.pop('admin_action', None)

async def admin_balance_user(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    target_id = int(query.data.replace("admin_balance_user_", ""))
    context.user_data['admin_action'] = 'add_balance'
    context.user_data['target_user'] = target_id
    await query.edit_message_text(f"💰 أرسل المبلغ لإضافته للمستخدم `{target_id}`:", parse_mode='Markdown')

async def admin_sub_user(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    target_id = int(query.data.replace("admin_sub_user_", ""))
    context.user_data['admin_action'] = 'activate_sub'
    context.user_data['target_user'] = target_id
    await query.edit_message_text(f"✅ أرسل عدد الأيام لتفعيل اشتراك المستخدم `{target_id}`:", parse_mode='Markdown')

async def admin_payment_requests(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    pending = db.get_pending_payments()
    if not pending:
        await query.edit_message_text("📭 لا توجد طلبات دفع معلقة")
        return
    context.user_data['pending_list'] = pending
    context.user_data['pending_index'] = 0
    await show_payment(update, context, 0)

async def show_payment(update: Update, context: ContextTypes.DEFAULT_TYPE, index: int):
    pending = context.user_data.get('pending_list', [])
    if not pending or index >= len(pending):
        return
    payment = pending[index]
    user_data = db.get_user(payment['user_id'])
    message = (
        f"💵 **طلب دفع**\n\n"
        f"🆔 المعرف: `{payment['id']}`\n"
        f"👤 المستخدم: {user_data.get('first_name', payment['user_id'])}\n"
        f"💰 المبلغ: {payment['amount']} {CURRENCY}\n"
        f"💳 الطريقة: {payment['method']}\n"
        f"📅 التاريخ: {payment['created_at'].split('T')[0]}\n\n"
        f"({index + 1}/{len(pending)})"
    )
    keyboard = [
        [InlineKeyboardButton("✅ تأكيد", callback_data=f"confirm_payment_{payment['id']}"),
         InlineKeyboardButton("❌ رفض", callback_data=f"reject_payment_{payment['id']}")],
    ]
    nav = []
    if index > 0:
        nav.append(InlineKeyboardButton("⬅️", callback_data="payment_prev"))
    if index < len(pending) - 1:
        nav.append(InlineKeyboardButton("➡️", callback_data="payment_next"))
    if nav:
        keyboard.append(nav)
    keyboard.append([InlineKeyboardButton("🔙 رجوع", callback_data="admin_panel")])
    await query.edit_message_text(message, reply_markup=InlineKeyboardMarkup(keyboard), parse_mode='Markdown')

async def payment_next(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    context.user_data['pending_index'] = context.user_data.get('pending_index', 0) + 1
    await show_payment(update, context, context.user_data['pending_index'])

async def payment_prev(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    context.user_data['pending_index'] = context.user_data.get('pending_index', 0) - 1
    await show_payment(update, context, context.user_data['pending_index'])

async def confirm_payment(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    payment_id = query.data.replace("confirm_payment_", "")
    payment = db.payments.get(payment_id)
    if not payment:
        await query.edit_message_text("❌ لم يتم العثور على الطلب")
        return
    db.complete_payment(payment_id)
    await context.bot.send_message(
        payment['user_id'],
        f"✅ **تم تأكيد دفعتك بنجاح!**\n\n"
        f"شكراً لك على ثقتك! 🎉"
    )
    await query.edit_message_text(f"✅ تم تأكيد الدفع للمستخدم {payment['user_id']}")
    # تحديث القائمة
    context.user_data['pending_list'] = db.get_pending_payments()
    if context.user_data['pending_list']:
        await show_payment(update, context, 0)
    else:
        await query.edit_message_text("📭 لا توجد طلبات دفع معلقة")

async def reject_payment(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    payment_id = query.data.replace("reject_payment_", "")
    payment = db.payments.get(payment_id)
    if not payment:
        await query.edit_message_text("❌ لم يتم العثور على الطلب")
        return
    del db.payments[payment_id]
    db.save_payments()
    await context.bot.send_message(
        payment['user_id'],
        f"❌ **تم رفض طلب الدفع**\n\nيرجى مراجعة الدعم الفني."
    )
    await query.edit_message_text(f"❌ تم رفض طلب المستخدم {payment['user_id']}")
    context.user_data['pending_list'] = db.get_pending_payments()
    if context.user_data['pending_list']:
        await show_payment(update, context, 0)
    else:
        await query.edit_message_text("📭 لا توجد طلبات دفع معلقة")

from config import FREE_IMAGES_LIMIT
