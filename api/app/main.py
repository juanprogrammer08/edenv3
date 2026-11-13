from fastapi import FastAPI, Depends, HTTPException, status, Form, Request
from fastapi.security import OAuth2PasswordRequestForm
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
from fastapi.routing import APIRouter
from jose import JWTError, jwt
from passlib.context import CryptContext
from sqlalchemy import create_engine, select, update, delete
from sqlalchemy.exc import SQLAlchemyError, OperationalError
from sqlalchemy.orm import sessionmaker, declarative_base, Session
from sqlalchemy import Column, Integer, String, Text, Float, ForeignKey, DateTime, Boolean
from sqlalchemy.orm import relationship
from datetime import datetime, timedelta
import os
import logging

# Configuración básica de logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Variables de entorno y configuración
AUTH_SECRET = os.getenv("AUTH_SECRET", "secretclaveparajwt")
DATABASE_URL = os.getenv("DATABASE_URL", "sqlite:///./app.db")
ALGORITHM = "HS256"
ACCESS_TOKEN_EXPIRE_MINUTES = 60 * 24 * 7  # 7 días

# Base de datos y ORM
Base = declarative_base()

# Intento de conexión a PostgreSQL, fallback a SQLite
try:
    engine = create_engine(DATABASE_URL, connect_args={"check_same_thread": False} if DATABASE_URL.startswith("sqlite") else {})
    # Test conexión
    with engine.connect() as conn:
        conn.execute("SELECT 1")
    logger.info(f"Conectado a base de datos: {DATABASE_URL}")
except OperationalError as e:
    logger.warning(f"No se pudo conectar a la base de datos PostgreSQL, usando SQLite local. Error: {e}")
    DATABASE_URL = "sqlite:///./app.db"
    engine = create_engine(DATABASE_URL, connect_args={"check_same_thread": False})
    logger.info("Conectado a base de datos SQLite local ./app.db")

SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)

# Contexto para hashing de contraseñas
pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")

# FastAPI app con root_path para que /docs y /openapi.json funcionen bajo /api
app = FastAPI(root_path="/api", title="EDÉN - Asistente Empresarial Inteligente API")

# CORS (permitir frontend local y producción)
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # En producción restringir a dominios específicos
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Modelos ORM

class User(Base):
    __tablename__ = "users"
    id = Column(Integer, primary_key=True, index=True)
    username = Column(String(50), unique=True, index=True, nullable=False)
    hashed_password = Column(String(128), nullable=False)
    full_name = Column(String(100), nullable=True)
    email = Column(String(100), unique=True, index=True, nullable=True)
    is_active = Column(Boolean, default=True)
    created_at = Column(DateTime, default=datetime.utcnow)

    cotizaciones = relationship("Cotizacion", back_populates="owner")
    proyectos = relationship("Proyecto", back_populates="owner")
    tareas = relationship("Tarea", back_populates="owner")

class Cotizacion(Base):
    __tablename__ = "cotizaciones"
    id = Column(Integer, primary_key=True, index=True)
    titulo = Column(String(150), nullable=False)
    descripcion = Column(Text, nullable=True)
    cliente = Column(String(150), nullable=True)
    fecha_creacion = Column(DateTime, default=datetime.utcnow)
    estado = Column(String(50), default="pendiente")  # pendiente, aceptada, rechazada
    total = Column(Float, default=0.0)

    owner_id = Column(Integer, ForeignKey("users.id"))
    owner = relationship("User", back_populates="cotizaciones")

class Proyecto(Base):
    __tablename__ = "proyectos"
    id = Column(Integer, primary_key=True, index=True)
    nombre = Column(String(150), nullable=False)
    descripcion = Column(Text, nullable=True)
    fecha_inicio = Column(DateTime, nullable=True)
    fecha_fin = Column(DateTime, nullable=True)
    estado = Column(String(50), default="activo")  # activo, finalizado, cancelado

    owner_id = Column(Integer, ForeignKey("users.id"))
    owner = relationship("User", back_populates="proyectos")

class Tarea(Base):
    __tablename__ = "tareas"
    id = Column(Integer, primary_key=True, index=True)
    titulo = Column(String(150), nullable=False)
    descripcion = Column(Text, nullable=True)
    fecha_vencimiento = Column(DateTime, nullable=True)
    completada = Column(Boolean, default=False)

    owner_id = Column(Integer, ForeignKey("users.id"))
    owner = relationship("User", back_populates="tareas")

# Crear tablas si no existen
Base.metadata.create_all(bind=engine)

# Schemas Pydantic para respuestas y peticiones

from pydantic import BaseModel, EmailStr
from typing import Optional, List

class Token(BaseModel):
    access_token: str
    token_type: str

class TokenData(BaseModel):
    username: Optional[str] = None

class UserBase(BaseModel):
    username: str
    full_name: Optional[str] = None
    email: Optional[EmailStr] = None
    is_active: Optional[bool] = True

class UserCreate(UserBase):
    password: str

class UserOut(UserBase):
    id: int

    class Config:
        orm_mode = True

class CotizacionBase(BaseModel):
    titulo: str
    descripcion: Optional[str] = None
    cliente: Optional[str] = None
    estado: Optional[str] = "pendiente"
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
    fecha_inicio: Optional[datetime] = None
    fecha_fin: Optional[datetime] = None
    estado: Optional[str] = "activo"

class ProyectoCreate(ProyectoBase):
    pass

class ProyectoOut(ProyectoBase):
    id: int
    owner_id: int

    class Config:
        orm_mode = True

class TareaBase(BaseModel):
    titulo: str
    descripcion: Optional[str] = None
    fecha_vencimiento: Optional[datetime] = None
    completada: Optional[bool] = False

class TareaCreate(TareaBase):
    pass

class TareaOut(TareaBase):
    id: int
    owner_id: int

    class Config:
        orm_mode = True

# Funciones utilitarias para autenticación y seguridad

def verify_password(plain_password: str, hashed_password: str) -> bool:
    return pwd_context.verify(plain_password, hashed_password)

def get_password_hash(password: str) -> str:
    return pwd_context.hash(password)

def create_access_token(data: dict, expires_delta: timedelta | None = None):
    to_encode = data.copy()
    expire = datetime.utcnow() + (expires_delta if expires_delta else timedelta(minutes=15))
    to_encode.update({"exp": expire})
    encoded_jwt = jwt.encode(to_encode, AUTH_SECRET, algorithm=ALGORITHM)
    return encoded_jwt

def get_user(db: Session, username: str) -> User | None:
    return db.execute(select(User).where(User.username == username)).scalars().first()

def authenticate_user(db: Session, username: str, password: str) -> User | None:
    user = get_user(db, username)
    if not user:
        return None
    if not verify_password(password, user.hashed_password):
        return None
    return user

# Dependencias

def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()

from fastapi.security import OAuth2PasswordBearer

oauth2_scheme = OAuth2PasswordBearer(tokenUrl="/api/auth/login")

async def get_current_user(token: str = Depends(oauth2_scheme), db: Session = Depends(get_db)) -> User:
    credentials_exception = HTTPException(
        status_code=status.HTTP_401_UNAUTHORIZED,
        detail="No se pudo validar las credenciales",
        headers={"WWW-Authenticate": "Bearer"},
    )
    try:
        payload = jwt.decode(token, AUTH_SECRET, algorithms=[ALGORITHM])
        username: str | None = payload.get("sub")
        if username is None:
            raise credentials_exception
        token_data = TokenData(username=username)
    except JWTError:
        raise credentials_exception
    user = get_user(db, username=token_data.username)
    if user is None:
        raise credentials_exception
    if not user.is_active:
        raise HTTPException(status_code=400, detail="Usuario inactivo")
    return user

# Routers

router = APIRouter(prefix="/api")

# Ruta healthcheck pública
@router.get("/health", tags=["health"])
async def health():
    return {"status": "ok"}

# Rutas de autenticación

@router.post("/auth/register", response_model=UserOut, tags=["auth"])
async def register(
    username: str = Form(...),
    password: str = Form(...),
    full_name: str | None = Form(None),
    email: str | None = Form(None),
    db: Session = Depends(get_db),
):
    user = get_user(db, username)
    if user:
        raise HTTPException(status_code=400, detail="El nombre de usuario ya está en uso")
    hashed_password = get_password_hash(password)
    new_user = User(
        username=username,
        hashed_password=hashed_password,
        full_name=full_name,
        email=email,
        is_active=True,
    )
    db.add(new_user)
    db.commit()
    db.refresh(new_user)
    return new_user

@router.post("/auth/login", response_model=Token, tags=["auth"])
async def login(form_data: OAuth2PasswordRequestForm = Depends(), db: Session = Depends(get_db)):
    user = authenticate_user(db, form_data.username, form_data.password)
    if not user:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Usuario o contraseña incorrectos",
            headers={"WWW-Authenticate": "Bearer"},
        )
    access_token_expires = timedelta(minutes=ACCESS_TOKEN_EXPIRE_MINUTES)
    access_token = create_access_token(
        data={"sub": user.username},
        expires_delta=access_token_expires,
    )
    return {"access_token": access_token, "token_type": "bearer"}

@router.get("/auth/me", response_model=UserOut, tags=["auth"])
async def read_users_me(current_user: User = Depends(get_current_user)):
    return current_user

# CRUD Cotizaciones

@router.post("/cotizaciones", response_model=CotizacionOut, tags=["cotizaciones"])
async def create_cotizacion(cotizacion: CotizacionCreate, current_user: User = Depends(get_current_user), db: Session = Depends(get_db)):
    db_cotizacion = Cotizacion(**cotizacion.dict(), owner_id=current_user.id)
    db.add(db_cotizacion)
    db.commit()
    db.refresh(db_cotizacion)
    return db_cotizacion

@router.get("/cotizaciones", response_model=List[CotizacionOut], tags=["cotizaciones"])
async def list_cotizaciones(current_user: User = Depends(get_current_user), db: Session = Depends(get_db)):
    cotizaciones = db.execute(select(Cotizacion).where(Cotizacion.owner_id == current_user.id)).scalars().all()
    return cotizaciones

@router.get("/cotizaciones/{cotizacion_id}", response_model=CotizacionOut, tags=["cotizaciones"])
async def get_cotizacion(cotizacion_id: int, current_user: User = Depends(get_current_user), db: Session = Depends(get_db)):
    cotizacion = db.execute(select(Cotizacion).where(Cotizacion.id == cotizacion_id, Cotizacion.owner_id == current_user.id)).scalars().first()
    if not cotizacion:
        raise HTTPException(status_code=404, detail="Cotización no encontrada")
    return cotizacion

@router.put("/cotizaciones/{cotizacion_id}", response_model=CotizacionOut, tags=["cotizaciones"])
async def update_cotizacion(cotizacion_id: int, cotizacion: CotizacionCreate, current_user: User = Depends(get_current_user), db: Session = Depends(get_db)):
    db_cotizacion = db.execute(select(Cotizacion).where(Cotizacion.id == cotizacion_id, Cotizacion.owner_id == current_user.id)).scalars().first()
    if not db_cotizacion:
        raise HTTPException(status_code=404, detail="Cotización no encontrada")
    for key, value in cotizacion.dict().items():
        setattr(db_cotizacion, key, value)
    db.commit()
    db.refresh(db_cotizacion)
    return db_cotizacion

@router.delete("/cotizaciones/{cotizacion_id}", status_code=204, tags=["cotizaciones"])
async def delete_cotizacion(cotizacion_id: int, current_user: User = Depends(get_current_user), db: Session = Depends(get_db)):
    cotizacion = db.execute(select(Cotizacion).where(Cotizacion.id == cotizacion_id, Cotizacion.owner_id == current_user.id)).scalars().first()
    if not cotizacion:
        raise HTTPException(status_code=404, detail="Cotización no encontrada")
    db.delete(cotizacion)
    db.commit()
    return JSONResponse(status_code=204, content=None)

# CRUD Proyectos

@router.post("/proyectos", response_model=ProyectoOut, tags=["proyectos"])
async def create_proyecto(proyecto: ProyectoCreate, current_user: User = Depends(get_current_user), db: Session = Depends(get_db)):
    db_proyecto = Proyecto(**proyecto.dict(), owner_id=current_user.id)
    db.add(db_proyecto)
    db.commit()
    db.refresh(db_proyecto)
    return db_proyecto

@router.get("/proyectos", response_model=List[ProyectoOut], tags=["proyectos"])
async def list_proyectos(current_user: User = Depends(get_current_user), db: Session = Depends(get_db)):
    proyectos = db.execute(select(Proyecto).where(Proyecto.owner_id == current_user.id)).scalars().all()
    return proyectos

@router.get("/proyectos/{proyecto_id}", response_model=ProyectoOut, tags=["proyectos"])
async def get_proyecto(proyecto_id: int, current_user: User = Depends(get_current_user), db: Session = Depends(get_db)):
    proyecto = db.execute(select(Proyecto).where(Proyecto.id == proyecto_id, Proyecto.owner_id == current_user.id)).scalars().first()
    if not proyecto:
        raise HTTPException(status_code=404, detail="Proyecto no encontrado")
    return proyecto

@router.put("/proyectos/{proyecto_id}", response_model=ProyectoOut, tags=["proyectos"])
async def update_proyecto(proyecto_id: int, proyecto: ProyectoCreate, current_user: User = Depends(get_current_user), db: Session = Depends(get_db)):
    db_proyecto = db.execute(select(Proyecto).where(Proyecto.id == proyecto_id, Proyecto.owner_id == current_user.id)).scalars().first()
    if not db_proyecto:
        raise HTTPException(status_code=404, detail="Proyecto no encontrado")
    for key, value in proyecto.dict().items():
        setattr(db_proyecto, key, value)
    db.commit()
    db.refresh(db_proyecto)
    return db_proyecto

@router.delete("/proyectos/{proyecto_id}", status_code=204, tags=["proyectos"])
async def delete_proyecto(proyecto_id: int, current_user: User = Depends(get_current_user), db: Session = Depends(get_db)):
    proyecto = db.execute(select(Proyecto).where(Proyecto.id == proyecto_id, Proyecto.owner_id == current_user.id)).scalars().first()
    if not proyecto:
        raise HTTPException(status_code=404, detail="Proyecto no encontrado")
    db.delete(proyecto)
    db.commit()
    return JSONResponse(status_code=204, content=None)

# CRUD Tareas

@router.post("/tareas", response_model=TareaOut, tags=["tareas"])
async def create_tarea(tarea: TareaCreate, current_user: User = Depends(get_current_user), db: Session = Depends(get_db)):
    db_tarea = Tarea(**tarea.dict(), owner_id=current_user.id)
    db.add(db_tarea)
    db.commit()
    db.refresh(db_tarea)
    return db_tarea

@router.get("/tareas", response_model=List[TareaOut], tags=["tareas"])
async def list_tareas(current_user: User = Depends(get_current_user), db: Session = Depends(get_db)):
    tareas = db.execute(select(Tarea).where(Tarea.owner_id == current_user.id)).scalars().all()
    return tareas

@router.get("/tareas/{tarea_id}", response_model=TareaOut, tags=["tareas"])
async def get_tarea(tarea_id: int, current_user: User = Depends(get_current_user), db: Session = Depends(get_db)):
    tarea = db.execute(select(Tarea).where(Tarea.id == tarea_id, Tarea.owner_id == current_user.id)).scalars().first()
    if not tarea:
        raise HTTPException(status_code=404, detail="Tarea no encontrada")
    return tarea

@router.put("/tareas/{tarea_id}", response_model=TareaOut, tags=["tareas"])
async def update_tarea(tarea_id: int, tarea: TareaCreate, current_user: User = Depends(get_current_user), db: Session = Depends(get_db)):
    db_tarea = db.execute(select(Tarea).where(Tarea.id == tarea_id, Tarea.owner_id == current_user.id)).scalars().first()
    if not db_tarea:
        raise HTTPException(status_code=404, detail="Tarea no encontrada")
    for key, value in tarea.dict().items():
        setattr(db_tarea, key, value)
    db.commit()
    db.refresh(db_tarea)
    return db_tarea

@router.delete("/tareas/{tarea_id}", status_code=204, tags=["tareas"])
async def delete_tarea(tarea_id: int, current_user: User = Depends(get_current_user), db: Session = Depends(get_db)):
    tarea = db.execute(select(Tarea).where(Tarea.id == tarea_id, Tarea.owner_id == current_user.id)).scalars().first()
    if not tarea:
        raise HTTPException(status_code=404, detail="Tarea no encontrada")
    db.delete(tarea)
    db.commit()
    return JSONResponse(status_code=204, content=None)

# Montar router en la app principal
app.include_router(router)