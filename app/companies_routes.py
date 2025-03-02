from flask import Blueprint, render_template, request, Response, redirect, url_for, flash, send_file, session, jsonify
from flask_login import login_user, logout_user, current_user, login_required
import user_agents
from app import db
from app.models import User, Leads, Company
from werkzeug.security import generate_password_hash, check_password_hash
import pandas as pd
from datetime import datetime, timedelta
import secrets
import string

from app.purchases.decorators import require_active_plan, require_lead_limit, require_employee_limit, require_companies_limit
#@require_active_plan
#@require_lead_limit
#@require_employee_limit
#@require_companies_limit


companies = Blueprint('companies', __name__)


def gerar_token_curto(tamanho=8):
    alfabeto = string.ascii_letters + string.digits  # Letras maiúsculas, minúsculas e números
    token = ''.join(secrets.choice(alfabeto) for _ in range(tamanho))
    return token

@companies.route('/', methods=['GET', 'POST'])
@login_required
def companies_page():
    user_id = current_user.id
    if current_user.role == 'owner' or current_user.role == 'admin':
        companies = Company.query.filter_by(owner_id=user_id).all()
        
        # Usando dicionários para armazenar as contagens
        leads_counts = {}
        employees_counts = {}
        
        for company in companies:
            # Contando leads e funcionários para cada empresa
            value_leads = Leads.query.filter_by(empresa_id=company.id).count()
            value_employees = User.query.filter_by(company_work=company.id).count()
            
            # Atribuindo a contagem ao dicionário com o ID da empresa como chave
            leads_counts[company.id] = value_leads
            employees_counts[company.id] = value_employees

        return render_template('companies/my_companies.html', header_title='Minhas Empresas', companies=companies, leads_counts=leads_counts, employees_counts=employees_counts)
    
    flash('Você não tem uma empresa para acessar esta página...')
    return redirect(url_for('user.my_data'))

@companies.route('/edit', methods=['GET', 'POST']) #exemplo de uso /edit?id=123
@login_required
@require_active_plan
def companies_edit():
    user_id = current_user.id
    company_id = request.args.get('id')

    if not company_id:
        flash('ID da empresa não fornecido.')
        return redirect(url_for('user.my_data'))
    
    employees = User.query.filter_by(company_work=company_id).all()
    print(employees, company_id)

    for employee in employees:
        print(employee.id, employee.name)

    # Buscar a empresa correspondente ao ID na query string
    company = Company.query.filter_by(id=company_id, owner_id=user_id).first()

    if current_user.role == "admin":
        company = Company.query.filter_by(id=company_id).first()

    if not company:
        flash('Você não tem permissão para editar esta empresa.')
        return redirect(url_for('user.my_data'))

    if request.method == 'POST':
        company.nome = request.form.get('name')
        company.plan = request.form.get('plan')  # Supondo que este campo seja editável
        company.admins = request.form.get('admins')  # Supondo que este campo seja editável
        company.cnpj = request.form.get('cnpj')
        company.collaborator = request.form.get('collaborator')
        company.invite = request.form.get('invite')
        company.bt_type_product = request.form.get('btprod')
        company.bt_action = request.form.get('btaction')

        db.session.commit()
        flash('Empresa atualizada com sucesso!')
        return redirect(url_for('companies.companies_page'))  # Redirecionar após a atualização

    # Renderizar o formulário de edição com os dados atuais da empresa
    return render_template('companies/user_companies/edit_company.html', header_title='Editar Empresa', company=company, employees=employees)

@companies.route('/remove_employee', methods=['POST', 'GET'])
@login_required
@require_active_plan
def companies_remove_employee():
    user_id = current_user.id
    employee_id = request.args.get('id')
    
    # Validação do ID do funcionário
    if not employee_id:
        flash('ID do funcionário não fornecido.')
        return redirect(url_for('user.my_data'))

    # Busca o funcionário
    employee = User.query.filter_by(id=employee_id).first()

    if not employee:
        flash('Funcionário não encontrado.')
        return redirect(url_for('user.my_data'))

    # Verifica se o usuário é o dono da empresa do funcionário
    company = Company.query.filter_by(id=employee.company_work, owner_id=user_id).first()

    if not company:
        flash('Você não tem permissão para remover este funcionário.')
        return redirect(url_for('user.my_data'))

    # Definir company_work do funcionário como null
    employee.company_work = None

    # Commit da alteração
    db.session.commit()

    flash('Funcionário removido da empresa com sucesso.')
    return redirect(url_for('companies.companies_page'))  # Redireciona para a página de empresas

@companies.route('/create_company', methods=['GET', 'POST'])
@login_required
@require_active_plan
@require_companies_limit
def create_company():
    # Se o usuário não for owner ou admin, redirecione
    if current_user.role not in ['owner', 'admin']:
        flash('Você não tem permissão para acessar esta página!', 'danger')
        return redirect(url_for('user.my_data'))
    
    if request.method == 'POST':
        # Obtenha os dados do formulário
        nome = request.form['nome']
        cnpj = request.form['cnpj']
        owner_id = request.form.get('owner_id', current_user.id)  # Certifique-se de que o campo está sendo enviado
        plan = request.form.get('plan', 1)  # Default para 1 se não for enviado
        admins = request.form.get('admins', '')  # Default para string vazia se não for enviado
        collaborator = request.form.get('collaborator', '')  # Default para string vazia se não for enviado
        invite = gerar_token_curto()
        token_api_generated = gerar_token_curto(18)

        # Criação da nova empresa
        new_company = Company(
            nome=nome,
            cnpj=cnpj,
            owner_id=owner_id,
            plan=plan,
            admins=admins,
            collaborator=collaborator,
            invite=invite,
            token_api=token_api_generated
        )

        # Adiciona a nova empresa ao banco de dados
        db.session.add(new_company)
        db.session.commit()

        flash('Empresa criada com sucesso!', 'success')

        # Redireciona após a criação
        return redirect(request.referrer or url_for('main.my_companies'))  # Use o referrer se disponível

    # Se o método for GET, exiba o formulário para criar uma nova empresa
    return render_template('companies/services/create_company.html')
