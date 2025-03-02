from flask_mail import Mail, Message
from flask import current_app

mail = Mail()

def init_mail(app):
    """Inicializa Flask-Mail com as configurações do app"""
    mail.init_app(app)

def send_email(subject, recipients, body, html_body=None, attachment=None):
    """Função para enviar e-mail com anexo opcional e corpo HTML"""
    with current_app.app_context():
        msg = Message(subject, recipients=recipients)
        msg.body = body

        if html_body:
            msg.html = html_body

        # Se houver anexo, verificar e corrigir o formato
        if attachment:
            if not isinstance(attachment, dict) or not all(
                key in attachment for key in ["filename", "mimetype", "data"]
            ):
                raise ValueError("O attachment deve ser um dicionário contendo 'filename', 'mimetype' e 'data'.")

            # Converter string para bytes, se necessário
            if isinstance(attachment['data'], str):
                attachment['data'] = attachment['data'].encode()  # Converte string para bytes

            msg.attach(attachment['filename'], attachment['mimetype'], attachment['data'])

        mail.send(msg)