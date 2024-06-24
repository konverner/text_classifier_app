from sqlalchemy.ext.declarative import declarative_base
from pydantic import BaseModel
from sqlalchemy import Column, Integer, String, ForeignKey
from sqlalchemy.orm import sessionmaker, relationship

Base = declarative_base()
class RegisterForm(BaseModel):
    login: str
    password: str

# Модель для формы входа
class LoginForm(BaseModel):
    login: str
    password: str

class NewsCheckRequest(BaseModel):
    url: str


class User(Base):
    __tablename__ = "users"
    id = Column(Integer, primary_key=True, index=True)
    login = Column(String, unique=True, index=True)
    hashed_password = Column(String)
    role = Column(String, default="user")


class History(Base):
    __tablename__ = "histories"
    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(Integer, ForeignKey("users.id"))
    url = Column(String)
    news_text = Column(String)
    result = Column(String)
    user = relationship("User", back_populates="histories")