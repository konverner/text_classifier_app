from fastapi import FastAPI, Form, Request
from fastapi.responses import HTMLResponse, RedirectResponse, JSONResponse
from fastapi.templating import Jinja2Templates
from pydantic import BaseModel
from werkzeug.security import generate_password_hash, check_password_hash
from typing import Dict, List
import httpx
from bs4 import BeautifulSoup

app = FastAPI()
templates = Jinja2Templates(directory="templates")

# Временное хранилище пользователей
users: Dict[str, str] = {"admin": generate_password_hash("admin")}

# Временное хранилище истории проверок
history: List[Dict[str, str]] = []

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

@app.get("/", response_class=HTMLResponse)
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
async def get_history_page(request: Request):
    return templates.TemplateResponse("user_list.html", {"request": request})

@app.get("/history", response_class=HTMLResponse)
async def get_history_page(request: Request):
    return templates.TemplateResponse("history.html", {"request": request})

@app.get("/api/history", response_class=JSONResponse)
async def get_history():
    return JSONResponse(content=history)

@app.post("/register", response_class=HTMLResponse)
async def register(request: Request, login: str = Form(...), password: str = Form(...)):
    if login in users:
        return HTMLResponse("Пользователь с таким логином уже существует!", status_code=400)
    
    hashed_password = generate_password_hash(password)
    users[login] = hashed_password
    return RedirectResponse(url="/login", status_code=302)

@app.post("/login", response_class=HTMLResponse)
async def login(request: Request, login: str = Form(...), password: str = Form(...)):
    if login not in users or not check_password_hash(users[login], password):
        return HTMLResponse("Неправильный логин или пароль!", status_code=400)
    
    if login == "admin":
        return RedirectResponse(url="/admin_page", status_code=302)
    
    return RedirectResponse(url="/user_page", status_code=302)

@app.post("/api/check_news", response_class=JSONResponse)
async def check_news(request: NewsCheckRequest):
    async with httpx.AsyncClient() as client:
        response = await client.get(request.url)
    
    soup = BeautifulSoup(response.content, "html.parser")
    news_text = " ".join([p.get_text() for p in soup.find_all("p")])
    
    # Логика проверки новости (для примера считаем новость ложной)
    result = "Результат проверки: Ложная новость"
    
    # Добавление в историю
    history.append({
        "url": request.url,
        "news_text": news_text,
        "result": result
    })
    
    return {"news_text": news_text, "result": result}

if __name__ == '__main__':
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000)
