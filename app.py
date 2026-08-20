import io
import base64
import sqlite3
from datetime import datetime, timedelta
from flask import Flask, render_template, request, redirect, url_for, flash, send_file, session
from flask_login import LoginManager, UserMixin, login_user, login_required, logout_user, current_user
from werkzeug.security import generate_password_hash, check_password_hash
import qrcode
import pandas as pd

app = Flask(__name__)
app.secret_key = 'super-secret-key-it-asset'

# Konfigurasi Keamanan Sesi (Auto Timeout 15 Menit Tidak Ada Aktivitas)
app.config['PERMANENT_SESSION_LIFETIME'] = timedelta(minutes=15)

@app.before_request
def make_session_permanent():
    session.permanent = True
    session.modified = True

# Setup Flask-Login
login_manager = LoginManager()
login_manager.init_app(app)
login_manager.login_view = 'login'

class User(UserMixin):
    def __init__(self, id, username, password):
        self.id = id
        self.username = username
        self.password = password

def get_db_connection():
    conn = sqlite3.connect('database.db')
    conn.row_factory = sqlite3.Row
    return conn

@login_manager.user_loader
def load_user(user_id):
    conn = get_db_connection()
    user_data = conn.execute('SELECT * FROM users WHERE id = ?', (user_id,)).fetchone()
    conn.close()
    if user_data:
        return User(user_data['id'], user_data['username'], user_data['password'])
    return None

# ==========================================
# FUNGSI GENERATE NIP OTOMATIS (9 DIGIT)
# ==========================================
def generate_nip_auto(birth_date_str):
    """
    Input birth_date_str format 'YYYY-MM-DD' (contoh: '1999-08-05')
    Format Output: '00' + '99' + '08' + '001' = '009908001' (Total 9 Digit)
    """
    birth_dt = datetime.strptime(birth_date_str, '%Y-%m-%d')
    year_short = birth_dt.strftime('%y')   # 2 digit tahun -> '99'
    month_str = birth_dt.strftime('%m')    # 2 digit bulan -> '08'
    
    # Prefix awal: '00' + '99' + '08' = '009908'
    prefix = f"00{year_short}{month_str}"
    
    conn = get_db_connection()
    # Hitung data karyawan di DB yang punya prefix tahun & bulan sama pada emp_code
    count_row = conn.execute(
        'SELECT COUNT(*) as count FROM employees WHERE emp_code LIKE ?', 
        (f"{prefix}%",)
    ).fetchone()
    conn.close()
    
    count = count_row['count'] if count_row else 0
    
    # Nomor urut 3 digit: 001, 002, ..., 100
    sequence = str(count + 1).zfill(3)
    
    return f"{prefix}{sequence}"

def init_db():
    conn = get_db_connection()
    conn.execute('''
        CREATE TABLE IF NOT EXISTS users (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            username TEXT UNIQUE NOT NULL,
            password TEXT NOT NULL
        )
    ''')
    conn.execute('''
        CREATE TABLE IF NOT EXISTS assets (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            asset_tag TEXT UNIQUE NOT NULL,
            name TEXT NOT NULL,
            category TEXT NOT NULL,
            serial_number TEXT,
            status TEXT NOT NULL DEFAULT 'Available',
            purchase_date DATE,
            po_number TEXT,
            warranty_expiry DATE,
            processor TEXT,
            ram TEXT,
            storage TEXT,
            os TEXT,
            office TEXT,
            current_user_id INTEGER,
            notes TEXT,
            FOREIGN KEY (current_user_id) REFERENCES employees (id)
        )
    ''')
    conn.execute('''
        CREATE TABLE IF NOT EXISTS employees (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            emp_code TEXT UNIQUE NOT NULL,
            full_name TEXT NOT NULL,
            department TEXT NOT NULL,
            email TEXT,
            birth_date DATE
        )
    ''')
    
    # Auto-migration: Tambah kolom birth_date jika belum ada di tabel employees
    try:
        conn.execute('ALTER TABLE employees ADD COLUMN birth_date DATE')
    except sqlite3.OperationalError:
        pass  # Kolom sudah ada

    conn.execute('''
        CREATE TABLE IF NOT EXISTS asset_logs (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            asset_id INTEGER NOT NULL,
            employee_id INTEGER,
            action TEXT NOT NULL,
            action_date DATETIME DEFAULT CURRENT_TIMESTAMP,
            notes TEXT,
            FOREIGN KEY (asset_id) REFERENCES assets (id),
            FOREIGN KEY (employee_id) REFERENCES employees (id)
        )
    ''')
    
    # Akun default: admin / admin123
    admin_exist = conn.execute('SELECT * FROM users WHERE username = ?', ('admin',)).fetchone()
    if not admin_exist:
        hashed_password = generate_password_hash('admin123')
        conn.execute('INSERT INTO users (username, password) VALUES (?, ?)', ('admin', hashed_password))
    
    conn.commit()
    conn.close()

# ---------------- ROUTE AUTENTIKASI ----------------

@app.route('/login', methods=['GET', 'POST'])
def login():
    if current_user.is_authenticated:
        return redirect(url_for('index'))
        
    if request.method == 'POST':
        username = request.form['username']
        password = request.form['password']

        conn = get_db_connection()
        user_data = conn.execute('SELECT * FROM users WHERE username = ?', (username,)).fetchone()
        conn.close()

        if user_data and check_password_hash(user_data['password'], password):
            user = User(user_data['id'], user_data['username'], user_data['password'])
            login_user(user)
            return redirect(url_for('index'))
        else:
            flash('Username atau Password salah!')

    return render_template('login.html')

@app.route('/logout')
@login_required
def logout():
    session.clear()
    logout_user()
    return redirect(url_for('login'))

# ---------------- ROUTE UTAMA & ASET ----------------

@app.route('/')
@login_required
def index():
    selected_status = request.args.get('status')
    conn = get_db_connection()
    query_all = '''
        SELECT a.*, e.full_name as user_name 
        FROM assets a 
        LEFT JOIN employees e ON a.current_user_id = e.id
    '''
    all_assets = conn.execute(query_all).fetchall()
    
    total = len(all_assets)
    in_use = len([a for a in all_assets if a['status'] == 'In Use'])
    available = len([a for a in all_assets if a['status'] == 'Available'])
    repair = len([a for a in all_assets if a['status'] == 'Repair'])
    
    category_counts = {}
    for asset in all_assets:
        cat = asset['category'] or 'Lainnya'
        category_counts[cat] = category_counts.get(cat, 0) + 1

    if selected_status:
        query_filter = query_all + ' WHERE a.status = ?'
        assets = conn.execute(query_filter, (selected_status,)).fetchall()
    else:
        assets = all_assets
        
    conn.close()
    return render_template('index.html', assets=assets, total=total, 
                           in_use=in_use, available=available, repair=repair,
                           category_counts=category_counts,
                           selected_status=selected_status)

@app.route('/add', methods=['GET', 'POST'])
@login_required
def add_asset():
    conn = get_db_connection()
    if request.method == 'POST':
        asset_tag = request.form['asset_tag']
        name = request.form['name']
        category = request.form['category']
        serial_number = request.form['serial_number']
        status = request.form['status']
        purchase_date = request.form.get('purchase_date')
        po_number = request.form.get('po_number')
        warranty_expiry = request.form.get('warranty_expiry')
        processor = request.form.get('processor', '-')
        ram = request.form.get('ram', '-')
        storage = request.form.get('storage', '-')
        os = request.form.get('os', '-')
        office = request.form.get('office', '-')
        user_id = request.form.get('user_id') or None
        notes = request.form['notes']

        cursor = conn.cursor()
        cursor.execute('''
            INSERT INTO assets (
                asset_tag, name, category, serial_number, status, 
                purchase_date, po_number, warranty_expiry, processor, ram, storage, os, office, 
                current_user_id, notes
            )
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
        ''', (asset_tag, name, category, serial_number, status, 
              purchase_date, po_number, warranty_expiry, processor, ram, storage, os, office, 
              user_id, notes))
        
        new_asset_id = cursor.lastrowid
        conn.execute('''
            INSERT INTO asset_logs (asset_id, employee_id, action, notes)
            VALUES (?, ?, ?, ?)
        ''', (new_asset_id, user_id, 'Registered', 'Aset baru didaftarkan ke sistem'))
        
        conn.commit()
        conn.close()
        return redirect(url_for('index'))

    employees = conn.execute('SELECT * FROM employees').fetchall()
    conn.close()
    return render_template('add_asset.html', employees=employees)

@app.route('/add-batch', methods=['GET', 'POST'])
@login_required
def add_batch():
    if request.method == 'POST':
        prefix = request.form['prefix'].strip().upper()
        start_number = int(request.form['start_number'])
        quantity = int(request.form['quantity'])
        
        name = request.form['name']
        category = request.form['category']
        purchase_date = request.form.get('purchase_date')
        po_number = request.form.get('po_number')
        warranty_expiry = request.form.get('warranty_expiry')
        processor = request.form.get('processor', '-')
        ram = request.form.get('ram', '-')
        storage = request.form.get('storage', '-')
        notes = request.form.get('notes', '')

        conn = get_db_connection()
        cursor = conn.cursor()

        for i in range(quantity):
            current_num = start_number + i
            asset_tag = f"{prefix}-{current_num:03d}"
            
            cursor.execute('''
                INSERT INTO assets (
                    asset_tag, name, category, serial_number, status, 
                    purchase_date, po_number, warranty_expiry, processor, ram, storage, os, office, 
                    current_user_id, notes
                )
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            ''', (asset_tag, name, category, '', 'Available', 
                  purchase_date, po_number, warranty_expiry, processor, ram, storage, '-', '-', 
                  None, notes))
            
            new_asset_id = cursor.lastrowid
            
            conn.execute('''
                INSERT INTO asset_logs (asset_id, employee_id, action, notes)
                VALUES (?, ?, ?, ?)
            ''', (new_asset_id, None, 'Registered (Batch)', f'Pengadaan batch PO: {po_number}'))

        conn.commit()
        conn.close()
        return redirect(url_for('index'))

    return render_template('add_batch.html')

@app.route('/edit/<int:id>', methods=['GET', 'POST'])
@login_required
def edit_asset(id):
    conn = get_db_connection()
    asset = conn.execute('SELECT * FROM assets WHERE id = ?', (id,)).fetchone()
    
    if not asset:
        conn.close()
        return "Aset tidak ditemukan", 404

    if request.method == 'POST':
        asset_tag = request.form['asset_tag']
        name = request.form['name']
        category = request.form['category']
        serial_number = request.form['serial_number']
        status = request.form['status']
        purchase_date = request.form.get('purchase_date')
        po_number = request.form.get('po_number')
        warranty_expiry = request.form.get('warranty_expiry')
        processor = request.form.get('processor', '-')
        ram = request.form.get('ram', '-')
        storage = request.form.get('storage', '-')
        os = request.form.get('os', '-')
        office = request.form.get('office', '-')
        user_id = request.form.get('user_id') or None
        notes = request.form['notes']

        conn.execute('''
            UPDATE assets 
            SET asset_tag = ?, name = ?, category = ?, serial_number = ?, status = ?,
                purchase_date = ?, po_number = ?, warranty_expiry = ?, processor = ?, ram = ?, storage = ?, 
                os = ?, office = ?, current_user_id = ?, notes = ?
            WHERE id = ?
        ''', (asset_tag, name, category, serial_number, status, 
              purchase_date, po_number, warranty_expiry, processor, ram, storage, 
              os, office, user_id, notes, id))
        
        conn.execute('''
            INSERT INTO asset_logs (asset_id, employee_id, action, notes)
            VALUES (?, ?, ?, ?)
        ''', (id, user_id, 'Updated', 'Informasi/spesifikasi aset diperbarui'))

        conn.commit()
        conn.close()
        return redirect(url_for('index'))

    employees = conn.execute('SELECT * FROM employees').fetchall()
    conn.close()
    return render_template('edit_asset.html', asset=asset, employees=employees)

# ---------------- ROUTE KARYAWAN ----------------

@app.route('/employees', methods=['GET', 'POST'])
@login_required
def employees():
    conn = get_db_connection()
    if request.method == 'POST':
        full_name = request.form['full_name']
        department = request.form['department']
        email = request.form['email']
        birth_date = request.form['birth_date']  # Format: YYYY-MM-DD

        # Generate NIP otomatis 9 digit berdasarkan Tanggal Lahir
        auto_emp_code = generate_nip_auto(birth_date)

        conn.execute('''
            INSERT INTO employees (emp_code, full_name, department, email, birth_date)
            VALUES (?, ?, ?, ?, ?)
        ''', (auto_emp_code, full_name, department, email, birth_date))
        conn.commit()
        conn.close()
        return redirect(url_for('employees'))

    employees_list = conn.execute('SELECT * FROM employees').fetchall()
    conn.close()
    return render_template('employees.html', employees=employees_list)

@app.route('/logs')
@login_required
def logs():
    conn = get_db_connection()
    logs_data = conn.execute('''
        SELECT l.*, a.asset_tag, a.name as asset_name, e.full_name as emp_name
        FROM asset_logs l
        JOIN assets a ON l.asset_id = a.id
        LEFT JOIN employees e ON l.employee_id = e.id
        ORDER BY l.action_date DESC
    ''').fetchall()
    conn.close()
    return render_template('logs.html', logs=logs_data)

@app.route('/asset/<int:id>')
@login_required
def asset_detail(id):
    conn = get_db_connection()
    asset = conn.execute('''
        SELECT a.*, e.full_name as assigned_to 
        FROM assets a 
        LEFT JOIN employees e ON a.current_user_id = e.id 
        WHERE a.id = ?
    ''', (id,)).fetchone()
    conn.close()
    
    if not asset:
        return "Aset tidak ditemukan", 404

    qr_data = f"TAG: {asset['asset_tag']} | NAME: {asset['name']} | CPU: {asset['processor']} | RAM: {asset['ram']}"
    img = qrcode.make(qr_data)
    
    buf = io.BytesIO()
    img.save(buf, format='PNG')
    qr_code_base64 = base64.b64encode(buf.getvalue()).decode('utf-8')
    
    return render_template('asset_detail.html', asset=asset, qr_code=qr_code_base64)

@app.route('/export/excel')
@login_required
def export_excel():
    conn = get_db_connection()
    df = pd.read_sql_query('''
        SELECT a.asset_tag, a.name, a.category, a.serial_number, a.status, 
               a.purchase_date, a.po_number, a.warranty_expiry,
               a.processor, a.ram, a.storage, a.os, a.office,
               e.full_name as current_user, a.notes 
        FROM assets a 
        LEFT JOIN employees e ON a.current_user_id = e.id
    ''', conn)
    conn.close()

    output = io.BytesIO()
    with pd.ExcelWriter(output, engine='openpyxl') as writer:
        df.to_excel(writer, index=False, sheet_name='IT Assets')
    output.seek(0)

    return send_file(output, download_name='IT_Assets_Report.xlsx', as_attachment=True)

@app.route('/delete/<int:id>')
@login_required
def delete_asset(id):
    conn = get_db_connection()
    conn.execute('DELETE FROM asset_logs WHERE asset_id = ?', (id,))
    conn.execute('DELETE FROM assets WHERE id = ?', (id,))
    conn.commit()
    conn.close()
    return redirect(url_for('index'))

init_db()

if __name__ == '__main__':
    app.run(debug=True)