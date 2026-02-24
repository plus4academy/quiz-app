import smtplib
from email.message import EmailMessage

from config import SMTP_CONFIG


def format_class_label(class_level, stream):
    if class_level == 'dropper':
        return f'Dropper ({stream.upper()})' if stream else 'Dropper'

    if class_level.startswith('class'):
        number = class_level.replace('class', '')
        if stream and stream != 'general':
            return f'Class {number} ({stream.upper()})'
        return f'Class {number}'

    return class_level


def send_plain_email(to_address, subject, body):
    to_address = (to_address or '').strip()
    if not to_address:
        return False, 'Recipient email not provided'

    if not SMTP_CONFIG.get('host'):
        return False, 'SMTP host not configured'

    sender = SMTP_CONFIG.get('sender') or SMTP_CONFIG.get('username')
    if not sender:
        return False, 'SMTP sender not configured'

    msg = EmailMessage()
    msg['Subject'] = subject
    msg['From'] = sender
    msg['To'] = to_address
    msg.set_content(body)

    try:
        with smtplib.SMTP(SMTP_CONFIG['host'], SMTP_CONFIG['port'], timeout=10) as smtp:
            if SMTP_CONFIG.get('use_tls', True):
                smtp.starttls()
            if SMTP_CONFIG.get('username') and SMTP_CONFIG.get('password'):
                smtp.login(SMTP_CONFIG['username'], SMTP_CONFIG['password'])
            smtp.send_message(msg)
        return True, 'sent'
    except Exception as err:
        return False, str(err)


def send_result_emails(student_name, student_email, phone, class_level, stream, score, total_questions):
    class_label = format_class_label(class_level, stream)
    percentage = round((score / total_questions * 100), 2) if total_questions else 0
    marks = f'{score}/{total_questions} ({percentage}%)'
    phone_value = (phone or '').strip()

    if not phone_value:
        return {
            'student_email': (False, 'Phone number missing; result email not sent'),
            'admin_email': (False, 'Phone number missing; result email not sent'),
        }

    subject = 'Plus4 Academy Quiz Result'
    body = (
        'Quiz Result Details\n\n'
        f'Student Name: {student_name}\n'
        f'Class: {class_label}\n'
        f'Marks Scored: {marks}\n'
        f'Phone Number: {phone_value}\n'
    )

    status = {}

    if student_email:
        status['student_email'] = send_plain_email(student_email, subject, body)
    else:
        status['student_email'] = (False, 'Student email not available')

    admin_email = 'plus4academy2025@gmail.com'
    admin_subject = f'Quiz Result - {student_name}'
    status['admin_email'] = send_plain_email(admin_email, admin_subject, body)

    return status
