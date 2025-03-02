from flask import Blueprint, render_template, request, Response, redirect, url_for, flash, send_file, session, request, jsonify
from flask_login import login_user, logout_user, current_user, login_required
from app.email_service import send_email
import user_agents
from app import db
from app.models import User, Leads, Company, LeadComment, Contacts
from werkzeug.security import generate_password_hash, check_password_hash
import pandas as pd
from datetime import datetime, timedelta
import secrets
import string
import io
import csv
from flask import flash, redirect, url_for, request
from sqlalchemy.exc import SQLAlchemyError

from app.purchases.decorators import require_active_plan, require_lead_limit, require_employee_limit
#@require_active_plan
#@require_lead_limit
#@require_employee_limit

clplugin = Blueprint('clplugin', __name__)

def gerar_token_curto(tamanho=8):
    alfabeto = string.ascii_letters + string.digits  # Letras maiúsculas, minúsculas e números
    token = ''.join(secrets.choice(alfabeto) for _ in range(tamanho))
    return token

@clplugin.route('/', methods=['GET', 'POST'])
@login_required
@require_active_plan
def my_clplugin():
    user_id = current_user.id
    user_agent = request.headers.get('User-Agent')
    ua = user_agents.parse(user_agent)
    is_mobile = ua.is_mobile  

    # Obter a lista de empresas do usuário
    companies = Company.query.filter_by(owner_id=user_id).all()

    if not companies:
        flash('Você não tem uma empresa para acessar contatos!')
        return redirect(url_for('user.my_data'))

    # Obter a empresa selecionada pelo usuário
    selected_company_id = request.args.get('company_id', companies[0].id)  # Se não houver, seleciona a primeira empresa
    selected_company = Company.query.get(selected_company_id)

    if not selected_company:
        flash('Empresa selecionada não encontrada!')
        return redirect(url_for('user.my_data'))

    # Obter o termo de pesquisa
    search_term = request.args.get('search', '').strip()

    # Obter a quantidade de contatos a ser exibida, padrão 20, máximo 100
    contacts_limit = request.args.get('contacts_limit', 20, type=int)
    contacts_limit = min(contacts_limit, 100)  # Limita a 100

    # Filtrar contatos pelo termo de pesquisa
    query = Contacts.query.filter_by(company_id=selected_company.id)

    if search_term:
        search_filter = f"%{search_term}%"  # Adiciona o termo de pesquisa com wildcard
        query = query.filter(
            (Contacts.name.ilike(search_filter)) | 
            (Contacts.phone.ilike(search_filter)) | 
            (Contacts.website.ilike(search_filter)) |
            (Contacts.page.ilike(search_filter))
        )

    all_contacts = query.limit(contacts_limit).all()

    return render_template('contactsLeadsPlugin/contactsLeadsPlugin.html', 
                           header_title='Lista de Contatos', 
                           contacts=all_contacts, 
                           company=selected_company, 
                           companies=companies, 
                           selected_company=selected_company, 
                           contacts_limit=contacts_limit, 
                           is_mobile=is_mobile,
                           search_term=search_term)


@clplugin.route('/send-lead/', methods=['POST'])
def send_lead():
    # Recebe os dados do lead do corpo da requisição
    data = request.get_json()

    # Verifica se todos os campos necessários estão presentes
    required_fields = ['name', 'phone', 'page', 'time', 'website', 'token_api']
    if not all(field in data for field in required_fields):
        return jsonify({'error': 'Missing required fields'}), 400

    name = data['name']
    phone = data['phone']
    page = data['page']
    time = data['time']
    website = data['website']
    token_api = data['token_api']
    print(token_api)

    try:
        # Pesquisa a empresa no banco de dados com o token_api fornecido
        company = Company.query.filter_by(token_api=token_api).first()

        if not company:
            return jsonify({'error': 'Company not found with the provided token'}), 404

        # Cria o novo contato
        contact = Contacts(
            company_id=company.id,
            name=name,
            phone=phone,
            page=page,
            time=time,
            website=website
        )

        # Salva o novo contato no banco de dados
        db.session.add(contact)
        db.session.commit()

        return jsonify({'message': 'Lead successfully added'}), 201

    except SQLAlchemyError as e:
        db.session.rollback()
        return jsonify({'error': str(e)}), 500