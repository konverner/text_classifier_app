from fastapi import FastAPI, Form, Request, Depends, HTTPException
from fastapi.responses import HTMLResponse, RedirectResponse, JSONResponse
from fastapi.templating import Jinja2Templates
from pydantic import BaseModel
from werkzeug.security import generate_password_hash, check_password_hash
from typing import List
from sqlalchemy import Column, Integer, String, create_engine, ForeignKey
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import sessionmaker, relationship

from language_model import BertModel
from parser_utils import parse_page

app = FastAPI()
templates = Jinja2Templates(directory="templates")

DATABASE_URL = "sqlite:///./test.db"

engine = create_engine(DATABASE_URL)
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)
Base = declarative_base()


class User(Base):
    __tablename__ = "users"
    id = Column(Integer, primary_key=True, index=True)
    login = Column(String, unique=True, index=True)
    hashed_password = Column(String)


class History(Base):
    __tablename__ = "histories"
    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(Integer, ForeignKey("users.id"))
    url = Column(String)
    news_text = Column(String)
    result = Column(String)
    user = relationship("User", back_populates="histories")


User.histories = relationship("History", back_populates="user", cascade="all, delete, delete-orphan")

Base.metadata.create_all(bind=engine)

# Языковая модель
language_model = BertModel("seara/rubert-tiny2-russian-sentiment")


# Dependency to get DB session
def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()


# Модель для формы регистрации
class RegisterForm(BaseModel):
    login: str
    password: str


# Модель для формы входа
class LoginForm(BaseModel):
    login: str
    password: str


class NewsCheckRequest(BaseModel):
    url: str


def get_current_user(request: Request, db: SessionLocal = Depends(get_db)):
    user_login = request.cookies.get("user")
    if user_login:
        return db.query(User).filter(User.login == user_login).first()
    return None


@app.get("/", response_class=HTMLResponse)
async def get_registration_page(request: Request):
    return templates.TemplateResponse("index.html", {"request": request})


@app.get("/registration", response_class=HTMLResponse)
async def get_registration_page(request: Request):
    return templates.TemplateResponse("registration.html", {"request": request})


@app.get("/login", response_class=HTMLResponse)
async def get_login_page(request: Request):
    return templates.TemplateResponse("login.html", {"request": request})


@app.get("/user_page", response_class=HTMLResponse)
async def get_user_page(request: Request):
    return templates.TemplateResponse("user_page.html", {"request": request})


@app.get("/admin_page", response_class=HTMLResponse)
async def get_admin_page(request: Request):
    return templates.TemplateResponse("admin_page.html", {"request": request})


@app.get("/user_list", response_class=HTMLResponse)
async def get_user_list(request: Request, db: SessionLocal = Depends(get_db)):
    users = db.query(User).all()
    user_list = [{"login": user.login} for user in users]
    return templates.TemplateResponse("user_list.html", {"request": request, "users": user_list})


@app.get("/history", response_class=HTMLResponse)
async def get_history_page(request: Request, user: User = Depends(get_current_user)):
    return templates.TemplateResponse("history.html", {"request": request, "history": user.histories if user else []})


@app.get("/api/history", response_class=JSONResponse)
async def get_history(user: User = Depends(get_current_user)):
    if user:
        return JSONResponse(content=[{"url": h.url, "news_text": h.news_text, "result": h.result} for h in user.histories])
    return JSONResponse(content=[])


@app.get("/api/user_history/{login}", response_class=JSONResponse)
async def get_user_history(login: str, user: User = Depends(get_current_user), db: SessionLocal = Depends(get_db)):
    if user.login != "admin":
        raise HTTPException(status_code=403, detail="Недостаточно прав для просмотра истории пользователя.")
    user_to_check = db.query(User).filter(User.login == login).first()
    if not user_to_check:
        raise HTTPException(status_code=404, detail="Пользователь не найден.")
    return JSONResponse(content=[{"url": h.url, "news_text": h.news_text, "result": h.result} for h in user_to_check.histories])


@app.post("/register", response_class=HTMLResponse)
async def register(request: Request, login: str = Form(...), password: str = Form(...), db: SessionLocal = Depends(get_db)):
    user = db.query(User).filter(User.login == login).first()
    if user:
        return HTMLResponse("Пользователь с таким логином уже существует!", status_code=400)
    hashed_password = generate_password_hash(password)
    new_user = User(login=login, hashed_password=hashed_password)
    db.add(new_user)
    db.commit()
    db.refresh(new_user)
    return RedirectResponse(url="/login", status_code=302)


@app.post("/login", response_class=HTMLResponse)
async def login(request: Request, login: str = Form(...), password: str = Form(...), db: SessionLocal = Depends(get_db)):
    user = db.query(User).filter(User.login == login).first()
    if not user or not check_password_hash(user.hashed_password, password):
        return HTMLResponse("Неправильный логин или пароль!", status_code=400)
    response = RedirectResponse(url="/admin_page" if login == "admin" else "/user_page", status_code=302)
    response.set_cookie(key="user", value=login)
    return response


@app.delete("/delete_user/{login}", response_class=JSONResponse)
async def delete_user(login: str, user: User = Depends(get_current_user), db: SessionLocal = Depends(get_db)):
    if user.login != "admin":
        raise HTTPException(status_code=403, detail="Недостаточно прав для удаления пользователя.")
    user_to_delete = db.query(User).filter(User.login == login).first()
    if not user_to_delete:
        raise HTTPException(status_code=404, detail="Пользователь не найден.")
    if login == "admin":
        raise HTTPException(status_code=400, detail="Невозможно удалить администратора.")
    db.delete(user_to_delete)
    db.commit()
    return JSONResponse(content={"message": "Пользователь удален."})


@app.post("/api/check_news", response_class=JSONResponse)
async def check_news(request: NewsCheckRequest, user: User = Depends(get_current_user), db: SessionLocal = Depends(get_db)):
    if not user:
        return JSONResponse(content={"error": "Необходима авторизация"}, status_code=403)
    # response = parse_page(request.url)
    response = {
        'status':
            {
                "code": 0,
                "message": "success"
            },
        'content':
            {
                'paragraphs': "test test"
            }
    }
    if response['status']['code'] == 0:
        language_model_output = language_model.run(response["content"]['paragraphs'][:2024] + "...")
        score = round(1 - language_model_output['score'], 3)
        if score <= 0.3:
            score += 0.31
        result = f"Вероятность фейковой новости: {score}"
    else:
        result = response['status']['message']
    news_text = response['content']['paragraphs']
    new_history = History(user_id=user.id, url=request.url, news_text=news_text, result=result)
    db.add(new_history)
    db.commit()
    return {"news_text": news_text, "result": result}


if __name__ == '__main__':
    import uvicorn
    uvicorn.run(app)
