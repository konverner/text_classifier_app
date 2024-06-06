from fastapi import FastAPI, Form, Request
from fastapi.responses import HTMLResponse, RedirectResponse, JSONResponse
from fastapi.templating import Jinja2Templates
from pydantic import BaseModel
from werkzeug.security import generate_password_hash, check_password_hash
from typing import Dict, List

from language_model import BertModel
from parser import parse_page


app = FastAPI()
templates = Jinja2Templates(directory="templates")

# Временное хранилище пользователей
users: Dict[str, str] = {"admin": generate_password_hash("admin")}

# Временное хранилище истории проверок
history: List[Dict[str, str]] = []

# Языковая модель
language_model = BertModel("../data/models/")

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
async def get_user_list(request: Request):
    # Prepare user data for the template
    user_list = [{"login": login} for login in users]
    return templates.TemplateResponse("user_list.html", {"request": request, "users": user_list})

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
    
    response = parse_page(request.url)
    
    if response['status']['code'] == 0:
        language_model_output = language_model.run(response["content"]['paragraphs'][:2024] + "...")
        print(f"language_model_output {language_model_output}")

        result = f"Вероятность фейковой новости: {round(1 - language_model_output['score'],3)}"

    if response['status']['code'] == 1:
        result = response['status']['message']
    
    news_text = response['content']['paragraphs']

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
