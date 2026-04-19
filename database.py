# database.py
import json
import os
from datetime import datetime, timedelta
from typing import Dict, List, Optional
import threading

BASE_DIR = os.path.dirname(os.path.abspath(__file__))

class Database:
    def __init__(self):
        self.lock = threading.Lock()
        self.users_file = os.path.join(BASE_DIR, "users_data.json")
        self.payments_file = os.path.join(BASE_DIR, "payments_data.json")
        self.load_data()
    
    def load_data(self):
        if os.path.exists(self.users_file):
            try:
                with open(self.users_file, 'r', encoding='utf-8') as f:
                    self.users = json.load(f)
            except:
                self.users = {}
        else:
            self.users = {}
        
        if os.path.exists(self.payments_file):
            try:
                with open(self.payments_file, 'r', encoding='utf-8') as f:
                    self.payments = json.load(f)
            except:
                self.payments = {}
        else:
            self.payments = {}
    
    def save_users(self):
        with self.lock:
            try:
                with open(self.users_file, 'w', encoding='utf-8') as f:
                    json.dump(self.users, f, ensure_ascii=False, indent=2)
            except Exception as e:
                print(f"خطأ في حفظ المستخدمين: {e}")
    
    def save_payments(self):
        with self.lock:
            try:
                with open(self.payments_file, 'w', encoding='utf-8') as f:
                    json.dump(self.payments, f, ensure_ascii=False, indent=2)
            except Exception as e:
                print(f"خطأ في حفظ المدفوعات: {e}")
    
    def get_user(self, user_id: int) -> Dict:
        uid = str(user_id)
        if uid not in self.users:
            self.users[uid] = {
                "user_id": user_id,
                "username": None,
                "first_name": None,
                "balance": 0,
                "subscription_active": False,
                "subscription_expiry": None,
                "images_used": 0,
                "images_limit": FREE_IMAGES_LIMIT,
                "created_at": datetime.now().isoformat(),
                "last_used": None
            }
            self.save_users()
        return self.users[uid]
    
    def update_user(self, user_id: int, data: Dict):
        uid = str(user_id)
        if uid in self.users:
            self.users[uid].update(data)
        else:
            user = self.get_user(user_id)
            user.update(data)
        self.save_users()
    
    def add_balance(self, user_id: int, amount: float, reason: str = ""):
        user = self.get_user(user_id)
        user["balance"] += amount
        self.save_users()
        return user["balance"]
    
    def deduct_balance(self, user_id: int, amount: float, reason: str = ""):
        user = self.get_user(user_id)
        if user["balance"] >= amount:
            user["balance"] -= amount
            self.save_users()
            return True
        return False
    
    def get_balance(self, user_id: int) -> float:
        return self.get_user(user_id)["balance"]
    
    def activate_subscription(self, user_id: int, days: int = 30):
        user = self.get_user(user_id)
        expiry = datetime.now() + timedelta(days=days)
        user["subscription_active"] = True
        user["subscription_expiry"] = expiry.isoformat()
        user["images_limit"] = 999999
        self.save_users()
        return expiry
    
    def deactivate_subscription(self, user_id: int):
        user = self.get_user(user_id)
        user["subscription_active"] = False
        user["subscription_expiry"] = None
        user["images_limit"] = FREE_IMAGES_LIMIT
        self.save_users()
    
    def check_subscription(self, user_id: int) -> bool:
        user = self.get_user(user_id)
        if not user["subscription_active"]:
            return False
        if user["subscription_expiry"]:
            expiry = datetime.fromisoformat(user["subscription_expiry"])
            if expiry < datetime.now():
                self.deactivate_subscription(user_id)
                return False
        return True
    
    def can_use_image(self, user_id: int) -> bool:
        user = self.get_user(user_id)
        if self.check_subscription(user_id):
            return True
        if user["balance"] > 0:
            return True
        if user["images_used"] < user["images_limit"]:
            return True
        return False
    
    def use_image(self, user_id: int) -> bool:
        if not self.can_use_image(user_id):
            return False
        user = self.get_user(user_id)
        if self.check_subscription(user_id):
            user["last_used"] = datetime.now().isoformat()
            self.save_users()
            return True
        if user["balance"] > 0:
            user["balance"] -= 1
            user["images_used"] += 1
            user["last_used"] = datetime.now().isoformat()
            self.save_users()
            return True
        if user["images_used"] < user["images_limit"]:
            user["images_used"] += 1
            user["last_used"] = datetime.now().isoformat()
            self.save_users()
            return True
        return False
    
    def add_payment_request(self, payment_id: str, user_id: int, amount: float, method: str):
        self.payments[payment_id] = {
            "id": payment_id,
            "user_id": user_id,
            "amount": amount,
            "method": method,
            "status": "pending",
            "created_at": datetime.now().isoformat(),
            "completed_at": None
        }
        self.save_payments()
        return payment_id
    
    def complete_payment(self, payment_id: str):
        if payment_id in self.payments:
            self.payments[payment_id]["status"] = "completed"
            self.payments[payment_id]["completed_at"] = datetime.now().isoformat()
            self.save_payments()
            return True
        return False
    
    def get_pending_payments(self) -> List[Dict]:
        return [p for p in self.payments.values() if p["status"] == "pending"]
    
    def get_stats(self) -> Dict:
        total_users = len(self.users)
        active_subscriptions = sum(1 for u in self.users.values() if u.get("subscription_active", False))
        total_balance = sum(u.get("balance", 0) for u in self.users.values())
        total_images_processed = sum(u.get("images_used", 0) for u in self.users.values())
        return {
            "total_users": total_users,
            "active_subscriptions": active_subscriptions,
            "total_balance": total_balance,
            "total_images_processed": total_images_processed
        }

from config import FREE_IMAGES_LIMIT
db = Database()
