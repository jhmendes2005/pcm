from flask import Blueprint, render_template, request, Response, redirect, url_for, flash, send_file, session, jsonify
from flask_login import login_user, logout_user, current_user, login_required
import user_agents
from app import db
from app.models import User, Leads, Company
from app.purchases.plans import PlanManager
from werkzeug.security import generate_password_hash, check_password_hash
import pandas as pd
from datetime import datetime, timedelta
import secrets
import string

admin = Blueprint('admin', __name__)

@admin.before_request
def update_last_active():
    if current_user.is_authenticated:
        current_user.last_active = datetime.utcnow()
        db.session.commit()

def check_inactivity():
    timeout_duration = timedelta(minutes=15)  # Desconectar após 15 minutos de inatividade
    for user in User.query.filter_by(is_active=True).all():
        if datetime.utcnow() - user.last_active > timeout_duration:
            user.is_active = False
            db.session.commit()

def gerar_token_curto(tamanho=8):
    alfabeto = string.ascii_letters + string.digits  # Letras maiúsculas, minúsculas e números
    token = ''.join(secrets.choice(alfabeto) for _ in range(tamanho))
    return token

@admin.route('/', methods=['GET', 'POST'])
@login_required
def admin_page():
    if current_user.role != 'admin':
        flash('Você não tem permissões de administrador!')
        return redirect(url_for('user.my_data'))
    
    user = User.query.all()
    companies = Company.query.all()
    plans = PlanManager.list_plans()

    counter_user = 0
    for users in user:
        counter_user += 1
    
    title = f'Administrador - {current_user.name}'
    return render_template('admin/admin.html', header_title=title, user=user, companies=companies, plans=plans)

@admin.route('/companies-admin', methods=['GET', 'POST'])
@login_required
def companies_page_admin():
    if current_user.role != 'admin':
        flash('Você não tem permissões de administrador!')
        return redirect(url_for('user.my_data'))
    
    companies = Company.query.all()

    title = f'Administrador - {current_user.name}'
    return render_template('admin/companies/companies_admin.html', header_title=title, companies=companies)

@admin.route('/plans-admin', methods=['GET', 'POST'])
@login_required
def plans_page_admin():
    if current_user.role != 'admin':
        flash('Você não tem permissões de administrador!')
        return redirect(url_for('user.my_data'))
    
    plans = PlanManager.list_plans()

    title = f'Administrador - {current_user.name}'
    return render_template('admin/plans/plans_admin.html', header_title=title, plans=plans)

@admin.route('/users-admin', methods=['GET', 'POST'])
@login_required
def users_page_admin():
    if current_user.role != 'admin':
        flash('Você não tem permissões de administrador!')
        return redirect(url_for('user.my_data'))
    users = User.query.all()
    title = f'Administrador - {current_user.name}'
    return render_template('admin/users/users_admin.html', header_title=title, users=users)

@admin.route('/delete_user', methods=['POST'])
@login_required
def delete_user():
    # Obtém o ID do usuário do formulário
    user_id = request.form.get('id')
    
    # Tente encontrar o usuário pelo ID
    user = User.query.get(user_id)
    if user:
        try:
            db.session.delete(user)
            db.session.commit()
            flash('Usuário deletado com sucesso!', 'success')
        except Exception as e:
            flash(f'Erro ao deletar usuário: {str(e)}', 'error')
    else:
        flash('Usuário não encontrado.', 'error')
    
    return redirect(url_for('admin.admin_page'))


@admin.route('/update-account', methods=['POST'])
@login_required
def update_user():
    previous_page = request.referrer
    session['previous_page'] = previous_page
    
    # Verifica se o usuário é admin
    if current_user.role != 'admin':
        flash('Acesso não autorizado!', 'danger')
        return redirect(url_for('user.my_data'))

    user_id = request.form.get('id')

    # Verifica se o ID do usuário é válido
    if not user_id.isnumeric():
        flash('ID de usuário inválido!', 'danger')
        return redirect(url_for('user.my_data'))

    user_to_update = User.query.get(user_id)

    if not user_to_update:
        flash('Usuário não encontrado!', 'danger')
        return redirect(url_for('user.my_data'))

    # Atualiza o nome do usuário
    user_to_update.name = request.form.get('name', user_to_update.name)

    # Atualiza o e-mail do usuário
    user_to_update.email = request.form.get('email', user_to_update.email)

    # Atualiza a função do usuário
    user_to_update.role = request.form.get('role', user_to_update.role)

    # Atualiza a nova senha apenas se fornecida
    new_password = request.form.get('password')
    if new_password:
        user_to_update.password = generate_password_hash(new_password)

    try:
        db.session.commit()
        flash('Dados do usuário atualizados com sucesso!', 'success')
    except Exception as e:
        db.session.rollback()  # Reverte a sessão em caso de erro
        flash('Erro ao atualizar dados do usuário: {}'.format(str(e)), 'danger')

    return redirect(session.pop('previous_page', url_for('admin.admin_page')))



@admin.route('/edit-user/<int:user_id>', methods=['GET'])
@login_required
def edit_user(user_id):
    user = User.query.get(user_id)  # Altere para a sua lógica de busca do usuário
    if user:
        return jsonify({
            'id': user.id,
            'name': user.name,
            'email': user.email,
            'role': user.role
        })
    return jsonify({'error': 'User not found'}), 404
