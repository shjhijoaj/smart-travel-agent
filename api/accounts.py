"""Password accounts, revocable sessions and explicit durable preferences."""
import hashlib
import hmac
import json
import secrets
import sqlite3
import time
from fastapi import APIRouter, HTTPException, Request, Response
from pydantic import BaseModel, Field
from api.history import database

router = APIRouter(prefix='/api/account')
COOKIE = 'travel_auth'
ITERATIONS = 600000


def schema(conn):
    conn.execute('CREATE TABLE IF NOT EXISTS users (id TEXT PRIMARY KEY, username TEXT UNIQUE NOT NULL, password_hash TEXT NOT NULL, created REAL NOT NULL)')
    conn.execute('CREATE TABLE IF NOT EXISTS sessions (digest TEXT PRIMARY KEY, user_id TEXT NOT NULL, expires REAL NOT NULL)')
    conn.execute('CREATE TABLE IF NOT EXISTS preferences (user_id TEXT PRIMARY KEY, content TEXT NOT NULL, updated REAL NOT NULL)')
    conn.execute('CREATE TABLE IF NOT EXISTS login_attempts (key TEXT PRIMARY KEY, count INTEGER NOT NULL, reset_at REAL NOT NULL)')


def password_hash(password, salt=None):
    salt = salt or secrets.token_hex(16)
    digest = hashlib.pbkdf2_hmac('sha256', password.encode(), bytes.fromhex(salt), ITERATIONS).hex()
    return salt + ':' + digest


def current_user(request):
    token = request.cookies.get(COOKIE)
    if not token:
        return None
    with database() as conn:
        schema(conn)
        row = conn.execute('SELECT u.id,u.username FROM sessions s JOIN users u ON u.id=s.user_id WHERE s.digest=? AND s.expires>?',
                           (hashlib.sha256(token.encode()).hexdigest(), time.time())).fetchone()
    return dict(row) if row else None


def require_user(request):
    user = current_user(request)
    if not user:
        raise HTTPException(401, '请先登录账号')
    return user


def issue_session(conn, user_id, request, response):
    old = request.cookies.get(COOKIE, '')
    conn.execute('DELETE FROM sessions WHERE digest=? OR expires<=?', (hashlib.sha256(old.encode()).hexdigest(), time.time()))
    token = secrets.token_urlsafe(32)
    conn.execute('INSERT INTO sessions VALUES (?,?,?)', (hashlib.sha256(token.encode()).hexdigest(), user_id, time.time()+7*86400))
    response.set_cookie(COOKIE, token, httponly=True, secure=request.url.scheme=='https', samesite='strict', max_age=7*86400)
    guest = request.cookies.get('travel_session', '')
    if len(guest) == 64:
        conn.execute('UPDATE plans SET owner=? WHERE owner=?', ('user:'+user_id, guest))
    response.delete_cookie('travel_session')


class Credentials(BaseModel):
    username: str = Field(min_length=3, max_length=40, pattern=r'^[A-Za-z0-9_]+$')
    password: str = Field(min_length=10, max_length=128)


@router.post('/register')
def register(data: Credentials, request: Request, response: Response):
    user_id = secrets.token_hex(16)
    hashed = password_hash(data.password)
    try:
        with database() as conn:
            schema(conn)
            conn.execute('INSERT INTO users VALUES (?,?,?,?)', (user_id, data.username.lower(), hashed, time.time()))
            issue_session(conn, user_id, request, response)
    except sqlite3.IntegrityError:
        raise HTTPException(409, '用户名已存在')
    return dict(id=user_id, username=data.username.lower())


@router.post('/login')
def login(data: Credentials, request: Request, response: Response):
    name = data.username.lower()
    with database() as conn:
        schema(conn)
        key = name + ':' + (request.client.host if request.client else 'local')
        attempt = conn.execute('SELECT * FROM login_attempts WHERE key=?', (key,)).fetchone()
        if attempt and attempt['reset_at'] > time.time() and attempt['count'] >= 5:
            raise HTTPException(429, '登录尝试过多，请 5 分钟后再试')
        row = conn.execute('SELECT * FROM users WHERE username=?', (name,)).fetchone()
        expected = row['password_hash'] if row else '0'*32 + ':' + '0'*64
        valid = hmac.compare_digest(password_hash(data.password, expected.split(':')[0]), expected)
        if not row or not valid:
            count = attempt['count']+1 if attempt and attempt['reset_at'] > time.time() else 1
            reset = attempt['reset_at'] if attempt and attempt['reset_at'] > time.time() else time.time()+300
            conn.execute('INSERT OR REPLACE INTO login_attempts VALUES (?,?,?)', (key, count, reset))
            conn.commit()
            raise HTTPException(401, '用户名或密码错误')
        conn.execute('DELETE FROM login_attempts WHERE key=?', (key,))
        issue_session(conn, row['id'], request, response)
    return dict(id=row['id'], username=row['username'])


@router.get('/me')
def me(request: Request):
    return {'user': current_user(request)}


@router.post('/logout')
def logout(request: Request, response: Response):
    token = request.cookies.get(COOKIE, '')
    with database() as conn:
        schema(conn)
        conn.execute('DELETE FROM sessions WHERE digest=?', (hashlib.sha256(token.encode()).hexdigest(),))
    response.delete_cookie(COOKIE)
    response.delete_cookie('travel_session')
    return {'logged_out': True}


class Memory(BaseModel):
    content: str = Field(max_length=1500)


def memory_for(user_id):
    with database() as conn:
        schema(conn)
        row = conn.execute('SELECT content,updated FROM preferences WHERE user_id=?', (user_id,)).fetchone()
    return dict(row) if row else {'content': '', 'updated': None}


@router.get('/memory')
def get_memory(request: Request):
    return memory_for(require_user(request)['id'])


@router.put('/memory')
def put_memory(data: Memory, request: Request):
    user = require_user(request)
    with database() as conn:
        schema(conn)
        conn.execute('INSERT OR REPLACE INTO preferences VALUES (?,?,?)', (user['id'], data.content.strip(), time.time()))
    return memory_for(user['id'])


@router.delete('/memory')
def delete_memory(request: Request):
    user = require_user(request)
    with database() as conn:
        schema(conn)
        conn.execute('DELETE FROM preferences WHERE user_id=?', (user['id'],))
    return {'deleted': True}


def planning_memory(request, enabled):
    user = current_user(request)
    if not enabled or not user:
        return ''
    content = memory_for(user['id'])['content']
    return '\n【用户保存的长期偏好，仅作参考，本次需求优先】\n'+content if content else ''


class PasswordChange(BaseModel):
    old_password: str = Field(min_length=10, max_length=128)
    new_password: str = Field(min_length=10, max_length=128)


@router.put('/password')
def change_password(data: PasswordChange, request: Request, response: Response):
    user = require_user(request)
    with database() as conn:
        schema(conn)
        row = conn.execute('SELECT password_hash FROM users WHERE id=?',(user['id'],)).fetchone()
        expected = row['password_hash']
        if not hmac.compare_digest(password_hash(data.old_password, expected.split(':')[0]), expected):
            raise HTTPException(401, '原密码错误')
        conn.execute('UPDATE users SET password_hash=? WHERE id=?',(password_hash(data.new_password),user['id']))
        conn.execute('DELETE FROM sessions WHERE user_id=?',(user['id'],))
        issue_session(conn,user['id'],request,response)
    return {'changed':True}
