import os
import json
import random
import time
import math
from typing import List, Optional

from fastapi import FastAPI, WebSocket, WebSocketDisconnect, Request, Form, Query, HTTPException
from fastapi.responses import RedirectResponse
from fastapi.staticfiles import StaticFiles
from fastapi.templating import Jinja2Templates
from pydantic import BaseModel, field_validator

from sqlalchemy import create_engine, Integer, String, Text
from sqlalchemy.orm import sessionmaker, DeclarativeBase, Mapped, mapped_column


# --- Database setup ---
DATA_DIR = os.path.join(os.getcwd(), 'data')
DB_PATH = os.path.join(DATA_DIR, 'pravda.db')
os.makedirs(DATA_DIR, exist_ok=True)

engine = create_engine(f'sqlite:///{DB_PATH}', connect_args={'check_same_thread': False})
SessionLocal = sessionmaker(bind=engine, autoflush=False, autocommit=False)


class Base(DeclarativeBase):
    pass


class Phrase(Base):
    __tablename__ = 'phrases'
    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    type: Mapped[str] = mapped_column(String(16), index=True)
    language: Mapped[str] = mapped_column(String(8), index=True, default='en')
    category: Mapped[str] = mapped_column(String(32), index=True, default='family')
    text: Mapped[str] = mapped_column(Text)
    created_at: Mapped[int] = mapped_column(Integer, default=lambda: int(time.time() * 1000))
    updated_at: Mapped[int] = mapped_column(Integer, default=lambda: int(time.time() * 1000))


Base.metadata.create_all(engine)


def ensure_language_column():
    with engine.connect() as conn:
        cols = conn.exec_driver_sql('PRAGMA table_info(phrases)').fetchall()
        names = [c[1] for c in cols]
        if 'language' not in names:
            conn.exec_driver_sql("ALTER TABLE phrases ADD COLUMN language TEXT DEFAULT 'en'")
        conn.exec_driver_sql("UPDATE phrases SET language='en' WHERE language IS NULL")


def ensure_category_column():
    with engine.connect() as conn:
        cols = conn.exec_driver_sql('PRAGMA table_info(phrases)').fetchall()
        names = [c[1] for c in cols]
        if 'category' not in names:
            conn.exec_driver_sql("ALTER TABLE phrases ADD COLUMN category TEXT DEFAULT 'family'")
        conn.exec_driver_sql("UPDATE phrases SET category='family' WHERE category IS NULL")


ensure_language_column()
ensure_category_column()


def normalize_type(v: Optional[str]) -> Optional[str]:
    if not v:
        return None
    s = str(v).strip().lower()
    if s in ('truth', 'правда'):
        return 'truth'
    if s in ('dare', 'действие'):
        return 'dare'
    return None


LANGS = {'en'}


def normalize_lang(v: Optional[str]) -> Optional[str]:
    if not v:
        return None
    s = str(v).strip().lower()
    mapping = {
        'русский': 'ru', 'ru': 'ru',
        'английский': 'en', 'english': 'en', 'en': 'en',
        'испанский': 'es', 'spanish': 'es', 'es': 'es',
        'китайский': 'zh', 'chinese': 'zh', 'zh': 'zh',
        'арабский': 'ar', 'arabic': 'ar', 'ar': 'ar',
        'японский': 'ja', 'japanese': 'ja', 'ja': 'ja',
    }
    return mapping.get(s)


def validate_text(text: Optional[str]) -> Optional[str]:
    if text is None:
        return 'Текст обязателен'
    t = str(text).strip()
    if len(t) < 3:
        return 'Минимальная длина фразы — 3 символа'
    if len(t) > 200:
        return 'Максимальная длина фразы — 200 символов'
    if '<' in t or '>' in t:
        return 'Запрещены символы < и >'
    return None


CATEGORIES = ['family', 'party', 'work', 'kids', 'couples', 'travel']


TRUTH_BASE = [
    'Share a childhood memory.',
    'What is your biggest fear?',
    'Describe your perfect day.',
    'What is a habit you want to change?',
    'Who inspires you and why?',
    'What is your guilty pleasure?',
    'Name a secret talent.',
    'What makes you feel loved?',
    'What is your most embarrassing moment?',
    'What is a dream you gave up?',
    'What is your favorite book and why?',
    'When did you last cry and why?',
    'What is your proudest achievement?',
    'What do you value most in friendship?',
    'Share a lesson you learned the hard way.',
    'What motivates you on bad days?',
    'What is your love language?',
    'What is your biggest pet peeve?',
    'What is your biggest goal this year?',
    'What are you grateful for today?',
    'Describe your first crush.',
    'What is a risk you want to take?',
    'What is your favorite family tradition?',
    'What scares you about the future?',
    'Share a funny story.',
    'What is your favorite place?',
    'What is a skill you want to learn?',
    'What is your favorite meal?',
    'What is one thing you cannot live without?',
    'What do you wish people knew about you?',
    'Describe your perfect weekend.',
    'What was your worst job?',
    'What is your favorite memory this year?',
    'What is a song that moves you?',
    'What is your favorite movie and why?',
    'What is your biggest challenge right now?',
    'What do you do to relax?',
    'What is the best advice you ever received?',
    'What would you tell your younger self?',
    'What is your favorite hobby?',
    'What is a tradition you want to start?',
    'What is your favorite holiday?',
    'What is your go-to comfort food?',
    'What is a fear you have overcome?',
    'Share a travel story.',
    'What is your biggest strength?',
    'What is your biggest weakness?',
    'What is your favorite season and why?',
    'What makes you laugh the most?',
    'What is a memory you cherish forever.'
]

DARE_BASE = [
    'Do 10 push-ups.',
    'Sing the chorus of a song.',
    'Dance for 30 seconds.',
    'Compliment the person on your left.',
    'Speak with a funny accent for one minute.',
    'Tell a joke.',
    'Do a plank for 20 seconds.',
    'Act out your favorite movie scene.',
    'Share a fun fact.',
    'Do a silly face for 10 seconds.',
    'Mime brushing your teeth.',
    'Pretend to be a news anchor.',
    'Hum a melody and let others guess.',
    'Walk like a model for 10 seconds.',
    'Do three squats.',
    'Balance a book on your head.',
    'Draw a self-portrait.',
    'Write a compliment and read it aloud.',
    'Share a positive affirmation.',
    'Do 15 jumping jacks.',
    'Pretend you are a chef and describe a dish.',
    'Imitate an animal sound.',
    'Whistle a tune.',
    'Speak only in questions for 30 seconds.',
    'Create a short poem.',
    'Pretend to play the guitar.',
    'Announce a fake weather forecast.',
    'Do a slow-motion run.',
    'Balance on one foot for 15 seconds.',
    'Snap your fingers to a rhythm.',
    'Pretend to take a selfie.',
    'Describe your day in three words.',
    'Make a heart with your hands.',
    'Spell your name backwards.',
    'Pretend to answer a call politely.',
    'Talk like a robot for 20 seconds.',
    'Give yourself a high-five.',
    'Do a quick stretch.',
    'Pretend to be a flight attendant.',
    'Say a tongue twister three times.',
    'Pretend to be a statue for 10 seconds.',
    'Invent a handshake with someone.',
    'Describe your favorite snack dramatically.',
    'Pretend to be a teacher taking attendance.',
    'Make an animal shadow with your hands.',
    'Pretend to be a photographer.',
    'Compliment three things around you.',
    'Do three deep breaths and smile.'
]

def generate_category_texts(category: str, truth_count: int = 50, dare_count: int = 50):
    truths = TRUTH_BASE[:truth_count]
    dares = DARE_BASE[:dare_count]
    return truths, dares


def seed_categories(mode: str = 'replace'):
    now = int(time.time() * 1000)
    with SessionLocal() as db:
        if mode == 'replace':
            db.query(Phrase).delete(synchronize_session=False)
        for cat in CATEGORIES:
            truths, dares = generate_category_texts(cat, 50, 50)
            for t in truths:
                db.add(Phrase(type='truth', language='en', category=cat, text=t, created_at=now, updated_at=now))
            for d in dares:
                db.add(Phrase(type='dare', language='en', category=cat, text=d, created_at=now, updated_at=now))
        db.commit()


seed_categories('replace')


# --- FastAPI app ---
app = FastAPI(
    title='Правда или Действие API',
    description='API, админка, мультиязычность и тестовая страница',
    version='1.1.0',
    swagger_ui_parameters={"defaultModelsExpandDepth": -1, "docExpansion": "none"}
)

app.mount('/static', StaticFiles(directory='static'), name='static')
templates = Jinja2Templates(directory='templates')


class PhraseIn(BaseModel):
    type: str
    text: str
    category: Optional[str] = 'family'

    @field_validator('type')
    @classmethod
    def _normalize_type(cls, v: str):
        nt = normalize_type(v)
        if not nt:
            raise ValueError('Неверный тип. Используйте truth/dare или правда/действие')
        return nt

    @field_validator('text')
    @classmethod
    def _validate_text(cls, v: str):
        err = validate_text(v)
        if err:
            raise ValueError(err)
        return v.strip()

    @field_validator('category')
    @classmethod
    def _normalize_cat(cls, v: Optional[str]):
        if v is None:
            return 'family'
        return str(v).strip() or 'family'


class PhraseOut(BaseModel):
    id: int
    type: str
    language: str
    text: str
    created_at: int
    updated_at: int


# --- WebSocket connections ---
connections: List[WebSocket] = []


async def broadcast(event: str, payload):
    data = json.dumps({'event': event, 'payload': payload})
    for ws in list(connections):
        try:
            await ws.send_text(data)
        except RuntimeError:
            try:
                connections.remove(ws)
            except ValueError:
                pass


def get_all_phrases() -> List[PhraseOut]:
    with SessionLocal() as db:
        items = db.query(Phrase).order_by(Phrase.id.asc()).all()
    return [PhraseOut(id=i.id, type=i.type, language=i.language, text=i.text, created_at=i.created_at, updated_at=i.updated_at) for i in items]


@app.websocket('/ws')
async def ws_endpoint(ws: WebSocket):
    await ws.accept()
    connections.append(ws)
    payload = [x.model_dump() for x in get_all_phrases()]
    await ws.send_text(json.dumps({'event': 'phrases_changed', 'payload': payload}))
    try:
        while True:
            await ws.receive_text()
    except WebSocketDisconnect:
        if ws in connections:
            connections.remove(ws)


# --- REST API ---
@app.get('/api/phrases', response_model=List[PhraseOut])
def list_phrases(category: Optional[str] = Query(default=None)):
    with SessionLocal() as db:
        q = db.query(Phrase)
        if category:
            q = q.filter(Phrase.category == category)
        items = q.order_by(Phrase.id.asc()).all()
        return [PhraseOut(id=i.id, type=i.type, language=i.language, text=i.text, created_at=i.created_at, updated_at=i.updated_at) for i in items]


@app.get('/api/phrases/truth', response_model=List[PhraseOut])
def list_truths(category: Optional[str] = Query(default=None)):
    with SessionLocal() as db:
        q = db.query(Phrase).filter(Phrase.type == 'truth')
        if category:
            q = q.filter(Phrase.category == category)
        items = q.order_by(Phrase.id.asc()).all()
        return [PhraseOut(id=i.id, type=i.type, language=i.language, text=i.text, created_at=i.created_at, updated_at=i.updated_at) for i in items]


@app.get('/api/phrases/dare', response_model=List[PhraseOut])
def list_dares(category: Optional[str] = Query(default=None)):
    with SessionLocal() as db:
        q = db.query(Phrase).filter(Phrase.type == 'dare')
        if category:
            q = q.filter(Phrase.category == category)
        items = q.order_by(Phrase.id.asc()).all()
        return [PhraseOut(id=i.id, type=i.type, language=i.language, text=i.text, created_at=i.created_at, updated_at=i.updated_at) for i in items]


@app.post('/api/phrases', response_model=PhraseOut, status_code=201)
def add_phrase(body: PhraseIn):
    now = int(time.time() * 1000)
    with SessionLocal() as db:
        p = Phrase(type=body.type, language='en', category=body.category, text=body.text.strip(), created_at=now, updated_at=now)
        db.add(p)
        db.commit()
        db.refresh(p)
        out = PhraseOut(id=p.id, type=p.type, language=p.language, text=p.text, created_at=p.created_at, updated_at=p.updated_at)
    # оповещение
    payload = list(map(lambda x: x.model_dump(), get_all_phrases()))
    try:
        import anyio
        anyio.from_thread.run(broadcast, 'phrases_changed', payload)
    except Exception:
        pass
    return out


@app.post('/api/phrases/bulk', status_code=201)
def add_bulk(items: List[PhraseIn]):
    now = int(time.time() * 1000)
    with SessionLocal() as db:
        for body in items:
            p = Phrase(type=body.type, language='en', category=body.category, text=body.text.strip(), created_at=now, updated_at=now)
            db.add(p)
        db.commit()
    payload = list(map(lambda x: x.model_dump(), get_all_phrases()))
    try:
        import anyio
        anyio.from_thread.run(broadcast, 'phrases_changed', payload)
    except Exception:
        pass
    return {'added': len(items)}


@app.put('/api/phrases/{pid}', response_model=PhraseOut)
def update_phrase(pid: int, type: Optional[str] = None, text: Optional[str] = None, language: Optional[str] = None, category: Optional[str] = None):
    with SessionLocal() as db:
        p = db.get(Phrase, pid)
        if not p:
            raise HTTPException(404, 'Фраза не найдена')
        if type is not None:
            nt = normalize_type(type)
            if not nt:
                raise HTTPException(400, 'Неверный тип. Используйте truth/dare или правда/действие')
            p.type = nt
        if text is not None:
            err = validate_text(text)
            if err:
                raise HTTPException(400, err)
            p.text = text.strip()
        if language is not None:
            p.language = 'en'
        if category is not None:
            p.category = (category or '').strip() or 'family'
        p.updated_at = int(time.time() * 1000)
        db.add(p)
        db.commit()
        db.refresh(p)
        out = PhraseOut(id=p.id, type=p.type, language=p.language, text=p.text, created_at=p.created_at, updated_at=p.updated_at)
    payload = list(map(lambda x: x.model_dump(), get_all_phrases()))
    try:
        import anyio
        anyio.from_thread.run(broadcast, 'phrases_changed', payload)
    except Exception:
        pass
    return out


@app.delete('/api/phrases/{pid}', status_code=204)
def delete_phrase(pid: int):
    with SessionLocal() as db:
        p = db.get(Phrase, pid)
        if not p:
            raise HTTPException(404, 'Фраза не найдена')
        db.delete(p)
        db.commit()
    payload = list(map(lambda x: x.model_dump(), get_all_phrases()))
    try:
        import anyio
        anyio.from_thread.run(broadcast, 'phrases_changed', payload)
    except Exception:
        pass
    return


@app.get('/api/random', response_model=PhraseOut)
def random_phrase(type: Optional[str] = Query(default=None), category: Optional[str] = Query(default=None)):
    nt = normalize_type(type)
    with SessionLocal() as db:
        q = db.query(Phrase)
        if nt:
            q = q.filter(Phrase.type == nt)
        if category:
            q = q.filter(Phrase.category == category)
        items = q.all()
        if not items:
            raise HTTPException(404, 'Нет доступных фраз')
        p = random.choice(items)
        return PhraseOut(id=p.id, type=p.type, language=p.language, text=p.text, created_at=p.created_at, updated_at=p.updated_at)


# --- Admin (server-rendered, no JS required) ---
@app.get('/admin')
def admin_page(request: Request, type: str = Query(default='all'), q: str = Query(default=''), category: str = Query(default='all'), show_tester: str = Query(default='0'), ttype: str = Query(default='random'), page: int = Query(default=1), per_page: int = Query(default=25)):
    nt = None if type == 'all' else normalize_type(type)
    cat = None if category == 'all' else (category or '').strip()
    page = max(1, int(page or 1))
    per_page = min(100, max(5, int(per_page or 25)))
    with SessionLocal() as db:
        query = db.query(Phrase)
        if nt:
            query = query.filter(Phrase.type == nt)
        if cat:
            query = query.filter(Phrase.category == cat)
        if q:
            query = query.filter(Phrase.text.ilike(f'%{q}%'))
        total = query.count()
        items = query.order_by(Phrase.id.asc()).offset((page - 1) * per_page).limit(per_page).all()
    with SessionLocal() as db:
        counts = {}
        for c in CATEGORIES:
            counts[c] = db.query(Phrase).filter(Phrase.category == c).count()
    test_phrase = None
    if show_tester == '1':
        nt2 = None if ttype == 'random' else normalize_type(ttype)
        with SessionLocal() as db:
            tq = db.query(Phrase)
            if nt2:
                tq = tq.filter(Phrase.type == nt2)
            if cat:
                tq = tq.filter(Phrase.category == cat)
            titems = tq.all()
        test_phrase = random.choice(titems).text if titems else 'Нет фраз'
    return templates.TemplateResponse('admin.html', {
        'request': request,
        'phrases': items,
        'filter': type,
        'search': q,
        'category': category,
        'categories': CATEGORIES,
        'cat_counts': counts,
        'page': page,
        'per_page': per_page,
        'total': total,
        'pages': max(1, math.ceil(total / per_page)),
        'show_tester': show_tester,
        'ttype': ttype,
        'test_phrase': test_phrase,
        'status': request.query_params.get('status', '')
    })


@app.get('/admin/category/{code}')
def admin_page_category(request: Request, code: str):
    return admin_page(request, category=code)


@app.post('/admin/add')
def admin_add(type: str = Form(...), text: str = Form(...), category: str = Form('family')):
    nt = normalize_type(type)
    if not nt:
        return RedirectResponse('/admin?status=error_type', status_code=303)
    cat = (category or '').strip() or 'family'
    err = validate_text(text)
    if err:
        return RedirectResponse('/admin?status=error_text', status_code=303)
    now = int(time.time() * 1000)
    with SessionLocal() as db:
        p = Phrase(type=nt, language='en', category=cat, text=text.strip(), created_at=now, updated_at=now)
        db.add(p)
        db.commit()
    return RedirectResponse('/admin?status=ok', status_code=303)


@app.post('/admin/clear')
def admin_clear(scope: str = Form(...), category: Optional[str] = Form(None)):
    scope = (scope or '').strip().lower()
    cat = (category or '').strip()
    with SessionLocal() as db:
        if scope == 'all':
            q = db.query(Phrase)
            if cat:
                q = q.filter(Phrase.category == cat)
            q.delete(synchronize_session=False)
        elif scope in ('truth', 'dare'):
            q = db.query(Phrase).filter(Phrase.type == scope)
            if cat:
                q = q.filter(Phrase.category == cat)
            q.delete(synchronize_session=False)
        else:
            return RedirectResponse('/admin?status=error_scope', status_code=303)
        db.commit()
    payload = list(map(lambda x: x.model_dump(), get_all_phrases()))
    try:
        import anyio
        anyio.from_thread.run(broadcast, 'phrases_changed', payload)
    except Exception:
        pass
    return RedirectResponse('/admin?status=ok', status_code=303)


@app.post('/admin/bulk-add')
def admin_bulk_add(type: str = Form(...), category: str = Form('family'), lines: str = Form(...)):
    nt = normalize_type(type)
    if not nt:
        return RedirectResponse('/admin?status=error_type', status_code=303)
    cat = (category or '').strip() or 'family'
    rows = [r.strip() for r in (lines or '').splitlines()]
    rows = [r for r in rows if r]
    if not rows:
        return RedirectResponse('/admin?status=empty', status_code=303)
    now = int(time.time() * 1000)
    with SessionLocal() as db:
        for r in rows:
            if validate_text(r):
                continue
            db.add(Phrase(type=nt, language='en', category=cat, text=r, created_at=now, updated_at=now))
        db.commit()
    payload = list(map(lambda x: x.model_dump(), get_all_phrases()))
    try:
        import anyio
        anyio.from_thread.run(broadcast, 'phrases_changed', payload)
    except Exception:
        pass
    return RedirectResponse('/admin?status=ok', status_code=303)


@app.post('/admin/bulk-replace')
def admin_bulk_replace(scope: str = Form(...), category: str = Form('family'), lines: str = Form(...)):
    scope = (scope or '').strip().lower()
    if scope not in ('truth', 'dare'):
        return RedirectResponse('/admin?status=error_scope', status_code=303)
    cat = (category or '').strip() or 'family'
    rows = [r.strip() for r in (lines or '').splitlines()]
    rows = [r for r in rows if r]
    now = int(time.time() * 1000)
    with SessionLocal() as db:
        db.query(Phrase).filter(Phrase.type == scope, Phrase.category == cat).delete(synchronize_session=False)
        for r in rows:
            if validate_text(r):
                continue
            db.add(Phrase(type=scope, language='en', category=cat, text=r, created_at=now, updated_at=now))
        db.commit()
    payload = list(map(lambda x: x.model_dump(), get_all_phrases()))
    try:
        import anyio
        anyio.from_thread.run(broadcast, 'phrases_changed', payload)
    except Exception:
        pass
    return RedirectResponse('/admin?status=ok', status_code=303)

@app.post('/admin/update/{pid}')
def admin_update(pid: int, type: Optional[str] = Form(None), text: Optional[str] = Form(None), category: Optional[str] = Form(None)):
    with SessionLocal() as db:
        p = db.get(Phrase, pid)
        if not p:
            return RedirectResponse('/admin?status=notfound', status_code=303)
        if type is not None:
            nt = normalize_type(type)
            if not nt:
                return RedirectResponse('/admin?status=error_type', status_code=303)
            p.type = nt
        if text is not None:
            err = validate_text(text)
            if err:
                return RedirectResponse('/admin?status=error_text', status_code=303)
            p.text = text.strip()
        if category is not None:
            p.category = (category or '').strip() or 'family'
        p.updated_at = int(time.time() * 1000)
        db.add(p)
        db.commit()
    return RedirectResponse('/admin?status=ok', status_code=303)


@app.get('/api/base')
def full_base():
    with SessionLocal() as db:
        items = db.query(Phrase).order_by(Phrase.id.asc()).all()
    result = {}
    for p in items:
        cat = p.category or 'family'
        if cat not in result:
            result[cat] = { 'actions': [], 'questions': [] }
        if p.type == 'dare':
            result[cat]['actions'].append(p.text)
        else:
            result[cat]['questions'].append(p.text)
    return result

@app.post('/admin/delete/{pid}')
def admin_delete(pid: int):
    with SessionLocal() as db:
        p = db.get(Phrase, pid)
        if p:
            db.delete(p)
            db.commit()
    return RedirectResponse('/admin?status=ok', status_code=303)


# Root redirect to admin
@app.get('/')
def root():
    return RedirectResponse('/admin')


@app.get('/tester')
def tester_page(request: Request, type: str = Query(default='random'), category: str = Query(default='family')):
    nt = None if type == 'random' else normalize_type(type)
    cat = (category or '').strip() or 'family'
    with SessionLocal() as db:
        q = db.query(Phrase)
        if nt:
            q = q.filter(Phrase.type == nt)
        q = q.filter(Phrase.category == cat)
        items = q.all()
    phrase = random.choice(items).text if items else 'Нет фраз'
    return templates.TemplateResponse('tester.html', {
        'request': request,
        'type': type,
        'category': cat,
        'categories': CATEGORIES,
        'phrase': phrase,
    })
# --- Helpers to generate language-specific texts ---
def purge_non_english():
    with SessionLocal() as db:
        db.query(Phrase).filter(Phrase.language != 'en').delete(synchronize_session=False)
        db.commit()

purge_non_english()
