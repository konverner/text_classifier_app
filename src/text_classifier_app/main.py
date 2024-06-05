from fastapi import FastAPI, Form, Request, Depends, HTTPException, status
from fastapi.responses import HTMLResponse, RedirectResponse
from fastapi.templating import Jinja2Templates
from sqlalchemy import create_engine, Column, Integer, String
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import sessionmaker, Session
from werkzeug.security import generate_password_hash, check_password_hash
from fastapi_login import LoginManager
from fastapi_login.exceptions import InvalidCredentialsException

DATABASE_URL = "sqlite:///./test.db"
SECRET = "admin"  # Change this to a strong secret key

# SQLAlchemy setup
engine = create_engine(DATABASE_URL)
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)
Base = declarative_base()

# Define the User model
class User(Base):
    __tablename__ = "users"

    id = Column(Integer, primary_key=True, index=True)
    login = Column(String, unique=True, index=True)
    password = Column(String)

# Create the database tables
Base.metadata.create_all(bind=engine)

app = FastAPI()
templates = Jinja2Templates(directory="templates")
manager = LoginManager(SECRET, token_url="/login")

def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()

def create_default_admin(db: Session):
    admin_user = db.query(User).filter(User.login == "admin").first()
    if not admin_user:
        hashed_password = generate_password_hash("admin")
        new_admin = User(login="admin", password=hashed_password)
        db.add(new_admin)
        db.commit()

@manager.user_loader()
def load_user(login: str, db: Session = SessionLocal()):
    user = db.query(User).filter(User.login == login).first()
    return user

@app.on_event("startup")
def on_startup():
    db = SessionLocal()
    create_default_admin(db)
    db.close()

@app.get("/", response_class=HTMLResponse)
async def get_registration_page(request: Request):
    return templates.TemplateResponse("registration.html", {"request": request})

@app.get("/login", response_class=HTMLResponse)
async def get_login_page(request: Request):
    return templates.TemplateResponse("login.html", {"request": request})

@app.post("/register", response_class=HTMLResponse)
async def register(request: Request, login: str = Form(...), password: str = Form(...), db: Session = Depends(get_db)):
    existing_user = db.query(User).filter(User.login == login).first()
    
    if existing_user:
        return HTMLResponse("Пользователь с таким логином уже существует!", status_code=400)
    
    hashed_password = generate_password_hash(password)
    new_user = User(login=login, password=hashed_password)
    db.add(new_user)
    db.commit()
    
    return RedirectResponse(url="/login", status_code=302)

@app.post("/login", response_class=HTMLResponse)
async def login(request: Request, response: HTMLResponse, login: str = Form(...), password: str = Form(...), db: Session = Depends(get_db)):
    user = load_user(login)
    
    if not user or not check_password_hash(user.password, password):
        raise InvalidCredentialsException
    
    access_token = manager.create_access_token(data={"sub": login})
    response = RedirectResponse(url="/admin", status_code=302)
    manager.set_cookie(response, access_token)
    return response

@app.get("/admin", response_class=HTMLResponse)
async def get_admin_page(request: Request, db: Session = Depends(get_db), user=Depends(manager)):
    if user.login != "admin":
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Недостаточно прав")

    users = db.query(User).all()
    return templates.TemplateResponse("admin.html", {"request": request, "users": users})

@app.delete("/delete_user/{user_id}", response_class=HTMLResponse)
async def delete_user(user_id: int, db: Session = Depends(get_db), user=Depends(manager)):
    if user.login != "admin":
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Недостаточно прав")

    user_to_delete = db.query(User).filter(User.id == user_id).first()
    
    if user_to_delete:
        db.delete(user_to_delete)
        db.commit()
        return HTMLResponse("Пользователь удален", status_code=200)
    
    return HTMLResponse("Пользователь не найден", status_code=404)

if __name__ == '__main__':
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000)
