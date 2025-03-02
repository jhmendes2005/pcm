from flask import Blueprint, render_template, request, Response, redirect, url_for, flash, send_file, session
from flask_login import login_user, logout_user, current_user, login_required
from app.email_service import send_email
import user_agents
from app import db
from app.models import User, Leads, Company
from werkzeug.security import generate_password_hash, check_password_hash
import pandas as pd
from datetime import datetime, timedelta
import secrets
import string
from app.purchases.decorators import require_active_plan, require_lead_limit, require_employee_limit
#@require_active_plan
#@require_lead_limit
#@require_employee_limit



user = Blueprint('user', __name__)

def gerar_token_curto(tamanho=8):
    alfabeto = string.ascii_letters + string.digits  # Letras maiúsculas, minúsculas e números
    token = ''.join(secrets.choice(alfabeto) for _ in range(tamanho))
    return token

@user.route('/')
@login_required
def home():
    return redirect(url_for('user.my_data'))

@user.route('/my-account', methods=['GET', 'POST'])
@login_required
def my_data():
    user_id = current_user.id
    if current_user.role == 'owner' or current_user.role == 'admin':
        companies = Company.query.filter_by(owner_id=user_id).all()
        return render_template('user/my_data.html', header_title='Minha Conta', companies=companies)
    
    companies = None
    return render_template('user/my_data.html', header_title='Minha Conta', companies=companies)

@user.route('/login', methods=['GET', 'POST'])
def login():
    if current_user.is_authenticated:
        flash('Você já está logado!!')
        return redirect(url_for('home.main'))

    if request.method == 'POST':
        email = request.form['email']
        pwd = request.form['password']
        user = User.query.filter_by(email=email).first()

        # Verifica se o usuário existe e se a senha está correta
        if not user:
            flash('E-mail ou senha incorretos.')
            return redirect(url_for('user.login'))

        if not user.verify_password(pwd):
            flash('E-mail ou senha incorretos.')
            return redirect(url_for('user.login'))

        # Verifica se a conta foi confirmada
        if not user.is_confirmed:
            flash('Sua conta não foi confirmada. Por favor, verifique seu e-mail para confirmar a conta.')
            return redirect(url_for('user.login'))

        # Se tudo estiver certo, faz o login
        user.is_active = True
        user.last_active = datetime.utcnow()  # Atualiza a última atividade no login
        db.session.commit()
        login_user(user)
        return redirect(url_for('home.main'))

    return render_template('user/services/login.html', header_title='Login')

@user.route('/logout')
@login_required
def logout():
    logout_user()
    flash('Você foi deslogado!')
    return redirect(url_for('user.login'))

@user.route('/register', methods=['GET', 'POST'])
def register():
    if current_user.is_authenticated:
        flash('Você já está logado!!')
        return redirect(url_for('user.my_data'))

    if request.method == 'POST':
        name = request.form['name']
        email = request.form['email']
        pwd = request.form['password']
        invite_id = request.form.get('invite_id')

        # Verifica se o e-mail já está registrado
        existing_user = User.query.filter_by(email=email).first()
        if existing_user:
            flash('E-mail já está em uso.')
            return redirect(url_for('user.register'))

        # Cria a conta com base no invite_id
        user = User(name=name, email=email, password=pwd)
        
        if invite_id:
            company = Company.query.filter_by(invite=invite_id).first()
            if not company:
                flash('Invite ID inválido.')
                return redirect(url_for('user.register'))
            user.company_work = company.id  # Associa o usuário à empresa

        # Gera um token de confirmação
        token = user.generate_confirmation_token()
        user.confirmation_token = token  # Armazena o token no banco de dados

        db.session.add(user)
        db.session.commit()

        # Envia o e-mail de confirmação
        send_email(
            subject='Confirmação de Conta PCM',
            recipients=[user.email],  # Envia para o e-mail do usuário
            body='Por favor, confirme sua conta clicando no link abaixo.',
            html_body=f'<p>Por favor, confirme sua conta clicando no link abaixo:</p>'
                       f'<p><a href="{url_for("user.confirm_email", token=token, _external=True)}">Confirmar conta</a></p>'
        )

        flash('Registro realizado com sucesso! Um e-mail de confirmação foi enviado para você.')
        return redirect(url_for('user.login'))

    return render_template('user/services/register.html', header_title='Registro')

@user.route('/confirm/<token>')
def confirm_email(token):
    user = User.query.filter_by(confirmation_token=token).first()
    print(user)

    if user is None:
        flash("Token inválido ou expirado.")
        return redirect(url_for('user.register'))

    # Confirma o e-mail do usuário
    if user.confirm(token):
        db.session.commit()
        flash("Conta confirmada com sucesso! Você já pode fazer login.")
        return redirect(url_for('user.login'))
    else:
        flash("Ocorreu um erro ao confirmar a conta.")
        return redirect(url_for('user.register'))
    
@user.route('/resend_confirmation', methods=['POST'])
def resend_confirmation():
    if current_user.is_authenticated:
        flash('Você já está logado!!')
        return redirect(url_for('user.my_data'))

    email = request.form['email']
    user = User.query.filter_by(email=email).first()

    if user and not user.is_confirmed:
        # Gera um novo token de confirmação
        token = user.generate_confirmation_token()
        user.confirmation_token = token  # Armazena o token no banco de dados
        db.session.commit()

        # Envia o e-mail de confirmação novamente
        send_email(
            subject='Confirmação de Conta PCM',
            recipients=[user.email],
            body='Por favor, confirme sua conta clicando no link abaixo.',
            html_body=f'<p>Por favor, confirme sua conta clicando no link abaixo:</p>'
                       f'<p><a href="{url_for("user.confirm_email", token=token, _external=True)}">Confirmar conta</a></p>'
        )

        flash('Um novo e-mail de confirmação foi enviado para você.')
    else:
        flash('E-mail não encontrado ou conta já confirmada.')

    return redirect(url_for('user.login'))


@user.route('/create_user', methods=['POST'])
@login_required
def create_user():
    previous_page = request.referrer
    session['previous_page'] = previous_page
    if request.method == 'POST':
        name = request.form['name']
        email = request.form['email']
        pwd = request.form['password']

        # Verifica se o e-mail já está em uso
        existing_user = User.query.filter_by(email=email).first()
        if existing_user:
            flash("E-mail já está em uso.", "error")
            return redirect(session.pop('previous_page', url_for('admin.admin_page')))

        # Criação do novo usuário
        try:
            user = User(name=name, email=email, password=generate_password_hash(pwd))
            db.session.add(user)
            db.session.commit()
            flash('Conta criada com sucesso!', 'success')
            return redirect(session.pop('previous_page', url_for('admin.admin_page')))
        except Exception as e:
            flash("Erro ao criar usuário: " + str(e), "error")
            return redirect(session.pop('previous_page', url_for('admin.admin_page')))
        
@user.route('/forgot-password', methods=['GET', 'POST'])
def forgot_password():
    if request.method == 'POST':
        email = request.form['email']
        user = User.query.filter_by(email=email).first()

        if user:
            # Gera um código de redefinição de senha
            reset_code = gerar_token_curto()  # Gera um código único
            user.reset_code = reset_code  # Armazena o código no banco de dados
            db.session.commit()

            # Gera o link para redefinir a senha
            reset_link = url_for('user.reset_password', email=email, code=reset_code, _external=True)

            # Envia o e-mail com o código de redefinição
            send_email(
                subject='Redefinição de Senha',
                recipients=[user.email],
                body='Use o seguinte código para redefinir sua senha: {}'.format(reset_code),
                html_body=f'<p>Use o seguinte código para redefinir sua senha: <strong>{reset_code}</strong></p>'
                            f'<p><a href="{reset_link}">ALTERAR SENHA</a></p>'  # Link atualizado
            )
            flash('Um e-mail com o código de redefinição foi enviado para você.')
            return redirect(url_for('user.login'))
        else:
            flash('E-mail não encontrado.')
    return render_template('user/services/forgot_password.html', header_title='Esqueci a Senha')


@user.route('/reset-password', methods=['GET', 'POST'])  # Exemplo de uso: /reset-password?email=seuemail@example.com
def reset_password():
    email = request.args.get('email')
    code_string = request.args.get('code')

    if request.method == 'POST':
        code = request.form['code']  # Código de verificação inserido pelo usuário
        new_password = request.form['password']  # Nova senha inserida pelo usuário

        user = User.query.filter_by(email=email).first()  # Busca o usuário

        if user:
            if user.reset_code == code:  # Verifica se o código inserido é o mesmo que o armazenado
                user.password = generate_password_hash(new_password)  # Redefine a senha
                user.reset_code = None  # Limpa o código após uso
                db.session.commit()  # Salva as alterações
                flash('Sua senha foi redefinida com sucesso! Você pode fazer login agora.')

                # Captura a data, hora e informações do dispositivo
                now = datetime.now()
                date_time = now.strftime("%d/%m/%Y %H:%M:%S")
                user_agent = request.user_agent.string

                # Envio de e-mail de confirmação
                send_email(
                    subject='Confirmação de Alteração de Senha',
                    recipients=[user.email],
                    body='Sua senha foi alterada com sucesso.',
                    html_body=(
                        f'<p>Olá {user.name},</p>'
                        '<p>Informamos que sua senha foi alterada com sucesso.</p>'
                        f'<p>Data e Hora da Alteração: {date_time}</p>'
                        f'<p>Dispositivo Utilizado: {user_agent}</p>'
                        '<p>Se você não solicitou essa alteração, entre em contato com o suporte imediatamente.</p>'
                        '<p>Atenciosamente,<br>Equipe de Suporte</p>'
                    )
                )
                return redirect(url_for('user.login'))
            else:
                flash('Código inválido. Tente novamente.')
        else:
            flash('E-mail não encontrado.')

    return render_template('user/services/reset_password.html', header_title='Redefinir Senha', email=email, code_string=code_string)

@user.route('/update-account', methods=['POST'])
@login_required
def update_account():
    if request.method == 'POST':
        # Atualiza apenas o nome do usuário
        current_user.name = request.form['name']
        # Atualiza a senha apenas se o campo não estiver vazio
        new_password = request.form.get('password')
        if new_password:
            current_user.password = generate_password_hash(new_password)  # Usa sua função de hash apropriada

        db.session.commit()
        flash('Dados atualizados com sucesso!')
        return redirect(url_for('user.my_data'))