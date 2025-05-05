import os
import json
import hashlib
import secrets
import pyttsx3
import speech_recognition as sr
from fpdf import FPDF
import time
from datetime import datetime, timedelta
import random
from translate import Translator
import requests
import bcrypt
from getpass import getpass
import tkinter as tk
from tkinter import ttk, messagebox, simpledialog, scrolledtext, font
from PIL import Image, ImageTk
import webbrowser
from tkinter.ttk import Combobox

# Supported languages and their codes
SUPPORTED_LANGUAGES = {
    "1": {"name": "English", "code": "en"},
    "2": {"name": "Hindi", "code": "hi"},
    "3": {"name": "Spanish", "code": "es"},
    "4": {"name": "French", "code": "fr"}
}

# Supported currencies
SUPPORTED_CURRENCIES = {
    "1": {"code": "INR", "symbol": "₹"},
    "2": {"code": "USD", "symbol": "$"},
    "3": {"code": "EUR", "symbol": "€"}
}

# Sample restaurant data
RESTAURANTS = {
    "1": {"name": "Pizza Palace", "cuisine": "Italian", "rating": 4.5, "delivery_time": "30-40 min"},
    "2": {"name": "Sushi Haven", "cuisine": "Japanese", "rating": 4.7, "delivery_time": "25-35 min"},
    "3": {"name": "Burger Bonanza", "cuisine": "American", "rating": 4.3, "delivery_time": "20-30 min"}
}

# Sample menu items
MENU_ITEMS = {
    "1": [
        {"item": "Margherita Pizza", "price": 299, "category": "Pizza", "veg": True},
        {"item": "Pepperoni Pizza", "price": 349, "category": "Pizza", "veg": False},
        {"item": "Garlic Bread", "price": 99, "category": "Sides", "veg": True}
    ],
    "2": [
        {"item": "California Roll", "price": 399, "category": "Sushi", "veg": False},
        {"item": "Miso Soup", "price": 149, "category": "Soup", "veg": True},
        {"item": "Edamame", "price": 199, "category": "Sides", "veg": True}
    ],
    "3": [
        {"item": "Classic Burger", "price": 249, "category": "Burger", "veg": False},
        {"item": "Veggie Burger", "price": 229, "category": "Burger", "veg": True},
        {"item": "French Fries", "price": 99, "category": "Sides", "veg": True}
    ]
}

# Promo codes
PROMO_CODES = {
    "FIRSTORDER": 0.20,  # 20% off first order
    "HUNGRY": 0.15,      # 15% off
    "QUICKBITE": 0.10   # 10% off
}

API_KEY = "4db4caec5f9518a9b9cacb21"
BASE_CURRENCY = "INR"

class UserAuth:
    def __init__(self):
        self.users_file = "users.json"
        self.sessions = {}
        self.session_duration = timedelta(hours=24)
        self._load_users()

    def _load_users(self):
        if os.path.exists(self.users_file):
            with open(self.users_file, 'r') as f:
                self.users = json.load(f)
            # Migrate old 'shopping_history' to 'order_history' if present
            for user_data in self.users.values():
                if 'shopping_history' in user_data and 'order_history' not in user_data:
                    user_data['order_history'] = user_data.pop('shopping_history')
                if 'order_history' not in user_data:
                    user_data['order_history'] = []
                if 'address' not in user_data:
                    user_data['address'] = "Address not provided"
        else:
            self.users = {}
            self._save_users()

    def _save_users(self):
        with open(self.users_file, 'w') as f:
            json.dump(self.users, f, indent=4)

    def register_user(self, username, password, email, address):
        if username in self.users:
            return False, "Username already exists"
        salt = bcrypt.gensalt()
        hashed = bcrypt.hashpw(password.encode('utf-8'), salt)
        self.users[username] = {
            'password': hashed.decode('utf-8'),
            'email': email,
            'address': address,
            'created_at': datetime.now().isoformat(),
            'order_history': []
        }
        self._save_users()
        return True, "Registration successful"

    def login(self, username, password):
        if username not in self.users:
            return False, "Invalid username or password"
        stored_hash = self.users[username]['password'].encode('utf-8')
        if bcrypt.checkpw(password.encode('utf-8'), stored_hash):
            session_token = secrets.token_hex(32)
            self.sessions[session_token] = {
                'username': username,
                'expires': datetime.now() + self.session_duration
            }
            return True, session_token
        return False, "Invalid username or password"

    def validate_session(self, session_token):
        if session_token not in self.sessions:
            return False
        session = self.sessions[session_token]
        if datetime.now() > session['expires']:
            del self.sessions[session_token]
            return False
        return True

    def get_user_data(self, session_token):
        if not self.validate_session(session_token):
            return None
        username = self.sessions[session_token]['username']
        return self.users[username]

    def save_order_history(self, session_token, order_data, total, currency_symbol, restaurant_id):
        if not self.validate_session(session_token):
            return False
        username = self.sessions[session_token]['username']
        order_record = {
            'date': datetime.now().isoformat(),
            'items': order_data,
            'total': total,
            'currency': currency_symbol,
            'restaurant_id': restaurant_id,
            'status': 'Order Placed',
            'order_id': secrets.token_hex(8)
        }
        self.users[username]['order_history'].append(order_record)
        self._save_users()
        return True

    def get_order_history(self, session_token):
        if not self.validate_session(session_token):
            return None
        username = self.sessions[session_token]['username']
        return self.users[username]['order_history']

def get_exchange_rate(target_currency):
    url = f"https://v6.exchangerate-api.com/v6/{API_KEY}/latest/{BASE_CURRENCY}"
    try:
        response = requests.get(url)
        if response.status_code == 200:
            data = response.json()
            return data['conversion_rates'][target_currency]
    except:
        return 1
    return 1

def convert_currency(amount, target_currency):
    rate = get_exchange_rate(target_currency)
    return amount * rate

def translate_text(text, dest_language='en'):
    try:
        translator = Translator(to_lang=dest_language)
        translation = translator.translate(text)
        return translation
    except Exception:
        return text

def display_cart(cart, language_code, currency_symbol):
    if not cart:
        return translate_text("\n🍽️ Your order is empty!", language_code)
    
    cart_text = translate_text("\n🍽️ Your Order:", language_code) + "\n"
    cart_text += f"{'#':<3} {'Item':<25} {'Qty':<6} {f'Price ({currency_symbol})':<15} {f'Total ({currency_symbol})':<15}\n"
    cart_text += "—" * 70 + "\n"
    
    total = 0
    for i, entry in enumerate(cart, start=1):
        total_price = entry['price'] * entry['quantity']
        total += total_price
        veg_mark = "🌱" if entry['veg'] else "🍖"
        cart_text += f"{i:<3} {entry['item']:<25} {entry['quantity']:<6} {currency_symbol}{entry['price']:<15.2f} {currency_symbol}{total_price:<15.2f} {veg_mark}\n"
    
    cart_text += f"🌟 {translate_text('Order Total:', language_code)} {currency_symbol}{total:.2f}\n"
    return cart_text

def apply_promo_code(total, promo_code, language_code):
    if promo_code in PROMO_CODES:
        discount_rate = PROMO_CODES[promo_code]
        discount = total * discount_rate
        return discount, translate_text(f"🎉 Promo {promo_code} applied! Saved {discount_rate*100}%!", language_code)
    return 0, translate_text("❌ Invalid promo code!", language_code)

def generate_pdf(cart, total, promo_discount, tax, grand_total, currency_symbol, user_data, restaurant_id):
    pdf = FPDF()
    pdf.add_page()
    pdf.add_font("DejaVu", "", "DejaVuSans.ttf", uni=True)
    pdf.set_font("DejaVu", "", 14)
    pdf.cell(200, 10, f"Order Receipt - {RESTAURANTS[restaurant_id]['name']}", ln=True, align='C')
    pdf.cell(200, 10, f"Date: {datetime.now().strftime('%Y-%m-%d %H:%M')}", ln=True, align='C')
    pdf.cell(200, 10, f"Customer: {user_data['email']}", ln=True, align='C')
    pdf.ln(10)
    pdf.cell(200, 10, "-" * 30, ln=True)
    for i, entry in enumerate(cart, start=1):
        total_price = entry['price'] * entry['quantity']
        line = f"{i}. {entry['item']} x{entry['quantity']} - {currency_symbol}{entry['price']:.2f}/unit = {currency_symbol}{total_price:.2f}"
        pdf.cell(200, 10, line, ln=True)
    pdf.cell(200, 10, "-" * 30, ln=True)
    pdf.cell(200, 10, f"Subtotal: {currency_symbol}{total:.2f}", ln=True)
    if promo_discount > 0:
        pdf.cell(200, 10, f"Promo Discount: -{currency_symbol}{promo_discount:.2f}", ln=True)
    pdf.cell(200, 10, f"Delivery Fee: +{currency_symbol}{tax:.2f}", ln=True)
    pdf.cell(200, 10, "=" * 30, ln=True)
    pdf.cell(200, 10, f"GRAND TOTAL: {currency_symbol}{grand_total:.2f}", ln=True)
    pdf.cell(200, 10, "=" * 30, ln=True)
    address = user_data.get('address', 'Address not provided')  # Handle missing address
    pdf.cell(200, 10, f"Delivery to: {address}", ln=True)
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    receipt_path = os.path.join(os.getcwd(), f"Order_Receipt_{timestamp}.pdf")
    pdf.output(receipt_path, "F")
    return receipt_path

class FoodOrderingApp:
    def __init__(self, root):
        self.root = root
        self.root.title("Food Ordering App")
        self.root.geometry("1000x700")
        self.root.resizable(False, False)
        
        self.style = ttk.Style()
        self.style.theme_use('clam')
        
        self.bg_color = "#f5f5f5"
        self.primary_color = "#ff5722"
        self.secondary_color = "#d84315"
        self.accent_color = "#ff8a65"
        self.text_color = "#333333"
        self.error_color = "#e53935"
        
        self.style.configure('TFrame', background=self.bg_color)
        self.style.configure('TLabel', background=self.bg_color, foreground=self.text_color, font=('Helvetica', 10))
        self.style.configure('TButton', font=('Helvetica', 10), background=self.primary_color, foreground='white')
        self.style.map('TButton', 
                      background=[('active', self.secondary_color)],
                      foreground=[('active', 'white')])
        self.style.configure('Header.TLabel', font=('Helvetica', 16, 'bold'), foreground=self.primary_color)
        self.style.configure('Error.TLabel', foreground=self.error_color)
        self.style.configure('Success.TLabel', foreground='#2e7d32')
        
        self.auth = UserAuth()
        self.session_token = None
        self.user_data = None
        self.language_code = "en"
        self.currency_code = "INR"
        self.currency_symbol = "₹"
        self.cart = []
        self.current_restaurant = None
        self.recognizer = sr.Recognizer()
        self.engine = pyttsx3.init()
        
        self.main_frame = ttk.Frame(root)
        self.main_frame.pack(fill=tk.BOTH, expand=True)
        
        self.show_login_screen()

    def clear_frame(self):
        for widget in self.main_frame.winfo_children():
            widget.destroy()

    def show_login_screen(self):
        self.clear_frame()
        
        header = ttk.Label(self.main_frame, text="🍽️ Food Ordering Portal", style='Header.TLabel')
        header.pack(pady=20)
        
        login_frame = ttk.Frame(self.main_frame)
        login_frame.pack(pady=20)
        
        ttk.Label(login_frame, text="Username:").grid(row=0, column=0, padx=5, pady=5, sticky=tk.E)
        self.username_entry = ttk.Entry(login_frame)
        self.username_entry.grid(row=0, column=1, padx=5, pady=5)
        
        ttk.Label(login_frame, text="Password:").grid(row=1, column=0, padx=5, pady=5, sticky=tk.E)
        self.password_entry = ttk.Entry(login_frame, show="*")
        self.password_entry.grid(row=1, column=1, padx=5, pady=5)
        
        buttons_frame = ttk.Frame(self.main_frame)
        buttons_frame.pack(pady=20)
        
        ttk.Button(buttons_frame, text="Login", command=self.handle_login).pack(side=tk.LEFT, padx=10)
        ttk.Button(buttons_frame, text="Register", command=self.show_register_screen).pack(side=tk.LEFT, padx=10)
        ttk.Button(buttons_frame, text="Exit", command=self.root.quit).pack(side=tk.LEFT, padx=10)
        
        self.login_status = ttk.Label(self.main_frame, text="", style='Error.TLabel')
        self.login_status.pack(pady=10)

    def show_register_screen(self):
        self.clear_frame()
        
        header = ttk.Label(self.main_frame, text="🌟 Create Account", style='Header.TLabel')
        header.pack(pady=20)
        
        register_frame = ttk.Frame(self.main_frame)
        register_frame.pack(pady=20)
        
        ttk.Label(register_frame, text="Username:").grid(row=0, column=0, padx=5, pady=5, sticky=tk.E)
        self.reg_username_entry = ttk.Entry(register_frame)
        self.reg_username_entry.grid(row=0, column=1, padx=5, pady=5)
        
        ttk.Label(register_frame, text="Password:").grid(row=1, column=0, padx=5, pady=5, sticky=tk.E)
        self.reg_password_entry = ttk.Entry(register_frame, show="*")
        self.reg_password_entry.grid(row=1, column=1, padx=5, pady=5)
        
        ttk.Label(register_frame, text="Email:").grid(row=2, column=0, padx=5, pady=5, sticky=tk.E)
        self.reg_email_entry = ttk.Entry(register_frame)
        self.reg_email_entry.grid(row=2, column=1, padx=5, pady=5)
        
        ttk.Label(register_frame, text="Delivery Address:").grid(row=3, column=0, padx=5, pady=5, sticky=tk.E)
        self.reg_address_entry = ttk.Entry(register_frame)
        self.reg_address_entry.grid(row=3, column=1, padx=5, pady=5)
        
        buttons_frame = ttk.Frame(self.main_frame)
        buttons_frame.pack(pady=20)
        
        ttk.Button(buttons_frame, text="Register", command=self.handle_register).pack(side=tk.LEFT, padx=10)
        ttk.Button(buttons_frame, text="Back", command=self.show_login_screen).pack(side=tk.LEFT, padx=10)
        
        self.register_status = ttk.Label(self.main_frame, text="", style='Error.TLabel')
        self.register_status.pack(pady=10)

    def handle_login(self):
        username = self.username_entry.get()
        password = self.password_entry.get()
        success, result = self.auth.login(username, password)
        if success:
            self.session_token = result
            self.user_data = self.auth.get_user_data(self.session_token)
            self.show_main_menu()
        else:
            self.login_status.config(text=result, style='Error.TLabel')

    def handle_register(self):
        username = self.reg_username_entry.get()
        password = self.reg_password_entry.get()
        email = self.reg_email_entry.get()
        address = self.reg_address_entry.get()
        
        if not all([username, password, email, address]):
            self.register_status.config(text="Please fill all fields", style='Error.TLabel')
            return
        
        success, message = self.auth.register_user(username, password, email, address)
        self.register_status.config(text=message, style='Success.TLabel' if success else 'Error.TLabel')
        if success:
            self.show_login_screen()

    def show_main_menu(self):
        self.clear_frame()
        
        header = ttk.Label(self.main_frame, text=f"🍴 Welcome, {self.user_data['email']}!", style='Header.TLabel')
        header.pack(pady=20)
        
        buttons_frame = ttk.Frame(self.main_frame)
        buttons_frame.pack(pady=20)
        
        ttk.Button(buttons_frame, text="🍽️ Order Food", command=self.show_language_selection).pack(pady=10, fill=tk.X, padx=50)
        ttk.Button(buttons_frame, text="📜 Order History", command=self.show_order_history).pack(pady=10, fill=tk.X, padx=50)
        ttk.Button(buttons_frame, text="🔒 Logout", command=self.handle_logout).pack(pady=10, fill=tk.X, padx=50)

    def show_language_selection(self):
        self.clear_frame()
        
        header = ttk.Label(self.main_frame, text="🌍 Select Preferences", style='Header.TLabel')
        header.pack(pady=20)
        
        lang_frame = ttk.Frame(self.main_frame)
        lang_frame.pack(pady=10)
        
        ttk.Label(lang_frame, text="Language:").grid(row=0, column=0, padx=5, pady=5, sticky=tk.E)
        self.language_var = tk.StringVar()
        lang_options = [f"{key}. {value['name']}" for key, value in SUPPORTED_LANGUAGES.items()]
        lang_dropdown = ttk.Combobox(lang_frame, textvariable=self.language_var, values=lang_options, state="readonly")
        lang_dropdown.grid(row=0, column=1, padx=5, pady=5)
        lang_dropdown.current(0)
        
        curr_frame = ttk.Frame(self.main_frame)
        curr_frame.pack(pady=10)
        
        ttk.Label(curr_frame, text="Currency:").grid(row=0, column=0, padx=5, pady=5, sticky=tk.E)
        self.currency_var = tk.StringVar()
        curr_options = [f"{key}. {value['code']} ({value['symbol']})" for key, value in SUPPORTED_CURRENCIES.items()]
        curr_dropdown = ttk.Combobox(curr_frame, textvariable=self.currency_var, values=curr_options, state="readonly")
        curr_dropdown.grid(row=0, column=1, padx=5, pady=5)
        curr_dropdown.current(0)
        
        buttons_frame = ttk.Frame(self.main_frame)
        buttons_frame.pack(pady=20)
        
        ttk.Button(buttons_frame, text="Continue", command=self.handle_language_currency_selection).pack(side=tk.LEFT, padx=10)
        ttk.Button(buttons_frame, text="Back", command=self.show_main_menu).pack(side=tk.LEFT, padx=10)

    def handle_language_currency_selection(self):
        lang_choice = self.language_var.get().split(".")[0]
        curr_choice = self.currency_var.get().split(".")[0]
        
        self.language_code = SUPPORTED_LANGUAGES[lang_choice]["code"]
        self.currency_code = SUPPORTED_CURRENCIES[curr_choice]["code"]
        self.currency_symbol = SUPPORTED_CURRENCIES[curr_choice]["symbol"]
        
        self.show_restaurant_selection()

    def show_restaurant_selection(self):
        self.clear_frame()
        
        header = ttk.Label(self.main_frame, text="🍴 Choose Restaurant", style='Header.TLabel')
        header.pack(pady=20)
        
        rest_frame = ttk.Frame(self.main_frame)
        rest_frame.pack(pady=10)
        
        for id, info in RESTAURANTS.items():
            rest_info = f"{info['name']} ({info['cuisine']}) - ★ {info['rating']} - {info['delivery_time']}"
            btn = ttk.Button(rest_frame, text=rest_info,
                           command=lambda r=id: self.show_menu(r))
            btn.pack(pady=5, fill=tk.X, padx=20)
        
        ttk.Button(self.main_frame, text="🔙 Back", command=self.show_main_menu).pack(pady=20)

    def show_menu(self, restaurant_id):
        self.current_restaurant = restaurant_id
        self.clear_frame()
        
        header = ttk.Label(self.main_frame, text=f"📋 Menu - {RESTAURANTS[restaurant_id]['name']}", style='Header.TLabel')
        header.pack(pady=20)
        
        menu_frame = ttk.Frame(self.main_frame)
        menu_frame.pack(pady=10)
        
        for item in MENU_ITEMS[restaurant_id]:
            veg_mark = "🌱" if item['veg'] else "🍖"
            item_text = f"{item['item']} - {self.currency_symbol}{convert_currency(item['price'], self.currency_code):.2f} {veg_mark}"
            btn = ttk.Button(menu_frame, text=item_text,
                           command=lambda i=item: self.add_to_cart(i))
            btn.pack(pady=5, fill=tk.X, padx=20)
        
        self.cart_text = scrolledtext.ScrolledText(self.main_frame, width=80, height=10, wrap=tk.WORD)
        self.cart_text.pack(pady=10, padx=20)
        self.update_cart_display()
        
        buttons_frame = ttk.Frame(self.main_frame)
        buttons_frame.pack(pady=10)
        
        ttk.Button(buttons_frame, text="➖ Remove Item", command=self.remove_item).pack(side=tk.LEFT, padx=5)
        ttk.Button(buttons_frame, text="🎟️ Apply Promo", command=self.apply_promo).pack(side=tk.LEFT, padx=5)
        ttk.Button(buttons_frame, text="💳 Place Order", command=self.checkout).pack(side=tk.LEFT, padx=5)
        ttk.Button(self.main_frame, text="🔙 Back", command=self.show_restaurant_selection).pack(pady=10)
        
        self.order_status = ttk.Label(self.main_frame, text="", style='Error.TLabel')
        self.order_status.pack(pady=5)

    def update_cart_display(self):
        cart_text = display_cart(self.cart, self.language_code, self.currency_symbol)
        self.cart_text.delete(1.0, tk.END)
        self.cart_text.insert(tk.INSERT, cart_text)

    def add_to_cart(self, item):
        quantity = simpledialog.askinteger("Add Item", f"Enter quantity for {item['item']}:", minvalue=1)
        if quantity:
            cart_item = {
                "item": item['item'],
                "price": convert_currency(item['price'], self.currency_code),
                "quantity": quantity,
                "veg": item['veg']
            }
            self.cart.append(cart_item)
            self.update_cart_display()
            self.order_status.config(text=f"Added {quantity} x {item['item']} to order", style='Success.TLabel')

    def remove_item(self):
        if not self.cart:
            self.order_status.config(text="Order is empty", style='Error.TLabel')
            return
        
        item_num = simpledialog.askinteger("Remove Item", "Enter item number to remove:", minvalue=1, maxvalue=len(self.cart))
        if item_num:
            removed_item = self.cart.pop(item_num - 1)
            self.update_cart_display()
            self.order_status.config(text=f"Removed {removed_item['quantity']} x {removed_item['item']}", style='Success.TLabel')

    def apply_promo(self):
        if not self.cart:
            self.order_status.config(text="Order is empty", style='Error.TLabel')
            return
        
        total = sum(item['price'] * item['quantity'] for item in self.cart)
        promo_code = simpledialog.askstring("Promo Code", "Enter promo code:")
        if promo_code:
            discount, message = apply_promo_code(total, promo_code.upper(), self.language_code)
            self.promo_discount = discount
            self.order_status.config(text=message, style='Success.TLabel' if discount > 0 else 'Error.TLabel')

    def checkout(self):
        if not self.cart:
            self.order_status.config(text="Order is empty", style='Error.TLabel')
            return
        
        total = sum(item['price'] * item['quantity'] for item in self.cart)
        delivery_fee = convert_currency(50, self.currency_code)  # Fixed delivery fee
        promo_discount = getattr(self, 'promo_discount', 0)
        grand_total = total - promo_discount + delivery_fee
        
        receipt_path = generate_pdf(self.cart, total, promo_discount, delivery_fee, grand_total,
                                  self.currency_symbol, self.user_data, self.current_restaurant)
        
        self.auth.save_order_history(self.session_token, self.cart, grand_total,
                                   self.currency_symbol, self.current_restaurant)
        
        messagebox.showinfo("Order Placed", f"Order placed successfully!\nReceipt saved at: {receipt_path}")
        self.cart = []
        self.promo_discount = 0
        self.show_order_tracking()

    def show_order_history(self):
        self.clear_frame()
        
        header = ttk.Label(self.main_frame, text="📜 Order History", style='Header.TLabel')
        header.pack(pady=20)
        
        history = self.auth.get_order_history(self.session_token)
        if not history:
            ttk.Label(self.main_frame, text="No orders yet!").pack(pady=20)
        else:
            history_text = scrolledtext.ScrolledText(self.main_frame, width=80, height=20, wrap=tk.WORD)
            history_text.pack(pady=10, padx=20)
            for order in reversed(history):
                text = f"Order #{order['order_id']} - {order['date']}\n"
                text += f"Restaurant: {RESTAURANTS[order['restaurant_id']]['name']}\n"
                text += f"Total: {order['currency']}{order['total']:.2f}\n"
                text += f"Status: {order['status']}\n\n"
                history_text.insert(tk.END, text)
            history_text.config(state='disabled')
        
        ttk.Button(self.main_frame, text="🔙 Back", command=self.show_main_menu).pack(pady=20)

    def show_order_tracking(self):
        self.clear_frame()
        
        header = ttk.Label(self.main_frame, text="🚚 Order Tracking", style='Header.TLabel')
        header.pack(pady=20)
        
        history = self.auth.get_order_history(self.session_token)
        latest_order = history[-1] if history else None
        
        if latest_order:
            status_frame = ttk.Frame(self.main_frame)
            status_frame.pack(pady=20)
            
            ttk.Label(status_frame, text=f"Order #{latest_order['order_id']}").pack()
            ttk.Label(status_frame, text=f"Restaurant: {RESTAURANTS[latest_order['restaurant_id']]['name']}").pack()
            ttk.Label(status_frame, text=f"Status: {latest_order['status']}").pack()
            ttk.Label(status_frame, text=f"Estimated Delivery: {RESTAURANTS[latest_order['restaurant_id']]['delivery_time']}").pack()
        
        ttk.Button(self.main_frame, text="🏠 Home", command=self.show_main_menu).pack(pady=20)

    def handle_logout(self):
        self.auth.logout(self.session_token)
        self.session_token = None
        self.user_data = None
        self.cart = []
        self.show_login_screen()

if __name__ == "__main__":
    root = tk.Tk()
    app = FoodOrderingApp(root)
    root.mainloop()