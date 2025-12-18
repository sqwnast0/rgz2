#!/usr/bin/env python3
"""
Утилита для проверки пользователей в базе данных
"""

import sys
import os
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

from app import app, db
from models import User
from werkzeug.security import check_password_hash

def list_users():
    """Вывод списка всех пользователей"""
    with app.app_context():
        users = User.query.order_by(User.username).all()
        
        if not users:
            print("В базе данных нет пользователей")
            return
        
        print(f"Найдено {len(users)} пользователей:")
        print("-" * 80)
        print(f"{'ID':<5} {'Логин':<20} {'Имя':<25} {'Email':<25} {'Активен':<10}")
        print("-" * 80)
        
        for user in users:
            status = "Да" if user.is_active else "Нет"
            print(f"{user.id:<5} {user.username:<20} {user.full_name or '-':<25} {user.email or '-':<25} {status:<10}")
        
        print("-" * 80)

def check_password(username, password):
    """Проверка пароля пользователя"""
    with app.app_context():
        user = User.query.filter_by(username=username).first()
        
        if not user:
            print(f"Пользователь '{username}' не найден")
            return False
        
        if user.check_password(password):
            print(f"Пароль для пользователя '{username}' верный")
            return True
        else:
            print(f"Неверный пароль для пользователя '{username}'")
            return False

def create_user(username, password, full_name=None, email=None):
    """Создание нового пользователя"""
    with app.app_context():
        # Проверяем, не существует ли уже пользователь
        existing = User.query.filter_by(username=username).first()
        if existing:
            print(f"Пользователь '{username}' уже существует")
            return False
        
        # Создаем нового пользователя
        user = User(
            username=username,
            full_name=full_name or username,
            email=email
        )
        user.set_password(password)
        
        db.session.add(user)
        db.session.commit()
        
        print(f"Пользователь '{username}' успешно создан")
        return True

def deactivate_user(username):
    """Деактивация пользователя"""
    with app.app_context():
        user = User.query.filter_by(username=username).first()
        
        if not user:
            print(f"Пользователь '{username}' не найден")
            return False
        
        user.is_active = False
        db.session.commit()
        
        print(f"Пользователь '{username}' деактивирован")
        return True

def activate_user(username):
    """Активация пользователя"""
    with app.app_context():
        user = User.query.filter_by(username=username).first()
        
        if not user:
            print(f"Пользователь '{username}' не найден")
            return False
        
        user.is_active = True
        db.session.commit()
        
        print(f"Пользователь '{username}' активирован")
        return True

def change_password(username, new_password):
    """Изменение пароля пользователя"""
    with app.app_context():
        user = User.query.filter_by(username=username).first()
        
        if not user:
            print(f"Пользователь '{username}' не найден")
            return False
        
        user.set_password(new_password)
        db.session.commit()
        
        print(f"Пароль для пользователя '{username}' изменен")
        return True

def show_help():
    """Вывод справки"""
    print("Утилита управления пользователями склада")
    print("\nИспользование:")
    print("  python check_users.py list                        - Вывод списка пользователей")
    print("  python check_users.py check <username> <password> - Проверка пароля")
    print("  python check_users.py create <username> <password> [full_name] [email] - Создание пользователя")
    print("  python check_users.py deactivate <username>       - Деактивация пользователя")
    print("  python check_users.py activate <username>         - Активация пользователя")
    print("  python check_users.py changepwd <username> <new_password> - Изменение пароля")
    print("\nПримеры:")
    print("  python check_users.py list")
    print("  python check_users.py check storekeeper password123")
    print("  python check_users.py create newuser newpass123 'Новый Кладовщик' new@example.com")

if __name__ == '__main__':
    if len(sys.argv) < 2:
        show_help()
        sys.exit(1)
    
    command = sys.argv[1].lower()
    
    if command == 'list':
        list_users()
    
    elif command == 'check':
        if len(sys.argv) < 4:
            print("Ошибка: укажите логин и пароль")
            sys.exit(1)
        username = sys.argv[2]
        password = sys.argv[3]
        check_password(username, password)
    
    elif command == 'create':
        if len(sys.argv) < 4:
            print("Ошибка: укажите логин и пароль")
            sys.exit(1)
        username = sys.argv[2]
        password = sys.argv[3]
        full_name = sys.argv[4] if len(sys.argv) > 4 else None
        email = sys.argv[5] if len(sys.argv) > 5 else None
        create_user(username, password, full_name, email)
    
    elif command == 'deactivate':
        if len(sys.argv) < 3:
            print("Ошибка: укажите логин")
            sys.exit(1)
        username = sys.argv[2]
        deactivate_user(username)
    
    elif command == 'activate':
        if len(sys.argv) < 3:
            print("Ошибка: укажите логин")
            sys.exit(1)
        username = sys.argv[2]
        activate_user(username)
    
    elif command == 'changepwd':
        if len(sys.argv) < 4:
            print("Ошибка: укажите логин и новый пароль")
            sys.exit(1)
        username = sys.argv[2]
        new_password = sys.argv[3]
        change_password(username, new_password)
    
    else:
        print(f"Неизвестная команда: {command}")
        show_help()
        sys.exit(1)