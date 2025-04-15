# Removing bcrypt import to store plain passwords
# from flask_bcrypt import generate_password_hash, check_password_hash
from datetime import datetime
from config.settings import *

class User:
    @staticmethod
    def create(username, email, password, full_name=None, phone=None, address=None):
        """Create a new user"""
        # Sử dụng mật khẩu thực tế, không hash
        data = {
            'username': username,
            'email': email,
            'password_hash': password,  # Lưu mật khẩu thực tế
            'full_name': full_name,
            'created_at': datetime.now()
        }
        
        if phone:
            data['phone'] = phone
        if address:
            data['address'] = address

        return insert_record('users', data)
    
    @staticmethod
    def get_by_id(user_id):
        """Get user by ID"""
        return find_record('users', {'id': user_id}, fetchone=True)
    
    @staticmethod
    def get_by_email(email):
        """Get user by email"""
        return find_record_by_sql("SELECT * FROM users WHERE email = %s", [email], fetchone=True)
    
    @staticmethod
    def get_by_username(username):
        """Get user by username"""
        return find_record_by_sql("SELECT * FROM users WHERE username = %s", [username], fetchone=True)
    
    @staticmethod
    def check_password(user, password):
        """Check if password is correct"""
        if not user:
            return False
        # So sánh trực tiếp mật khẩu thay vì dùng hàm hash
        return user['password_hash'] == password
    
    @staticmethod
    def update_profile(user_id, data):
        """Update user profile"""
        # Tối ưu hiệu suất với việc lưu trữ hình ảnh đại diện
        condition = {'id': user_id}
        return update_record('users', data, condition)
    
    @staticmethod
    def change_password(user_id, new_password):
        """Change user password"""
        # Lưu mật khẩu thật, không hash
        condition = {'id': user_id}
        data = {'password_hash': new_password, 'updated_at': datetime.now()}
        return update_record('users', data, condition)

class Category:
    @staticmethod
    def get_all():
        """Get all categories"""
        return find_record('categories')
    
    @staticmethod
    def get_by_id(category_id):
        """Get category by ID"""
        return find_record('categories', {'id': category_id}, fetchone=True)

class Product:
    @staticmethod
    def get_all(category_id=None, featured=None, limit=None):
        """Get all products with optional filtering"""
        query = "SELECT p.*, c.name as category_name FROM products p JOIN categories c ON p.category_id = c.id"
        params = []
        
        if category_id or featured is not None:
            query += " WHERE"
            conditions = []
            
            if category_id:
                conditions.append(" p.category_id = %s")
                params.append(category_id)
            
            if featured is not None:
                conditions.append(" p.featured = %s")
                params.append(featured)
            
            query += " AND".join(conditions)
        
        query += " ORDER BY p.created_at DESC"
        
        if limit:
            query += f" LIMIT {limit}"
        
        return find_record_by_sql(query, params)
    
    @staticmethod
    def get_by_id(product_id):
        """Get product by ID"""
        query = """
            SELECT p.*, c.name as category_name 
            FROM products p 
            JOIN categories c ON p.category_id = c.id 
            WHERE p.id = %s
        """
        return find_record_by_sql(query, [product_id], fetchone=True)
    
    @staticmethod
    def search(keyword):
        """Search products by keyword"""
        query = """
            SELECT p.*, c.name as category_name 
            FROM products p 
            JOIN categories c ON p.category_id = c.id 
            WHERE p.name LIKE %s OR p.description LIKE %s
            ORDER BY p.created_at DESC
        """
        search_term = f"%{keyword}%"
        return find_record_by_sql(query, [search_term, search_term])

    @staticmethod
    def get_by_category(category_id):
        """Get products by category"""
        return find_record('products', {'category_id': category_id})

    @staticmethod
    def update_stock(product_id, quantity_change):
        """Update product stock quantity"""
        try:
            # Lấy số lượng hiện tại
            product = find_record('products', {'id': product_id}, fetchone=True)
            if not product:
                return False
                
            current_stock = product['stock_quantity']
            new_stock = max(0, current_stock + quantity_change)  # Đảm bảo số lượng không âm
            
            # Cập nhật số lượng mới
            result = update_record(
                'products',
                {'stock_quantity': new_stock},
                {'id': product_id}
            )
            
            return result and result.get('affected_rows', 0) > 0
        except Exception as e:
            print(f"Error updating stock: {str(e)}")
            return False

    @staticmethod
    def create(name, description, price, category_id, image_url=None, stock_quantity=0, discount_price=None, badge=None):
        """Create a new product"""
        data = {
            'name': name,
            'description': description,
            'price': price,
            'category_id': category_id,
            'image_url': image_url,
            'stock_quantity': stock_quantity,
            'discount_price': discount_price,
            'badge': badge,
            'created_at': datetime.now()
        }
        return insert_record('products', data)

class Cart:
    @staticmethod
    def add_item(user_id, product_id, quantity=1):
        """Add item to cart"""
        # Check if product already in cart
        existing = find_record_by_sql(
            "SELECT * FROM cart_items WHERE user_id = %s AND product_id = %s",
            [user_id, product_id],
            fetchone=True
        )
        
        if existing:
            # Update quantity
            data = {
                'quantity': existing['quantity'] + quantity,
                'updated_at': datetime.now()
            }
            condition = {'id': existing['id']}
            return update_record('cart_items', data, condition)
        else:
            # Insert new cart item
            data = {
                'user_id': user_id,
                'product_id': product_id,
                'quantity': quantity,
                'created_at': datetime.now()
            }
            return insert_record('cart_items', data)
    
    @staticmethod
    def get_items(user_id):
        """Get cart items for user"""
        query = """
            SELECT c.*, p.name, p.price, p.image_url, p.stock_quantity
            FROM cart_items c
            JOIN products p ON c.product_id = p.id
            WHERE c.user_id = %s
        """
        return find_record_by_sql(query, [user_id])
    
    @staticmethod
    def update_quantity(cart_id, quantity):
        """Update cart item quantity"""
        data = {'quantity': quantity, 'updated_at': datetime.now()}
        condition = {'id': cart_id}
        return update_record('cart_items', data, condition)
    
    @staticmethod
    def remove_item(cart_id):
        """Remove item from cart"""
        condition = {'id': cart_id}
        return delete_record('cart_items', condition)
    
    @staticmethod
    def clear_cart(user_id):
        """Clear all items from user's cart"""
        condition = {'user_id': user_id}
        return delete_record('cart_items', condition)

class Wallet:
    @staticmethod
    def get_balance(user_id):
        """Get user wallet balance"""
        user = find_record('users', {'id': user_id}, select="wallet_balance", fetchone=True)
        return user['wallet_balance'] if user else 0
    
    @staticmethod
    def update_balance(user_id, amount):
        """Update user wallet balance"""
        data = {'wallet_balance': amount, 'updated_at': datetime.now()}
        condition = {'id': user_id}
        return update_record('users', data, condition)
    
    @staticmethod
    def add_transaction(user_id, amount, transaction_type, description):
        """Add transaction record"""
        data = {
            'user_id': user_id,
            'amount': amount,
            'transaction_type': transaction_type,
            'description': description,
            'created_at': datetime.now()
        }
        return insert_record('wallet_transactions', data)
    
    @staticmethod
    def get_transactions(user_id):
        """Get wallet transactions for user"""
        return find_record('wallet_transactions', {'user_id': user_id}, order_by="created_at DESC")

class Order:
    @staticmethod
    def create(user_id, total_amount, shipping_address, payment_method, reference_code=None, voucher_code=None, discount_amount=None):
        """Create a new order"""
        # Import thực hiện tại thời điểm sử dụng để tránh circular import
        from utils import generate_reference_code
        
        data = {
            'user_id': user_id,
            'total_amount': total_amount,
            'status': 'completed',  # For digital products, we mark as completed immediately
            'shipping_address': shipping_address,
            'payment_method': payment_method,
            'reference_code': reference_code or generate_reference_code(),
            'voucher_code': voucher_code,
            'discount_amount': discount_amount,
            'created_at': datetime.now()
        }
        return insert_record('orders', data)
    
    @staticmethod
    def add_item(order_id, product_id, quantity, price):
        """Add item to order"""
        data = {
            'order_id': order_id,
            'product_id': product_id,
            'quantity': quantity,
            'price': price
        }
        return insert_record('order_items', data)
    
    @staticmethod
    def get_user_orders(user_id):
        """Get orders for user"""
        return find_record('orders', {'user_id': user_id}, order_by="created_at DESC")
    
    @staticmethod
    def get_order_items(order_id):
        """Get items for an order"""
        query = """
            SELECT oi.*, p.name, p.image_url
            FROM order_items oi
            JOIN products p ON oi.product_id = p.id
            WHERE oi.order_id = %s
        """
        return find_record_by_sql(query, [order_id])
    
    @staticmethod
    def get_order_with_items(order_id):
        """Get order with its items"""
        order = find_record('orders', {'id': order_id}, fetchone=True)
        if order:
            order['items'] = Order.get_order_items(order_id)
        return order

class Comment:
    @staticmethod
    def create(user_id, product_id, comment, rating):
        """Create a new comment/review"""
        data = {
            'user_id': user_id,
            'product_id': product_id,
            'comment': comment,
            'rating': rating,
            'created_at': datetime.now()
        }
        return insert_record('comments', data)
    
    @staticmethod
    def get_for_product(product_id):
        """Get comments for a product"""
        query = """
            SELECT c.*, u.username, u.profile_image
            FROM comments c
            JOIN users u ON c.user_id = u.id
            WHERE c.product_id = %s
            ORDER BY c.created_at DESC
        """
        return find_record_by_sql(query, [product_id])

class Notification:
    @staticmethod
    def create(user_id, title, message, notification_type="info"):
        """Create a new notification"""
        data = {
            'user_id': user_id,
            'title': title,
            'message': message,
            'type': notification_type,
            'created_at': datetime.now()
        }
        return insert_record('notifications', data)
    
    @staticmethod
    def get_for_user(user_id, limit=5):
        """Get notifications for a user"""
        return find_record('notifications', {'user_id': user_id}, order_by="created_at DESC", limit=limit)
    
    @staticmethod
    def mark_as_read(notification_id):
        """Mark notification as read"""
        data = {'is_read': True}
        condition = {'id': notification_id}
        return update_record('notifications', data, condition)
