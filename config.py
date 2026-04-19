# config.py
import os

# ================== الإعدادات العامة ==================
# جلب التوكن من متغيرات البيئة (ضروري لـ Kuberns)
BOT_TOKEN = os.environ.get("BOT_TOKEN", "")

# إذا لم يكن موجوداً، اطلبه (للتشغيل المحلي فقط)
if not BOT_TOKEN:
    BOT_TOKEN = input("أدخل توكن البوت: ")

# ================== إعدادات الدفع ==================
CURRENCY = "ليرة سورية جديدة"
SUBSCRIPTION_PRICE = 50
FREE_IMAGES_LIMIT = 3

# ================== قنوات الاشتراك الإجباري ==================
REQUIRED_CHANNELS = [
    # "channel_username_1",  # أضف معرفات القنوات هنا إذا أردت
]

# ================== طرق الدفع ==================
PAYMENT_METHODS = {
    "card": {
        "name": "💳 شام كاش",
        "enabled": True,
        "instructions": "e6b15e5dcb1934930754fc5a27b983a9"
    },
    "crypto": {
        "name": "₿ عملات رقمية (USDT/BTC)",
        "enabled": True,
        "instructions": "أرسل المبلغ إلى المحفظة: "
    },

}
