from sqlalchemy import create_engine
import configparser
from sshtunnel import SSHTunnelForwarder
import pandas as pd

config = configparser.ConfigParser()
config.read('config.ini')

SSH_SERV = config['DATABASE']['ssh_server']
SSH_USER = config['DATABASE']['ssh_user']
SSH_PASS = config['DATABASE']['ssh_pass']

MYSQL_HOST = config['DATABASE']['mysql_host']
MYSQL_USER = config['DATABASE']['mysql_user']
MYSQL_DB = config['DATABASE']['mysql_db']
MYSQL_PASS = config['DATABASE']['mysql_pass']

SERVER = SSHTunnelForwarder((SSH_SERV, 22),
                            ssh_password=SSH_PASS,
                            ssh_username=SSH_USER,
                            remote_bind_address=('127.0.0.1', 3306))

SERVER.start()


def connect():
    engine = create_engine(
        f"mysql+pymysql://{MYSQL_USER}:{MYSQL_PASS}@{MYSQL_HOST}:{SERVER.local_bind_port}/{MYSQL_DB}"
    )
    conn = engine.connect()
    return conn


def run_query(query):
    conn = connect()
    results = pd.read_sql(query, conn)

    return results