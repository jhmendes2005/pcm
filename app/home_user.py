from flask import Blueprint, render_template, request, Response, redirect, url_for, flash, send_file, session
from flask_login import login_user, logout_user, current_user, login_required
from app.email_service import send_email
import user_agents
from app import db
from app.models import User, Leads, Company
from werkzeug.security import generate_password_hash, check_password_hash
import pandas as pd
from datetime import datetime, timedelta

# Configurar o blueprint
home = Blueprint('home', __name__)

@home.route('/', methods=['GET'])
@login_required
def main():
    return render_template('home/home-logged.html')