from database import SessionLocal, engine
from fastapi import FastAPI, Depends, HTTPException
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials
from pydantic import BaseModel
from sqlalchemy.orm import Session
from sqlalchemy import select, text
from typing import Any
from datetime import date, datetime, timezone, time, timedelta
from decimal import Decimal
from fastapi import Depends, HTTPException

from models import User, ContractDetails
from auth import hash_password, verify_password, create_access_token, decode_token

from pbi_client import pbi_get, pbi_post  # ✅ make sure pbi_post exists in pbi_client.py

app = FastAPI( title="UMS Data & Power BI Metrics API",
    description="API for retrieving UMS contract data and Power BI service metrics",
    version="1.0.0")

# ✅ Create ONLY app-owned tables (NOT views)
User.__table__.create(bind=engine, checkfirst=True)

def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()

# -------- Auth helpers --------
bearer = HTTPBearer(auto_error=False)

def get_current_username(
    creds: HTTPAuthorizationCredentials = Depends(bearer),
) -> str:
    if not creds or creds.scheme.lower() != "bearer":
        raise HTTPException(status_code=401, detail="Missing bearer token")
    try:
        return decode_token(creds.credentials)
    except ValueError:
        raise HTTPException(status_code=401, detail="Invalid token")

class SignUpIn(BaseModel):
    username: str
    password: str

class TokenOut(BaseModel):
    access_token: str
    token_type: str = "bearer"

@app.post("/auth/signup")
def signup(payload: SignUpIn, db: Session = Depends(get_db)):
    username = payload.username.strip().lower()
    if len(username) < 3 or len(payload.password) < 8:
        raise HTTPException(status_code=400, detail="Username min 3 chars; password min 8 chars")

    exists = db.execute(select(User).where(User.username == username)).scalar_one_or_none()
    if exists:
        raise HTTPException(status_code=409, detail="User already exists")

    u = User(username=username, password_hash=hash_password(payload.password))
    db.add(u)
    db.commit()
    return {"message": "User created"}

@app.post("/auth/login", response_model=TokenOut)
def login(payload: SignUpIn, db: Session = Depends(get_db)):
    username = payload.username.strip().lower()
    u = db.execute(select(User).where(User.username == username)).scalar_one_or_none()
    if not u or not verify_password(payload.password, u.password_hash):
        raise HTTPException(status_code=401, detail="Invalid username or password")

    token = create_access_token(sub=username)
    return TokenOut(access_token=token)

@app.get("/me")
def me(username: str = Depends(get_current_username)):
    return {"username": username}

@app.get("/health")
def health():
    return {"status": "ok"}

# -------- View endpoints (read-only) --------
class ContractOut(BaseModel):
    ums_id: int
    cost_Cat_code: str | None = None
    contract_number: str | None = None
    contract_start_date: date | None = None
    contract_end_date: date | None = None
    region_name: str | None = None
    center_name: str | None = None
    total: Decimal | None = None
    created_by: str | None = None
    created_date: datetime | None = None

    class Config:
        from_attributes = True  # Pydantic v2

@app.get("/contracts", response_model=list[ContractOut])
def list_contracts(
    limit: int = 50,
    db: Session = Depends(get_db),
    username: str = Depends(get_current_username),
):
    return db.execute(select(ContractDetails).limit(limit)).scalars().all()

# -------- Stored procedure endpoint --------
@app.get("/contracts/sp/by-ums/{ums_id}")
def sp_contracts_by_ums_id(
    ums_id: int,
    db: Session = Depends(get_db),
    username: str = Depends(get_current_username),
):
    # ✅ Make sure this proc exists in the DB you connected to
    stmt = text("EXEC dbo.usp_GetContractInfo_ByUMSId @ums_id = :ums_id")
    result = db.execute(stmt, {"ums_id": ums_id})
    rows = result.mappings().all()

    if not rows:
        raise HTTPException(status_code=404, detail="No rows returned")
    return rows

# -------- Stored procedure endpoint --------
@app.get("/contracts/sp/by-venue/{searchvenue}")
def sp_contracts_by_venue(
    searchvenue: str,
    db: Session = Depends(get_db),
    username: str = Depends(get_current_username),
):
    # ✅ Make sure this proc exists in the DB you connected to
    stmt = text("EXEC dbo.uspSearch_Contract @searchvenue = :searchvenue")
    result = db.execute(stmt, {"searchvenue": searchvenue})
    rows = result.mappings().all()

    if not rows:
        raise HTTPException(status_code=404, detail="No rows returned")
    return rows

# -------- Power BI endpoints --------
class RefreshRequest(BaseModel):
    notifyOption: str | None = "NoNotification"  # NoNotification, MailOnFailure, MailOnCompletion

@app.get("/pbi/groups/{group_id}/datasets/{dataset_id}/refreshes")
def get_dataset_refresh_history(
    group_id: str,
    dataset_id: str,
    username: str = Depends(get_current_username),
):
    return pbi_get(f"/groups/{group_id}/datasets/{dataset_id}/refreshes")

@app.post("/pbi/groups/{group_id}/datasets/{dataset_id}/refreshes")
def trigger_dataset_refresh(
    group_id: str,
    dataset_id: str,
    payload: RefreshRequest = RefreshRequest(),
    username: str = Depends(get_current_username),
):
    pbi_post(
        f"/groups/{group_id}/datasets/{dataset_id}/refreshes",
        json={"notifyOption": payload.notifyOption},
    )
    return {"status": "submitted"}

@app.get("/pbi/admin/activityevents")
def activity_events(
    start: date,
    end: date,
    username: str = Depends(get_current_username),
):
    if end < start:
        raise HTTPException(status_code=400, detail="end must be >= start")

    all_events = []
    current = datetime.combine(start, time.min).replace(tzinfo=timezone.utc)
    final_end = datetime.combine(end, time.max).replace(tzinfo=timezone.utc)

    while current < final_end:
        next_hour = min(current + timedelta(hours=1), final_end)

        params = {
            "startDateTime": f"'{current.strftime('%Y-%m-%dT%H:%M:%S.000Z')}'",
            "endDateTime": f"'{next_hour.strftime('%Y-%m-%dT%H:%M:%S.000Z')}'",
        }

        data = pbi_get("/admin/activityevents", params=params)
        all_events.extend(data.get("activityEventEntities", []))

        token = data.get("continuationToken")
        while token:
            data = pbi_get(
                "/admin/activityevents",
                params={"continuationToken": f"'{token}'"}
            )
            all_events.extend(data.get("activityEventEntities", []))
            token = data.get("continuationToken")

        current = next_hour

    return {"count": len(all_events), "events": all_events}