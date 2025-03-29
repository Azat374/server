import os

BASE_DIR = os.path.abspath(os.path.dirname(__file__))
DATABASE_PATH = os.path.join(BASE_DIR, "database", "math_checker.db")

# Используем абсолютный путь
print("DATABASE_PATH:", DATABASE_PATH)  # 🔹 Вывод пути в консоль

SQLALCHEMY_DATABASE_URI = f"sqlite:///{DATABASE_PATH}"
SQLALCHEMY_TRACK_MODIFICATIONS = False
import os
from dotenv import load_dotenv

load_dotenv()

BASE_DIR = os.path.abspath(os.path.dirname(__file__))
DATABASE_PATH = os.path.join(BASE_DIR, "database", "math_checker.db")

class Config:
    SECRET_KEY = os.getenv('SECRET_KEY', '23e629b053aeda6ff423b58a99f861cecd1670e05af7bb9ea55757f419e2a0dcdab40e36e772fbf55ef0ba5533527e4360ad2c25b740336049a9d30667ca126c')
    SQLALCHEMY_DATABASE_URI = f"sqlite:///{DATABASE_PATH}"
    SQLALCHEMY_TRACK_MODIFICATIONS = False
    DEBUG = True
