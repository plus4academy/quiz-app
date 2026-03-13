import logging
from config import SMTP_CONFIG
import sib_api_v3_sdk
logger = logging.getLogger(__name__)

# Try to import Brevo SDK, fallback to SMTP if not available
try:
    import sib_api_v3_sdk
    from sib_api_v3_sdk.rest import ApiException
    USE_BREVO_API = True
except ImportError:
    import smtplib
    from email.message import EmailMessage
    import ssl
    USE_BREVO_API = False
    logger.warning("Brevo SDK not found, falling back to SMTP")


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
    """Send email using Brevo API (preferred) or SMTP fallback"""
    to_address = (to_address or '').strip()
    if not to_address:
        return False, 'Recipient email not provided'

    sender_email = SMTP_CONFIG.get('sender') or SMTP_CONFIG.get('username')
    if not sender_email:
        return False, 'Sender email not configured'

    # Method 1: Use Brevo API (works on Railway)
    if USE_BREVO_API:
        api_key = SMTP_CONFIG.get('password')  # Reuse password field for API key
        if not api_key:
            return False, 'Brevo API key not configured'

        try:
            # Configure Brevo API
            configuration = sib_api_v3_sdk.Configuration()
            configuration.api_key['api-key'] = api_key
            api_instance = sib_api_v3_sdk.TransactionalEmailsApi(
                sib_api_v3_sdk.ApiClient(configuration)
            )

            # Create email
            send_smtp_email = sib_api_v3_sdk.SendSmtpEmail(
                to=[{"email": to_address}],
                sender={"email": sender_email, "name": "Plus4 Academy"},
                subject=subject,
                text_content=body
            )

            # Send via API
            api_instance.send_transac_email(send_smtp_email)
            logger.info(f"Email sent via Brevo API to {to_address}")
            return True, 'sent'

        except ApiException as e:
            logger.error(f"Brevo API error: {e}")
            return False, f'Brevo API error: {e}'
        except Exception as err:
            logger.error(f"Email send error: {err}")
            return False, str(err)

    # Method 2: SMTP fallback (for local development)
    else:
        if not SMTP_CONFIG.get('host'):
            return False, 'SMTP host not configured'

        msg = EmailMessage()
        msg['Subject'] = subject
        msg['From'] = sender_email
        msg['To'] = to_address
        msg.set_content(body)

        try:
            smtp_cls = smtplib.SMTP_SSL if SMTP_CONFIG.get('use_ssl') else smtplib.SMTP
            with smtp_cls(
                SMTP_CONFIG['host'],
                SMTP_CONFIG['port'],
                timeout=SMTP_CONFIG.get('timeout', 10),
            ) as smtp:
                smtp.ehlo()
                if SMTP_CONFIG.get('use_tls', True) and not SMTP_CONFIG.get('use_ssl'):
                    smtp.starttls(context=ssl.create_default_context())
                    smtp.ehlo()
                if SMTP_CONFIG.get('username') and SMTP_CONFIG.get('password'):
                    smtp.login(SMTP_CONFIG['username'], SMTP_CONFIG['password'])
                smtp.send_message(msg)
            logger.info(f"Email sent via SMTP to {to_address}")
            return True, 'sent'
        except Exception as err:
            logger.exception(
                'SMTP send failed',
                extra={
                    'smtp_host': SMTP_CONFIG.get('host'),
                    'smtp_port': SMTP_CONFIG.get('port'),
                    'smtp_sender': sender_email,
                    'recipient': to_address,
                },
            )
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