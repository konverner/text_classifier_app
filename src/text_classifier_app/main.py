from fastapi import FastAPI, Form, Request
from fastapi.responses import HTMLResponse, RedirectResponse
from fastapi.templating import Jinja2Templates
from pydantic import BaseModel
from werkzeug.security import generate_password_hash, check_password_hash
from typing import Dict

app = FastAPI()
templates = Jinja2Templates(directory="templates")

users: Dict[str, str] = {}

class RegisterForm(BaseModel):
    login: str
    password: str

@app.get("/", response_class=HTMLResponse)
async def get_registration_page(request: Request):
    return templates.TemplateResponse("registration.html", {"request": request})

@app.post("/register", response_class=HTMLResponse)
async def register(request: Request, login: str = Form(...), password: str = Form(...)):
    if login in users:
        return HTMLResponse("Пользователь с таким логином уже существует!", status_code=400)
    
    hashed_password = generate_password_hash(password)
    users[login] = hashed_password
    return RedirectResponse(url="/", status_code=302)

if __name__ == '__main__':
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000)
