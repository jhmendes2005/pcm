from flask import Blueprint, render_template, request, Response, redirect, url_for, flash, send_file, session
from flask_login import login_user, logout_user, current_user, login_required
from app.email_service import send_email
import user_agents
from app import db
from app.models import User, Leads, Company, LeadComment
from werkzeug.security import generate_password_hash, check_password_hash
import pandas as pd
from datetime import datetime, timedelta
import secrets
import string
import io
import csv
from flask import flash, redirect, url_for, request
from app.purchases.decorators import require_active_plan, require_lead_limit, require_employee_limit
from app.purchases.plans import PlanManager
import io
import csv
from flask import Response, request, redirect, url_for
from flask_login import login_required, current_user
from app.models import Leads
from app.email_service import send_email

leads = Blueprint('leads', __name__)

def gerar_token_curto(tamanho=8):
    alfabeto = string.ascii_letters + string.digits  # Letras maiúsculas, minúsculas e números
    token = ''.join(secrets.choice(alfabeto) for _ in range(tamanho))
    return token

@leads.route('/', methods=['GET', 'POST'])
@login_required
def leads_main():
    user_id = current_user.id
    user_agent = request.headers.get('User-Agent')
    ua = user_agents.parse(user_agent)
    is_mobile = ua.is_mobile 

    # Obter a lista de empresas do usuário
    companies = Company.query.filter_by(owner_id=user_id).all()

    if not companies:
        flash('Você não tem uma empresa para acessar leads!')
        return redirect(url_for('user.my_data'))

    # Obter a empresa selecionada pelo usuário
    selected_company_id = request.args.get('company_id', companies[0].id)  
    selected_company = Company.query.get(selected_company_id)

    if not selected_company:
        flash('Empresa selecionada não encontrada!')
        return redirect(url_for('user.my_data'))

    # Obter os filtros
    status_filter = request.args.get('status')
    search_term = request.args.get('search', '').strip()
    data_inicial = request.args.get('data_inicial')
    data_final = request.args.get('data_final')

    # Obter o limite de leads
    leads_limit = request.args.get('leads_limit', 20, type=int)
    leads_limit = min(leads_limit, 100) 

    # Construir a consulta
    query = Leads.query.filter_by(empresa_id=selected_company.id)

    if status_filter and status_filter != "all":
        query = query.filter_by(status=status_filter)

    if search_term:
        search_filter = f"%{search_term}%"
        query = query.filter(
            (Leads.nome.ilike(search_filter)) | 
            (Leads.telefone.ilike(search_filter)) | 
            (Leads.id.ilike(search_filter)) | 
            (Leads.city.ilike(search_filter))
        )

    # Aplicar filtro por data
    if data_inicial:
        try:
            data_inicial = datetime.strptime(data_inicial, '%Y-%m-%d')
            query = query.filter(Leads.created_at >= data_inicial)
        except ValueError:
            flash('Data inicial inválida.', 'error')

    if data_final:
        try:
            data_final = datetime.strptime(data_final, '%Y-%m-%d')
            query = query.filter(Leads.created_at <= data_final)
        except ValueError:
            flash('Data final inválida.', 'error')

    all_leads = query.limit(leads_limit).all()

    return render_template('leads_manager/leads.html', 
                           header_title='Lista de Leads', 
                           leads=all_leads, 
                           company=selected_company, 
                           companies=companies, 
                           selected_company=selected_company, 
                           leads_limit=leads_limit, 
                           is_mobile=is_mobile,
                           search_term=search_term,
                           data_inicial=request.args.get('data_inicial', ''),
                           data_final=request.args.get('data_final', ''))


@leads.route('/add_lead', methods=['GET', 'POST'])
@login_required
@require_active_plan
@require_lead_limit
def add_lead():
    user_id = current_user.id
    empresa_id = request.args.get('empresa_id')  # Obtém o ID da empresa da URL

    # Verificação se o ID da empresa está presente
    if not empresa_id:
        flash('Erro: ID da empresa não foi fornecido.')
        return redirect(request.referrer or url_for('leads.leads_main'))

    # Obter funcionários da empresa
    funcionarios = User.query.filter_by(company_work=empresa_id).all()
    print(funcionarios)

    if request.method == 'POST':
        # Captura dos dados do formulário
        nome = request.form['nome']
        telefone = request.form['telefone']
        produto = request.form.get('produto')
        comentario = request.form.get('comentario', None)
        city = request.form.get('cidade', None)
        status = request.form.get('status')
        funcionario_id = request.form.get('funcionario_id', ' ')

        # Verificação dos campos obrigatórios
        if not nome or not telefone:
            flash('Nome e Telefone são obrigatórios para adicionar um lead.')
            return redirect(url_for('leads.add_lead', empresa_id=empresa_id))

        # Criação do novo lead
        new_lead = Leads(
            nome=nome,
            usuario_id=funcionario_id,
            telefone=telefone,
            produto=produto,
            city=city,
            status=status,
            empresa_id=empresa_id
        )

        db.session.add(new_lead)
        db.session.flush()  # Para garantir que o lead_id seja gerado
        lead_id = new_lead.id

        # Adicionar comentário, se existir
        if comentario:
            lead_comment = LeadComment(
                lead_id=lead_id,
                comentario=comentario,
                created_at=datetime.utcnow(),
                usuario_id=user_id,
                nome_usuario=current_user.name
            )
            db.session.add(lead_comment)

        db.session.commit()
        flash('Lead adicionado com sucesso!')
        return redirect(url_for('leads.leads_main'))

    return render_template('leads_manager/services/add_lead.html', header_title='Adicionar Lead', empresa_id=empresa_id, funcionarios=funcionarios)

@leads.route('/export_leads', methods=['GET'])
@login_required
@require_active_plan
def export_leads():
    user_id = current_user.id
    selected_company_id = request.args.get('company_id')

    # Obter os leads da empresa selecionada
    leads = Leads.query.filter_by(empresa_id=selected_company_id).all()

    # Criar um arquivo CSV em memória
    output = io.StringIO()
    writer = csv.writer(output)

    # Escrever o cabeçalho
    writer.writerow(['Nome', 'Telefone', 'Status', 'Produto', 'Cidade', 'Criado em', 'Atualizado em'])

    # Escrever os dados dos leads
    for lead in leads:
        writer.writerow([lead.nome, lead.telefone, lead.status, lead.produto, lead.city, lead.created_at, lead.updated_at])

    # Mover o ponteiro do StringIO para o início
    output.seek(0)

    # Preparar os dados do anexo
    attachment = {
        'filename': f'leads_empresa_{selected_company_id}.csv',
        'mimetype': 'text/csv',
        'data': output.getvalue().encode('utf-8')  # Converte para bytes
    }

    # Enviar o e-mail
    subject = f"Leads da Empresa {selected_company_id}"
    recipients = [current_user.email]  # Ou qualquer outro destinatário que você desejar
    send_email(subject, recipients, "Aqui estão os leads da empresa selecionada.", attachment=attachment)

    # Fechar o StringIO
    output.close()

    # Redirecionar de volta para a página principal dos leads
    flash('Leads enviado para seu email!')
    return redirect(url_for('leads.leads_main'))
    
@leads.route('/import_leads', methods=['GET', 'POST'])
@login_required
@require_active_plan
@require_lead_limit
def import_leads():
    user_id = current_user.id
    empresas = Company.query.filter_by(owner_id=user_id).all()

    if request.method == 'POST':
        if 'file' not in request.files:
            flash('Nenhum arquivo foi enviado.')
            return redirect(url_for('main.import_leads'))

        file = request.files['file']

        if file.filename.endswith('.xlsx') or file.filename.endswith('.csv'):
            try:
                df = pd.read_excel(file) if file.filename.endswith('.xlsx') else pd.read_csv(file)
                empresa_id = request.form['empresa_id']
                first_city = None  # Para armazenar a cidade da primeira linha
                
                for index, row in df.iterrows():
                    if pd.isna(row['Nome']) or pd.isna(row['Telefone']):
                        flash('Nome e Telefone são obrigatórios para todos os leads.')
                        return redirect(url_for('main.import_leads'))

                    # Tratamento dos campos
                    nome = row['Nome']
                    telefone = ''.join(filter(str.isdigit, str(row['Telefone'])))  # Remove caracteres não numéricos
                    status = row.get('Status', 'pending')  
                    produto = row.get('Produto', '') if not pd.isna(row.get('Produto')) else ''

                    # Padronização do telefone
                    if len(telefone) == 11:
                        telefone = f"({telefone[:2]}) {telefone[2:7]}-{telefone[7:]}"
                    elif len(telefone) == 10:
                        telefone = f"({telefone[:2]}) {telefone[2:6]}-{telefone[6:]}"
                    else:
                        telefone = telefone.ljust(15, 'x')  # Se for inválido, preenche com 'x'

                    # Verifica se o telefone já existe na base
                    lead_existente = Leads.query.filter_by(empresa_id=empresa_id, telefone=telefone).first()
                    if lead_existente:
                        continue  # Se já existir, pula para o próximo lead

                    # Preenchimento da cidade
                    if pd.isna(row.get('Cidade')):
                        city = first_city if first_city else ''
                    else:
                        city = row['Cidade']
                        if not first_city:
                            first_city = city

                    created_at = row.get('Criado em', datetime.utcnow()) if not pd.isna(row.get('Criado em')) else datetime.utcnow()
                    updated_at = row.get('Atualizado em', datetime.utcnow()) if not pd.isna(row.get('Atualizado em')) else datetime.utcnow()

                    # Criar novo lead apenas se o telefone não existir
                    lead = Leads(
                        usuario_id=user_id,
                        empresa_id=empresa_id,
                        nome=nome,
                        telefone=telefone,
                        status=status,
                        city=city,
                        produto=produto,
                        created_at=created_at,
                        updated_at=updated_at
                    )

                    db.session.add(lead)
                    db.session.flush()  # Garante que o lead_id seja gerado sem commit
                    lead_id = lead.id  

                    # Adicionar comentário, se existir
                    comentario = row.get('Comentário', None)
                    if not pd.isna(comentario):
                        comentario_obj = LeadComment(
                            lead_id=lead_id,
                            comentario=comentario,
                            created_at=datetime.utcnow(),
                            usuario_id=current_user.id,
                            nome_usuario=current_user.name
                        )
                        db.session.add(comentario_obj)

                db.session.commit()
                flash('Leads importados com sucesso!')
            except Exception as e:
                db.session.rollback()
                flash(f'Ocorreu um erro ao importar os leads: {e}')
        else:
            flash('Formato de arquivo inválido. Por favor, envie um arquivo .xlsx ou .csv.')

        return redirect(url_for('leads.import_leads'))

    return render_template('leads_manager/services/import_leads.html', empresas=empresas)


@leads.route('/edit_lead/<int:lead_id>', methods=['GET'])
@login_required
@require_active_plan
def edit_lead(lead_id):
    # Busca o lead pelo ID
    lead = Leads.query.get_or_404(lead_id)
    # Busca os comentários do lead, se existirem
    comments = LeadComment.query.filter_by(lead_id=lead_id).all()
    # Renderiza o template edit_lead.html passando o lead e os comentários
    return render_template('leads_manager/services/edit_lead.html', lead=lead, comments=comments, header_title="Editar Lead")

@leads.route('/update_lead', methods=['POST'])
@login_required
@require_active_plan
def update_lead():
    lead_id = request.form.get('lead_id')
    lead = Leads.query.get(lead_id)

    if not lead:
        flash('Lead não encontrado.', 'error')
        return redirect(url_for('leads.leads_main'))

    # Obtém os valores do formulário
    nome = request.form.get('name')
    telefone = request.form.get('plan')  # Atualizado para 'plan' conforme HTML
    status = request.form.get('lead_status')
    novo_comentario = request.form.get('lead_comentario')
    produto = request.form.get('invite')  # Atualizado para 'invite' conforme HTML

    novo_comentario = f"Criado em: {datetime.utcnow()} \n {novo_comentario}"

    # Atualiza as informações do lead
    lead.nome = nome
    lead.telefone = telefone
    lead.status = status
    lead.produto = produto
    lead.updated_at = datetime.utcnow()  # Atualiza a data de modificação

    # Adiciona o novo comentário ao lead, se houver
    if novo_comentario:
        comment_created = datetime.utcnow()
        comentario = LeadComment(lead_id=lead_id, comentario=novo_comentario, created_at=comment_created, usuario_id=current_user.id, nome_usuario=current_user.name)
        db.session.add(comentario)

    # Salva as alterações no banco de dados
    try:
        db.session.commit()
        flash('Lead atualizado com sucesso!', 'success')
    except Exception as e:
        db.session.rollback()
        flash(f'Erro ao atualizar o lead: {str(e)}', 'error')

    return redirect(url_for('leads.leads_main', company_id=lead.empresa_id))


@leads.route('/calls', methods=['GET', 'POST'])
@login_required
@require_active_plan
def calls():
    user_id = current_user.id
    companies, selected_company, leads_comments = [], None, ''

    # Verificar se o usuário é do tipo 'owner' ou 'admin'
    if current_user.role in ['owner', 'admin']:
        flash('Recomenda-se utilizar uma conta "Colaborador" para esta página.')
    
    # Verificar se o usuário é 'employee' e obter empresa associada
    if current_user.role == 'employee':
        company_work_id = current_user.company_work
        if company_work_id:
            selected_company = Company.query.get(company_work_id)
            if not selected_company:
                flash('A empresa associada não foi encontrada!')
                return redirect(url_for('user.my_data'))
        else:
            flash('Você não está associado a nenhuma empresa!')
            return redirect(url_for('user.my_data'))
    else:
        # Carregar empresas para 'owner' ou 'admin'
        companies = Company.query.filter_by(owner_id=user_id).all()
        if not companies:
            flash('Você não possui uma empresa para acessar leads!')
            return redirect(url_for('user.my_data'))

        selected_company_id = request.args.get('company_id', companies[0].id)
        selected_company = Company.query.get(selected_company_id)
        if not selected_company:
            flash('Empresa selecionada não encontrada!')
            return redirect(url_for('user.my_data'))

    # Verificar se o usuário já possui um lead 'in_progress'
    user_lead = Leads.query.filter_by(empresa_id=selected_company.id, usuario_id=user_id, status='in_progress').first()
    if user_lead:
        leads_comments = LeadComment.query.filter_by(lead_id=user_lead.id).all()
    else:
        # Buscar um lead 'pending' se não houver lead 'in_progress'
        user_lead = Leads.query.filter_by(empresa_id=selected_company.id, status='pending').first()
        if user_lead:
            user_lead.usuario_id, user_lead.status, user_lead.updated_at = user_id, 'in_progress', datetime.utcnow()
            db.session.commit()
            leads_comments = LeadComment.query.filter_by(lead_id=user_lead.id).all()
        else:
            flash("Nenhuma empresa possui leads disponíveis!")
            return redirect(url_for('leads.leads_main'))

    # Lógica para manipulação de lead via POST
    if request.method == 'POST':
        action = request.form.get('action')
        comment = request.form.get('comentario', '')

        # Função auxiliar para adicionar comentário
        def add_comment(comment_text):
            comment_text = f"Criado em: {datetime.utcnow()} \n {comment_text}"
            lead_comment = LeadComment(
                usuario_id=user_id,
                lead_id=user_lead.id,
                comentario=comment_text,
                created_at=datetime.utcnow(),
                nome_usuario=current_user.name
            )
            db.session.add(lead_comment)

        # Executar ações baseadas no botão pressionado
        if action == 'finalize':
            user_lead.nome = request.form['nome']
            user_lead.telefone = request.form['telefone']
            user_lead.produto = request.form['produto']
            user_lead.city = request.form['cidade']
            user_lead.status = 'completed'
            if comment:
                add_comment(comment)
            db.session.commit()
            flash('Lead finalizado com sucesso!')

        elif action == 'cancel':
            user_lead.status = 'cancelled'
            if comment:
                add_comment(comment)
            db.session.commit()
            flash('Lead cancelado com sucesso!')

        elif action == 'move_to_end':
            # Mover o lead para o final da fila
            last_id = db.session.query(db.func.max(Leads.id)).scalar() or 0
            user_lead.id, user_lead.status = last_id + 1, 'pending'
            if comment:
                add_comment(comment)
            db.session.commit()
            flash('Lead movido para o final da fila!')

        return redirect(url_for('leads.calls'))

    return render_template(
        'leads_manager/calls/calls.html', 
        header_title='Lista de Leads', 
        company=selected_company, 
        companies=companies, 
        selected_company=selected_company,
        user_lead=user_lead, 
        leads_comments=leads_comments
    )