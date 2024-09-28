from app import create_app, db
from flask import render_template, request, Response, redirect, url_for, flash, send_file
from flask_login import login_user, logout_user, current_user, login_required
from app.models import User, Leads, Company
from werkzeug.security import generate_password_hash, check_password_hash
import pandas as pd
from datetime import datetime, timedelta
import json

app = create_app()

@app.route('/')
def home():
    return render_template('index.html')

@app.before_request
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

@app.route('/login', methods=['GET', 'POST'])
def login():
    if current_user.is_authenticated:
        flash('Você já está logado!!')
        return redirect(url_for('home'))
    
    if request.method == 'POST':
        email = request.form['email']
        pwd = request.form['password']
        user = User.query.filter_by(email=email).first()

        if not user or not user.verify_password(pwd):
            flash('E-mail ou senha incorretos.')
            return redirect(url_for('login'))

        user.is_active = True
        user.last_active = datetime.utcnow()  # Atualizar no login
        db.session.commit()
        login_user(user)
        return redirect(url_for('home'))

    return render_template('login.html', header_title='Login')


@app.route('/logout')
@login_required
def logout():
    logout_user()
    flash('Você foi deslogado!')
    return redirect(url_for('login'))


@app.route('/register', methods=['GET', 'POST'])
def register():
    if current_user.is_authenticated:
        flash('Você já está logado!!')
        return redirect(url_for('home'))

    if request.method == 'POST':
        name = request.form['name']
        email = request.form['email']
        pwd = request.form['password']
        invite_id = request.form.get('invite_id')  # Pega o invite_id do formulário, pode ser None

        # Verifica se o e-mail já está registrado
        existing_user = User.query.filter_by(email=email).first()
        if existing_user:
            flash('E-mail já está em uso.')
            return redirect(url_for('register'))

        # Cria a conta com base no invite_id
        if email and pwd:
            if invite_id:  # Se o invite_id foi fornecido
                # Valida se existe uma empresa com o invite_id fornecido
                company = Company.query.filter_by(invite=invite_id).first()
                if not company:
                    flash('Invite ID inválido.')
                    return redirect(url_for('register'))
                
                # Associa o usuário à empresa e define o cargo como 'employee'
                user = User(name=name, email=email, password=pwd, role='employee', company_work=company.id)
                flash(f'Você foi adicionado à empresa {company.nome}.')
            else:
                # Se não foi fornecido invite_id, o usuário é criado sem vínculo de empresa
                user = User(name=name, email=email, password=pwd, role='employee')

            db.session.add(user)
            db.session.commit()

            flash('Registro realizado com sucesso! Você pode fazer login agora.')
            return redirect(url_for('login'))

    return render_template('register.html', header_title='Registro')


@app.route('/create_user', methods=['POST'])
def create_user():
    if request.method == 'POST':
        name = request.form['name']
        email = request.form['email']
        pwd = request.form['password']

        # Verifica se o e-mail já está em uso
        existing_user = User.query.filter_by(email=email).first()
        if existing_user:
            flash("E-mail já está em uso.", "error")
            return redirect(url_for('admin_page'))  # Substitua pelo nome da sua rota de formulário

        # Criação do novo usuário
        try:
            user = User(name=name, email=email, password=generate_password_hash(pwd))
            db.session.add(user)
            db.session.commit()
            flash('Conta criada com sucesso!', 'success')
            return redirect(url_for('admin_page'))  # Substitua pelo nome da sua rota de formulário
        except Exception as e:
            flash("Erro ao criar usuário: " + str(e), "error")
            return redirect(url_for('admin_page'))  # Substitua pelo nome da sua rota de formulário

@app.route('/delete_user', methods=['POST'])
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
    
    return redirect(url_for('admin_page'))


@app.route('/forgot-password', methods=['GET', 'POST'])
def forgot_password():
    if request.method == 'POST':
        email = request.form['email']
        user = User.query.filter_by(email=email).first()

        if user:
            # Aqui, você pode armazenar o código em algum lugar se precisar
            # Neste exemplo, estamos apenas permitindo que o código seja "123"
            flash('Digite o código de redefinição para continuar.')
            return redirect(url_for('reset_password', email=email))
        else:
            flash('E-mail não encontrado.')

    return render_template('forgot_password.html', header_title='Esqueci a Senha')

@app.route('/reset-password', methods=['GET', 'POST'])
def reset_password():
    email = request.args.get('email')

    if request.method == 'POST':
        code = request.form['code']
        new_password = request.form['password']

        if code == '123':  # Verifica se o código inserido é o esperado
            user = User.query.filter_by(email=email).first()
            if user:
                user.password = generate_password_hash(new_password)  # Use sua função de hash apropriada
                db.session.commit()
                flash('Sua senha foi redefinida com sucesso! Você pode fazer login agora.')
                return redirect(url_for('login'))
            else:
                flash('E-mail não encontrado.')
        else:
            flash('Código inválido. Tente novamente.')

    return render_template('reset_password.html', header_title='Redefinir Senha', email=email)

@app.route('/update-account', methods=['POST'])
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
        return redirect(url_for('my_account'))

@app.route('/update_user', methods=['POST'])
@login_required
def update_user():
    if current_user.role != 'admin':
        flash('Você não tem permissões de administrador!')
        return redirect(url_for('home'))

    user_id = request.form.get('id')
    user = User.query.get(user_id)
    
    if user:
        user.name = request.form.get('name')
        user.email = request.form.get('email')
        user.role = request.form.get('role')
        db.session.commit()
        flash('Informações do usuário atualizadas com sucesso!')
    else:
        flash('Usuário não encontrado.')
    
    return redirect(url_for('admin_page'))

@app.route('/create_company', methods=['GET', 'POST'])
def create_company():
    if request.method == 'POST':
        # Obtenha os dados do formulário
        nome = request.form['nome']
        cnpj = request.form['cnpj']
        owner_id = request.form['owner_id']  # Certifique-se de que isso está sendo enviado no formulário
        plan = request.form['plan']  # Certifique-se de que isso está sendo enviado no formulário
        admins = request.form.get('admins', '')  # Se não houver admins, armazene uma string vazia
        collaborator = request.form.get('collaborator', '')  # Se não houver colaboradores, armazene uma string vazia

        # Criação da nova empresa
        new_company = Company(
            nome=nome,
            cnpj=cnpj,
            owner_id=owner_id,
            plan=plan,
            admins=admins,
            collaborator=collaborator
        )
        
        # Adiciona a nova empresa ao banco de dados
        db.session.add(new_company)
        db.session.commit()
        
        flash('Empresa criada com sucesso!', 'success')
        return redirect(url_for('admin_page'))  # Redirecionar após a criação

    # Se o método for GET, exiba o formulário para criar uma nova empresa
    return render_template('create_company.html') 

@app.route('/delete_company', methods=['POST'])
def delete_company():
    company_id = request.form.get('id')  # Obtém o ID da empresa do formulário
    delete_leads = request.form.get('delete_leads') == 'true'  # Verifica se leads devem ser excluídos
    company = Company.query.get(company_id)  # Busca a empresa pelo ID

    if not company:
        flash('Empresa não encontrada.', 'error')
        return redirect(url_for('admin_page'))  # Redireciona para a página de listagem

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

    return redirect(url_for('admin_page'))  # Redireciona para a página de listagem



@app.route('/admin-page', methods=['GET', 'POST'])
@login_required
def admin_page():
    if current_user.role != 'admin':
        flash('Você não tem permissões de administrador!')
        return redirect(url_for('home'))
    
    # Recuperar todos os usuários
    users = User.query.all()  # Obtém todos os usuários do banco de dados

    companies = Company.query.all()

    title = f'Administrador - {current_user.name}'
    return render_template('admin.html', header_title=title, users=users, companies=companies)

@app.route('/my-account', methods=['GET', 'POST'])
@login_required
def my_account():
    user_id = current_user.id
    if current_user.role == 'owner' or current_user.role == 'admin':
        companies = Company.query.filter_by(owner_id=user_id).all()
        return render_template('my_account.html', header_title='Minha Conta', companies=companies)
    
    companies = None
    return render_template('my_account.html', header_title='Minha Conta', companies=companies)

@app.route('/about')
def about():
    return render_template('about.html', header_title='Sobre Nós')

@app.route('/update_company', methods=['POST'])
@login_required
def update_company():
    if current_user.role != 'admin':
        flash('Você não tem permissões de administrador!')
        return redirect(url_for('admin_companies'))

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

    return redirect(url_for('admin_page'))

@app.route('/leads', methods=['GET', 'POST'])
@login_required
def leads():
    user_id = current_user.id
    
    # Obter a lista de empresas do usuário
    companies = Company.query.filter_by(owner_id=user_id).all()
    
    if not companies:
        flash('Você não tem uma empresa para acessar leads!')
        return redirect(url_for('home'))
    
    # Obter a empresa selecionada pelo usuário
    selected_company_id = request.args.get('company_id', companies[0].id)  # Se não houver, seleciona a primeira empresa
    selected_company = Company.query.get(selected_company_id)

    if not selected_company:
        flash('Empresa selecionada não encontrada!')
        return redirect(url_for('home'))

    # Obter o status do filtro, se houver
    status_filter = request.args.get('status', None)

    # Obter a quantidade de leads a ser exibida, padrão 20, máximo 100
    leads_limit = request.args.get('leads_limit', 20, type=int)
    leads_limit = min(leads_limit, 100)  # Limita a 100

    # Filtrar leads por status
    if status_filter == "all" or status_filter is None:
        all_leads = Leads.query.filter_by(empresa_id=selected_company.id).limit(leads_limit).all()
    else:
        all_leads = Leads.query.filter_by(empresa_id=selected_company.id, status=status_filter).limit(leads_limit).all()
        
    return render_template('leads.html', header_title='Lista de Leads', leads=all_leads, company=selected_company, companies=companies, selected_company=selected_company, leads_limit=leads_limit)

@app.route('/add_lead', methods=['GET', 'POST'])
@login_required
def add_lead():
    user_id = current_user.id

    # Obter a lista de empresas do usuário
    companies = Company.query.filter_by(owner_id=user_id).all()

    if request.method == 'POST':
        # Captura dos dados do formulário
        empresa_id = request.form['empresa_id']
        nome = request.form['nome']
        email = request.form['email']
        telefone = request.form['telefone']
        veiculo = request.form['veiculo']

        # Criação do novo lead
        new_lead = Leads(
            nome=nome,
            email=email,
            telefone=telefone,
            veiculo=veiculo,
            status='pending',  # Novo lead começa com status 'pending'
            empresa_id=empresa_id
        )

        db.session.add(new_lead)
        db.session.commit()
        flash('Lead adicionado com sucesso!')
        return redirect(url_for('leads'))

    return render_template('add_lead.html', header_title='Adicionar Lead', companies=companies)

@app.route('/export_leads', methods=['GET'])
@login_required
def export_leads():
    user_id = current_user.id
    selected_company_id = request.args.get('company_id')

    # Obter os leads da empresa selecionada
    leads = Leads.query.filter_by(empresa_id=selected_company_id).all()
    
    # Definir o nome do arquivo CSV
    csv_filename = f'leads_empresa_{selected_company_id}.csv'

    # Criar a resposta CSV
    def generate():
        yield 'ID,Nome,Telefone,Status,Comentário,Veículo,Criado em,Atualizado em\n'  # Cabeçalho
        for lead in leads:
            yield f"{lead.id},{lead.nome},{lead.telefone},{lead.status},{lead.comentario},{lead.veiculo},{lead.created_at},{lead.updated_at}\n"

    return Response(generate(), mimetype='text/csv', headers={"Content-Disposition": f"attachment;filename={csv_filename}"})
    
@app.route('/import_leads', methods=['GET', 'POST'])
@login_required
def import_leads():
    user_id = current_user.id

    # Obter as empresas do usuário
    empresas = Company.query.filter_by(owner_id=user_id).all()

    if request.method == 'POST':
        if 'file' not in request.files:
            flash('Nenhum arquivo foi enviado.')
            return redirect(url_for('import_leads'))

        file = request.files['file']

        if file.filename.endswith('.xlsx') or file.filename.endswith('.csv'):
            try:
                if file.filename.endswith('.xlsx'):
                    df = pd.read_excel(file)
                else:
                    df = pd.read_csv(file)

                empresa_id = request.form['empresa_id']  # ID da empresa selecionada

                # Validar e adicionar os leads
                for index, row in df.iterrows():
                    if pd.isna(row['Nome']) or pd.isna(row['Telefone']):
                        flash('Nome e Telefone são obrigatórios para todos os leads.')
                        return redirect(url_for('import_leads'))

                    # Definir valores padrão para campos que podem estar ausentes
                    status = row.get('Status')
                    if pd.isna(status):  # Se status é NaN, use o valor padrão
                        status = 'pending'  # Defina o status padrão

                    # Verifique e trate outros campos para evitar NaN
                    comentario = row.get('Comentário', '')
                    if pd.isna(comentario):
                        comentario = ''  # Use string vazia se NaN

                    veiculo = row.get('Veículo', '')
                    if pd.isna(veiculo):
                        veiculo = ''  # Use string vazia se NaN

                    created_at = row.get('Criado em')
                    if pd.isna(created_at):
                        created_at = datetime.utcnow()  # Use a data atual se não estiver presente

                    updated_at = row.get('Atualizado em')
                    if pd.isna(updated_at):
                        updated_at = datetime.utcnow()  # Use a data atual se não estiver presente

                    # Criação do lead
                    lead = Leads(
                        usuario_id=user_id,
                        empresa_id=empresa_id,  # ID da empresa selecionada
                        nome=row['Nome'],
                        telefone=row['Telefone'],
                        status=status,
                        comentario=comentario,
                        veiculo=veiculo,
                        created_at=created_at,
                        updated_at=updated_at
                    )

                    db.session.add(lead)

                db.session.commit()
                flash('Leads importados com sucesso!')
            except Exception as e:
                db.session.rollback()
                flash(f'Ocorreu um erro ao importar os leads: {e}')
        else:
            flash('Formato de arquivo inválido. Por favor, envie um arquivo .xlsx ou .csv.')

        return redirect(url_for('import_leads'))

    return render_template('import_leads.html', empresas=empresas)

@app.route('/update_lead', methods=['POST'])
def update_lead():
    lead_id = request.form['lead_id']
    nome = request.form['lead_nome']
    telefone = request.form['lead_telefone']
    status = request.form['lead_status']
    comentario = request.form['lead_comentario']
    veiculo = request.form['lead_veiculo']

    # Verifica se o lead existe
    lead = Leads.query.get(lead_id)
    if lead:
        # Atualiza as informações do lead
        lead.nome = nome
        lead.telefone = telefone
        lead.status = status
        lead.comentario = comentario
        lead.veiculo = veiculo
        lead.updated_at = datetime.utcnow()  # Atualiza a data de modificação

        # Salva as alterações no banco de dados
        db.session.commit()
        flash('Lead atualizado com sucesso!', 'success')
    else:
        flash('Lead não encontrado.', 'error')

    return redirect(url_for('leads', company_id=lead.empresa_id))

@app.route('/calls', methods=['GET', 'POST'])
@login_required
def calls():
    user_id = current_user.id
    companies = []
    selected_company = None

    # Verificar se o usuário é um 'employee'
    if current_user.role == 'owner' or current_user.role == 'admin':
        flash('Não recomendamos utilizar esta página com este tipo de conta. Favor, utilize uma conta "Colaborador".')
    if current_user.role == 'employee':
        company_work_id = current_user.company_work
        if company_work_id:
            selected_company = Company.query.get(company_work_id)
            if not selected_company:
                flash('A empresa associada não foi encontrada!')
                return redirect(url_for('home'))
        else:
            flash('Você não está associado a nenhuma empresa!')
            return redirect(url_for('home'))
    else:
        companies = Company.query.filter_by(owner_id=user_id).all()

        if not companies:
            flash('Você não tem uma empresa para acessar leads!')
            return redirect(url_for('home'))

        selected_company_id = request.args.get('company_id', companies[0].id)
        selected_company = Company.query.get(selected_company_id)

        if not selected_company:
            flash('Empresa selecionada não encontrada!')
            return redirect(url_for('home'))

    # Verificar se o usuário já tem um lead 'in_progress'
    user_lead = Leads.query.filter_by(usuario_id=user_id, status='in_progress').first()

    if not user_lead:
        # Buscar um lead pendente
        user_lead = Leads.query.filter_by(empresa_id=selected_company.id, status='pending').first()

        if user_lead:
            # Atribuir lead ao usuário e atualizar status para 'in_progress'
            user_lead.usuario_id = user_id
            user_lead.status = 'in_progress'
            user_lead.updated_at = datetime.utcnow()
            db.session.commit()

    # Atualizar ou finalizar o lead com as informações enviadas via POST
    if request.method == 'POST':
        action = request.form.get('action')
        if action == 'finalize':
            user_lead.nome = request.form['nome']
            user_lead.telefone = request.form['telefone']
            user_lead.veiculo = request.form['veiculo']
            user_lead.comentario = request.form['comentario']
            user_lead.status = 'completed'
            db.session.commit()
            flash('Lead finalizado com sucesso!')

        elif action == 'cancel':
            user_lead.status = 'cancelled'
            user_lead.comentario = request.form['comentario']
            db.session.commit()
            flash('Lead cancelado com sucesso!')

        elif action == 'move_to_end':
            # Move o lead para o final da fila
            last_id = db.session.query(db.func.max(Leads.id)).scalar()
            user_lead.id = last_id + 1
            user_lead.status = 'pending'
            db.session.commit()
            flash('Lead movido para o final da fila!')

        return redirect(url_for('calls'))


    return render_template('calls.html', 
                           header_title='Lista de Leads', 
                           company=selected_company, 
                           companies=companies, 
                           selected_company=selected_company,
                           user_lead=user_lead)



if __name__ == '__main__':
    app.run(debug=True)
