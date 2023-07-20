from flask import Flask
from flask_sqlalchemy import SQLAlchemy
from flask_login import LoginManager

app = Flask(__name__)

app.config['SQLALCHEMY_DATABASE_URI'] = 'sqlite:///thedatabase.db'
app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False
app.config['SECRET_KEY'] = '923784293rh2fo2jned9sdyru23jeqnde3uh43ou8@^#T*G'

db = SQLAlchemy(app)

login_manager = LoginManager()
login_manager.init_app(app)

import routes, models
