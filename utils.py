import os
import random
import string
import qrcode
from io import BytesIO
import base64
from flask import session
from datetime import datetime
from decimal import Decimal
import json

def generate_reference_code(prefix="TS"):
    """Generate a unique reference code for transactions"""
    chars = string.digits
    random_code = ''.join(random.choice(chars) for _ in range(6))
    return f"{prefix} {random_code}"

def generate_qr_code(data):
    """Generate QR code image from data"""
    qr = qrcode.QRCode(
        version=1,
        error_correction=qrcode.constants.ERROR_CORRECT_L,
        box_size=10,
        border=4,
    )
    qr.add_data(data)
    qr.make(fit=True)
    
    img = qr.make_image(fill_color="black", back_color="white")
    
    buffered = BytesIO()
    img.save(buffered)
    img_str = base64.b64encode(buffered.getvalue()).decode()
    
    return f"data:image/png;base64,{img_str}"

def login_user(user):
    """Log in a user by setting session variables"""
    if user:
        session['user_id'] = user['id']
        session['username'] = user['username']
        session['email'] = user['email']
        session['logged_in'] = True

def logout_user():
    """Log out a user by clearing session variables"""
    session.clear()

def is_logged_in():
    """Check if a user is logged in"""
    return session.get('logged_in', False)

def process_transaction(user_id, amount, transaction_type, description):
    """Process a wallet transaction"""
    # Import các thư viện cần thiết tại điểm sử dụng để tránh circular import
    from models import Wallet, Notification
    
    # Get current balance
    current_balance = Wallet.get_balance(user_id)
    
    # Convert to decimal if needed
    if not isinstance(current_balance, Decimal):
        current_balance = Decimal(str(current_balance))
    if not isinstance(amount, Decimal):
        amount = Decimal(str(amount))
    
    # Calculate new balance
    if transaction_type == 'credit':
        new_balance = current_balance + amount
    else:  # debit
        if current_balance < amount:
            return False, "Insufficient balance"
        new_balance = current_balance - amount
    
    # Update balance
    update_result = Wallet.update_balance(user_id, new_balance)
    
    if update_result and update_result.get('affected_rows', 0) > 0:
        # Record transaction
        transaction_result = Wallet.add_transaction(user_id, amount, transaction_type, description)
        
        if transaction_result and transaction_result.get('last_insert_id'):
            # Create notification
            if transaction_type == 'credit':
                title = "Top-up Successful"
                message = f"Your account has been credited with {amount}. New balance: {new_balance}"
            else:
                title = "Purchase Successful" 
                message = f"Your account has been debited with {amount}. New balance: {new_balance}"
            
            Notification.create(user_id, title, message, "success")
            
            return True, new_balance
    
    return False, "Transaction failed"

def format_date(date_str):
    """Format date string for display"""
    if isinstance(date_str, str):
        dt = datetime.strptime(date_str, '%Y-%m-%d %H:%M:%S')
    else:
        dt = date_str
    return dt.strftime('%d %b %Y, %H:%M')

class CustomJSONEncoder(json.JSONEncoder):
    def default(self, obj):
        if isinstance(obj, Decimal):
            return float(obj)
        if isinstance(obj, datetime):
            return obj.isoformat()
        return super().default(obj)

def format_currency(amount):
    """Format currency with thousand separator"""
    return "{:,.2f}".format(float(amount))
