import os
from pathlib import Path
from urllib.parse import quote_plus

from dotenv import load_dotenv
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

# Load .env from same folder as this file
load_dotenv(dotenv_path=Path(__file__).with_name(".env"))

server = os.getenv("MSSQL_SERVER")
db = os.getenv("MSSQL_DB")
user = os.getenv("MSSQL_USER")
pwd = os.getenv("MSSQL_PASSWORD")
driver = os.getenv("MSSQL_DRIVER", "ODBC Driver 17 for SQL Server")

if not all([server, db, user, pwd]):
    raise RuntimeError("Missing one or more .env values: MSSQL_SERVER, MSSQL_DB, MSSQL_USER, MSSQL_PASSWORD")

# Minimal ODBC string (match your successful pyodbc test)
odbc = (
    f"DRIVER={{{driver}}};"
    f"SERVER={server};"
    f"DATABASE={db};"
    f"UID={user};"
    f"PWD={pwd};"
    f"TrustServerCertificate=yes;"
    f"Encrypt=no;"
)

engine = create_engine(
    "mssql+pyodbc:///?odbc_connect=" + quote_plus(odbc),
    pool_pre_ping=True,
    connect_args={"timeout": 5},  # <-- pyodbc timeout (seconds)
    future=True,
)

SessionLocal = sessionmaker(bind=engine, autocommit=False, autoflush=False, future=True)