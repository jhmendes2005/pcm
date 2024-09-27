from . import db, login_manager
from flask_login import UserMixin
from sqlalchemy import Enum
from datetime import datetime
from .sec.security import hash_password, verify_password

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
    role = db.Column(db.Enum('owner', 'employee', 'admin'), nullable=False, default='employee')  # Define o papel do usuário
    is_active = db.Column(db.Boolean, default=False)  # Indica se o usuário está online
    last_active = db.Column(db.DateTime, default=datetime.utcnow)  # Última atividade do usuário

    def __init__(self, name, email, password, role='employee'):
        self.email = email
        self.name = name
        self.password = hash_password(password)
        self.role = role

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
    comentario = db.Column(db.Text)  # Comentário
    veiculo = db.Column(db.String(255))  # Veículo de interesse
    created_at = db.Column(db.DateTime, default=datetime.utcnow)  # Data de criação
    updated_at = db.Column(db.DateTime, onupdate=datetime.utcnow)  # Data de atualização

    def __repr__(self):
        return f'<Lead {self.nome}>'

class Company(db.Model):
    __tablename__ = 'companies'
    
    id = db.Column(db.Integer, primary_key=True, autoincrement=True)
    owner_id = db.Column(db.Integer, nullable=False)  # ID do dono da empresa
    plan = db.Column(db.Integer, nullable=False)  # ID do plano da empresa
    admins = db.Column(db.Text, nullable=True)  # Armazena uma lista de administradores, talvez em formato JSON ou CSV
    nome = db.Column(db.String(255), nullable=False)  # Nome da empresa
    cnpj = db.Column(db.String(20), nullable=False)  # CNPJ da empresa
    collaborator = db.Column(db.Text, nullable=True)  # Armazena uma lista de colaboradores, talvez em formato JSON ou CSV

    def __repr__(self):
        return (f"<Company(id={self.id}, owner_id={self.owner_id}, "
                f"plan={self.plan}, admins={self.admins}, nome={self.nome}, "
                f"CNPJ={self.CNPJ}, collaborator={self.collaborator})>")
