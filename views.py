from flask import render_template, redirect, url_for, request, session, flash, abort, jsonify, make_response, g
from functools import wraps
from datetime import datetime
from decimal import Decimal
import os

from app import app
from models import User, Product, Category, Cart, Wallet, Order, Comment, Notification
from forms import LoginForm, RegisterForm, ChangePasswordForm, ProfileForm, TopupForm, CommentForm, GiftcodeForm, SearchForm
from utils import generate_reference_code, generate_qr_code, login_user, logout_user, is_logged_in, process_transaction
from config.settings import find_record, find_record_by_sql, update_record, delete_record, insert_record

# Decorator to require login
def login_required(f):
    @wraps(f)
    def decorated_function(*args, **kwargs):
        if not is_logged_in():
            flash('Vui lòng đăng nhập để truy cập', 'warning')
            return redirect(url_for('login'))
        return f(*args, **kwargs)
    return decorated_function

# Store current user in g for templates
@app.before_request
def before_request():
    if is_logged_in():
        user_id = session.get('user_id')
        user = User.get_by_id(user_id)
        
        if user:
            # Make user data available for templates
            app.jinja_env.globals.update(
                current_user=user,
                notifications=Notification.get_for_user(user_id)
            )

# Home page
@app.route('/')
def home():
    # Get featured products
    featured_products = Product.get_all(featured=True, limit=8)
    categories = Category.get_all()
    
    return render_template('pages/home.html', 
                          featured_products=featured_products,
                          categories=categories)

# Login
@app.route('/login', methods=['GET', 'POST'])
def login():
    if is_logged_in():
        return redirect(url_for('home'))
    
    form = LoginForm()
    
    if form.validate_on_submit():
        email = form.email.data
        password = form.password.data
        
        # Try to find user by email
        user = User.get_by_email(email)
        
        if user and User.check_password(user, password):
            login_user(user)
            flash('Đăng nhập thành công', 'success')
            return redirect(url_for('home'))
        else:
            flash('Email hoặc mật khẩu không hợp lệ', 'danger')
    
    return render_template('pages/login.html', form=form)

# Register
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
        
        # Check if username or email already exists
        existing_user = User.get_by_username(username)
        if existing_user:
            flash('Username đã tồn tại', 'danger')
            return render_template('pages/register.html', form=form)
        
        existing_email = User.get_by_email(email)
        if existing_email:
            flash('Email đã tồn tại', 'danger')
            return render_template('pages/register.html', form=form)
        
        # Create user
        result = User.create(username, email, password, full_name)
        
        if result and result.get('last_insert_id'):
            flash('Đăng ký thành công, bạn có thể đăng nhập', 'success')
            return redirect(url_for('login'))
        else:
            flash('Đăng ký thất bại', 'danger')
    
    return render_template('pages/register.html', form=form)

# Logout
@app.route('/logout')
def logout():
    logout_user()
    flash('Bạn đã được đăng xuất', 'info')
    return redirect(url_for('home'))

# Profile
@app.route('/profile', methods=['GET', 'POST'])
@login_required
def profile():
    user_id = session['user_id']
    user = User.get_by_id(user_id)
    
    if not user:
        abort(404)
    
    # Lấy danh sách giao dịch gần đây để hiển thị
    transactions = find_record(
        'wallet_transactions', 
        {'user_id': user_id}, 
        order_by='created_at DESC', 
        limit=5
    )
    
    # Nếu là yêu cầu GET, tạo form với dữ liệu từ user
    if request.method == 'GET':
        form = ProfileForm()
        form.full_name.data = user.get('full_name', '')
        form.phone.data = user.get('phone', '')
        form.address.data = user.get('address', '')
        form.bio.data = user.get('bio', '')
    else:
        form = ProfileForm()
    
    if form.validate_on_submit():
        data = {
            'full_name': form.full_name.data,
            'phone': form.phone.data,
            'address': form.address.data,
            'bio': form.bio.data,
            'updated_at': datetime.now()
        }
        
        # Xử lý tải lên hình ảnh đại diện - tối ưu hiệu suất
        if form.profile_image.data and form.profile_image.data.filename:
            # Import tại đây để tránh xung đột
            import os
            from PIL import Image
            import secrets
            import io
            
            try:
                # Đọc file vào bộ nhớ thay vì tạo file tạm
                file_data = form.profile_image.data.read()
                
                if file_data:  # Chỉ xử lý khi có dữ liệu file
                    # Tạo tên file ngẫu nhiên để tránh trùng lặp
                    random_hex = secrets.token_hex(8)
                    _, file_extension = os.path.splitext(form.profile_image.data.filename)
                    image_filename = random_hex + file_extension.lower()
                    
                    # Đảm bảo thư mục tồn tại
                    upload_dir = 'static/uploads/profiles'
                    if not os.path.exists(upload_dir):
                        os.makedirs(upload_dir, exist_ok=True)
                    
                    # Đường dẫn lưu file
                    image_path = os.path.join(upload_dir, image_filename)
                    
                    # Xử lý trong bộ nhớ, tối ưu hiệu suất
                    img = Image.open(io.BytesIO(file_data))
                    img.thumbnail((200, 200))  # Resize thành kích thước hợp lý
                    
                    # Lưu ảnh với định dạng tối ưu
                    if file_extension.lower() in ['.jpg', '.jpeg']:
                        img.save(image_path, optimize=True, quality=85)
                    elif file_extension.lower() == '.png':
                        img.save(image_path, optimize=True, compress_level=7)
                    else:
                        img.save(image_path)
                    
                    # Thêm vào dữ liệu cập nhật
                    data['profile_image'] = '/static/uploads/profiles/' + image_filename
            except Exception as e:
                print(f"Lỗi xử lý tải ảnh: {str(e)}")
                # Không cập nhật ảnh đại diện nếu có lỗi
        
        # Update user profile
        result = User.update_profile(user_id, data)
        
        if result and result.get('affected_rows', 0) > 0:
            # Sử dụng JavaScript toast thay vì flash để tránh hiển thị thông báo ở nhiều nơi
            session['show_toast'] = {
                'message': 'Cập nhật hồ sơ thành công',
                'type': 'success'
            }
            # Force refresh user data
            user = User.get_by_id(user_id)
            return redirect(url_for('profile'))
        else:
            session['show_toast'] = {
                'message': 'Cập nhật hồ sơ thất bại',
                'type': 'danger'
            }
    
    # Get recent transactions
    transactions = Wallet.get_transactions(user_id)
    
    return render_template('pages/profile.html', form=form, user=user, transactions=transactions)

# Change password
@app.route('/change-password', methods=['GET', 'POST'])
@login_required
def change_password():
    form = ChangePasswordForm()
    
    if form.validate_on_submit():
        user_id = session['user_id']
        user = User.get_by_id(user_id)
        
        if not user:
            abort(404)
        
        # Check current password
        if not User.check_password(user, form.current_password.data):
            session['show_toast'] = {
                'message': 'Mật khẩu hiện tại không chính xác',
                'type': 'danger'
            }
            return render_template('pages/change_password.html', form=form)
        
        # Change password
        result = User.change_password(user_id, form.new_password.data)
        
        if result and result.get('affected_rows', 0) > 0:
            session['show_toast'] = {
                'message': 'Đổi mật khẩu thành công',
                'type': 'success'
            }
            return redirect(url_for('profile'))
        else:
            session['show_toast'] = {
                'message': 'Đổi mật khẩu thất bại',
                'type': 'danger'
            }
    
    return render_template('pages/change_password.html', form=form)

# Products
@app.route('/products')
def products():
    # Lấy các tham số tìm kiếm và lọc
    category_id = request.args.get('category')
    search_query = request.args.get('q')
    sort_option = request.args.get('sort', 'newest')
    
    # Lấy các bộ lọc bổ sung
    in_stock = request.args.get('in_stock') == '1'
    has_discount = request.args.get('has_discount') == '1'
    featured = request.args.get('featured') == '1'
    high_rated = request.args.get('high_rated') == '1'
    
    products_list = []
    categories = Category.get_all()
    
    # Tính số lượng sản phẩm cho mỗi danh mục
    all_products = Product.get_all()
    category_counts = {}
    for prod in all_products:
        cat_id = prod.get('category_id')
        if cat_id:
            category_counts[cat_id] = category_counts.get(cat_id, 0) + 1
    
    # Thêm thông tin số lượng vào mỗi danh mục
    for cat in categories:
        cat['count'] = category_counts.get(cat['id'], 0)
    
    title = 'Tất cả sản phẩm'
    
    # Lọc sản phẩm theo danh mục hoặc từ khóa
    if search_query:
        products_list = Product.search(search_query)
        title = f'Kết quả tìm kiếm cho "{search_query}"'
    elif category_id:
        products_list = Product.get_all(category_id=category_id)
        # Tìm tên danh mục
        category_name = None
        for cat in categories:
            if str(cat['id']) == str(category_id):
                category_name = cat['name']
                break
        title = f'Danh mục: {category_name}' if category_name else 'Sản phẩm'
    else:
        products_list = Product.get_all()
    
    # Thêm số lượng Gmail chưa bán cho mỗi sản phẩm
    for product in products_list:
        if 'Gmail' in product['name']:
            gmail_count = find_record_by_sql(
                "SELECT COUNT(*) as count FROM gmail_accounts WHERE is_sold = FALSE AND product_id = %s",
                [product['id']],
                fetchone=True
            )
            product['stock_quantity'] = gmail_count['count'] if gmail_count else 0
    
    # Áp dụng bộ lọc bổ sung
    if products_list:
        filtered_products = []
        for product in products_list:
            # Kiểm tra tình trạng kho hàng
            if in_stock and int(product.get('stock', 0)) <= 0:
                continue
                
            # Kiểm tra có đang giảm giá không
            if has_discount and not product.get('discount_price'):
                continue
                
            # Kiểm tra có phải sản phẩm nổi bật không
            if featured and not product.get('featured'):
                continue
                
            # Kiểm tra có đánh giá cao không (trên 4 sao)
            if high_rated and float(product.get('rating', 0)) < 4:
                continue
                
            filtered_products.append(product)
        products_list = filtered_products
        
        # Sắp xếp sản phẩm theo lựa chọn
        # Chuẩn hóa sort_option để hỗ trợ cả dấu gạch ngang và gạch dưới
        if sort_option in ['price-low', 'price_low']:
            # Sắp xếp theo giá tăng dần
            products_list = sorted(products_list, key=lambda p: float(p.get('discount_price', 0) or p.get('price', 0)))
        elif sort_option in ['price-high', 'price_high']:
            # Sắp xếp theo giá giảm dần
            products_list = sorted(products_list, key=lambda p: float(p.get('discount_price', 0) or p.get('price', 0)), reverse=True)
        elif sort_option in ['popular', 'rating']:
            # Sắp xếp theo đánh giá cao nhất
            products_list = sorted(products_list, key=lambda p: float(p.get('rating', 0)), reverse=True)
    
    return render_template('pages/products.html', 
                          products=products_list, 
                          categories=categories,
                          current_category=category_id,
                          search_query=search_query,
                          title=title,
                          sort_option=sort_option,
                          in_stock=in_stock,
                          has_discount=has_discount,
                          featured=featured,
                          high_rated=high_rated)

# Product detail
@app.route('/products/<int:product_id>')
def product_detail(product_id):
    product = Product.get_by_id(product_id)
    
    if not product:
        abort(404)
    
    # Get comments for product
    comments = Comment.get_for_product(product_id)
    
    # Get related products
    related_products = Product.get_all(category_id=product['category_id'], limit=4)
    
    # Initialize comment form
    comment_form = CommentForm()
    
    # Get user balance
    user_balance = 0
    if is_logged_in():
        user_id = session['user_id']
        user_balance = float(Wallet.get_balance(user_id))
    
    # Lấy giá sản phẩm (dùng giá khuyến mãi nếu có)
    if product.get('discount_price'):
        price = float(product['discount_price'])
    else:
        price = float(product['price']) if product.get('price') else 0
    
    # Tính số tiền thiếu
    amount_needed = max(0, price - user_balance)
    
    # Nếu là sản phẩm Gmail, lấy số lượng Gmail chưa bán
    if 'Gmail' in product['name']:
        gmail_count = find_record_by_sql(
            "SELECT COUNT(*) as count FROM gmail_accounts WHERE is_sold = FALSE AND product_id = %s",
            [product_id],
            fetchone=True
        )
        product['stock_quantity'] = gmail_count['count'] if gmail_count else 0
        print(f"DEBUG: Số lượng Gmail chưa bán cho sản phẩm {product_id}: {product['stock_quantity']}")
    
    return render_template('pages/product_detail.html', 
                          product=product, 
                          comments=comments,
                          related_products=related_products,
                          form=comment_form,
                          user_balance=user_balance,
                          price=price,
                          amount_needed=amount_needed)

# Add comment
@app.route('/products/<int:product_id>/comment', methods=['POST'])
@login_required
def add_comment(product_id):
    form = CommentForm()
    
    if form.validate_on_submit():
        user_id = session['user_id']
        comment_text = form.comment.data
        rating = int(form.rating.data)
        
        result = Comment.create(user_id, product_id, comment_text, rating)
        
        if result and result.get('last_insert_id'):
            flash('Nhận xét được thêm thành công', 'success')
        else:
            flash('Không thể thêm bình luận', 'danger')
    
    return redirect(url_for('product_detail', product_id=product_id))

# Xác nhận mua hàng (Chuyển sang AJAX)
@app.route('/confirm-purchase/<int:product_id>', methods=['GET', 'POST'])
@login_required
def confirm_purchase(product_id):
    """Xác nhận mua hàng"""
    # Import tại điểm sử dụng để tránh xung đột
    from decimal import Decimal
    
    user_id = session['user_id']
    user = User.get_by_id(user_id)
    product = Product.get_by_id(product_id)
    
    if not product:
        flash('Sản phẩm không tồn tại', 'danger')
        return redirect(url_for('products'))
    
    # Lấy số lượng từ form hoặc mặc định là 1 cho phương thức GET
    if request.method == 'POST':
        quantity = int(request.form.get('quantity', 1))
    else:
        quantity = 1
    
    # Kiểm tra số lượng hợp lệ
    if quantity <= 0:
        flash('Số lượng không hợp lệ', 'danger')
        return redirect(url_for('product_detail', product_id=product_id))
    
    if quantity > product['stock_quantity']:
        flash('Số lượng vượt quá hàng tồn kho', 'danger')
        return redirect(url_for('product_detail', product_id=product_id))
    
    # Tính tổng tiền
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
                          discount=0)

# Xử lý mua hàng
@app.route('/process_purchase', methods=['POST'])
@login_required
def process_purchase():
    try:
        user_id = session.get('user_id')
        data = request.get_json()  # Lấy dữ liệu từ JSON request
        
        # Kiểm tra dữ liệu bắt buộc
        required_fields = ['product_id', 'quantity', 'voucher_code']
        for field in required_fields:
            if field not in data:
                return jsonify({'success': False, 'message': f'Thiếu thông tin {field}'})
        
        product_id = data.get('product_id')
        quantity = int(data.get('quantity', 1))
        voucher_code = data.get('voucher_code')
        
        # print("DEBUG: Bắt đầu xử lý đơn hàng")
        # print(f"DEBUG: User ID: {user_id}")
        # print(f"DEBUG: Product ID: {product_id}")
        # print(f"DEBUG: Request data: {data}")
        
        if not product_id:
            return jsonify({'success': False, 'message': 'Thiếu thông tin sản phẩm'})
            
        # Lấy thông tin sản phẩm
        product = Product.get_by_id(product_id)
        if not product:
            return jsonify({'success': False, 'message': 'Sản phẩm không tồn tại'})
            
        # print(f"DEBUG: Product price: {product['price']}")
        # print(f"DEBUG: Product discount price: {product.get('discount_price')}")
        # print(f"DEBUG: Quantity: {quantity}")
        # print(f"DEBUG: Voucher code: {voucher_code}")
        
        # Tính giá đơn vị (ưu tiên giá khuyến mãi nếu có)
        unit_price = product.get('discount_price') or product['price']
        # print(f"DEBUG: Unit price: {unit_price}")
        
        # Tính tổng tiền trước khi áp dụng voucher
        total_amount = unit_price * quantity
        # print(f"DEBUG: Total amount before discount: {total_amount}")
        
        # Kiểm tra và áp dụng voucher nếu có
        discount_amount = 0
        if voucher_code:
            voucher = find_record_by_sql(
                "SELECT * FROM voucher WHERE voucher_code = %s",
                [voucher_code],
                fetchone=True
            )
            if voucher:
                current_date = datetime.now().date()
                if current_date >= voucher['valid_from'] and current_date <= voucher['valid_until']:
                    discount_amount = voucher['discount_value']
                    total_amount = max(0, total_amount - discount_amount)
                    print(f"DEBUG: Applied voucher discount: {discount_amount}")
                    print(f"DEBUG: New total amount: {total_amount}")
        
        # Kiểm tra số dư ví
        user = User.get_by_id(user_id)
        wallet_balance = user['wallet_balance']
        print(f"DEBUG: Wallet balance: {wallet_balance}")
        print(f"DEBUG: Total amount to pay: {total_amount}")
        
        if wallet_balance < total_amount:
            return jsonify({
                'success': False,
                'message': 'Số dư ví không đủ để thanh toán'
            })
        
        # Tạo mã tham chiếu
        reference_code = generate_reference_code()
        print(f"DEBUG: Reference code: {reference_code}")
        
        # Tạo đơn hàng
        print(f"DEBUG: Đang tạo đơn hàng với tổng tiền: {total_amount}")
        order_result = Order.create(
            user_id=user_id,
            total_amount=total_amount,
            shipping_address="Digital Delivery",
            payment_method="wallet",
            reference_code=reference_code,
            voucher_code=voucher_code,
            discount_amount=discount_amount
        )
        print(f"DEBUG: Kết quả tạo đơn hàng: {order_result}")
        
        if not order_result:
            # Hoàn tiền nếu tạo đơn hàng thất bại
            Wallet.update_balance(user_id, wallet_balance)
            return jsonify({
                'success': False,
                'message': 'Có lỗi xảy ra khi tạo đơn hàng'
            })
        
        order_id = order_result['last_insert_id']
        print(f"DEBUG: Đã tạo đơn hàng với ID = {order_id}")
        
        # Thêm sản phẩm vào đơn hàng
        Order.add_item(order_id, product_id, quantity, unit_price)
        
        # Xử lý Gmail nếu là sản phẩm Gmail
        if 'Gmail' in product['name']:
            # Debug: In ra số lượng Gmail hiện tại
            gmail_count = find_record_by_sql(
                "SELECT COUNT(*) as count FROM gmail_accounts WHERE is_sold = FALSE",
                fetchone=True
            )
            print(f"DEBUG: Số lượng Gmail chưa bán hiện tại: {gmail_count['count']}")
            
            # Lấy Gmail từ cơ sở dữ liệu và đánh dấu đã bán
            gmail_result = find_record_by_sql(
                "SELECT * FROM gmail_accounts WHERE is_sold = FALSE LIMIT %s",
                [quantity],
                fetchone=False
            )
            
            print(f"DEBUG: Số lượng Gmail tìm thấy: {len(gmail_result) if gmail_result else 0}")
            
            if gmail_result and len(gmail_result) >= quantity:
                for i in range(quantity):
                    gmail_account = gmail_result[i]
                    # Cập nhật trạng thái Gmail
                    update_result = update_record(
                        'gmail_accounts',
                        {'is_sold': True, 'order_id': order_id},
                        {'id': gmail_account['id']}
                    )
                    print(f"DEBUG: Cập nhật Gmail {gmail_account['id']}: {update_result}")
            else:
                # Nếu không đủ Gmail, hoàn tiền và hủy đơn hàng
                Wallet.update_balance(user_id, wallet_balance)
                delete_record('orders', {'id': order_id})
                return jsonify({
                    'success': False,
                    'message': 'Không đủ tài khoản Gmail trong kho'
                })
            
            # Debug: In ra số lượng Gmail sau khi cập nhật
            gmail_count_after = find_record_by_sql(
                "SELECT COUNT(*) as count FROM gmail_accounts WHERE is_sold = FALSE",
                fetchone=True
            )
            print(f"DEBUG: Số lượng Gmail chưa bán sau khi cập nhật: {gmail_count_after['count']}")
        else:
            # Cập nhật số lượng tồn kho cho sản phẩm thông thường
            Product.update_stock(product_id, -quantity)
        
        # Ghi log giao dịch và cập nhật số dư ví
        print(f"DEBUG - Trước khi cập nhật ví:")
        print(f"DEBUG - User ID: {user_id}")
        print(f"DEBUG - Số dư hiện tại: {wallet_balance}")
        print(f"DEBUG - Số tiền cần trừ: {total_amount}")
        
        # Cập nhật số dư ví
        new_balance = Decimal(str(wallet_balance)) - Decimal(str(total_amount))
        print(f"DEBUG - Số dư mới (đã tính): {new_balance}")
        
        # Cập nhật vào database
        update_result = Wallet.update_balance(user_id, new_balance)
        print(f"DEBUG - Kết quả cập nhật ví: {update_result}")
        
        # Kiểm tra lại số dư sau khi cập nhật
        current_balance = Wallet.get_balance(user_id)
        print(f"DEBUG - Số dư sau khi cập nhật (từ DB): {current_balance}")
        
        # Ghi log giao dịch
        transaction_result = Wallet.add_transaction(
            user_id=user_id,
            amount=total_amount,
            transaction_type='debit',
            description=f'Mua sản phẩm {product["name"]} - Mã đơn hàng: {reference_code}'
        )
        print(f"DEBUG - Kết quả ghi log giao dịch: {transaction_result}")
        
        # Lấy số dư mới sau khi thanh toán
        new_balance = Wallet.get_balance(user_id)
        print(f"DEBUG - Số dư cuối cùng: {new_balance}")
        
        try:
            print("DEBUG: Bắt đầu tạo thông báo...")
            # Tạo thông báo cho người dùng
            notification_data = {
                'user_id': user_id,
                'title': 'Mua hàng thành công',
                'message': f'Tài khoản của bạn đã bị trừ {total_amount:,.2f} VND. Số dư mới: {new_balance:,.2f} VND',
                'type': 'success',
                'is_read': False,
                'created_at': datetime.now()
            }
            print(f"DEBUG: Dữ liệu thông báo đã tạo: {notification_data}")
            
            # Thực hiện insert và lưu kết quả
            insert_result = insert_record('notifications', notification_data)
            print(f"DEBUG: Kết quả insert thông báo: {insert_result}")
            
            if insert_result and insert_result.get('last_insert_id'):
                print(f"DEBUG: Thông báo đã được tạo thành công với ID: {insert_result['last_insert_id']}")
            else:
                print("DEBUG: Không thể tạo thông báo - insert_result trả về None hoặc không có last_insert_id")
                
        except Exception as e:
            print(f"DEBUG ERROR: Lỗi khi tạo thông báo: {str(e)}")
            import traceback
            print(f"DEBUG ERROR Details: {traceback.format_exc()}")
        
        return jsonify({
            'success': True,
            'message': 'Đặt hàng thành công',
            'order_id': order_id,
            'reference_code': reference_code,
            'total_amount': total_amount,
            'discount_amount': discount_amount,
            'new_wallet_balance': float(new_balance)
        })
        
    except Exception as e:
        print(f"ERROR: {str(e)}")
        return jsonify({
            'success': False,
            'message': 'Có lỗi xảy ra, vui lòng thử lại'
        })

# Tải về Gmail
@app.route('/download_gmail_accounts/<int:order_id>')
@login_required
def download_gmail_accounts(order_id):
    # Kiểm tra đơn hàng có thuộc về user không
    user_id = session['user_id']
    order = find_record('orders', {'id': order_id, 'user_id': user_id}, fetchone=True)
    
    if not order:
        return jsonify({'error': 'Order not found'}), 404

    # Tạo nội dung file với định dạng mới
    content = f"ORDER: {order['reference_code']}|{order['created_at'].strftime('%d/%m/%Y %H:%M:%S')}\n"
    # Lấy danh sách Gmail từ đơn hàng
    gmail_accounts = find_record('gmail_accounts', {'order_id': order_id})
    for account in gmail_accounts:
        content += f"{account['email']}|{account['password']}\n"

    # Tạo response với file text
    response = make_response(content)
    response.headers['Content-Type'] = 'text/plain'
    response.headers['Content-Disposition'] = f'attachment; filename=MMOSHOP_{order["reference_code"]}.txt'
    
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
            flash('Lựa chọn ngân hàng không hợp lệ', 'danger')
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
                flash('Mã quà tặng đã được đổi thành công! 100.000 VND đã được thêm vào ví của bạn.', 'success')
            else:
                flash('Đổi mã quà tặng thất bại', 'danger')
        else:
            flash('Mã quà tặng không hợp lệ', 'danger')
    
    return redirect(url_for('topup'))

# Simulate topup completion (this would normally be done by a background process)
@app.route('/complete-topup', methods=['POST'])
@login_required
def complete_topup():
    ref_code = session.get('topup_ref')
    amount = session.get('topup_amount')
    
    if not ref_code or not amount:
        flash('Nạp tiền không hợp lệ', 'danger')
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
        
        # Tạo thông báo cho người dùng
        notification_data = {
            'user_id': user_id,
            'title': 'Nạp tiền thành công',
            'message': f'Tài khoản của bạn đã được cộng {amount:,.1f} VND. Số dư mới: {new_balance:,.2f} VND',
            'type': 'success',
            'is_read': False,
            'created_at': datetime.now()
        }
        insert_record('notifications', notification_data)
        print(f"DEBUG: Đã thêm thông báo: {notification_data}")
        
        flash(f'Nạp tiền thành công! {amount} VND đã được thêm vào ví của bạn.', 'success')
        return redirect(url_for('transactions'))
    else:
        flash('Nạp tiền thất bại', 'danger')
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
    
    # Nếu không có đơn hàng, khởi tạo danh sách trống
    if orders_list is None:
        orders_list = []
    
    # Get items for each order
    for order in orders_list:
        # Sử dụng dict đặc biệt để xử lý items
        items = Order.get_order_items(order['id'])
        if items is None:
            items = []
        order['item_list'] = items  # Đổi tên từ 'items' thành 'item_list' để tránh va chạm với phương thức mặc định
        
        # Lấy danh sách Gmail accounts cho đơn hàng
        gmail_accounts = find_record('gmail_accounts', {'order_id': order['id']})
        if gmail_accounts is None:
            gmail_accounts = []
        order['gmail_accounts'] = gmail_accounts
        
        print(f"DEBUG: Order {order['id']} has {len(gmail_accounts)} Gmail accounts")
    
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
    
# API endpoints
@app.route('/api/order/<int:order_id>')
@login_required
def get_order_api(order_id):
    # Kiểm tra đơn hàng có thuộc về user không
    user_id = session['user_id']
    order = find_record('orders', {'id': order_id, 'user_id': user_id}, fetchone=True)
    
    if not order:
        return jsonify({'error': 'Đơn hàng không tồn tại hoặc bạn không có quyền truy cập'}), 404
    
    # Lấy thông tin đơn hàng
    order_items = Order.get_order_items(order_id)
    
    # Lấy thông tin sản phẩm cho từng item
    products = []
    if order_items:
        for item in order_items:
            product = Product.get_by_id(item['product_id'])
            if product:
                products.append({
                    'name': product['name'],
                    'image_url': product['image_url'],
                    'price': str(item['price']),
                    'quantity': item['quantity']
                })
    
    # Lấy danh sách Gmail accounts nếu có
    gmail_accounts = find_record('gmail_accounts', {'order_id': order_id})
    gmail_list = []
    if gmail_accounts:
        for account in gmail_accounts:
            gmail_list.append({
                'email': account['email'],
                'password': account['password']
            })
    
    # Chuẩn bị dữ liệu phản hồi
    response_data = {
        'id': order['id'],
        'reference_code': order['reference_code'],
        'order_date': order['created_at'].strftime('%d/%m/%Y %H:%M:%S'),
        'total_amount': str(order['total_amount']),
        'status': order['status'],
        'items': products,
        'product_name': products[0]['name'] if products else '',
        'quantity': sum(item['quantity'] for item in products) if products else 0,
        'gmail_accounts': gmail_list  # Thêm danh sách Gmail accounts vào response
    }
    
    return jsonify(response_data)

@app.route('/validate_voucher', methods=['POST'])
@login_required
def validate_voucher():
    if not session.get('logged_in'):
        return jsonify({'success': False, 'message': 'Vui lòng đăng nhập để sử dụng mã giảm giá'})
    
    data = request.get_json()
    voucher_code = data.get('voucher_code')
    product_id = data.get('product_id')  # Thêm product_id vào request
    
    if not voucher_code:
        return jsonify({'success': False, 'message': 'Vui lòng nhập mã giảm giá'})
    
    if not product_id:
        return jsonify({'success': False, 'message': 'Thiếu thông tin sản phẩm'})
    
    # Debug: In ra mã giảm giá đang kiểm tra
    print(f"Debug: Checking voucher code: {voucher_code}")
    print(f"Debug: Product ID: {product_id}")
    
    # Query the database for the voucher using raw SQL
    voucher = find_record_by_sql(
        "SELECT * FROM voucher WHERE voucher_code = %s",
        [voucher_code],
        fetchone=True
    )
    
    if not voucher:
        return jsonify({'success': False, 'message': 'Mã giảm giá không hợp lệ'})
    
    # Check voucher validity dates
    current_date = datetime.now().date()
    start_date = voucher.get('valid_from')
    end_date = voucher.get('valid_until')
    
    if start_date and current_date < start_date:
        return jsonify({'success': False, 'message': 'Mã giảm giá chưa có hiệu lực'})
    
    if end_date and current_date > end_date:
        return jsonify({'success': False, 'message': 'Mã giảm giá đã hết hạn'})
    
    # Lấy thông tin sản phẩm để tính toán giá
    product = Product.get_by_id(product_id)
    if not product:
        return jsonify({'success': False, 'message': 'Sản phẩm không tồn tại'})
    
    # Tính giá đơn vị (ưu tiên giá khuyến mãi nếu có)
    unit_price = product.get('discount_price') or product['price']
    discount_amount = voucher['discount_value']
    total_amount = max(0, unit_price - discount_amount)
    
    return jsonify({
        'success': True,
        'voucher': {
            'voucher_code': voucher['voucher_code'],
            'discount_value': float(voucher['discount_value']),  # Convert Decimal to float for JSON serialization
            'total_amount': float(total_amount)
        }
    })

@app.route('/subscribe_newsletter', methods=['POST'])
def subscribe_newsletter():
    email = request.form.get('email')
    if not email:
        flash('Vui lòng nhập email', 'error')
        return redirect(request.referrer or url_for('index'))
    
    try:
        # Check if email already exists
        cursor = mysql.connection.cursor()
        cursor.execute("SELECT id FROM newsletter_subscribers WHERE email = %s", (email,))
        if cursor.fetchone():
            flash('Email đã được đăng ký trước đó', 'info')
            return redirect(request.referrer or url_for('index'))
        
        # Add new subscriber
        cursor.execute(
            "INSERT INTO newsletter_subscribers (email, created_at) VALUES (%s, NOW())",
            (email,)
        )
        mysql.connection.commit()
        flash('Đăng ký nhận tin thành công!', 'success')
    except Exception as e:
        mysql.connection.rollback()
        flash('Có lỗi xảy ra, vui lòng thử lại sau', 'error')
    finally:
        cursor.close()
    
    return redirect(request.referrer or url_for('index'))
