import os
import csv
import requests
from flask import Flask, request, jsonify
from threading import Thread
from datetime import datetime
import smtplib
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart
from dotenv import load_dotenv

from pathlib import Path

# Agrega flask_restx
from flask_restx import Api, Resource, fields

env_path = Path("/home/josechelseashop/mysite/.env")

# VERIFICACIÓN EXPLÍCITA DEL .env
print(f"🔍 Buscando .env en: {env_path}")
if env_path.exists():
    print(f"✅ Archivo .env encontrado")
    load_dotenv(env_path)
else:
    print(f"❌ ERROR: Archivo .env NO existe en esa ubicación")

# VERIFICA LAS VARIABLES
print("\n🔍 Valores de entorno cargados:")
print(f"TELEGRAM_TOKEN: {os.getenv('TELEGRAM_TOKEN')}")
print(f"ADMIN_CHAT_ID: {os.getenv('ADMIN_CHAT_ID')}")
print(f"SMTP_SERVER: {os.getenv('SMTP_SERVER')}")
print(f"SMTP_USER: {os.getenv('SMTP_USER')}")
print(f"SMTP_PASSWORD: {'*****' if os.getenv('SMTP_PASSWORD') else None}")

app = Flask(__name__)
api = Api(app, title="Lead CV API", description="API para recepción de leads y comunicación con Telegram", version="1.0")
ns = api.namespace('api', description='Operaciones de leads')

# Modelos para documentación
cv_model = api.model('CVLead', {
    'company': fields.String(required=False, description='Nombre de la empresa'),
    'email': fields.String(required=True, description='Correo electrónico'),
    'phone': fields.String(required=False, description='Teléfono'),
    'position': fields.String(required=False, description='Posición')
})

landing_model = api.model('LandingLead', {
    'name': fields.String(required=False, description='Nombre'),
    'email': fields.String(required=True, description='Correo electrónico'),
    'message': fields.String(required=False, description='Mensaje')
})

# Configuración (cambia estos valores en tus variables de entorno)
TELEGRAM_TOKEN = os.getenv('TELEGRAM_TOKEN')  # Token del bot de Telegram
ADMIN_CHAT_ID = os.getenv('ADMIN_CHAT_ID')    # Chat ID del administrador
SMTP_SERVER = os.getenv('SMTP_SERVER')        # Ej: smtp.gmail.com
SMTP_PORT = int(os.getenv('SMTP_PORT', 587))  # Ej: 587
SMTP_USER = os.getenv('SMTP_USER')            # Correo para SMTP
SMTP_PASSWORD = os.getenv('SMTP_PASSWORD')    # Contraseña para SMTP


def send_telegram_message(chat_id, text):
    try:
        url = f"https://api.telegram.org/bot{TELEGRAM_TOKEN}/sendMessage"
        payload = {'chat_id': chat_id, 'text': text, 'parse_mode': 'HTML'}
        response = requests.post(url, json=payload, timeout=10)

        # Registro detallado (verás esto en los logs de PythonAnywhere)
        print(f"""
        ⚡️ Intento de envío a Telegram:
        - URL: {url}
        - Chat ID: {chat_id}
        - Texto: {text[:50]}...
        - Status: {response.status_code}
        - Respuesta: {response.text}
        """)

        return response.json()
    except Exception as e:
        print(f"🚨 Error en send_telegram_message: {str(e)}")
        return None

def send_email(to_email, subject, body):
    """Envía un correo electrónico usando SMTP"""
    msg = MIMEMultipart()
    msg['From'] = SMTP_USER
    msg['To'] = to_email
    msg['Subject'] = subject
    msg.attach(MIMEText(body, 'plain'))

    with smtplib.SMTP(SMTP_SERVER, SMTP_PORT) as server:
        server.connect(SMTP_SERVER, SMTP_PORT)  # <-- Añade esta línea
        server.starttls()
        server.login(SMTP_USER, SMTP_PASSWORD)
        server.send_message(msg)

# --- Recursos RESTX ---

@ns.route('/cv')
class CVResource(Resource):
    @ns.expect(cv_model)
    def post(self):
        """Recibe leads desde el curriculum vitae"""
        data = request.json
        company = data.get('company', '').strip()
        email = data.get('email', '').strip()
        phone = data.get('phone', '').strip()
        position = data.get('position', '').strip()

        if not email or '@' not in email:
            return {"success": False, "error": "Email inválido"}, 400

        # Mensaje para Telegram
        message = (
            f"📬 Nuevo lead desde CV recibido:\n"
            f"Empresa: {company}\nEmail: {email}\nTeléfono: {phone}\nPosición: {position}"
        )
        send_telegram_message(ADMIN_CHAT_ID, message)

        # Correo de agradecimiento al empleador
        subject_thanks = "¡Gracias por tu interés!"
        body_thanks = (
            f"Hola,\n\n"
            f"Gracias por ponerte en contacto a través de mi currículum. "
            f"Pronto me comunicaré contigo.\n\n"
            f"Datos recibidos:\n"
            f"Empresa: {company}\n"
            f"Teléfono: {phone}\n"
            f"Posición: {position}\n\n"
            f"Saludos,\nJosé Yoel"
        )
        send_email(email, subject_thanks, body_thanks)

        # Correo a jymendev@gmail.com con los datos del empleador
        subject_admin = "Nuevo lead recibido desde CV"
        body_admin = (
            f"Se recibió un nuevo lead desde el CV:\n\n"
            f"Empresa: {company}\n"
            f"Email: {email}\n"
            f"Teléfono: {phone}\n"
            f"Posición: {position}\n"
            f"Fecha: {datetime.now()}\n"
        )
        send_email("jymendev@gmail.com", subject_admin, body_admin)

        return {"success": True}

@ns.route('/landing')
class LandingResource(Resource):
    @ns.expect(landing_model)
    def post(self):
        """Recibe leads desde la landing page"""
        data = request.json
        name = data.get('name', '').strip()
        email = data.get('email', '').strip()
        message_text = data.get('message', '').strip()

        if not email or '@' not in email:
            return {"success": False, "error": "Email inválido"}, 400

        # Mensaje para Telegram
        message = (
            f"📬 Nuevo lead desde landing:\n"
            f"Nombre: {name}\nEmail: {email}\nMensaje: {message_text}"
        )
        send_telegram_message(ADMIN_CHAT_ID, message)

        # Correo de agradecimiento al visitante
        subject_thanks = "¡Gracias por tu mensaje!"
        body_thanks = (
            f"Hola {name or ''},\n\n"
            f"Gracias por ponerte en contacto a través de mi página. "
            f"Pronto responderé tu mensaje.\n\n"
            f"Mensaje recibido:\n{message_text}\n\n"
            f"Saludos,\nJosé Yoel"
        )
        send_email(email, subject_thanks, body_thanks)

        # Correo a jymendev@gmail.com con los datos del visitante
        subject_admin = "Nuevo lead recibido desde landing"
        body_admin = (
            f"Se recibió un nuevo lead desde la landing:\n\n"
            f"Nombre: {name}\n"
            f"Email: {email}\n"
            f"Mensaje: {message_text}\n"
            f"Fecha: {datetime.now()}\n"
        )
        send_email("jymendev@gmail.com", subject_admin, body_admin)

        return {"success": True}

@api.route('/test-telegram')
class TestTelegramResource(Resource):
    def get(self):
        """Prueba la conexión con Telegram"""
        test_msg = "🔍 Prueba de conexión con Telegram"
        result = send_telegram_message(ADMIN_CHAT_ID, test_msg)
        return jsonify(success=bool(result), response=result)

if __name__ == '__main__':
    app.run(debug=True)