from flask import Flask, render_template, request, redirect, url_for, session, flash, jsonify, make_response
from decimal import Decimal
import os

from app import app
from models import User, Product, Order, Comment, Cart, Wallet, Notification
from forms import LoginForm, RegisterForm, ChangePasswordForm, ProfileForm, TopupForm, CommentForm, GiftcodeForm, SearchForm
from utils import login_user, logout_user, is_logged_in, generate_reference_code, generate_qr_code, process_transaction
from config.settings import find_record, update_record, delete_record, find_record_by_sql

@app.before_request
def before_request():
    """Set up global variables for templates"""
    # Initialize search form for navbar
    if request.endpoint != 'static':
        g.search_form = SearchForm()
        
        # Get categories for navbar
        g.categories = find_record('categories')
        
        # Check if user is logged in
        if is_logged_in():
            user_id = session.get('user_id')
            g.user = User.get_by_id(user_id)
            
            # Get notifications
            g.notifications = Notification.get_for_user(user_id)
            
            # Count unread notifications
            g.unread_count = len([n for n in g.notifications if not n['is_read']])

# Login decorator
def login_required(f):
    @wraps(f)
    def decorated_function(*args, **kwargs):
        if not is_logged_in():
            flash('Vui lòng đăng nhập để truy cập trang này.', 'warning')
            return redirect(url_for('login', next=request.url))
        return f(*args, **kwargs)
    return decorated_function

# Home page
@app.route('/')
def home():
    featured_products = Product.get_all(featured=True, limit=8)
    categories = find_record('categories')
    return render_template('pages/home.html', featured_products=featured_products, categories=categories)

# Login page
@app.route('/login', methods=['GET', 'POST'])
def login():
    if is_logged_in():
        return redirect(url_for('home'))
        
    form = LoginForm()
    
    if form.validate_on_submit():
        email = form.email.data
        password = form.password.data
        
        # Check if user exists
        user = User.get_by_email(email)
        
        if user and password == user['password']:  # Plain text comparison for demo
            login_user(user)
            flash('Đăng nhập thành công!', 'success')
            
            next_page = request.args.get('next')
            if next_page:
                return redirect(next_page)
            return redirect(url_for('home'))
        else:
            flash('Email hoặc mật khẩu không chính xác', 'danger')
            
    return render_template('pages/login.html', form=form)

# Register page
@app.route('/register', methods=['GET', 'POST'])
def register():
    if is_logged_in():
        return redirect(url_for('home'))
        
    form = RegisterForm()
    
    if form.validate_on_submit():
        username = form.username.data
        email = form.email.data
        password = form.password.data
        full_name = form.full_name.data
        
        # Check if email already exists
        existing_user = User.get_by_email(email)
        if existing_user:
            flash('Email đã được đăng ký', 'danger')
            return render_template('pages/register.html', form=form)
            
        # Check if username already exists
        existing_username = User.get_by_username(username)
        if existing_username:
            flash('Tên đăng nhập đã được sử dụng', 'danger')
            return render_template('pages/register.html', form=form)
            
        # Create user
        user_result = User.create(username, email, password, full_name)
        
        if user_result and user_result.get('last_insert_id'):
            # Create empty wallet for user
            user_id = user_result['last_insert_id']
            Wallet.update_balance(user_id, 0)
            
            flash('Đăng ký thành công! Vui lòng đăng nhập.', 'success')
            return redirect(url_for('login'))
        else:
            flash('Có lỗi xảy ra trong quá trình đăng ký', 'danger')
            
    return render_template('pages/register.html', form=form)

# Logout
@app.route('/logout')
def logout():
    logout_user()
    flash('Đã đăng xuất', 'info')
    return redirect(url_for('home'))

# Profile page
@app.route('/profile', methods=['GET', 'POST'])
@login_required
def profile():
    user_id = session['user_id']
    user = User.get_by_id(user_id)
    
    form = ProfileForm()
    password_form = ChangePasswordForm()
    
    if form.validate_on_submit():
        data = {
            'full_name': form.full_name.data,
            'phone': form.phone.data,
            'address': form.address.data,
            'bio': form.bio.data
        }
        
        # Handle profile image upload
        if form.profile_image.data:
            profile_image = form.profile_image.data
            # Simple image saving logic for demo
            filename = f"user_{user_id}_profile.jpg"
            profile_image.save(os.path.join('static/uploads/profiles', filename))
            data['profile_image'] = f"/static/uploads/profiles/{filename}"
            
        update_result = User.update_profile(user_id, data)
        
        if update_result and update_result.get('affected_rows', 0) > 0:
            flash('Thông tin cá nhân đã được cập nhật', 'success')
            return redirect(url_for('profile'))
        else:
            flash('Có lỗi xảy ra khi cập nhật', 'danger')
            
    elif request.method == 'GET':
        form.full_name.data = user.get('full_name', '')
        form.phone.data = user.get('phone', '')
        form.address.data = user.get('address', '')
        form.bio.data = user.get('bio', '')
    
    # Get wallet balance
    wallet_balance = Wallet.get_balance(user_id)
    
    # Get recent transactions
    recent_transactions = Wallet.get_transactions(user_id, limit=5)
    
    # Get recent orders
    recent_orders = Order.get_user_orders(user_id, limit=5)
    
    return render_template('pages/profile.html', 
                          user=user, 
                          form=form, 
                          password_form=password_form,
                          wallet_balance=wallet_balance,
                          recent_transactions=recent_transactions,
                          recent_orders=recent_orders)

# Change password
@app.route('/change-password', methods=['POST'])
@login_required
def change_password():
    form = ChangePasswordForm()
    
    if form.validate_on_submit():
        user_id = session['user_id']
        user = User.get_by_id(user_id)
        
        current_password = form.current_password.data
        new_password = form.new_password.data
        
        if current_password == user['password']:  # Plain text comparison for demo
            update_result = User.change_password(user_id, new_password)
            
            if update_result and update_result.get('affected_rows', 0) > 0:
                flash('Mật khẩu đã được cập nhật', 'success')
            else:
                flash('Có lỗi xảy ra khi cập nhật mật khẩu', 'danger')
        else:
            flash('Mật khẩu hiện tại không chính xác', 'danger')
            
    return redirect(url_for('profile'))

# Product listing
@app.route('/products')
def products():
    category_id = request.args.get('category')
    products_list = Product.get_all(category_id=category_id)
    
    category_name = "Tất cả sản phẩm"
    if category_id:
        category = find_record('categories', {'id': category_id}, fetchone=True)
        if category:
            category_name = category['name']
    
    return render_template('pages/products.html', products=products_list, category_name=category_name)

# Product detail
@app.route('/product/<int:product_id>')
def product_detail(product_id):
    product = Product.get_by_id(product_id)
    
    if not product:
        flash('Sản phẩm không tồn tại', 'danger')
        return redirect(url_for('products'))
    
    # Get related products
    related_products = Product.get_all(category_id=product['category_id'], limit=4)
    
    # Get comments/reviews
    comments = Comment.get_for_product(product_id)
    
    form = CommentForm()
    
    return render_template('pages/product_detail.html', 
                          product=product, 
                          related_products=related_products,
                          comments=comments,
                          form=form)

# Add comment
@app.route('/product/<int:product_id>/comment', methods=['POST'])
@login_required
def add_comment(product_id):
    form = CommentForm()
    
    if form.validate_on_submit():
        user_id = session['user_id']
        comment = form.comment.data
        rating = int(form.rating.data)
        
        result = Comment.create(user_id, product_id, comment, rating)
        
        if result and result.get('last_insert_id'):
            flash('Đánh giá của bạn đã được gửi', 'success')
        else:
            flash('Có lỗi xảy ra khi gửi đánh giá', 'danger')
    
    return redirect(url_for('product_detail', product_id=product_id))

# Confirm purchase
@app.route('/confirm-purchase/<int:product_id>', methods=['GET', 'POST'])
@login_required
def confirm_purchase(product_id):
    """Xác nhận mua hàng"""
    user_id = session['user_id']
    user = User.get_by_id(user_id)
    product = Product.get_by_id(product_id)
    
    if not product:
        flash('Sản phẩm không tồn tại', 'danger')
        return redirect(url_for('products'))
    
    # Kiểm tra còn hàng không
    if product['stock_quantity'] <= 0:
        flash('Sản phẩm đã hết hàng', 'danger')
        return redirect(url_for('product_detail', product_id=product_id))
    
    # Lấy số lượng từ form
    quantity = int(request.form.get('quantity', 1))
    
    # Kiểm tra số lượng hợp lệ
    if quantity <= 0:
        flash('Số lượng không hợp lệ', 'danger')
        return redirect(url_for('product_detail', product_id=product_id))
    
    if quantity > product['stock_quantity']:
        flash('Số lượng vượt quá hàng tồn kho', 'danger')
        return redirect(url_for('product_detail', product_id=product_id))
    
    # Tính tổng tiền
    from decimal import Decimal
    
    # Đảm bảo kiểu dữ liệu nhất quán - chuyển về Decimal
    if product['discount_price']:
        unit_price = Decimal(str(product['discount_price']))
    else:
        unit_price = Decimal(str(product['price']))
        
    quantity_decimal = Decimal(str(quantity))
    total_amount = unit_price * quantity_decimal
    
    # Kiểm tra số dư - đảm bảo cùng kiểu dữ liệu
    wallet_balance = Decimal(str(user['wallet_balance']))
    if wallet_balance < total_amount:
        flash('Số dư không đủ. Vui lòng nạp thêm tiền.', 'danger')
        return redirect(url_for('topup'))
    
    # Hiển thị trang xác nhận
    return render_template('pages/confirm_purchase.html', 
                          product=product, 
                          quantity=quantity, 
                          total_amount=total_amount,
                          wallet_balance=wallet_balance)

# Process purchase
@app.route('/process-purchase/<int:product_id>', methods=['POST'])
@login_required
def process_purchase(product_id):
    """Xử lý mua hàng sau khi xác nhận"""
    user_id = session['user_id']
    user = User.get_by_id(user_id)
    product = Product.get_by_id(product_id)
    
    if not product:
        flash('Sản phẩm không tồn tại', 'danger')
        return redirect(url_for('products'))
    
    # Lấy số lượng từ form
    quantity = int(request.form.get('quantity', 1))
    
    # Kiểm tra số lượng hợp lệ
    if quantity <= 0:
        flash('Số lượng không hợp lệ', 'danger')
        return redirect(url_for('product_detail', product_id=product_id))
    
    if quantity > product['stock_quantity']:
        flash('Số lượng vượt quá hàng tồn kho', 'danger')
        return redirect(url_for('product_detail', product_id=product_id))
    
    # Tính tổng tiền
    from decimal import Decimal
    
    # Đảm bảo kiểu dữ liệu nhất quán - chuyển về Decimal
    if product['discount_price']:
        unit_price = Decimal(str(product['discount_price']))
    else:
        unit_price = Decimal(str(product['price']))
        
    quantity_decimal = Decimal(str(quantity))
    total_amount = unit_price * quantity_decimal
    
    # Kiểm tra số dư - đảm bảo cùng kiểu dữ liệu
    wallet_balance = Decimal(str(user['wallet_balance']))
    if wallet_balance < total_amount:
        flash('Số dư không đủ. Vui lòng nạp thêm tiền.', 'danger')
        return redirect(url_for('topup'))
    
    # Tạo mã tham chiếu cho đơn hàng
    reference_code = generate_reference_code()
    
    # Tạo đơn hàng và kiểm tra việc tạo đơn hàng thành công
    transaction_success = False
    order_id = None
    item_result = None
    gmail_accounts = []
    
    try:
        # Trước tiên, xử lý thanh toán
        success, message = process_transaction(
            user_id, 
            total_amount, 
            'debit', 
            f"Purchase: {product['name']} (x{quantity}) - Order #{reference_code}"
        )
        
        if not success:
            flash('Thanh toán thất bại', 'danger')
            return redirect(url_for('product_detail', product_id=product_id))
            
        # Sau khi thanh toán thành công, tạo đơn hàng
        order_result = Order.create(
            user_id=user_id,
            total_amount=total_amount,
            shipping_address=user['address'] or 'Digital delivery',
            payment_method='Wallet',
            reference_code=reference_code
        )
        
        if order_result and order_result.get('last_insert_id'):
            order_id = order_result['last_insert_id']
            transaction_success = True
            
            # Thêm sản phẩm vào đơn hàng
            item_result = Order.add_item(
                order_id=order_id,
                product_id=product_id,
                quantity=quantity,
                price=unit_price
            )
            
            if item_result and item_result.get('last_insert_id'):
                # Xử lý Gmail nếu là sản phẩm Gmail
                if 'Gmail' in product['name']:
                    # Lấy Gmail từ cơ sở dữ liệu và đánh dấu đã bán
                    gmail_result = find_record_by_sql(
                        "SELECT * FROM gmail_accounts WHERE is_sold = FALSE LIMIT %s",
                        [quantity],
                        fetchone=False
                    )
                    
                    if gmail_result and len(gmail_result) >= quantity:
                        for i in range(quantity):
                            gmail_account = gmail_result[i]
                            # Cập nhật trạng thái Gmail
                            update_record(
                                'gmail_accounts',
                                {'is_sold': True, 'order_id': order_id},
                                {'id': gmail_account['id']}
                            )
                            gmail_accounts.append(gmail_account)
                
                # Cập nhật số lượng sản phẩm
                # Đảm bảo số lượng luôn là số nguyên không âm
                from decimal import Decimal
                
                # Đảm bảo kiểu dữ liệu nhất quán - chuyển đổi sang số nguyên
                if isinstance(product['stock_quantity'], Decimal):
                    current_stock = int(product['stock_quantity'])
                else:
                    current_stock = int(product['stock_quantity'])
                    
                quantity_to_reduce = int(quantity)
                new_stock = max(0, current_stock - quantity_to_reduce)
                
                update_record(
                    'products',
                    {'stock_quantity': new_stock},
                    {'id': product_id}
                )
                
                # Lấy thông tin đơn hàng
                order = find_record('orders', {'id': order_id}, fetchone=True)
                order_items = find_record('order_items', {'order_id': order_id})
                
                # Thêm thông tin sản phẩm vào đơn hàng
                for item in order_items:
                    prod = Product.get_by_id(item['product_id'])
                    if prod:
                        item['product_name'] = prod['name']
                
                # Trả về JSON response cho xử lý modal
                if request.headers.get('X-Requested-With') == 'XMLHttpRequest':
                    return jsonify({
                        'success': True, 
                        'order': order,
                        'redirect_url': url_for('product_detail', product_id=product_id, order_success=True, order_id=order_id)
                    })
                
                # Nếu không phải AJAX, hiển thị trang xác nhận đơn hàng
                return render_template('pages/order_confirmation.html', 
                                      order=order, 
                                      order_items=order_items,
                                      gmail_accounts=gmail_accounts,
                                      discount=0)
    except Exception as e:
        # Log the error
        print(f"Error in processing purchase: {str(e)}")
        # If any error occurs during transaction, show an error message
        flash('Giao dịch thất bại: ' + str(e), 'danger')
        
    # If we get here, something went wrong
    return redirect(url_for('product_detail', product_id=product_id))

# Tải về Gmail
@app.route('/download-gmail/<int:order_id>')
@login_required
def download_gmail_accounts(order_id):
    """Tải về danh sách Gmail đã mua"""
    user_id = session['user_id']
    
    # Kiểm tra đơn hàng có thuộc về user không
    order = find_record('orders', {'id': order_id, 'user_id': user_id}, fetchone=True)
    
    if not order:
        flash('Đơn hàng không tồn tại hoặc bạn không có quyền truy cập', 'danger')
        return redirect(url_for('orders'))
    
    # Lấy danh sách Gmail
    gmail_accounts = find_record('gmail_accounts', {'order_id': order_id})
    
    if not gmail_accounts:
        flash('Không tìm thấy tài khoản Gmail trong đơn hàng này', 'danger')
        return redirect(url_for('orders'))
    
    # Tạo nội dung file txt
    content = f"Mã đơn hàng: {order['reference_code']}\n"
    content += f"Ngày mua: {order['created_at'].strftime('%d/%m/%Y %H:%M:%S')}\n\n"
    content += "STT\tEmail\t\t\tMật khẩu\n"
    content += "-------------------------------------------\n"
    
    for i, account in enumerate(gmail_accounts, 1):
        content += f"{i}\t{account['email']}\t{account['password']}\n"
    
    # Tạo response
    response = make_response(content)
    response.headers["Content-Disposition"] = f"attachment; filename=gmail_order_{order['reference_code']}.txt"
    response.headers["Content-Type"] = "text/plain; charset=utf-8"
    
    return response

# Top up wallet
@app.route('/topup', methods=['GET', 'POST'])
@login_required
def topup():
    form = TopupForm()
    giftcode_form = GiftcodeForm()
    
    if form.validate_on_submit():
        amount = form.amount.data
        bank = form.bank_name.data
        
        # Generate reference code
        ref_code = generate_reference_code()
        session['topup_ref'] = ref_code
        session['topup_amount'] = float(amount)
        
        # Bank details
        bank_details = {
            'vcb': {
                'name': 'Vietcombank',
                'account': '1234567890',
                'holder': 'NGUYEN VAN A'
            },
            'tcb': {
                'name': 'Techcombank',
                'account': '0987654321',
                'holder': 'NGUYEN VAN A'
            },
            'mb': {
                'name': 'MB Bank',
                'account': '123456789012',
                'holder': 'NGUYEN VAN A'
            },
            'acb': {
                'name': 'ACB',
                'account': '0123456789',
                'holder': 'NGUYEN VAN A'
            }
        }
        
        selected_bank = bank_details.get(bank)
        
        if not selected_bank:
            flash('Invalid bank selection', 'danger')
            return redirect(url_for('topup'))
        
        # Generate QR code data
        qr_data = f"Banking info: {selected_bank['name']}\nAccount: {selected_bank['account']}\nHolder: {selected_bank['holder']}\nAmount: {amount}\nContent: {ref_code}"
        qr_code = generate_qr_code(qr_data)
        
        return render_template('pages/topup.html', 
                              form=form, 
                              giftcode_form=giftcode_form,
                              bank=selected_bank, 
                              ref_code=ref_code, 
                              amount=amount,
                              qr_code=qr_code,
                              show_payment=True)
    
    return render_template('pages/topup.html', form=form, giftcode_form=giftcode_form, show_payment=False)

# Redeem gift code
@app.route('/redeem-giftcode', methods=['POST'])
@login_required
def redeem_giftcode():
    form = GiftcodeForm()
    
    if form.validate_on_submit():
        code = form.code.data
        
        # For demo purposes, let's say 'DEMO123' is a valid code worth 100,000 VND
        if code == 'DEMO123':
            user_id = session['user_id']
            success, new_balance = process_transaction(
                user_id=user_id,
                amount=100000,
                transaction_type='credit',
                description='Gift code: DEMO123'
            )
            
            if success:
                flash('Gift code redeemed successfully! 100,000 VND added to your wallet.', 'success')
            else:
                flash('Failed to redeem gift code', 'danger')
        else:
            flash('Invalid gift code', 'danger')
    
    return redirect(url_for('topup'))

# Simulate topup completion (this would normally be done by a background process)
@app.route('/complete-topup', methods=['POST'])
@login_required
def complete_topup():
    ref_code = session.get('topup_ref')
    amount = session.get('topup_amount')
    
    if not ref_code or not amount:
        flash('Invalid topup session', 'danger')
        return redirect(url_for('topup'))
    
    user_id = session['user_id']
    
    # Process transaction
    success, new_balance = process_transaction(
        user_id=user_id,
        amount=amount,
        transaction_type='credit',
        description=f'Topup: {ref_code}'
    )
    
    if success:
        # Clear topup session
        session.pop('topup_ref', None)
        session.pop('topup_amount', None)
        
        flash(f'Topup successful! {amount} VND added to your wallet.', 'success')
        return redirect(url_for('transactions'))
    else:
        flash('Failed to complete topup', 'danger')
        return redirect(url_for('topup'))

# Transactions
@app.route('/transactions')
@login_required
def transactions():
    user_id = session['user_id']
    
    # Get user's transactions
    transactions_list = Wallet.get_transactions(user_id)
    
    return render_template('pages/transactions.html', transactions=transactions_list)

# Orders
@app.route('/orders')
@login_required
def orders():
    user_id = session['user_id']
    
    # Get user's orders
    orders_list = Order.get_user_orders(user_id)
    
    # Get items for each order
    for order in orders_list:
        order['items'] = Order.get_order_items(order['id'])
    
    return render_template('pages/orders.html', orders=orders_list)

# Error handlers
@app.errorhandler(404)
def page_not_found(e):
    return render_template('pages/error.html', error=404, message="Page not found"), 404

@app.errorhandler(500)
def server_error(e):
    return render_template('pages/error.html', error=500, message="Server error"), 500

@app.route('/support')
def support():
    """Support page with contact information and FAQ"""
    return render_template('pages/support.html')