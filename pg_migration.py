import psycopg2
from config import DBNAME, USER, PASSWORD, HOST, PORT


connection = psycopg2.connect(dbname=DBNAME, user=USER, password=PASSWORD, host=HOST, port=PORT)
cursor = connection.cursor()

query = f"""
    CREATE TABLE IF NOT EXISTS accounts (
        id SERIAL PRIMARY KEY,
        user_id INTEGER NOT NULL,
        name VARCHAR(255),
        init_balance NUMERIC(20, 2),
        balance NUMERIC(20, 2),
        data TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
        
        FOREIGN KEY (user_id) REFERENCES users(id) ON DELETE CASCADE
    )
"""
cursor.execute(query)

query = f"""
    CREATE TABLE IF NOT EXISTS accounts_details (
        id SERIAL PRIMARY KEY,
        account_id INTEGER NOT NULL,
        instrument_id INTEGER NOT NULL,
        purchase_price NUMERIC(20, 2),
        quantity INTEGER,
        sum_price NUMERIC(20, 2),
        data TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
        
        FOREIGN KEY (account_id) REFERENCES accounts(id) ON DELETE CASCADE,
        FOREIGN KEY (instrument_id) REFERENCES instruments(id) ON DELETE CASCADE
    )
"""
cursor.execute(query)

connection.commit()
print("Миграция завершена")
cursor.close()  # закрываем курсор
connection.close()  # закрываем соединение