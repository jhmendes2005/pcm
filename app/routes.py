from flask import render_template
from . import create_app
from .models import User

app = create_app()

@app.route('/')
def home():
    users = User.query.all()
    return render_template('index.html', users=users)

@app.route('/test')
def test():
    return "Rota de teste está funcionando!"