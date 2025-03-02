import json
from flask import flash
from app.models import db, Purchase, Company
from functools import wraps
from flask_login import current_user

class PlanManager:
    """ Gerencia os planos e permissões dos usuários """
    
    PLANS_JSON = 'app/purchases/plans.json'

    @classmethod
    def get_user_plan(cls, user_id):
        """ Obtém o plano ativo do usuário a partir do banco de dados """
        purchase = Purchase.query.filter_by(user_id=user_id).order_by(Purchase.id.desc()).first()
        
        if not purchase:
            # Caso não haja compra, retornamos um valor padrão
            return None, None  # Nenhuma compra encontrada, retorna tupla com dois None

        data_expiracao = purchase.data_expiracao
        
        # Retorna o plano e a data de expiração
        return cls.load_plan_from_json(purchase.plano_id), data_expiracao


    @classmethod
    def load_plan_from_json(cls, plano_id):
        print(plano_id)
        """ Carrega os detalhes do plano a partir do JSON """
        try:
            with open(cls.PLANS_JSON, 'r') as file:
                plans = json.load(file)
            return plans.get(str(plano_id), None)
        except (FileNotFoundError, json.JSONDecodeError) as e:
            return {"error": f"Erro ao carregar os planos: {e}"}

    @classmethod
    def can_add_lead(cls, user_id, empresa_id):
        """ Verifica se o usuário pode adicionar leads com base no plano """
        plan, exp = cls.get_user_plan(user_id)
        if not plan:
            return False, "Você não tem um plano ativo. Adquira um plano para adicionar leads."

        # Conta quantos leads a empresa já tem
        from app.models import Leads
        lead_count = Leads.query.filter_by(empresa_id=empresa_id).count()

        if lead_count >= plan["max_leads"]:
            return False, f"Limite de leads ({plan['max_leads']}) atingido para esta empresa."

        return True, None

    @classmethod
    def can_add_employee(cls, user_id, empresa_id):
        """ Verifica se o usuário pode adicionar funcionários com base no plano """
        plan, exp = cls.get_user_plan(user_id)
        if not plan:
            return False, "Você não tem um plano ativo. Adquira um plano para adicionar funcionários."

        from app.models import User
        employee_count = User.query.filter_by(company_work=empresa_id).count()

        if employee_count >= plan["max_employees"]:
            return False, f"Limite de funcionários ({plan['max_employees']}) atingido para esta empresa."

        return True, None
    
    @classmethod
    def can_add_companie(cls, user_id):
        """ Verifica se o usuário pode adicionar funcionários com base no plano """
        plan, exp = cls.get_user_plan(user_id)
        if not plan:
            return False, "Você não tem um plano ativo. Adquira um plano para adicionar funcionários."

        from app.models import User
        companies_count = Company.query.filter_by(owner_id=user_id).count()

        if companies_count >= plan["max_companies"]:
            return False, f"Limite de empresas ({plan['max_companies']}) atingido para seu plano!"
        return True, None

    @classmethod
    def register_purchase(cls, user_id, plano_id, charge_id, periodo_meses):
        """ Registra a compra de um plano no banco de dados """
        try:
            new_purchase = Purchase(user_id=user_id, plano_id=plano_id, charge_id=charge_id, periodo_meses=periodo_meses)
            db.session.add(new_purchase)
            db.session.commit()
            return {"success": "Compra registrada com sucesso!"}
        except Exception as e:
            db.session.rollback()
            return {"error": f"Erro ao registrar a compra: {e}"}

    @classmethod
    def list_plans(cls):
        """ Lista todos os planos disponíveis """
        try:
            with open(cls.PLANS_JSON, 'r') as file:
                return json.load(file)
        except FileNotFoundError as e:
            return {"error": f"Erro ao carregar os planos: {e}"}

    @classmethod
    def edit_plan(cls, plano_id, max_leads, max_employees, max_upload_per_file):
        """ Edita um plano existente no JSON """
        try:
            with open(cls.PLANS_JSON, 'r') as file:
                plans = json.load(file)

            if str(plano_id) in plans:
                plans[str(plano_id)].update({
                    "max_leads": max_leads,
                    "max_employees": max_employees,
                    "max_upload_per_file": max_upload_per_file
                })

                with open(cls.PLANS_JSON, 'w') as file:
                    json.dump(plans, file, indent=4)

                return {"success": f"Plano {plano_id} atualizado com sucesso!"}
            else:
                return {"error": f"Plano {plano_id} não encontrado."}
        except (FileNotFoundError, json.JSONDecodeError) as e:
            return {"error": f"Erro ao editar o plano: {e}"}