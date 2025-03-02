from functools import wraps
from datetime import datetime
from flask import request, flash, redirect, url_for
from flask_login import current_user
from app.purchases.plans import PlanManager

def require_active_plan(func):
    """ Decorador para verificar se o usuário tem um plano ativo e não vencido """
    @wraps(func)
    def wrapper(*args, **kwargs):
        # Obtém o plano ativo do usuário
        user_plan, data_expiracao = PlanManager.get_user_plan(current_user.id)
        if not user_plan:
            flash("Você não tem um plano ativo. Adquira um plano para acessar esta funcionalidade.", "error")
            return redirect(url_for("home.main"))
        
        # Verifica se o plano está vencido
        if data_expiracao < datetime.now():
            flash("Seu plano está vencido. Renove para continuar acessando esta funcionalidade.", "error")
            #return redirect(url_for("plans.purchase_page"))
            return redirect(url_for("home.main"))
        return func(*args, **kwargs)
    
    return wrapper

def require_lead_limit(func):
    """ Decorador para verificar se o usuário pode adicionar leads """
    @wraps(func)
    def wrapper(*args, **kwargs):
        empresa_id = request.args.get('empresa_id')  # Captura empresa_id da URL
        
        if not empresa_id:
            flash("Empresa inválida.", "error")
            return redirect(url_for("companies.companies_page"))

        can_add, message = PlanManager.can_add_lead(current_user.id, empresa_id)
        if not can_add:
            flash(message, "error")
            return redirect(url_for("companies.companies_page"))
        
        return func(*args, **kwargs)
    
    return wrapper

def require_employee_limit(func):
    """ Decorador para verificar se o usuário pode adicionar funcionários """
    @wraps(func)
    def wrapper(*args, **kwargs):
        empresa_id = kwargs.get('empresa_id') or (args[0] if args else None)
        if not empresa_id:
            flash("Empresa inválida.", "error")
            return redirect(url_for("companies.companies_page"))
        
        can_add, message = PlanManager.can_add_employee(current_user.id, empresa_id)
        if not can_add:
            flash(message, "error")
            return redirect(url_for("companies.companies_page"))
        
        return func(*args, **kwargs)
    return wrapper

def require_companies_limit(func):
    """ Decorador para verificar se o usuário pode adicionar funcionários """
    @wraps(func)
    def wrapper(*args, **kwargs):       
        can_add, message = PlanManager.can_add_companie(current_user.id)
        if not can_add:
            flash(message, "error")
            return redirect(url_for("companies.companies_page"))
        
        return func(*args, **kwargs)
    return wrapper
