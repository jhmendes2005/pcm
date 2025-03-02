from flask import Blueprint, render_template, request, Response, redirect, url_for, flash, send_file, session
from flask_login import login_user, logout_user, current_user, login_required
from app.email_service import send_email
import user_agents
from app import db
from app.models import User, Leads, Company, LeadComment
import pandas as pd
from datetime import datetime, timedelta
import secrets
import string
import io
import csv

reports = Blueprint('reports', __name__)

def gerar_token_curto(tamanho=8):
    alfabeto = string.ascii_letters + string.digits  # Letras maiúsculas, minúsculas e números
    token = ''.join(secrets.choice(alfabeto) for _ in range(tamanho))
    return token

@reports.route('/', methods=['GET', 'POST'])
@login_required
def leads_main():
    user_id = current_user.id
    companies = Company.query.filter_by(owner_id=user_id).all()

    if not companies:
        flash('Você não tem uma empresa para acessar reports de leads!')
        return redirect(url_for('user.my_data'))
    return render_template('reports/reports.html', header_title='Lista de Leads', companies=companies)

@reports.route('/get/', methods=['GET'])
@login_required
def report_leads():
    days = request.args.get('days', default=30, type=int)
    date_limit = datetime.now() - timedelta(days=days)
    company_id = request.args.get('company_id')
    status_filter = request.args.get('status')
    atendent_filter = request.args.get('atendent')
    
    # Passar as empresas do usuário para o template
    companies = Company.query.filter_by(owner_id=current_user.id).all()

    company_valid = Company.query.filter_by(id=company_id, owner_id=current_user.id).first()

    if not company_valid:
        flash("Você não tem permissão para acessar os leads dessa empresa.", "danger")
        return redirect(url_for('user.my_data'))

    # O restante do código para buscar os leads
    company_leads_query = Leads.query.filter(Leads.empresa_id == company_id, Leads.updated_at >= date_limit)

    # Adiciona outros filtros
    if status_filter:
        company_leads_query = company_leads_query.filter(Leads.status == status_filter)

    if atendent_filter:
        company_leads_query = company_leads_query.filter(Leads.usuario_id == atendent_filter)

    company_leads = company_leads_query.all()

    # Obtém todos os atendentes da empresa
    atendents = User.query.filter_by(company_work=company_id).all()

    atendent_leads_count = {atendent.id: 0 for atendent in atendents}
    atendent_completed_count = {atendent.id: 0 for atendent in atendents}

    for lead in company_leads:
        # Adiciona os comentários e atendentes ao lead
        recent_comment = LeadComment.query.filter_by(lead_id=lead.id).order_by(LeadComment.created_at.desc()).first()
        atendent = User.query.filter_by(id=lead.usuario_id).first()
        lead.comment = recent_comment.comentario if recent_comment else "Sem comentários"
        lead.atendent = atendent.name if atendent else "Sem atendente"

        # Atualiza contagem de leads atendidos e concluídos
        if atendent and atendent.id in atendent_leads_count:
            atendent_leads_count[atendent.id] += 1
        if lead.status == 'completed' and atendent and atendent.id in atendent_completed_count:
            atendent_completed_count[atendent.id] += 1

    return render_template('reports/services/get.html', 
                           company_leads=company_leads, 
                           atendent_leads_count=atendent_leads_count, 
                           atendent_completed_count=atendent_completed_count, 
                           atendents=atendents,
                           companies=companies)  # Passa as empresas para o template
