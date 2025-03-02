from flask import Blueprint, render_template, request, Response, redirect, url_for, flash, send_file, session, current_app, jsonify
from flask_login import login_user, logout_user, current_user, login_required
import user_agents
from app import db
from app.models import User, Leads, Company
from werkzeug.security import generate_password_hash, check_password_hash
import pandas as pd
from datetime import datetime, timedelta
from app.purchases.plans import Plans
import secrets
import string
import stripe

stripe.api_key = current_app.config['STRIPE_SECRET_KEY']

# Crie um blueprint para as rotas
main = Blueprint('main', __name__)

def gerar_token_curto(tamanho=8):
    alfabeto = string.ascii_letters + string.digits  # Letras maiúsculas, minúsculas e números
    token = ''.join(secrets.choice(alfabeto) for _ in range(tamanho))
    return token

@main.route('/')
def default():
        return redirect(url_for('user.my_data'))

@main.route('/create_company', methods=['GET', 'POST'])
@login_required
def create_company():
    if request.method == 'POST':
        # Obtenha os dados do formulário
        nome = request.form['nome']
        cnpj = request.form['cnpj']
        owner_id = request.form.get('owner_id', current_user.id)  # Certifique-se de que isso está sendo enviado no formulário
        plan = request.form.get('plan', 1) # Certifique-se de que isso está sendo enviado no formulário
        admins = request.form.get('admins', '')  # Se não houver admins, armazene uma string vazia
        collaborator = request.form.get('collaborator', '')  # Se não houver colaboradores, armazene uma string vazia
        invite = gerar_token_curto()

        # Criação da nova empresa
        new_company = Company(
            nome=nome,
            cnpj=cnpj,
            owner_id=owner_id,
            plan=plan,
            admins=admins,
            collaborator=collaborator,
            invite=invite
        )
        
        # Adiciona a nova empresa ao banco de dados
        db.session.add(new_company)
        db.session.commit()
        flash('Empresa criada com sucesso!', 'success')
        if request.referrer:
            return redirect(request.referrer)
        return redirect(url_for('main.my_companies'))  # Redirecionar após a criação
    
    # Se o método for GET, exiba o formulário para criar uma nova empresa
    return render_template('create_company.html') 

@main.route('/delete_company', methods=['POST'])
@login_required
def delete_company():
    company_id = request.form.get('id')  # Obtém o ID da empresa do formulário
    delete_leads = request.form.get('delete_leads') == 'true'  # Verifica se leads devem ser excluídos
    company = Company.query.get(company_id)  # Busca a empresa pelo ID

    if not company:
        flash('Empresa não encontrada.', 'error')
        return redirect(url_for('main.admin_page'))  # Redireciona para a página de listagem

    try:
        if delete_leads:
            # Exclui todos os leads associados à empresa
            Leads.query.filter_by(empresa_id=company_id).delete()

        db.session.delete(company)  # Exclui a empresa
        db.session.commit()  # Confirma a exclusão
        flash('Empresa e leads excluídos com sucesso!' if delete_leads else 'Empresa excluída com sucesso!', 'success')
    except Exception as e:
        db.session.rollback()  # Reverte a transação em caso de erro
        flash(f'Ocorreu um erro ao excluir a empresa: {str(e)}', 'error')

    return redirect(url_for('main.admin_page'))  # Redireciona para a página de listagem

@main.route('/my-companies', methods=['GET', 'POST'])
@login_required
def my_companies():
    user_id = current_user.id
    if current_user.role == 'owner' or current_user.role == 'admin':
        companies = Company.query.filter_by(owner_id=user_id).all()
        return render_template('my_companies.html', header_title='Minha Conta', companies=companies)
    flash('Você não tem uma empresa para acessar esta página...')
    return render_template('my_data.html', header_title='Minha Conta', companies=companies)

@main.route('/update_company', methods=['POST'])
@login_required
def update_company():
    if current_user.role != 'admin':
        flash('Você não tem permissões de administrador!')
        return redirect(url_for('main.admin_companies'))

    # Armazenar a URL anterior em uma variável de sessão
    previous_page = request.referrer
    session['previous_page'] = previous_page

    owner_id = request.form.get('owner_id')
    company_id = request.form.get('id')
    nome = request.form.get('nome')
    cnpj = request.form.get('cnpj')
    plan = request.form.get('plan')
    admins = request.form.get('admins')
    collaborator = request.form.get('collaborator')

    company = Company.query.get(company_id)
    
    if company:
        company.owner_id = owner_id 
        company.nome = nome
        company.cnpj = cnpj
        company.plan = plan
        company.admins = admins
        company.collaborator = collaborator
        db.session.commit()
        flash('Empresa atualizada com sucesso!')
    else:
        flash('Empresa não encontrada!')


    # Redirecionar de volta para a página anterior ou para a página padrão
    return redirect(session.pop('previous_page', url_for('admin.admin_page')))