import pymysql
import sys
import logging

if hasattr(sys.stdout, 'reconfigure'):
    sys.stdout.reconfigure(encoding='utf-8')

try:
    from config import MYSQL_HOST, MYSQL_PORT, MYSQL_USER, MYSQL_PASSWORD, MYSQL_DB
except ImportError:
    from backend.config import MYSQL_HOST, MYSQL_PORT, MYSQL_USER, MYSQL_PASSWORD, MYSQL_DB

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger("db")


def get_connection(host=None, port=None, user=None, password=None, db=None, connect_timeout=5):
    """Tạo kết nối tới database MySQL."""
    h = host if host is not None else MYSQL_HOST
    p = port if port is not None else MYSQL_PORT
    u = user if user is not None else MYSQL_USER
    pwd = password if password is not None else MYSQL_PASSWORD
    database = db if db is not None else (MYSQL_DB if MYSQL_DB else None)

    connection_kwargs = {
        "host": h,
        "port": p,
        "user": u,
        "password": pwd,
        "connect_timeout": connect_timeout,
        "autocommit": True,
        "cursorclass": pymysql.cursors.DictCursor
    }
    if database:
        connection_kwargs["database"] = database

    return pymysql.connect(**connection_kwargs)
