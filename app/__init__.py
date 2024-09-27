from flask import Flask, json
from flask_sqlalchemy import SQLAlchemy
from flask_login import LoginManager

db = SQLAlchemy()
login_manager = LoginManager()

def create_app():
    app = Flask(__name__)
    
    # Configurações
    app.config['SECRET_KEY'] = 'sua_chave_secreta'  # Defina uma chave secreta
    app.config['SQLALCHEMY_DATABASE_URI'] = 'mysql://root:@localhost/test'
    
    db.init_app(app)
    login_manager.init_app(app)

    # A URL de redirecionamento padrão após o login
    login_manager.login_view = 'login'

    # Função para carregar o arquivo JSON
    def get_project_info():
        with open('./version.json', 'r', encoding='utf-8') as f:
            return json.load(f)

    # Context processor para injetar as informações no template
    @app.context_processor
    def inject_project_info():
        project_info = get_project_info()
        return dict(
            project_name=project_info.get('project_name'),
            project=project_info.get('project'),
            year_copy=project_info.get('year_copy'),
            version=project_info.get('version'),
            description=project_info.get('description'),
            author=project_info.get('author'),
            license=project_info.get('license')
        )

    with app.app_context():
        from . import routes  # Importe suas rotas

    return app
