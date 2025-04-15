import os
import psycopg2
from psycopg2 import Error
from psycopg2.extras import RealDictCursor
import logging
from dotenv import load_dotenv
load_dotenv()


# Configure logging
logging.basicConfig(level=logging.DEBUG)
logger = logging.getLogger(__name__)

# Database configuration - using Replit's PostgreSQL environment variables
DB_CONFIG = {
    'host': os.environ.get('PGHOST'),
    'user': os.environ.get('PGUSER'),
    'password': os.environ.get('PGPASSWORD'),
    'dbname': os.environ.get('PGDATABASE'),
    'port': os.environ.get('PGPORT')
}

# Session configuration
SECRET_KEY = os.environ.get('SESSION_SECRET', 'your_secret_key')

def get_db_connection():
    """Create and return a database connection"""
    try:
        connection = psycopg2.connect(**DB_CONFIG)
        return connection
    except Error as e:
        logger.error(f"Error connecting to PostgreSQL: {e}")
        return None

def execute_query(query, params=None, fetch=True, fetchone=False):
    """Execute SQL query and return results if needed"""
    connection = get_db_connection()
    result = None
    cursor = None
    
    if connection is None:
        return None
    
    try:
        cursor = connection.cursor(cursor_factory=RealDictCursor)
        cursor.execute(query, params or ())
        
        if fetchone:
            result = cursor.fetchone()
        elif fetch:
            result = cursor.fetchall()
        else:
            # Commit sau mỗi lần thực thi không yêu cầu kết quả trả về
            connection.commit()
            result = {'affected_rows': cursor.rowcount}
        
        # Luôn commit sau khi thực thi thành công để đảm bảo dữ liệu được lưu
        connection.commit()
    
    except Error as e:
        logger.error(f"Error executing query: {e}")
        if connection:
            connection.rollback()
    finally:
        if cursor:
            cursor.close()
        if connection and not connection.closed:
            connection.close()
    
    return result

def insert_record(table, data):
    """Insert a record into a table"""
    fields = ', '.join(data.keys())
    placeholders = ', '.join(['%s'] * len(data))
    query = f"INSERT INTO {table} ({fields}) VALUES ({placeholders}) RETURNING id"
    
    result = execute_query(query, list(data.values()), fetchone=True)
    if result:
        return {'affected_rows': 1, 'last_insert_id': result['id']}
    return None

def update_record(table, data, condition):
    """Update a record in a table"""
    # Tối ưu tốc độ: Tránh thực hiện RETURNING khi không cần thiết
    # Thông thường khi cập nhật hồ sơ hệ thống không thực sự cần dữ liệu trả về
    if 'profile_image' in data:
        # Đối với cập nhật profile, thực hiện truy vấn tối ưu
        set_clause = ', '.join([f"{field} = %s" for field in data.keys()])
        where_clause = ' AND '.join([f"{field} = %s" for field in condition.keys()])
        query = f"UPDATE {table} SET {set_clause} WHERE {where_clause}"
        
        params = list(data.values()) + list(condition.values())
        result = execute_query(query, params, fetch=False)
        if result and result.get('affected_rows', 0) > 0:
            # Vẫn trả về kết quả có định dạng tương tự để tương thích với code hiện tại
            return {'affected_rows': result.get('affected_rows', 0)}
        return {'affected_rows': 0}
    else:
        # Với các truy vấn khác, giữ nguyên logic cũ để đảm bảo tính nhất quán
        set_clause = ', '.join([f"{field} = %s" for field in data.keys()])
        where_clause = ' AND '.join([f"{field} = %s" for field in condition.keys()])
        query = f"UPDATE {table} SET {set_clause} WHERE {where_clause} RETURNING *"
        
        params = list(data.values()) + list(condition.values())
        result = execute_query(query, params, fetchone=True)
        if result:
            return {'affected_rows': 1, 'updated_data': result}
        return {'affected_rows': 0}

def delete_record(table, condition):
    """Delete a record from a table"""
    where_clause = ' AND '.join([f"{field} = %s" for field in condition.keys()])
    query = f"DELETE FROM {table} WHERE {where_clause}"
    
    return execute_query(query, list(condition.values()), fetch=False)

def find_record(table, condition=None, select="*", order_by=None, limit=None, fetchone=False):
    """Find records in a table"""
    query = f"SELECT {select} FROM {table}"
    params = []
    
    if condition:
        where_clause = ' AND '.join([f"{field} = %s" for field in condition.keys()])
        query += f" WHERE {where_clause}"
        params = list(condition.values())
    
    if order_by:
        query += f" ORDER BY {order_by}"
    
    if limit:
        query += f" LIMIT {limit}"
    
    return execute_query(query, params, fetchone=fetchone)

def find_record_by_sql(sql, params=None, fetchone=False):
    """Execute a custom SQL query"""
    return execute_query(sql, params, fetchone=fetchone)
