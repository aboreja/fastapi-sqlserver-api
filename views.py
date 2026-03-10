from sqlalchemy import MetaData, Table
from database import engine

metadata = MetaData()

# If your view is under dbo schema, set schema="dbo"
V_Contrat_Details_P = Table(
    "V_Contrat_Details_P",
    metadata,
    autoload_with=engine,
    schema="dbo",
)