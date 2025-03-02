from . import db, login_manager
from flask_login import UserMixin
from flask import current_app
from sqlalchemy import Enum
from datetime import datetime, timedelta
from .sec.security import hash_password, verify_password
import itsdangerous

# Função para carregar o usuário pelo ID (Flask-Login)
@login_manager.user_loader
def load_user(user_id):
    return User.query.get(int(user_id))

class User(db.Model, UserMixin):
    __tablename__ = 'users'

    id = db.Column(db.Integer, primary_key=True, autoincrement=True)
    email = db.Column(db.String(255), unique=True, nullable=False)
    password = db.Column(db.String(255), nullable=False)
    name = db.Column(db.String(255), nullable=False)
    role = db.Column(db.Enum('owner', 'employee', 'admin'), nullable=False, default='owner')  # Define o papel do usuário
    is_active = db.Column(db.Boolean, default=False)  # Indica se o usuário está online
    last_active = db.Column(db.DateTime, default=datetime.utcnow)  # Última atividade do usuário
    company_work = db.Column(db.Integer)
    is_confirmed = db.Column(db.Boolean, default=False)  # Campo para verificar se o e-mail foi confirmado
    confirmation_token = db.Column(db.String(100), nullable=True)  # Token para confirmação
    reset_code = db.Column(db.String(10), nullable=True)

    def generate_confirmation_token(self):
        serializer = itsdangerous.URLSafeTimedSerializer(current_app.config['SECRET_KEY'])
        return serializer.dumps(self.email)
    
    def confirm(self, token):
        serializer = itsdangerous.URLSafeTimedSerializer(current_app.config['SECRET_KEY'])
        try:
            email = serializer.loads(token, max_age=3600)  # O token expira em 1 hora
        except itsdangerous.SignatureExpired:
            return False
        except itsdangerous.BadSignature:
            return False

        if email == self.email:
            self.is_confirmed = True
            self.confirmation_token = None  # Limpa o token após a confirmação
            return True
        return False

    def __init__(self, name, email, password, role='owner', company_work=''):
        self.email = email
        self.name = name
        self.password = hash_password(password)
        self.role = role
        self.company_work = company_work

    def verify_password(self, pwd):
        return verify_password(self.password, pwd)
    
    def hash_password(self, pwd):
        return hash_password(pwd)

    def __repr__(self):
        return f'<User {self.email}>'

class Leads(db.Model):
    __tablename__ = 'leads'

    id = db.Column(db.BigInteger, primary_key=True, autoincrement=True)  # ID do lead
    usuario_id = db.Column(db.Integer, db.ForeignKey('users.id'), nullable=False)  # ID do usuário, chave estrangeira
    empresa_id = db.Column(db.Integer, nullable=False)  # ID da empresa
    nome = db.Column(db.String(255), nullable=False)  # Nome do lead
    telefone = db.Column(db.String(50), nullable=False)  # Telefone do lead
    status = db.Column(Enum('pending', 'in_progress', 'completed', 'cancelled'), nullable=False)  # Status do lead
    produto = db.Column(db.String(255))  # Produto de interesse
    city = db.Column(db.String(255))  # Produto de interesse
    created_at = db.Column(db.DateTime, default=datetime.utcnow)  # Data de criação
    updated_at = db.Column(db.DateTime, onupdate=datetime.utcnow)  # Data de atualização

    def __repr__(self):
        return f'<Lead {self.nome}>'
    
class LeadComment(db.Model):
    __tablename__ = 'lead_comments'

    id = db.Column(db.BigInteger, primary_key=True, autoincrement=True)
    lead_id = db.Column(db.BigInteger, db.ForeignKey('leads.id', ondelete='CASCADE'), nullable=False)
    usuario_id = db.Column(db.Integer, db.ForeignKey('users.id', ondelete='SET NULL'), nullable=True)
    comentario = db.Column(db.Text, nullable=False)
    created_at = db.Column(db.TIMESTAMP, default=datetime.utcnow, nullable=False)
    nome_usuario = db.Column(db.String(255))

class Company(db.Model):
    __tablename__ = 'companies'
    
    id = db.Column(db.Integer, primary_key=True, autoincrement=True)
    owner_id = db.Column(db.Integer, nullable=False)  # ID do dono da empresa
    plan = db.Column(db.Integer, nullable=False)  # ID do plano da empresa
    admins = db.Column(db.Text, nullable=True)  # Armazena uma lista de administradores, talvez em formato JSON ou CSV
    nome = db.Column(db.String(255), nullable=False)  # Nome da empresa
    cnpj = db.Column(db.String(20), nullable=False)  # CNPJ da empresa
    collaborator = db.Column(db.Text, nullable=True)  # Armazena uma lista de colaboradores, talvez em formato JSON ou CSV
    invite = db.Column(db.String(255))
    bt_action = db.Column(db.String(255))  # Ação do botão
    bt_type_product = db.Column(db.String(255))  # Tipo do produto associado ao botão
    token_api = db.Column(db.String(100), nullable=True)

    def __repr__(self):
        return (f"<Company(id={self.id}, owner_id={self.owner_id}, "
                f"plan={self.plan}, admins={self.admins}, nome={self.nome}, "
                f"CNPJ={self.CNPJ}, collaborator={self.collaborator})>, invite={self.invite})>")
class Purchase(db.Model):
    __tablename__ = 'purchases'

    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey('users.id'), nullable=False)
    plano_id = db.Column(db.String(255), nullable=False)
    charge_id = db.Column(db.String(255), nullable=False)
    data_aquisicao = db.Column(db.DateTime, default=datetime.utcnow)
    data_expiracao = db.Column(db.DateTime, nullable=False)
    valor = db.Column(db.Integer, nullable=False, default=0)  # Nova coluna

    def __init__(self, user_id, plano_id, charge_id, periodo_meses):
        self.user_id = user_id
        self.plano_id = plano_id
        self.charge_id = charge_id
        self.data_expiracao = datetime.utcnow() + timedelta(days=30 * periodo_meses)

    def __repr__(self):
        return f"<Purchase(user_id={self.user_id}, plano_id={self.plano_id}, charge_id={self.charge_id})>"

    # Método para obter a duração restante do plano em dias
    def dias_restantes(self):
        return (self.data_expiracao - datetime.utcnow()).days

    # Método para verificar se o plano está ativo
    def esta_ativo(self):
        return datetime.utcnow() < self.data_expiracao
    
class Contacts(db.Model):
    __tablename__ = 'contacts'

    id = db.Column(db.BigInteger, primary_key=True, autoincrement=True)  # ID do contato
    company_id = db.Column(db.Integer, db.ForeignKey('companies.id'), nullable=False)  # ID da empresa, chave estrangeira
    name = db.Column(db.String(255), nullable=False)  # Nome do contato
    phone = db.Column(db.String(50))  # Telefone do contato
    page = db.Column(db.String(255))  # Página de origem do contato
    time = db.Column(db.DateTime, default=datetime.utcnow)  # Hora do registro
    website = db.Column(db.String(255))  # Website associado

    def __repr__(self):
        return f'<Contact {self.name}>'
    
class Feirao(db.Model):
    __tablename__ = 'feirao'

    id = db.Column(db.Integer, primary_key=True, autoincrement=True)
    empresa_id = db.Column(db.Integer, db.ForeignKey('companies.id'), nullable=False)  # Relacionado à empresa
    nome_feirao = db.Column(db.String(255), nullable=False)  # Nome do feirão
    status = db.Column(db.Enum('ativo', 'inativo'), nullable=False, default='ativo')  # Status do feirão
    funcionarios = db.Column(db.JSON, nullable=True)  # Lista de IDs de funcionários

    def add_funcionario(self, funcionario_id):
        """Adiciona um funcionário à lista."""
        if self.funcionarios is None:
            self.funcionarios = []
        if funcionario_id not in self.funcionarios:
            self.funcionarios.append(funcionario_id)

    def remove_funcionario(self, funcionario_id):
        """Remove um funcionário da lista."""
        if self.funcionarios and funcionario_id in self.funcionarios:
            self.funcionarios.remove(funcionario_id)

    def __repr__(self):
        return f'<Feirao {self.nome_feirao}>'
    
class Integration(db.Model):
    __tablename__ = 'integrations'
    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey('users.id'), nullable=False)
    type = db.Column(db.Integer, nullable=False)
    token_api = db.Column(db.String(255), nullable=False)
    status = db.Column(db.String(50), nullable=False)
    message_alias = db.Column(db.String(255), nullable=True)

    user = db.relationship('User', backref='integrations')

    def __init__(self, user_id, type, token_api, status, message_alias=None):
        self.user_id = user_id
        self.type = type
        self.token_api = token_api
        self.status = status
        self.message_alias = message_alias