from flask import Flask, json
from flask_sqlalchemy import SQLAlchemy
from flask_login import LoginManager
from sqlalchemy import create_engine

db = SQLAlchemy()
login_manager = LoginManager()

def create_app():
    app = Flask(__name__)

    # Configurações
    app.config['SECRET_KEY'] = 'f8ee8897dc09a283101bac9111785cbf1ca69a812a79e23075db7e3c4ecfbcaf'
    app.config['SQLALCHEMY_DATABASE_URI'] = 'mysql+pymysql://pcm_leads:Pcm%40123INFRA@pcm_leads.mysql.dbaas.com.br/pcm_leads'
    app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False

    # Configuração do pool de conexões para SQLAlchemy
    engine = create_engine(
        app.config['SQLALCHEMY_DATABASE_URI'],
        pool_pre_ping=True,  # Testa a conexão antes de usá-la
        pool_size=10,  # Tamanho do pool de conexões
        max_overflow=20  # Número máximo de conexões extras
    )

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

    # Registrar rotas dentro do contexto do aplicativo
    with app.app_context():
        from . import routes  # Importe suas rotas aqui

    return app
