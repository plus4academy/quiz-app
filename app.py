from flask import Flask, render_template, request, jsonify
from flask_mysqldb import MySQL

app = Flask(__name__)

# MySQL Configuration
app.config['MYSQL_HOST'] = 'localhost'
app.config['MYSQL_USER'] = 'root'
app.config['MYSQL_PASSWORD'] = 'root'
app.config['MYSQL_DB'] = 'student_info'

mysql = MySQL(app)

# Home Page
@app.route('/')
def index():
    return render_template('Signup.html')

# Signup Form Handler
@app.route('/signup', methods=['POST'])
def signup():
    name = request.form.get('name')
    email = request.form.get('email')
    contact = request.form.get('contact')
    class_enrolled = request.form.get('class')

    cur = mysql.connection.cursor()

    try:
        cur.execute(
            "INSERT INTO students (name, email, contact, class_enrolled) VALUES (%s, %s, %s, %s)",
            (name, email, contact, class_enrolled)
        )
        mysql.connection.commit()
        return "Registration Successful ✅"

    except Exception as e:
        mysql.connection.rollback()
        return f"Error: {str(e)}"

    finally:
        cur.close()

if __name__ == '__main__':
    app.run(debug=True)


"""
Flask Backend for OTP Verification using 2Factor.in API
"""

from flask import Flask, render_template, request, jsonify
from flask_cors import CORS
import requests
import os
from datetime import datetime, timedelta
import json

app = Flask(__name__)
CORS(app)

# ===== CONFIGURATION =====
# TODO: Replace with your 2factor.in API key
TWO_FACTOR_API_KEY = os.getenv('TWO_FACTOR_API_KEY', 'YOUR_API_KEY_HERE')
TWO_FACTOR_API_URL = 'https://2factor.in/API/V1'

# In-memory storage for OTP sessions (for demo purposes)
# In production, use Redis or a database
otp_sessions = {}


class OTPSession:
    """Class to store OTP session data"""
    def __init__(self, phone, session_id):
        self.phone = phone
        self.session_id = session_id
        self.created_at = datetime.now()
        self.expires_at = datetime.now() + timedelta(minutes=5)
        self.verified = False
    
    def is_expired(self):
        """Check if OTP session has expired"""
        return datetime.now() > self.expires_at
    
    def mark_verified(self):
        """Mark OTP as verified"""
        self.verified = True


# ===== ROUTES =====

@app.route('/')
def index():
    """Serve the signup page"""
    return render_template('index.html')


@app.route('/send-otp', methods=['POST'])
def send_otp():
    """
    Send OTP to phone number using 2Factor.in API
    
    Expected JSON:
    {
        "phone": "9876543210"  (10-digit Indian phone number)
    }
    """
    try:
        data = request.get_json()
        phone = data.get('phone', '').strip()
        
        # Validate phone number
        if not phone or len(phone) != 10 or not phone.isdigit():
            return jsonify({
                'success': False,
                'error': 'Invalid phone number. Please enter 10 digits.'
            }), 400
        
        # Add country code (India: +91)
        phone_with_country = f'91{phone}'
        
        console_log(f"[v0] Sending OTP to: {phone}")
        
        # Call 2Factor.in API to send OTP
        api_endpoint = f'{TWO_FACTOR_API_URL}/sendOTP'
        
        params = {
            'apikey': TWO_FACTOR_API_KEY,
            'method': 'SMS',
            'to': phone_with_country,
            'otpLength': 6
        }
        
        response = requests.get(api_endpoint, params=params, timeout=10)
        api_response = response.json()
        
        console_log(f"[v0] 2Factor API Response: {api_response}")
        
        # Check if OTP was sent successfully
        if api_response.get('Status') == 'Success':
            session_id = api_response.get('Details')
            
            # Store OTP session
            otp_sessions[phone] = OTPSession(phone, session_id)
            
            console_log(f"[v0] OTP sent successfully. Session ID: {session_id}")
            
            return jsonify({
                'success': True,
                'message': f'OTP sent to {phone}',
                'session_id': session_id
            }), 200
        else:
            error_msg = api_response.get('ErrorMessage', 'Failed to send OTP')
            console_log(f"[v0] API Error: {error_msg}")
            
            return jsonify({
                'success': False,
                'error': f'Failed to send OTP: {error_msg}'
            }), 400
    
    except requests.exceptions.Timeout:
        console_log("[v0] Request timeout while sending OTP")
        return jsonify({
            'success': False,
            'error': 'Request timeout. Please try again.'
        }), 500
    
    except requests.exceptions.RequestException as e:
        console_log(f"[v0] Request error: {str(e)}")
        return jsonify({
            'success': False,
            'error': 'Network error. Please try again.'
        }), 500
    
    except Exception as e:
        console_log(f"[v0] Unexpected error: {str(e)}")
        return jsonify({
            'success': False,
            'error': 'An error occurred. Please try again.'
        }), 500


@app.route('/verify-otp', methods=['POST'])
def verify_otp():
    """
    Verify OTP sent to phone number
    
    Expected JSON:
    {
        "phone": "9876543210",
        "otp": "123456"
    }
    """
    try:
        data = request.get_json()
        phone = data.get('phone', '').strip()
        otp = data.get('otp', '').strip()
        
        # Validate inputs
        if not phone or len(phone) != 10 or not phone.isdigit():
            return jsonify({
                'success': False,
                'error': 'Invalid phone number.'
            }), 400
        
        if not otp or len(otp) != 6 or not otp.isdigit():
            return jsonify({
                'success': False,
                'error': 'Invalid OTP. Please enter 6 digits.'
            }), 400
        
        # Check if OTP session exists
        if phone not in otp_sessions:
            return jsonify({
                'success': False,
                'error': 'No OTP found for this number. Please send OTP first.'
            }), 400
        
        session = otp_sessions[phone]
        
        # Check if OTP is expired
        if session.is_expired():
            del otp_sessions[phone]
            return jsonify({
                'success': False,
                'error': 'OTP has expired. Please request a new one.'
            }), 400
        
        console_log(f"[v0] Verifying OTP: {otp} for phone: {phone}")
        
        # Call 2Factor.in API to verify OTP
        api_endpoint = f'{TWO_FACTOR_API_URL}/verifyOTP'
        
        params = {
            'apikey': TWO_FACTOR_API_KEY,
            'otp': otp,
            'sessionid': session.session_id
        }
        
        response = requests.get(api_endpoint, params=params, timeout=10)
        api_response = response.json()
        
        console_log(f"[v0] OTP Verification Response: {api_response}")
        
        # Check if OTP was verified successfully
        if api_response.get('Status') == 'Success':
            session.mark_verified()
            
            console_log(f"[v0] OTP verified successfully for phone: {phone}")
            
            return jsonify({
                'success': True,
                'message': 'Phone number verified successfully!',
                'phone': phone
            }), 200
        else:
            error_msg = api_response.get('ErrorMessage', 'Invalid OTP')
            console_log(f"[v0] OTP Verification Failed: {error_msg}")
            
            return jsonify({
                'success': False,
                'error': error_msg
            }), 400
    
    except requests.exceptions.Timeout:
        console_log("[v0] Request timeout while verifying OTP")
        return jsonify({
            'success': False,
            'error': 'Request timeout. Please try again.'
        }), 500
    
    except requests.exceptions.RequestException as e:
        console_log(f"[v0] Request error: {str(e)}")
        return jsonify({
            'success': False,
            'error': 'Network error. Please try again.'
        }), 500
    
    except Exception as e:
        console_log(f"[v0] Unexpected error: {str(e)}")
        return jsonify({
            'success': False,
            'error': 'An error occurred. Please try again.'
        }), 500


@app.route('/signup', methods=['POST'])
def signup():
    """
    Handle student registration
    
    Expected form data:
    {
        "name": "Student Name",
        "email": "student@example.com",
        "contact": "9876543210",
        "class": "11th-jee"
    }
    """
    try:
        data = request.get_json() if request.is_json else request.form
        
        name = data.get('name', '').strip()
        email = data.get('email', '').strip()
        contact = data.get('contact', '').strip()
        student_class = data.get('class', '').strip()
        
        # Validate inputs
        if not all([name, email, contact, student_class]):
            return jsonify({
                'success': False,
                'error': 'All fields are required.'
            }), 400
        
        # Verify phone number was OTP verified
        if contact not in otp_sessions or not otp_sessions[contact].verified:
            return jsonify({
                'success': False,
                'error': 'Phone number not verified. Please complete OTP verification.'
            }), 400
        
        console_log(f"[v0] New Registration: {name}, {email}, {contact}, {student_class}")
        
        # TODO: Save registration to database
        # db.students.insert_one({
        #     'name': name,
        #     'email': email,
        #     'phone': contact,
        #     'class': student_class,
        #     'registered_at': datetime.now()
        # })
        
        return jsonify({
            'success': True,
            'message': 'Registration successful!',
            'student': {
                'name': name,
                'email': email,
                'phone': contact,
                'class': student_class
            }
        }), 200
    
    except Exception as e:
        console_log(f"[v0] Registration error: {str(e)}")
        return jsonify({
            'success': False,
            'error': 'Registration failed. Please try again.'
        }), 500


@app.route('/health', methods=['GET'])
def health_check():
    """Health check endpoint"""
    return jsonify({
        'status': 'healthy',
        'api_key_configured': TWO_FACTOR_API_KEY != 'YOUR_API_KEY_HERE'
    }), 200


# ===== UTILITY FUNCTIONS =====

def console_log(message):
    """Print log messages with timestamp"""
    timestamp = datetime.now().strftime('%Y-%m-%d %H:%M:%S')
    print(f"[{timestamp}] {message}")


# ===== ERROR HANDLERS =====

@app.errorhandler(404)
def not_found(error):
    return jsonify({'error': 'Not found'}), 404


@app.errorhandler(500)
def internal_error(error):
    return jsonify({'error': 'Internal server error'}), 500


# ===== MAIN =====

if __name__ == '__main__':
    # Check if API key is set
    if TWO_FACTOR_API_KEY == 'YOUR_API_KEY_HERE':
        console_log("⚠️  WARNING: TWO_FACTOR_API_KEY is not set!")
        console_log("Please set the environment variable: TWO_FACTOR_API_KEY")
    else:
        console_log("✓ TWO_FACTOR_API_KEY is configured")
    
    console_log("Starting Flask server...")
    app.run(debug=True, host='0.0.0.0', port=5000)
    console_log("Flask server stopped")