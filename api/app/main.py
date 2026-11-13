from fastapi import FastAPI, Depends, HTTPException, status, Form, Request
from fastapi.security import OAuth2PasswordRequestForm
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
from fastapi.routing import APIRouter
from jose import JWTError, jwt
from passlib.context import CryptContext
from pydantic import BaseModel
from sqlalchemy import create_engine, Column, Integer, String, Text, ForeignKey, Float, DateTime
from sqlalchemy.orm import sessionmaker, declarative_base, Session, relationship
from sqlalchemy.exc import SQLAlchemyError
from typing import Optional, List
from datetime import datetime, timedelta
import os

# Configuración y constantes
AUTH_SECRET = os.getenv("AUTH_SECRET", "secret-key-change-me")
ALGORITHM = "HS256"
ACCESS_TOKEN_EXPIRE_MINUTES = 60 * 24 * 7  # 7 días

DATABASE_URL = os.getenv(
    "DATABASE_URL",
    "sqlite:///./app.db"
)

# Motor y sesión SQLAlchemy
try:
    engine = create_engine(DATABASE_URL, connect_args={"check_same_thread": False} if DATABASE_URL.startswith("sqlite") else {})
    SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)
    Base = declarative_base()
    # Test connection
    with engine.connect() as conn:
        pass
except Exception:
    # Fallback a SQLite local
    DATABASE_URL = "sqlite:///./app.db"
    engine = create_engine(DATABASE_URL, connect_args={"check_same_thread": False})
    SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)
    Base = declarative_base()

# Contexto para hashing de contraseñas
pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")

# FastAPI app con root_path para que /docs y /openapi.json funcionen bajo /api
app = FastAPI(root_path="/api")

# CORS (permitir frontend local y producción)
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # En producción restringir a dominios específicos
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Modelos SQLAlchemy

class User(Base):
    __tablename__ = "users"
    id = Column(Integer, primary_key=True, index=True)
    username = Column(String(50), unique=True, index=True, nullable=False)
    hashed_password = Column(String(128), nullable=False)
    full_name = Column(String(100), nullable=True)

    cotizaciones = relationship("Cotizacion", back_populates="owner")
    proyectos = relationship("Proyecto", back_populates="owner")

class Cotizacion(Base):
    __tablename__ = "cotizaciones"
    id = Column(Integer, primary_key=True, index=True)
    titulo = Column(String(150), nullable=False)
    descripcion = Column(Text, nullable=True)
    fecha_creacion = Column(DateTime, default=datetime.utcnow)
    estado = Column(String(50), default="pendiente")  # pendiente, aceptada, rechazada
    cliente = Column(String(100), nullable=True)
    total = Column(Float, default=0.0)

    owner_id = Column(Integer, ForeignKey("users.id"))
    owner = relationship("User", back_populates="cotizaciones")

class Proyecto(Base):
    __tablename__ = "proyectos"
    id = Column(Integer, primary_key=True, index=True)
    nombre = Column(String(150), nullable=False)
    descripcion = Column(Text, nullable=True)
    fecha_inicio = Column(DateTime, default=datetime.utcnow)
    fecha_fin = Column(DateTime, nullable=True)
    estado = Column(String(50), default="activo")  # activo, finalizado, cancelado
    presupuesto = Column(Float, default=0.0)

    owner_id = Column(Integer, ForeignKey("users.id"))
    owner = relationship("User", back_populates="proyectos")

# Crear tablas si no existen
Base.metadata.create_all(bind=engine)

# Pydantic Schemas

class Token(BaseModel):
    access_token: str
    token_type: str

class TokenData(BaseModel):
    username: Optional[str] = None

class UserBase(BaseModel):
    username: str
    full_name: Optional[str] = None

class UserCreate(UserBase):
    password: str

class UserOut(UserBase):
    id: int

    class Config:
        orm_mode = True

class CotizacionBase(BaseModel):
    titulo: str
    descripcion: Optional[str] = None
    estado: Optional[str] = "pendiente"
    cliente: Optional[str] = None
    total: Optional[float] = 0.0

class CotizacionCreate(CotizacionBase):
    pass

class CotizacionOut(CotizacionBase):
    id: int
    fecha_creacion: datetime
    owner_id: int

    class Config:
        orm_mode = True

class ProyectoBase(BaseModel):
    nombre: str
    descripcion: Optional[str] = None
    estado: Optional[str] = "activo"
    presupuesto: Optional[float] = 0.0
    fecha_fin: Optional[datetime] = None

class ProyectoCreate(ProyectoBase):
    pass

class ProyectoOut(ProyectoBase):
    id: int
    fecha_inicio: datetime
    owner_id: int

    class Config:
        orm_mode = True

# Utilidades de seguridad

def verify_password(plain_password: str, hashed_password: str) -> bool:
    return pwd_context.verify(plain_password, hashed_password)

def get_password_hash(password: str) -> str:
    return pwd_context.hash(password)

def create_access_token(data: dict, expires_delta: Optional[timedelta] = None) -> str:
    to_encode = data.copy()
    expire = datetime.utcnow() + (expires_delta if expires_delta else timedelta(minutes=ACCESS_TOKEN_EXPIRE_MINUTES))
    to_encode.update({"exp": expire})
    encoded_jwt = jwt.encode(to_encode, AUTH_SECRET, algorithm=ALGORITHM)
    return encoded_jwt

def decode_access_token(token: str) -> Optional[TokenData]:
    try:
        payload = jwt.decode(token, AUTH_SECRET, algorithms=[ALGORITHM])
        username: str = payload.get("sub")
        if username is None:
            return None
        return TokenData(username=username)
    except JWTError:
        return None

# Dependencias

def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()

def get_user_by_username(db: Session, username: str) -> Optional[User]:
    return db.query(User).filter(User.username == username).first()

def authenticate_user(db: Session, username: str, password: str) -> Optional[User]:
    user = get_user_by_username(db, username)
    if not user:
        return None
    if not verify_password(password, user.hashed_password):
        return None
    return user

async def get_current_user(request: Request, db: Session = Depends(get_db)) -> User:
    auth_header = request.headers.get("Authorization")
    if not auth_header or not auth_header.startswith("Bearer "):
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="No autorizado")
    token = auth_header[7:]
    token_data = decode_access_token(token)
    if not token_data or not token_data.username:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Token inválido o expirado")
    user = get_user_by_username(db, token_data.username)
    if not user:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Usuario no encontrado")
    return user

# Routers

router = APIRouter(prefix="/api")

# Healthcheck

@router.get("/health")
def health():
    return {"status": "ok"}

# Auth endpoints

@router.post("/auth/register", response_model=UserOut)
def register(username: str = Form(...), password: str = Form(...), full_name: Optional[str] = Form(None), db: Session = Depends(get_db)):
    if get_user_by_username(db, username):
        raise HTTPException(status_code=400, detail="El usuario ya existe")
    hashed_password = get_password_hash(password)
    user = User(username=username, hashed_password=hashed_password, full_name=full_name)
    db.add(user)
    db.commit()
    db.refresh(user)
    return user

@router.post("/auth/login", response_model=Token)
def login(form_data: OAuth2PasswordRequestForm = Depends(), db: Session = Depends(get_db)):
    user = authenticate_user(db, form_data.username, form_data.password)
    if not user:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Usuario o contraseña incorrectos")
    access_token = create_access_token(data={"sub": user.username})
    return {"access_token": access_token, "token_type": "bearer"}

@router.get("/auth/me", response_model=UserOut)
async def read_users_me(current_user: User = Depends(get_current_user)):
    return current_user

# CRUD Cotizaciones

@router.post("/cotizaciones", response_model=CotizacionOut)
def create_cotizacion(cotizacion: CotizacionCreate, current_user: User = Depends(get_current_user), db: Session = Depends(get_db)):
    db_cot = Cotizacion(**cotizacion.dict(), owner_id=current_user.id)
    db.add(db_cot)
    db.commit()
    db.refresh(db_cot)
    return db_cot

@router.get("/cotizaciones", response_model=List[CotizacionOut])
def list_cotizaciones(current_user: User = Depends(get_current_user), db: Session = Depends(get_db)):
    return db.query(Cotizacion).filter(Cotizacion.owner_id == current_user.id).all()

@router.get("/cotizaciones/{cotizacion_id}", response_model=CotizacionOut)
def get_cotizacion(cotizacion_id: int, current_user: User = Depends(get_current_user), db: Session = Depends(get_db)):
    cot = db.query(Cotizacion).filter(Cotizacion.id == cotizacion_id, Cotizacion.owner_id == current_user.id).first()
    if not cot:
        raise HTTPException(status_code=404, detail="Cotización no encontrada")
    return cot

@router.put("/cotizaciones/{cotizacion_id}", response_model=CotizacionOut)
def update_cotizacion(cotizacion_id: int, cotizacion: CotizacionCreate, current_user: User = Depends(get_current_user), db: Session = Depends(get_db)):
    db_cot = db.query(Cotizacion).filter(Cotizacion.id == cotizacion_id, Cotizacion.owner_id == current_user.id).first()
    if not db_cot:
        raise HTTPException(status_code=404, detail="Cotización no encontrada")
    for key, value in cotizacion.dict().items():
        setattr(db_cot, key, value)
    db.commit()
    db.refresh(db_cot)
    return db_cot

@router.delete("/cotizaciones/{cotizacion_id}", status_code=204)
def delete_cotizacion(cotizacion_id: int, current_user: User = Depends(get_current_user), db: Session = Depends(get_db)):
    db_cot = db.query(Cotizacion).filter(Cotizacion.id == cotizacion_id, Cotizacion.owner_id == current_user.id).first()
    if not db_cot:
        raise HTTPException(status_code=404, detail="Cotización no encontrada")
    db.delete(db_cot)
    db.commit()
    return JSONResponse(status_code=204, content=None)

# CRUD Proyectos

@router.post("/proyectos", response_model=ProyectoOut)
def create_proyecto(proyecto: ProyectoCreate, current_user: User = Depends(get_current_user), db: Session = Depends(get_db)):
    db_proy = Proyecto(**proyecto.dict(), owner_id=current_user.id)
    db.add(db_proy)
    db.commit()
    db.refresh(db_proy)
    return db_proy

@router.get("/proyectos", response_model=List[ProyectoOut])
def list_proyectos(current_user: User = Depends(get_current_user), db: Session = Depends(get_db)):
    return db.query(Proyecto).filter(Proyecto.owner_id == current_user.id).all()

@router.get("/proyectos/{proyecto_id}", response_model=ProyectoOut)
def get_proyecto(proyecto_id: int, current_user: User = Depends(get_current_user), db: Session = Depends(get_db)):
    proy = db.query(Proyecto).filter(Proyecto.id == proyecto_id, Proyecto.owner_id == current_user.id).first()
    if not proy:
        raise HTTPException(status_code=404, detail="Proyecto no encontrado")
    return proy

@router.put("/proyectos/{proyecto_id}", response_model=ProyectoOut)
def update_proyecto(proyecto_id: int, proyecto: ProyectoCreate, current_user: User = Depends(get_current_user), db: Session = Depends(get_db)):
    db_proy = db.query(Proyecto).filter(Proyecto.id == proyecto_id, Proyecto.owner_id == current_user.id).first()
    if not db_proy:
        raise HTTPException(status_code=404, detail="Proyecto no encontrado")
    for key, value in proyecto.dict().items():
        setattr(db_proy, key, value)
    db.commit()
    db.refresh(db_proy)
    return db_proy

@router.delete("/proyectos/{proyecto_id}", status_code=204)
def delete_proyecto(proyecto_id: int, current_user: User = Depends(get_current_user), db: Session = Depends(get_db)):
    db_proy = db.query(Proyecto).filter(Proyecto.id == proyecto_id, Proyecto.owner_id == current_user.id).first()
    if not db_proy:
        raise HTTPException(status_code=404, detail="Proyecto no encontrado")
    db.delete(db_proy)
    db.commit()
    return JSONResponse(status_code=204, content=None)

# Montar router en la app
app.include_router(router)