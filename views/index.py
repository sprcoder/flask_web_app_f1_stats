from flask import Blueprint, redirect, request, render_template, url_for, flash
from flask_login import current_user
from sql.db import DB
home = Blueprint('home', __name__, url_prefix='/')

@home.route('/')
def index():
    if not current_user.is_authenticated:
      return redirect(url_for("auth.login"))
    else:
      return redirect(url_for("auth.landing_page"))