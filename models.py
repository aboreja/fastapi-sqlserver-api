from sqlalchemy.orm import DeclarativeBase, Mapped, mapped_column
from sqlalchemy import Integer, String, Date, DateTime, Numeric
from decimal import Decimal
from datetime import datetime, date

class Base(DeclarativeBase):
    pass

class User(Base):
    __tablename__ = "app_users"
    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    username: Mapped[str] = mapped_column(String(150), unique=True, index=True)
    password_hash: Mapped[str] = mapped_column(String(255))

class ContractDetails(Base):
    __tablename__ = "V_Contract_Details_P"
    __table_args__ = {"schema": "dbo"}  # change schema if needed

    # SQLAlchemy requires a primary key even for a VIEW.
    # If ums_id is unique in the view, use it:
    ums_id: Mapped[int] = mapped_column(Integer, primary_key=True)
    cost_Cat_code: Mapped[str | None] = mapped_column(String(200))
    contract_number: Mapped[str | None] = mapped_column(String(50))
    contract_start_date: Mapped[date | None] = mapped_column(Date)
    contract_end_date: Mapped[date | None] = mapped_column(Date)
    region_name: Mapped[str | None] = mapped_column(String(50))
    center_name: Mapped[str | None] = mapped_column(String(50))
    total: Mapped[Decimal | None] = mapped_column(Numeric(28, 2))
    created_by: Mapped[str | None] = mapped_column(String(50))
    created_date: Mapped[datetime | None] = mapped_column(DateTime)
    