import psycopg2
from config import DBNAME, HOST, USER, PASSWORD, PORT


class PostgresAdapter:
    def __init__(self):
        self.__connection = None
        self.__cursor = None


    def connect(self):
        try:
            self.__connection = psycopg2.connect(dbname=DBNAME, user=USER, password=PASSWORD, host=HOST, port=PORT)
            self.__cursor = self.__connection.cursor()
        except psycopg2.Error as e:
            print("Ошибка подключения", e)


    def execute(self, query, params = None):
        if self.__cursor is None:
            return None

        try:
            self.__connection.set_isolation_level(psycopg2.extensions.ISOLATION_LEVEL_SERIALIZABLE)
            self.__cursor = self.__connection.cursor()

            self.__cursor.execute("BEGIN;")
            self.__cursor.execute(query, params)

            self.__connection.commit()

        except psycopg2.Error as e:
            self.__connection.rollback()
            print("Ошибка выполнения запроса", e)


    def fetch_data(self, query, params = None):
        if self.__cursor is None:
            return None

        try:
            self.__cursor.execute(query, params)
            return self.__cursor.fetchall()

        except psycopg2.Error as e:
            print("Ошибка извлечения данных", e)


    def disconnect(self):
        self.__cursor.close()
        self.__connection.close()