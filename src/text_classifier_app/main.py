from fastapi import FastAPI, Form, Request, Depends, HTTPException
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

# Временное хранилище истории проверок для каждого пользователя
user_history: Dict[str, List[Dict[str, str]]] = {user: [] for user in users}

# Языковая модель
language_model = BertModel("seara/rubert-tiny2-russian-sentiment")

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

def get_current_user(request: Request):
    return request.cookies.get("user")

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
async def get_history_page(request: Request, user: str = Depends(get_current_user)):
    return templates.TemplateResponse("history.html", {"request": request, "history": user_history.get(user, [])})

@app.get("/api/history", response_class=JSONResponse)
async def get_history(user: str = Depends(get_current_user)):
    return JSONResponse(content=user_history.get(user, []))

@app.get("/api/user_history/{login}", response_class=JSONResponse)
async def get_user_history(login: str, user: str = Depends(get_current_user)):
    if user != "admin":
        raise HTTPException(status_code=403, detail="Недостаточно прав для просмотра истории пользователя.")
    
    if login not in users:
        raise HTTPException(status_code=404, detail="Пользователь не найден.")
    
    return JSONResponse(content=user_history.get(login, []))

@app.post("/register", response_class=HTMLResponse)
async def register(request: Request, login: str = Form(...), password: str = Form(...)):
    if login in users:
        return HTMLResponse("Пользователь с таким логином уже существует!", status_code=400)
    
    hashed_password = generate_password_hash(password)
    users[login] = hashed_password
    user_history[login] = []
    return RedirectResponse(url="/login", status_code=302)

@app.post("/login", response_class=HTMLResponse)
async def login(request: Request, login: str = Form(...), password: str = Form(...)):
    if login not in users or not check_password_hash(users[login], password):
        return HTMLResponse("Неправильный логин или пароль!", status_code=400)
    
    response = RedirectResponse(url="/admin_page" if login == "admin" else "/user_page", status_code=302)
    response.set_cookie(key="user", value=login)
    return response

@app.delete("/delete_user/{login}", response_class=JSONResponse)
async def delete_user(login: str, user: str = Depends(get_current_user)):
    if user != "admin":
        raise HTTPException(status_code=403, detail="Недостаточно прав для удаления пользователя.")
    
    if login not in users:
        raise HTTPException(status_code=404, detail="Пользователь не найден.")
    
    if login == "admin":
        raise HTTPException(status_code=400, detail="Невозможно удалить администратора.")
    
    # Удаление пользователя и его истории
    del users[login]
    del user_history[login]
    
    return JSONResponse(content={"message": "Пользователь удален."})

@app.post("/api/check_news", response_class=JSONResponse)
async def check_news(request: NewsCheckRequest, user: str = Depends(get_current_user)):
    if not user:
        return JSONResponse(content={"error": "Необходима авторизация"}, status_code=403)
    
    # response = parse_page(request.url)
    
    # if response['status']['code'] == 0:
    #     language_model_output = language_model.run(response["content"]['paragraphs'][:2024] + "...")
    #     result = f"Вероятность фейковой новости: {round(1 - language_model_output['score'],3)}"

    # if response['status']['code'] == 1:
    #     result = response['status']['message']
    
    # news_text = response['content']['paragraphs']

    news_text = "Здесь будет текст новости"
    result = f"Вероятность фейковой новости {0.0042}%"

    # Добавление в историю
    user_history[user].append({
        "url": request.url,
        "news_text": news_text,
        "result": result
    })
    
    return {"news_text": news_text, "result": result}

if __name__ == '__main__':
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000)
