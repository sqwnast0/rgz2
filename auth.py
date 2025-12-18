from flask_login import LoginManager
from models import User, db

login_manager = LoginManager()
login_manager.login_view = 'login'
login_manager.login_message = 'Пожалуйста, войдите в систему для доступа к этой странице.'
login_manager.login_message_category = 'warning'

@login_manager.user_loader
def load_user(user_id):
    return User.query.get(int(user_id))

def authenticate(username, password):
    user = User.query.filter_by(username=username, is_active=True).first()
    if user and user.check_password(password):
        return user
    return None