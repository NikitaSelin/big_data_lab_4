import os
import psycopg2


class PostgresDB:
    def __init__(self, host='postgres', port=5432):
        dbname = os.getenv('POSTGRES_DB')
        user = os.getenv('POSTGRES_USER')
        password = os.getenv('POSTGRES_PASSWORD')
        self.conn = psycopg2.connect(
            dbname=dbname,
            user=user,
            password=password,
            host=host,
            port=port
        )
        self.cursor = self.conn.cursor()

    def create_table(self):
        self.cursor.execute('''
            CREATE TABLE IF NOT EXISTS results (
                id SERIAL PRIMARY KEY,
                Round VARCHAR(10000),
                air_date_group VARCHAR(10000),
                Question VARCHAR(10000),
                Value INT
            );
        ''')
        self.conn.commit()

    def insert_data(self, round, air_date_group, question, value):
        self.cursor.execute('''
            INSERT INTO results (Round, air_date_group, Question, Value) VALUES (%s, %s, %s, %s);
        ''', (round, air_date_group, question, value))
        self.conn.commit()

    def drop_table(self):
        self.cursor.execute('DROP TABLE IF EXISTS results;')
        self.conn.commit()

    def close(self):
        self.cursor.close()
        self.conn.close()
