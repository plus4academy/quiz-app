# from flask import Flask, render_template, request, jsonify
# from flask_mysqldb import MySQL

# app = Flask(__name__)

# # MySQL Configuration
# app.config['MYSQL_HOST'] = 'localhost'
# app.config['MYSQL_USER'] = 'root'
# app.config['MYSQL_PASSWORD'] = 'root'
# app.config['MYSQL_DB'] = 'student_info'

# mysql = MySQL(app)

# # Home Page
# @app.route('/')
# def index():
#     return render_template('Signup.html')

# # Signup Form Handler
# @app.route('/signup', methods=['POST'])
# def signup():
#     name = request.form.get('name')
#     email = request.form.get('email')
#     contact = request.form.get('contact')
#     class_enrolled = request.form.get('class')

#     cur = mysql.connection.cursor()

#     try:
#         cur.execute(
#             "INSERT INTO students (name, email, contact, class_enrolled) VALUES (%s, %s, %s, %s)",
#             (name, email, contact, class_enrolled)
#         )
#         mysql.connection.commit()
#         return "Registration Successful ✅"

#     except Exception as e:
#         mysql.connection.rollback()
#         return f"Error: {str(e)}"

#     finally:
#         cur.close()

# if __name__ == '__main__':
#     app.run(debug=True)


# """
# Flask Backend for OTP Verification using 2Factor.in API
# """

# from flask import Flask, render_template, request, jsonify
# from flask_cors import CORS
# import requests
# import os
# from datetime import datetime, timedelta
# import json

# app = Flask(__name__)
# CORS(app)

# # ===== CONFIGURATION =====
# # TODO: Replace with your 2factor.in API key
# TWO_FACTOR_API_KEY = os.getenv('TWO_FACTOR_API_KEY', 'YOUR_API_KEY_HERE')
# TWO_FACTOR_API_URL = 'https://2factor.in/API/V1'

# # In-memory storage for OTP sessions (for demo purposes)
# # In production, use Redis or a database
# otp_sessions = {}


# class OTPSession:
#     """Class to store OTP session data"""
#     def __init__(self, phone, session_id):
#         self.phone = phone
#         self.session_id = session_id
#         self.created_at = datetime.now()
#         self.expires_at = datetime.now() + timedelta(minutes=5)
#         self.verified = False
    
#     def is_expired(self):
#         """Check if OTP session has expired"""
#         return datetime.now() > self.expires_at
    
#     def mark_verified(self):
#         """Mark OTP as verified"""
#         self.verified = True


# # ===== ROUTES =====

# @app.route('/')
# def index():
#     """Serve the signup page"""
#     return render_template('index.html')


# @app.route('/send-otp', methods=['POST'])
# def send_otp():
#     """
#     Send OTP to phone number using 2Factor.in API
    
#     Expected JSON:
#     {
#         "phone": "9876543210"  (10-digit Indian phone number)
#     }
#     """
#     try:
#         data = request.get_json()
#         phone = data.get('phone', '').strip()
        
#         # Validate phone number
#         if not phone or len(phone) != 10 or not phone.isdigit():
#             return jsonify({
#                 'success': False,
#                 'error': 'Invalid phone number. Please enter 10 digits.'
#             }), 400
        
#         # Add country code (India: +91)
#         phone_with_country = f'91{phone}'
        
#         console_log(f"[v0] Sending OTP to: {phone}")
        
#         # Call 2Factor.in API to send OTP
#         api_endpoint = f'{TWO_FACTOR_API_URL}/sendOTP'
        
#         params = {
#             'apikey': TWO_FACTOR_API_KEY,
#             'method': 'SMS',
#             'to': phone_with_country,
#             'otpLength': 6
#         }
        
#         response = requests.get(api_endpoint, params=params, timeout=10)
#         api_response = response.json()
        
#         console_log(f"[v0] 2Factor API Response: {api_response}")
        
#         # Check if OTP was sent successfully
#         if api_response.get('Status') == 'Success':
#             session_id = api_response.get('Details')
            
#             # Store OTP session
#             otp_sessions[phone] = OTPSession(phone, session_id)
            
#             console_log(f"[v0] OTP sent successfully. Session ID: {session_id}")
            
#             return jsonify({
#                 'success': True,
#                 'message': f'OTP sent to {phone}',
#                 'session_id': session_id
#             }), 200
#         else:
#             error_msg = api_response.get('ErrorMessage', 'Failed to send OTP')
#             console_log(f"[v0] API Error: {error_msg}")
            
#             return jsonify({
#                 'success': False,
#                 'error': f'Failed to send OTP: {error_msg}'
#             }), 400
    
#     except requests.exceptions.Timeout:
#         console_log("[v0] Request timeout while sending OTP")
#         return jsonify({
#             'success': False,
#             'error': 'Request timeout. Please try again.'
#         }), 500
    
#     except requests.exceptions.RequestException as e:
#         console_log(f"[v0] Request error: {str(e)}")
#         return jsonify({
#             'success': False,
#             'error': 'Network error. Please try again.'
#         }), 500
    
#     except Exception as e:
#         console_log(f"[v0] Unexpected error: {str(e)}")
#         return jsonify({
#             'success': False,
#             'error': 'An error occurred. Please try again.'
#         }), 500


# @app.route('/verify-otp', methods=['POST'])
# def verify_otp():
#     """
#     Verify OTP sent to phone number
    
#     Expected JSON:
#     {
#         "phone": "9876543210",
#         "otp": "123456"
#     }
#     """
#     try:
#         data = request.get_json()
#         phone = data.get('phone', '').strip()
#         otp = data.get('otp', '').strip()
        
#         # Validate inputs
#         if not phone or len(phone) != 10 or not phone.isdigit():
#             return jsonify({
#                 'success': False,
#                 'error': 'Invalid phone number.'
#             }), 400
        
#         if not otp or len(otp) != 6 or not otp.isdigit():
#             return jsonify({
#                 'success': False,
#                 'error': 'Invalid OTP. Please enter 6 digits.'
#             }), 400
        
#         # Check if OTP session exists
#         if phone not in otp_sessions:
#             return jsonify({
#                 'success': False,
#                 'error': 'No OTP found for this number. Please send OTP first.'
#             }), 400
        
#         session = otp_sessions[phone]
        
#         # Check if OTP is expired
#         if session.is_expired():
#             del otp_sessions[phone]
#             return jsonify({
#                 'success': False,
#                 'error': 'OTP has expired. Please request a new one.'
#             }), 400
        
#         console_log(f"[v0] Verifying OTP: {otp} for phone: {phone}")
        
#         # Call 2Factor.in API to verify OTP
#         api_endpoint = f'{TWO_FACTOR_API_URL}/verifyOTP'
        
#         params = {
#             'apikey': TWO_FACTOR_API_KEY,
#             'otp': otp,
#             'sessionid': session.session_id
#         }
        
#         response = requests.get(api_endpoint, params=params, timeout=10)
#         api_response = response.json()
        
#         console_log(f"[v0] OTP Verification Response: {api_response}")
        
#         # Check if OTP was verified successfully
#         if api_response.get('Status') == 'Success':
#             session.mark_verified()
            
#             console_log(f"[v0] OTP verified successfully for phone: {phone}")
            
#             return jsonify({
#                 'success': True,
#                 'message': 'Phone number verified successfully!',
#                 'phone': phone
#             }), 200
#         else:
#             error_msg = api_response.get('ErrorMessage', 'Invalid OTP')
#             console_log(f"[v0] OTP Verification Failed: {error_msg}")
            
#             return jsonify({
#                 'success': False,
#                 'error': error_msg
#             }), 400
    
#     except requests.exceptions.Timeout:
#         console_log("[v0] Request timeout while verifying OTP")
#         return jsonify({
#             'success': False,
#             'error': 'Request timeout. Please try again.'
#         }), 500
    
#     except requests.exceptions.RequestException as e:
#         console_log(f"[v0] Request error: {str(e)}")
#         return jsonify({
#             'success': False,
#             'error': 'Network error. Please try again.'
#         }), 500
    
#     except Exception as e:
#         console_log(f"[v0] Unexpected error: {str(e)}")
#         return jsonify({
#             'success': False,
#             'error': 'An error occurred. Please try again.'
#         }), 500


# @app.route('/signup', methods=['POST'])
# def signup():
#     """
#     Handle student registration
    
#     Expected form data:
#     {
#         "name": "Student Name",
#         "email": "student@example.com",
#         "contact": "9876543210",
#         "class": "11th-jee"
#     }
#     """
#     try:
#         data = request.get_json() if request.is_json else request.form
        
#         name = data.get('name', '').strip()
#         email = data.get('email', '').strip()
#         contact = data.get('contact', '').strip()
#         student_class = data.get('class', '').strip()
        
#         # Validate inputs
#         if not all([name, email, contact, student_class]):
#             return jsonify({
#                 'success': False,
#                 'error': 'All fields are required.'
#             }), 400
        
#         # Verify phone number was OTP verified
#         if contact not in otp_sessions or not otp_sessions[contact].verified:
#             return jsonify({
#                 'success': False,
#                 'error': 'Phone number not verified. Please complete OTP verification.'
#             }), 400
        
#         console_log(f"[v0] New Registration: {name}, {email}, {contact}, {student_class}")
        
#         # TODO: Save registration to database
#         # db.students.insert_one({
#         #     'name': name,
#         #     'email': email,
#         #     'phone': contact,
#         #     'class': student_class,
#         #     'registered_at': datetime.now()
#         # })
        
#         return jsonify({
#             'success': True,
#             'message': 'Registration successful!',
#             'student': {
#                 'name': name,
#                 'email': email,
#                 'phone': contact,
#                 'class': student_class
#             }
#         }), 200
    
#     except Exception as e:
#         console_log(f"[v0] Registration error: {str(e)}")
#         return jsonify({
#             'success': False,
#             'error': 'Registration failed. Please try again.'
#         }), 500


# @app.route('/health', methods=['GET'])
# def health_check():
#     """Health check endpoint"""
#     return jsonify({
#         'status': 'healthy',
#         'api_key_configured': TWO_FACTOR_API_KEY != 'YOUR_API_KEY_HERE'
#     }), 200


# # ===== UTILITY FUNCTIONS =====

# def console_log(message):
#     """Print log messages with timestamp"""
#     timestamp = datetime.now().strftime('%Y-%m-%d %H:%M:%S')
#     print(f"[{timestamp}] {message}")


# # ===== ERROR HANDLERS =====

# @app.errorhandler(404)
# def not_found(error):
#     return jsonify({'error': 'Not found'}), 404


# @app.errorhandler(500)
# def internal_error(error):
#     return jsonify({'error': 'Internal server error'}), 500


# # ===== MAIN =====

# if __name__ == '__main__':
#     # Check if API key is set
#     if TWO_FACTOR_API_KEY == 'YOUR_API_KEY_HERE':
#         console_log("⚠️  WARNING: TWO_FACTOR_API_KEY is not set!")
#         console_log("Please set the environment variable: TWO_FACTOR_API_KEY")
#     else:
#         console_log("✓ TWO_FACTOR_API_KEY is configured")
    
#     console_log("Starting Flask server...")
#     app.run(debug=True, host='0.0.0.0', port=5000)
#     console_log("Flask server stopped")




"""
Quiz Web Application - Flask Backend
A complete quiz platform with authentication, timer, and tab switching detection
Author: Senior Full-Stack Developer
"""
"""
Quiz Web Application - Flask Backend
A complete quiz platform with authentication, timer, and tab switching detection
Author: Senior Full-Stack Developer
"""

from flask import Flask, render_template, request, session, redirect, url_for, jsonify
from datetime import datetime, timedelta
import secrets
import sqlite3
import json
import os
from functools import wraps

app = Flask(__name__)
app.secret_key = secrets.token_hex(32)  # Secure random secret key
app.config['PERMANENT_SESSION_LIFETIME'] = timedelta(hours=2)

# Database initialization
def init_db():
    """Initialize SQLite database with required tables"""
    conn = sqlite3.connect('quiz_app.db')
    cursor = conn.cursor()
    
    # Users table for storing login and test data
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS users (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            username TEXT NOT NULL,
            password TEXT NOT NULL,
            class_level TEXT NOT NULL,
            stream TEXT NOT NULL,
            login_time TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        )
    ''')
    
    # Test results table
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS test_results (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            user_id INTEGER,
            username TEXT NOT NULL,
            class_level TEXT NOT NULL,
            stream TEXT NOT NULL,
            score INTEGER NOT NULL,
            total_questions INTEGER NOT NULL,
            tab_switches INTEGER DEFAULT 0,
            submission_type TEXT,
            test_date TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            FOREIGN KEY (user_id) REFERENCES users (id)
        )
    ''')
    
    conn.commit()
    conn.close()

# Initialize database on startup
init_db()

# Helper function to load questions from JSON files
def load_questions(class_level, stream):
    """Load questions from JSON file based on class and stream"""
    filename = f'data/questions_{class_level}_{stream}.json'
    filepath = os.path.join(os.path.dirname(__file__), filename)
    
    try:
        with open(filepath, 'r', encoding='utf-8') as f:
            return json.load(f)
    except FileNotFoundError:
        return []

# Login required decorator
def login_required(f):
    """Decorator to ensure user is logged in before accessing routes"""
    @wraps(f)
    def decorated_function(*args, **kwargs):
        if 'username' not in session:
            return redirect(url_for('login'))
        return f(*args, **kwargs)
    return decorated_function

# Scholarship calculation function
def calculate_scholarship(percentage):
    """Calculate scholarship percentage based on score"""
    if percentage >= 90:
        return 100, "Full Scholarship - Congratulations!"
    elif percentage >= 75:
        return 50, "Half Scholarship - Well Done!"
    elif percentage >= 60:
        return 25, "Quarter Scholarship - Good Effort!"
    else:
        return 0, "No Scholarship - Keep Trying!"

@app.route('/')
def index():
    """Redirect to login page or test page if already logged in"""
    if 'username' in session and 'test_completed' not in session:
        class_level = session.get('class_level')
        stream = session.get('stream')
        if class_level == 'dropper':
            return redirect(url_for('test_page', class_level='dropper', stream=stream))
        else:
            return redirect(url_for('test_page', class_level=class_level, stream=stream))
    return redirect(url_for('login'))

@app.route('/login', methods=['GET', 'POST'])
def login():
    """Handle user login and authentication"""
    if request.method == 'POST':
        username = request.form.get('username', '').strip()
        password = request.form.get('password', '').strip()
        class_level = request.form.get('class_level', '').strip()
        stream = request.form.get('stream', '').strip()
        
        # Basic validation
        if not all([username, password, class_level]):
            return render_template('login.html', error="Username, password, and class are required")
        
        # Validate class level
        valid_classes = ['class9', 'class10', 'class11', 'class12', 'dropper']
        
        if class_level not in valid_classes:
            return render_template('login.html', error="Invalid class selection")
        
        # Stream is required only for class 11, 12, and dropper
        if class_level in ['class11', 'class12', 'dropper']:
            valid_streams = ['jee', 'neet']
            if not stream or stream not in valid_streams:
                return render_template('login.html', error="Please select a stream for Class 11, 12, or Dropper")
        else:
            # For class 9 and 10, set stream to 'general'
            stream = 'general'
        
        # Store user data in database
        conn = sqlite3.connect('quiz_app.db')
        cursor = conn.cursor()
        cursor.execute('''
            INSERT INTO users (username, password, class_level, stream)
            VALUES (?, ?, ?, ?)
        ''', (username, password, class_level, stream))
        user_id = cursor.lastrowid
        conn.commit()
        conn.close()
        
        # Set session data
        session.permanent = True
        session['username'] = username
        session['user_id'] = user_id
        session['class_level'] = class_level
        session['stream'] = stream
        session['tab_switches'] = 0
        session['test_start_time'] = datetime.now().isoformat()
        
        # Redirect to appropriate test
        if class_level in ['class9', 'class10']:
            return redirect(url_for('test_page', class_level=class_level))
        elif class_level == 'dropper':
            return redirect(url_for('test_page', class_level='dropper', stream=stream))
        else:
            return redirect(url_for('test_page', class_level=class_level, stream=stream))
    
    return render_template('login.html')

@app.route('/test/<class_level>')
@app.route('/test/<class_level>/<stream>')
@login_required
def test_page(class_level=None, stream=None):
    """Display test page with questions"""
    # Check if test is already completed
    if 'test_completed' in session:
        return redirect(url_for('score'))
    
    # Verify user has access to this test
    if session.get('class_level') != class_level:
        return redirect(url_for('login'))
    
    # For class 9 and 10, use 'general' stream
    if class_level in ['class9', 'class10']:
        user_stream = 'general'
    else:
        # For class 11, 12, and dropper, stream is required
        user_stream = stream if stream else session.get('stream')
        if session.get('stream') != user_stream:
            return redirect(url_for('login'))
    
    # Get questions for this class and stream
    questions = load_questions(class_level, user_stream)
    
    if not questions:
        return render_template('error.html', 
                             message=f"No questions available for {class_level}" + 
                                    (f" - {user_stream}" if user_stream != 'general' else ""))
    
    return render_template('test.html', 
                         questions=questions,
                         class_level=class_level,
                         stream=user_stream,
                         username=session.get('username'))

@app.route('/api/submit_test', methods=['POST'])
@login_required
def submit_test():
    """Handle test submission and calculate score"""
    try:
        data = request.get_json()
        answers = data.get('answers', {})
        tab_switches = data.get('tab_switches', 0)
        submission_type = data.get('submission_type', 'manual')  # manual, timeout, or tab_violation
        
        # Load questions to check answers
        class_level = session.get('class_level')
        stream = session.get('stream')
        questions = load_questions(class_level, stream)
        
        # Calculate score
        correct_count = 0
        total_questions = len(questions)
        
        for question in questions:
            question_id = str(question['id'])
            if question_id in answers:
                user_answer = int(answers[question_id])
                if user_answer == question['correct']:
                    correct_count += 1
        
        # Store result in database
        conn = sqlite3.connect('quiz_app.db')
        cursor = conn.cursor()
        cursor.execute('''
            INSERT INTO test_results 
            (user_id, username, class_level, stream, score, total_questions, tab_switches, submission_type)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?)
        ''', (session.get('user_id'), session.get('username'), class_level, stream, 
              correct_count, total_questions, tab_switches, submission_type))
        conn.commit()
        conn.close()
        
        # Store in session for score page
        session['test_completed'] = True
        session['score'] = correct_count
        session['total_questions'] = total_questions
        session['tab_switches'] = tab_switches
        session['submission_type'] = submission_type
        
        return jsonify({
            'success': True,
            'score': correct_count,
            'total': total_questions
        })
    
    except Exception as e:
        return jsonify({'success': False, 'error': str(e)}), 500

@app.route('/api/log_tab_switch', methods=['POST'])
@login_required
def log_tab_switch():
    """Log tab switch event"""
    try:
        session['tab_switches'] = session.get('tab_switches', 0) + 1
        return jsonify({
            'success': True,
            'tab_switches': session['tab_switches']
        })
    except Exception as e:
        return jsonify({'success': False, 'error': str(e)}), 500

@app.route('/score')
@login_required
def score():
    """Display test results and scholarship information"""
    if 'test_completed' not in session:
        return redirect(url_for('index'))
    
    score = session.get('score', 0)
    total = session.get('total_questions', 0)
    percentage = (score / total * 100) if total > 0 else 0
    
    scholarship_percent, scholarship_message = calculate_scholarship(percentage)
    
    return render_template('score.html',
                         username=session.get('username'),
                         class_level=session.get('class_level'),
                         stream=session.get('stream'),
                         score=score,
                         total=total,
                         percentage=round(percentage, 2),
                         scholarship_percent=scholarship_percent,
                         scholarship_message=scholarship_message,
                         tab_switches=session.get('tab_switches', 0),
                         submission_type=session.get('submission_type', 'manual'))

@app.route('/logout')
def logout():
    """Clear session and logout user"""
    session.clear()
    return redirect(url_for('login'))

# Error handlers
@app.errorhandler(404)
def not_found(e):
    """Handle 404 errors"""
    return render_template('error.html', message="Page not found"), 404

@app.errorhandler(500)
def server_error(e):
    """Handle 500 errors"""
    return render_template('error.html', message="Internal server error"), 500

if __name__ == '__main__':
    app.run(debug=True, host='0.0.0.0', port=5000)