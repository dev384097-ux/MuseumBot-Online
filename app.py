from dotenv import load_dotenv
load_dotenv()

import os
import uuid
import random
from flask import Flask, request, jsonify, render_template, session, redirect, url_for, flash
from werkzeug.security import generate_password_hash, check_password_hash
from chatbot_engine import MuseumChatbot
from database import init_db, get_db_connection
from authlib.integrations.flask_client import OAuth
from flask_mail import Mail, Message

from werkzeug.middleware.proxy_fix import ProxyFix

app = Flask(__name__)
# Enable ProxyFix to handle HTTPS redirects correctly behind Render's proxy
app.wsgi_app = ProxyFix(app.wsgi_app, x_for=1, x_proto=1, x_host=1, x_prefix=1)
app.secret_key = os.getenv('SECRET_KEY')
if not app.secret_key:
    # Fallback only for development, otherwise will cause issues
    app.secret_key = 'development_only_key_please_set_in_env'

# OAuth Configuration
oauth = OAuth(app)
google = oauth.register(
    name='google',
    client_id=os.getenv('GOOGLE_CLIENT_ID'),
    client_secret=os.getenv('GOOGLE_CLIENT_SECRET'),
    server_metadata_url='https://accounts.google.com/.well-known/openid-configuration',
    client_kwargs={'scope': 'openid email profile'}
)

# Mail Configuration
app.config['MAIL_SERVER'] = 'smtp.gmail.com'
app.config['MAIL_PORT'] = 465
app.config['MAIL_USE_TLS'] = False
app.config['MAIL_USE_SSL'] = True
app.config['MAIL_USERNAME'] = os.getenv('MAIL_USERNAME')
app.config['MAIL_PASSWORD'] = os.getenv('MAIL_PASSWORD')
app.config['MAIL_DEFAULT_SENDER'] = os.getenv('MAIL_USERNAME')
app.config['MAIL_DEBUG'] = True

mail = Mail(app)

if not os.path.exists(os.path.join(os.path.dirname(__file__), 'data', 'museum.db')):
    with app.app_context():
        init_db()

chatbot = MuseumChatbot()

@app.route('/register', methods=['GET', 'POST'])
def register():
    if request.method == 'POST':
        username = request.form['username']
        password = request.form['password']
        
        conn = get_db_connection()
        user = conn.execute('SELECT * FROM users WHERE username = ?', (username,)).fetchone()
        
        if user:
            flash('Username already exists.')
            return redirect(url_for('register'))
            
        conn.execute('INSERT INTO users (username, email, password_hash, is_verified) VALUES (?, ?, ?, 1)',
                     (username, username, generate_password_hash(password)))
        conn.commit()
        conn.close()
        
        flash('Registration successful. Please log in.')
        return redirect(url_for('login'))
        
    return render_template('register.html')

@app.route('/login', methods=['GET', 'POST'])
def login():
    if request.method == 'POST':
        username = request.form['username']
        password = request.form['password']
        
        conn = get_db_connection()
        user = conn.execute('SELECT * FROM users WHERE username = ?', (username,)).fetchone()
        conn.close()
        
        if user and user['password_hash'] and check_password_hash(user['password_hash'], password):
            session['user_id'] = user['id']
            session['username'] = user['full_name'] or user['username']
            return redirect(url_for('home'))
            
        flash('Invalid username or password.')
        
    return render_template('login.html')

@app.route('/logout')
def logout():
    session.clear()
    return redirect(url_for('login'))

@app.route('/')
def home():
    is_logged_in = 'user_id' in session
    username = session.get('username', None)
    
    if 'session_id' not in session:
        session['session_id'] = str(uuid.uuid4())
    return render_template('index.html', logged_in=is_logged_in, username=username)

@app.route('/login/google')
def login_google():
    if not os.getenv('GOOGLE_CLIENT_ID') or "your" in os.getenv('GOOGLE_CLIENT_ID').lower():
        # Mock Google Login for development
        mock_user = {
            'email': 'visitor@example.com',
            'name': 'Heritage Visitor'
        }
        return google_mock_callback(mock_user)
        
    redirect_uri = url_for('google_callback', _external=True)
    return google.authorize_redirect(redirect_uri)

def google_mock_callback(user_info):
    email = user_info['email']
    name = user_info['name']
    
    # Generate OTP
    otp = str(random.randint(100000, 999999))
    
    conn = get_db_connection()
    user = conn.execute('SELECT * FROM users WHERE email = ?', (email,)).fetchone()
    
    if user:
        conn.execute('UPDATE users SET otp = ?, full_name = ? WHERE email = ?', (otp, name, email))
    else:
        conn.execute('INSERT INTO users (username, email, full_name, otp, is_verified) VALUES (?, ?, ?, ?, 0)',
                     (email, email, name, otp))
    
    conn.commit()
    conn.close()
    
    # Send OTP (Mock)
    if not os.getenv('MAIL_PASSWORD') or "your" in os.getenv('MAIL_PASSWORD').lower():
        print(f"MOCK EMAIL: To {email}, OTP is {otp}")
        session['mock_otp'] = otp # For easy testing
        flash(f"Check server console for OTP (Mock Mode).")
    else:
        try:
            msg = Message("Your MuseumBot Verification Code", recipients=[email])
            msg.body = f"Hello {name},\n\nYour OTP is: {otp}"
            mail.send(msg)
        except:
            flash("Email config failed. Check console for OTP.")
            session['mock_otp'] = otp
            
    session['temp_email'] = email
    return redirect(url_for('verify_otp'))

@app.route('/auth/callback')
def google_callback():
    token = google.authorize_access_token()
    user_info = token.get('userinfo')
    
    if not user_info:
        flash("Failed to retrieve user information from Google.")
        return redirect(url_for('login'))
        
    email = user_info['email']
    name = user_info.get('name', email.split('@')[0])
    
    # Generate OTP
    otp = str(random.randint(100000, 999999))
    
    conn = get_db_connection()
    user = conn.execute('SELECT * FROM users WHERE email = ?', (email,)).fetchone()
    
    if user:
        conn.execute('UPDATE users SET otp = ?, full_name = ? WHERE email = ?', (otp, name, email))
    else:
        conn.execute('INSERT INTO users (username, email, full_name, otp, is_verified) VALUES (?, ?, ?, ?, 0)',
                     (email, email, name, otp))
    
    conn.commit()
    conn.close()
    
    # Send OTP Email
    try:
        msg = Message("Your MuseumBot Verification Code", recipients=[email])
        msg.body = f"Hello {name},\n\nYour One-Time Password (OTP) for MuseumBot is: {otp}\n\nPlease enter this on the verification page to complete your login."
        mail.send(msg)
        session['temp_email'] = email
        session['temp_name'] = name
        return redirect(url_for('verify_otp'))
    except Exception as e:
        print(f"SMTP ERROR: {e}")
        flash(f"Error sending verification email: {str(e)}")
        return redirect(url_for('login'))

@app.route('/verify-otp', methods=['GET', 'POST'])
def verify_otp():
    email = session.get('temp_email')
    name = session.get('temp_name')
    if not email:
        return redirect(url_for('login'))
        
    if request.method == 'POST':
        otp_input = request.form.get('otp')
        
        conn = get_db_connection()
        user = conn.execute('SELECT * FROM users WHERE email = ?', (email,)).fetchone()
        
        if user and user['otp'] == otp_input:
            conn.execute('UPDATE users SET is_verified = 1, otp = NULL WHERE email = ?', (email,))
            conn.commit()
            
            session['user_id'] = user['id']
            session['username'] = user['full_name'] or user['username']
            session.pop('temp_email', None)
            session.pop('temp_name', None)
            conn.close()
            return redirect(url_for('home'))
        else:
            conn.close()
            flash("Invalid OTP. Please try again.")
            
    return render_template('verify_otp.html', email=email, name=name)

@app.route('/api/chat', methods=['POST'])
def chat():
    if 'user_id' not in session:
        return jsonify({'response': 'Please log in first.'}), 401
        
    user_message = request.json.get('message', '')
    bot_state = session.get('chatbot_state', {'state': 'idle'})
    
    response_text, updated_state = chatbot.process_message(user_message, bot_state)
    
    session['chatbot_state'] = updated_state
    session.modified = True
    
    return jsonify({'response': response_text})

@app.route('/api/pay', methods=['POST'])
def pay():
    if 'user_id' not in session:
        return jsonify({'success': False, 'message': 'Not logged in'})
        
    bot_state = session.get('chatbot_state', {'state': 'idle'})
    user_id = session['user_id']
    
    # Delegate to chatbot to handle the state transition and save booking
    res, updated_state = chatbot.process_payment_success(bot_state, user_id)
    
    session['chatbot_state'] = updated_state
    session.modified = True
    
    return jsonify(res)

@app.route('/api/manual_book', methods=['POST'])
def manual_book():
    if 'user_id' not in session:
        return jsonify({'success': False, 'message': 'Please log in before booking.'}), 401
    
    data = request.json
    user_id = session['user_id']
    museum = data.get('museum')
    visitor_name = data.get('visitor_name')
    count = int(data.get('count', 1))
    total = float(data.get('total', 0))
    
    import uuid
    ticket_hash = str(uuid.uuid4())[:8].upper()
    
    conn = get_db_connection()
    # We'll use exhibition_id = 99 for "Manual/Various" since the manual form has its own museum select
    conn.execute(
        'INSERT INTO bookings (user_id, visitor_name, exhibition_id, num_tickets, total_price, ticket_hash) VALUES (?, ?, ?, ?, ?, ?)',
        (user_id, visitor_name, 99, count, total, ticket_hash)
    )
    conn.commit()
    conn.close()
    
    return jsonify({
        'success': True, 
        'ticket_no': ticket_hash,
        'message': f'Booking for {museum} successful!'
    })

if __name__ == '__main__':
    app.run(debug=True, port=5000)
