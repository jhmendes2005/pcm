from flask import Blueprint, render_template, request, Response, redirect, url_for, flash, send_file, session
from flask_login import login_user, logout_user, current_user, login_required
from app.email_service import send_email
import user_agents
from app import db
from app.models import User, Leads, Company, LeadComment, Integration
import pandas as pd
from datetime import datetime, timedelta
import secrets
import string
import io
import csv

integrations = Blueprint('integracoes', __name__)

def gerar_token_curto(tamanho=8):
    alfabeto = string.ascii_letters + string.digits  # Letras maiúsculas, minúsculas e números
    token = ''.join(secrets.choice(alfabeto) for _ in range(tamanho))
    return token

@integrations.route('/', methods=['GET', 'POST'])
@login_required
def main():
    user_id = current_user.id
    companies = Company.query.filter_by(owner_id=user_id).all()

    if not companies:
        flash('Você não tem uma empresa para acessar reports de leads!')
        return redirect(url_for('user.my_data'))
    return render_template('integrations/integrations.html', header_title='Nossas integrações', companies=companies)

@integrations.route('/autolead', methods=['GET', 'POST'])
@login_required
def autolead():
    user_id = current_user.id
    companies = Company.query.filter_by(owner_id=user_id).all()

    if not companies:
        flash('Você não tem uma empresa para acessar reports de leads!')
        return redirect(url_for('user.my_data'))

    # Verifica se o usuário já possui uma integração AutoLead (type 2)
    integration = Integration.query.filter_by(user_id=user_id, type=2).first()

    # Verifica se o formulário foi enviado
    if request.method == 'POST':
        token_api = request.form['token_api']
        status = request.form['lead_status']
        message_alias = request.form.get('lead_comentario')

        if integration:
            # Atualiza a integração existente
            integration.token_api = token_api
            integration.status = status
            integration.message_alias = message_alias
            db.session.commit()
            flash('Integração AutoLead atualizada com sucesso!')
        else:
            # Criação de uma nova integração AutoLead
            new_integration = Integration(
                user_id=user_id,
                type=2,  # AutoLead será sempre tipo 2
                token_api=token_api,
                status=status,
                message_alias=message_alias
            )
            db.session.add(new_integration)
            db.session.commit()
            flash('Integração AutoLead criada com sucesso!')

        return redirect(url_for('integracoes.autolead'))  # Redireciona para a mesma página

    # Caso contrário, exibe o formulário
    return render_template('integrations/services/autolead.html', header_title='AutoLead', companies=companies, integration=integration)
