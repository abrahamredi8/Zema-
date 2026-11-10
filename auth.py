"""Private-beta account authentication. Local SQLite storage is EPHEMERAL on Render Free.
Do not use for production customers until persistent DB and email verification exist.
"""
import base64, hashlib, hmac, os, re, secrets, sqlite3, time
from pathlib import Path
from fastapi import APIRouter, HTTPException, Request, Response
from pydantic import BaseModel, Field

router=APIRouter(prefix="/auth",tags=["accounts"])
DB=Path(os.getenv("ZEMAVOICE_USERS_DB","/tmp/zemavoice-users.sqlite3"))
COOKIE="zemavoice_session"
MAX_AGE=60*60*24*7
attempts={}

def db():
    DB.parent.mkdir(parents=True,exist_ok=True)
    c=sqlite3.connect(str(DB),timeout=10)
    c.execute("CREATE TABLE IF NOT EXISTS users (id TEXT PRIMARY KEY, email TEXT NOT NULL UNIQUE, salt BLOB NOT NULL, password_hash BLOB NOT NULL, created_at INTEGER NOT NULL)")
    return c

def secret():
    s=os.getenv("ZEMAVOICE_SESSION_SECRET","")
    if len(s)<32: raise HTTPException(503,"Account login not configured: session secret missing")
    return s.encode()

def hash_password(password,salt):
    return hashlib.scrypt(password.encode(),salt=salt,n=2**14,r=8,p=1,dklen=32)

def token(uid):
    exp=int(time.time())+MAX_AGE
    payload=f"{uid}:{exp}".encode()
    mac=hmac.new(secret(),payload,hashlib.sha256).digest()
    return base64.urlsafe_b64encode(payload+mac).decode().rstrip("=")

def decode_token(value):
    try:
        raw=base64.urlsafe_b64decode(value+"="*(-len(value)%4))
        payload,mac=raw[:-32],raw[-32:]
        if not hmac.compare_digest(mac,hmac.new(secret(),payload,hashlib.sha256).digest()):return None
        uid,exp=payload.decode().rsplit(":",1)
        if int(exp)<time.time():return None
        return uid
    except (ValueError,UnicodeDecodeError,TypeError):return None

def guard(request):
    origin=request.headers.get("origin")
    if origin:
        from urllib.parse import urlsplit
        try:
            o=urlsplit(origin)
            if o.scheme!="https" or o.netloc!=request.headers.get("host"):raise ValueError()
        except ValueError:raise HTTPException(403,"Invalid request origin")
    ip=request.client.host if request.client else "unknown"
    now=time.monotonic()
    history=[t for t in attempts.get(ip,[]) if now-t<900]
    if len(history)>=15:raise HTTPException(429,"Too many login attempts. Try again later.")
    history.append(now);attempts[ip]=history

class Credentials(BaseModel):
    email:str=Field(min_length=5,max_length=254)
    password:str=Field(min_length=12,max_length=128)

def normalized(email):
    e=email.strip().lower()
    if not re.fullmatch(r"[^\s@]+@[^\s@]+\.[^\s@]+",e):raise HTTPException(400,"Enter a valid email address")
    return e

def set_cookie(response,uid):
    response.set_cookie(COOKIE,token(uid),max_age=MAX_AGE,httponly=True,secure=True,samesite="strict",path="/")

@router.post("/register",status_code=201)
def register(creds:Credentials,request:Request,response:Response):
    guard(request)
    email=normalized(creds.email)
    uid=secrets.token_hex(16);salt=os.urandom(16)
    try:
        with db() as c:
            c.execute("INSERT INTO users VALUES (?,?,?,?,?)",(uid,email,salt,hash_password(creds.password,salt),int(time.time())))
    except sqlite3.IntegrityError:raise HTTPException(409,"An account with this email already exists")
    set_cookie(response,uid)
    return {"email":email,"message":"Beta account created"}

@router.post("/login")
def login(creds:Credentials,request:Request,response:Response):
    guard(request);email=normalized(creds.email)
    with db() as c:
        row=c.execute("SELECT id,salt,password_hash FROM users WHERE email=?",(email,)).fetchone()
    if not row or not hmac.compare_digest(hash_password(creds.password,row[1]),row[2]):
        raise HTTPException(401,"Invalid email or password")
    set_cookie(response,row[0])
    return {"email":email,"message":"Signed in"}

@router.get("/me")
def me(request:Request):
    uid=decode_token(request.cookies.get(COOKIE,""))
    if not uid:raise HTTPException(401,"Not signed in")
    with db() as c:
        row=c.execute("SELECT email FROM users WHERE id=?",(uid,)).fetchone()
    if not row:raise HTTPException(401,"Session expired")
    return {"email":row[0]}

@router.post("/logout")
def logout(request:Request,response:Response):
    guard(request)
    response.delete_cookie(COOKIE,path="/",secure=True,httponly=True,samesite="strict")
    return {"message":"Signed out"}
