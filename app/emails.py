# admin_routes.py
from flask import Blueprint, render_template, request, Response, redirect, url_for, flash, send_file, session
from flask_login import login_user, logout_user, current_user, login_required
import user_agents
from app import db
from app.models import User, Leads, Company
from werkzeug.security import generate_password_hash, check_password_hash
import pandas as pd
from datetime import datetime, timedelta
import secrets
import string
from app.email_service import send_email

email = Blueprint('email', __name__)

def generate_confirmation_token():
    return secrets.token_urlsafe(16)

@email.route("/send_email")
def send_email_route():
    try:
        send_email(
            subject='Assunto do E-mail',
            recipients=['jhmendes2005@gmail.com'],  # Destinatário do e-mail
            body='Este é o corpo do e-mail.',
            html_body='<b>Este é o corpo do e-mail em HTML</b>'
        )
        return "E-mail enviado com sucesso!"
    except Exception as e:
        return str(e)
    
@email.route("/register_confirmation")
def send_register_confirmation():
    try:
        # Gera o token para confirmação
        token = generate_confirmation_token()

        # Gera o link de confirmação
        confirmation_url = url_for('confirm_email', token=token, _external=True)

        # Corpo do e-mail com link de confirmação
        html_body = f"""
        <h1>Bem-vindo ao PCM!</h1>
        <p>Obrigado por criar uma conta. Por favor, confirme seu e-mail clicando no link abaixo:</p>
        <a href="{confirmation_url}">Clique aqui para confirmar sua conta</a>
        """

        # Envia o e-mail de confirmação
        send_email(
            subject='Confirmação de Conta PCM',
            recipients=['jhmendes2005@gmail.com'],  # Coloque aqui o e-mail do usuário
            body='Obrigado por criar uma conta no PCM. Clique no link para confirmar sua conta.',
            html_body=html_body
        )
        return "E-mail de confirmação enviado com sucesso!"
    except Exception as e:
        return str(e)