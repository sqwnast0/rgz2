import psycopg2
from psycopg2 import sql
import getpass

def create_database():
    """Создание базы данных и пользователя в PostgreSQL"""
    
    # Подключаемся к PostgreSQL как суперпользователь
    print("=== Настройка базы данных PostgreSQL ===")
    print("Введите данные для подключения к PostgreSQL (по умолчанию - localhost, порт 5432)")
    
    host = input("Хост [localhost]: ") or "localhost"
    port = input("Порт [5432]: ") or "5432"
    admin_user = input("Имя пользователя PostgreSQL [postgres]: ") or "postgres"
    admin_password = getpass.getpass(f"Пароль для пользователя {admin_user}: ")
    
    try:
        # Подключаемся как администратор
        conn = psycopg2.connect(
            host=host,
            port=port,
            user=admin_user,
            password=admin_password,
            database='postgres'  # Подключаемся к системной БД
        )
        conn.autocommit = True
        cursor = conn.cursor()
        
        # Создаем базу данных
        db_name = "warehouse_db"
        cursor.execute(sql.SQL("SELECT 1 FROM pg_database WHERE datname = %s"), [db_name])
        
        if not cursor.fetchone():
            cursor.execute(sql.SQL("CREATE DATABASE {}").format(sql.Identifier(db_name)))
            print(f"База данных '{db_name}' создана")
        else:
            print(f"База данных '{db_name}' уже существует")
        
        # Создаем пользователя
        user_name = "warehouse_user"
        user_password = "warehouse_pass"
        
        cursor.execute(sql.SQL("SELECT 1 FROM pg_roles WHERE rolname = %s"), [user_name])
        
        if not cursor.fetchone():
            cursor.execute(sql.SQL("CREATE USER {} WITH PASSWORD %s").format(
                sql.Identifier(user_name)), [user_password])
            print(f"Пользователь '{user_name}' создан")
        else:
            print(f"Пользователь '{user_name}' уже существует")
        
        # Даем права пользователю на базу данных
        cursor.execute(sql.SQL("GRANT ALL PRIVILEGES ON DATABASE {} TO {}").format(
            sql.Identifier(db_name), sql.Identifier(user_name)))
        
        print("Настройка завершена успешно!")
        print(f"\nДанные для подключения:")
        print(f"  База данных: {db_name}")
        print(f"  Пользователь: {user_name}")
        print(f"  Пароль: {user_password}")
        print(f"  Хост: {host}:{port}")
        
        cursor.close()
        conn.close()
        
    except Exception as e:
        print(f"Ошибка при создании базы данных: {e}")
        return False
    
    return True

if __name__ == '__main__':
    create_database()