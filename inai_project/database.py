import os
from sqlalchemy import create_engine
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import sessionmaker
from dotenv import load_dotenv

# ✅ .env ફાઇલમાંથી વાતાવરણ વાચવું
load_dotenv()

# ✅ DATABASE_URL માટેનું મૂલ્ય .env ફાઇલમાંથી મેળવવું
SQLALCHEMY_DATABASE_URL = os.getenv("DATABASE_URL")

# ✅ PostgreSQL માટે કનેક્શન બનાવવું
engine = create_engine(SQLALCHEMY_DATABASE_URL)

# ✅ SessionLocal → દરેક API કોલ માટે નવી ડેટાબેઝ સત્ર આપે છે
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)

# ✅ Base → તમામ મોડલ્સ માટે આધારભૂત ક્લાસ
Base = declarative_base()
