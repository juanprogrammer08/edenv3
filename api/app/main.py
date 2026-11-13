from fastapi import FastAPI, Depends, HTTPException, status, Form, Request
from fastapi.security import OAuth2PasswordRequestForm
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
from fastapi.routing import APIRouter
from jose import JWTError, jwt
from passlib.context import CryptContext
from sqlalchemy import create_engine, select, update, delete
from sqlalchemy.exc import SQLAlchemyError
from sqlalchemy.orm import sessionmaker, declarative_base, Session
from sqlalchemy import Column, Integer, String, Text, Float, ForeignKey, DateTime, Boolean
from sqlalchemy.orm import relationship
from datetime import datetime, timedelta
import os
import logging

# Configuración de logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Variables de entorno y configuración
AUTH_SECRET = os.getenv("AUTH_SECRET", "cambiasecretodefault")
ALGORITHM = "HS256"
ACCESS_TOKEN_EXPIRE_MINUTES = 60 * 24 * 7  # 7 días

DATABASE_URL = os.getenv(
    "DATABASE_URL",
    "sqlite:///./app.db"
)

# Base de datos y sesión
Base = declarative_base()

def get_engine():
    try:
        engine = create_engine(DATABASE_URL, connect_args={"check_same_thread": False} if DATABASE_URL.startswith("sqlite") else {})
        # Probar conexión
        with engine.connect() as conn:
            conn.execute("SELECT 1")
        logger.info(f"Conectado a base de datos: {DATABASE_URL}")
        return engine
    except Exception as e:
        logger.error(f"No se pudo conectar a la base de datos principal: {e}")
        # Fallback a SQLite local
        fallback_url = "sqlite:///./app.db"
        engine = create_engine(fallback_url, connect_args={"check_same_thread": False})
        logger.info(f"Usando base de datos fallback SQLite: {fallback_url}")
        return engine

engine = get_engine()
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)

# Modelos SQLAlchemy

class User(Base):
    __tablename__ = "users"
    id = Column(Integer, primary_key=True, index=True)
    username = Column(String(50), unique=True, index=True, nullable=False)
    hashed_password = Column(String(128), nullable=False)
    is_active = Column(Boolean, default=True)
    created_at = Column(DateTime, default=datetime.utcnow)

    cotizaciones = relationship("Cotizacion", back_populates="owner")
    proyectos = relationship("Proyecto", back_populates="owner")

class Cotizacion(Base):
    __tablename__ = "cotizaciones"
    id = Column(Integer, primary_key=True, index=True)
    titulo = Column(String(100), nullable=False)
    descripcion = Column(Text, nullable=True)
    fecha_creacion = Column(DateTime, default=datetime.utcnow)
    estado = Column(String(30), default="pendiente")  # pendiente, aceptada, rechazada
    cliente = Column(String(100), nullable=True)
    total = Column(Float, default=0.0)

    owner_id = Column(Integer, ForeignKey("users.id"))
    owner = relationship("User", back_populates="cotizaciones")

class Proyecto(Base):
    __tablename__ = "proyectos"
    id = Column(Integer, primary_key=True, index=True)
    nombre = Column(String(100), nullable=False)
    descripcion = Column(Text, nullable=True)
    fecha_inicio = Column(DateTime, default=datetime.utcnow)
    fecha_fin = Column(DateTime, nullable=True)
    estado = Column(String(30), default="activo")  # activo, finalizado, cancelado
    cliente = Column(String(100), nullable=True)

    owner_id = Column(Integer, ForeignKey("users.id"))
    owner = relationship("User", back_populates="proyectos")

# Crear tablas
Base.metadata.create_all(bind=engine)

# Seguridad y autenticación
pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")

def verify_password(plain_password: str, hashed_password: str) -> bool:
    return pwd_context.verify(plain_password, hashed_password)

def get_password_hash(password: str) -> str:
    return pwd_context.hash(password)

def create_access_token(data: dict, expires_delta: timedelta | None = None) -> str:
    to_encode = data.copy()
    expire = datetime.utcnow() + (expires_delta if expires_delta else timedelta(minutes=ACCESS_TOKEN_EXPIRE_MINUTES))
    to_encode.update({"exp": expire})
    encoded_jwt = jwt.encode(to_encode, AUTH_SECRET, algorithm=ALGORITHM)
    return encoded_jwt

def decode_access_token(token: str):
    try:
        payload = jwt.decode(token, AUTH_SECRET, algorithms=[ALGORITHM])
        username: str = payload.get("sub")
        if username is None:
            raise JWTError("Token sin sujeto")
        return username
    except JWTError:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Token inválido o expirado",
            headers={"WWW-Authenticate": "Bearer"},
        )

# Dependencias

def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()

from fastapi.security import OAuth2PasswordBearer

oauth2_scheme = OAuth2PasswordBearer(tokenUrl="/api/auth/login")

def get_current_user(token: str = Depends(oauth2_scheme), db: Session = Depends(get_db)) -> User:
    username = decode_access_token(token)
    user = db.execute(select(User).where(User.username == username)).scalar_one_or_none()
    if user is None or not user.is_active:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Usuario no autorizado")
    return user

# FastAPI app y router

app = FastAPI(root_path="/api")

# Permitir CORS para desarrollo local (ajustar en producción)
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

api_router = APIRouter(prefix="/api")

# Rutas públicas

@api_router.get("/health", tags=["salud"])
def health_check():
    return {"status": "ok"}

@api_router.post("/auth/register", tags=["auth"])
def register(username: str = Form(...), password: str = Form(...), db: Session = Depends(get_db)):
    username = username.strip().lower()
    if len(username) < 3 or len(password) < 6:
        raise HTTPException(status_code=400, detail="Usuario o contraseña demasiado cortos")
    existing_user = db.execute(select(User).where(User.username == username)).scalar_one_or_none()
    if existing_user:
        raise HTTPException(status_code=400, detail="El usuario ya existe")
    hashed_password = get_password_hash(password)
    new_user = User(username=username, hashed_password=hashed_password)
    db.add(new_user)
    db.commit()
    db.refresh(new_user)
    return {"msg": "Usuario registrado correctamente"}

@api_router.post("/auth/login", tags=["auth"])
def login(form_data: OAuth2PasswordRequestForm = Depends(), db: Session = Depends(get_db)):
    username = form_data.username.strip().lower()
    user = db.execute(select(User).where(User.username == username)).scalar_one_or_none()
    if not user or not verify_password(form_data.password, user.hashed_password):
        raise HTTPException(status_code=401, detail="Usuario o contraseña incorrectos")
    access_token = create_access_token(data={"sub": user.username})
    return {"access_token": access_token, "token_type": "bearer"}

@api_router.get("/auth/me", tags=["auth"])
def read_current_user(current_user: User = Depends(get_current_user)):
    return {"username": current_user.username, "id": current_user.id, "created_at": current_user.created_at.isoformat()}

# Rutas CRUD protegidas para Cotizaciones

@api_router.post("/cotizaciones", tags=["cotizaciones"])
def create_cotizacion(
    titulo: str = Form(...),
    descripcion: str | None = Form(None),
    cliente: str | None = Form(None),
    total: float | None = Form(0.0),
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    cot = Cotizacion(
        titulo=titulo.strip(),
        descripcion=descripcion.strip() if descripcion else None,
        cliente=cliente.strip() if cliente else None,
        total=total if total else 0.0,
        owner_id=current_user.id,
    )
    db.add(cot)
    db.commit()
    db.refresh(cot)
    return {
        "id": cot.id,
        "titulo": cot.titulo,
        "descripcion": cot.descripcion,
        "cliente": cot.cliente,
        "total": cot.total,
        "estado": cot.estado,
        "fecha_creacion": cot.fecha_creacion.isoformat(),
    }

@api_router.get("/cotizaciones", tags=["cotizaciones"])
def list_cotizaciones(current_user: User = Depends(get_current_user), db: Session = Depends(get_db)):
    cotizaciones = db.execute(select(Cotizacion).where(Cotizacion.owner_id == current_user.id)).scalars().all()
    return [
        {
            "id": c.id,
            "titulo": c.titulo,
            "descripcion": c.descripcion,
            "cliente": c.cliente,
            "total": c.total,
            "estado": c.estado,
            "fecha_creacion": c.fecha_creacion.isoformat(),
        }
        for c in cotizaciones
    ]

@api_router.get("/cotizaciones/{cot_id}", tags=["cotizaciones"])
def get_cotizacion(cot_id: int, current_user: User = Depends(get_current_user), db: Session = Depends(get_db)):
    cot = db.execute(select(Cotizacion).where(Cotizacion.id == cot_id, Cotizacion.owner_id == current_user.id)).scalar_one_or_none()
    if not cot:
        raise HTTPException(status_code=404, detail="Cotización no encontrada")
    return {
        "id": cot.id,
        "titulo": cot.titulo,
        "descripcion": cot.descripcion,
        "cliente": cot.cliente,
        "total": cot.total,
        "estado": cot.estado,
        "fecha_creacion": cot.fecha_creacion.isoformat(),
    }

@api_router.put("/cotizaciones/{cot_id}", tags=["cotizaciones"])
def update_cotizacion(
    cot_id: int,
    titulo: str = Form(...),
    descripcion: str | None = Form(None),
    cliente: str | None = Form(None),
    total: float | None = Form(0.0),
    estado: str = Form("pendiente"),
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    cot = db.execute(select(Cotizacion).where(Cotizacion.id == cot_id, Cotizacion.owner_id == current_user.id)).scalar_one_or_none()
    if not cot:
        raise HTTPException(status_code=404, detail="Cotización no encontrada")
    cot.titulo = titulo.strip()
    cot.descripcion = descripcion.strip() if descripcion else None
    cot.cliente = cliente.strip() if cliente else None
    cot.total = total if total else 0.0
    cot.estado = estado.strip()
    db.commit()
    db.refresh(cot)
    return {
        "id": cot.id,
        "titulo": cot.titulo,
        "descripcion": cot.descripcion,
        "cliente": cot.cliente,
        "total": cot.total,
        "estado": cot.estado,
        "fecha_creacion": cot.fecha_creacion.isoformat(),
    }

@api_router.delete("/cotizaciones/{cot_id}", status_code=204, tags=["cotizaciones"])
def delete_cotizacion(cot_id: int, current_user: User = Depends(get_current_user), db: Session = Depends(get_db)):
    cot = db.execute(select(Cotizacion).where(Cotizacion.id == cot_id, Cotizacion.owner_id == current_user.id)).scalar_one_or_none()
    if not cot:
        raise HTTPException(status_code=404, detail="Cotización no encontrada")
    db.delete(cot)
    db.commit()
    return JSONResponse(status_code=204, content=None)

# Rutas CRUD protegidas para Proyectos

@api_router.post("/proyectos", tags=["proyectos"])
def create_proyecto(
    nombre: str = Form(...),
    descripcion: str | None = Form(None),
    cliente: str | None = Form(None),
    fecha_fin: str | None = Form(None),
    estado: str = Form("activo"),
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    fecha_fin_dt = None
    if fecha_fin:
        try:
            fecha_fin_dt = datetime.fromisoformat(fecha_fin)
        except ValueError:
            raise HTTPException(status_code=400, detail="Formato de fecha_fin inválido, use ISO 8601")
    proyecto = Proyecto(
        nombre=nombre.strip(),
        descripcion=descripcion.strip() if descripcion else None,
        cliente=cliente.strip() if cliente else None,
        fecha_fin=fecha_fin_dt,
        estado=estado.strip(),
        owner_id=current_user.id,
    )
    db.add(proyecto)
    db.commit()
    db.refresh(proyecto)
    return {
        "id": proyecto.id,
        "nombre": proyecto.nombre,
        "descripcion": proyecto.descripcion,
        "cliente": proyecto.cliente,
        "fecha_inicio": proyecto.fecha_inicio.isoformat(),
        "fecha_fin": proyecto.fecha_fin.isoformat() if proyecto.fecha_fin else None,
        "estado": proyecto.estado,
    }

@api_router.get("/proyectos", tags=["proyectos"])
def list_proyectos(current_user: User = Depends(get_current_user), db: Session = Depends(get_db)):
    proyectos = db.execute(select(Proyecto).where(Proyecto.owner_id == current_user.id)).scalars().all()
    return [
        {
            "id": p.id,
            "nombre": p.nombre,
            "descripcion": p.descripcion,
            "cliente": p.cliente,
            "fecha_inicio": p.fecha_inicio.isoformat(),
            "fecha_fin": p.fecha_fin.isoformat() if p.fecha_fin else None,
            "estado": p.estado,
        }
        for p in proyectos
    ]

@api_router.get("/proyectos/{proy_id}", tags=["proyectos"])
def get_proyecto(proy_id: int, current_user: User = Depends(get_current_user), db: Session = Depends(get_db)):
    proyecto = db.execute(select(Proyecto).where(Proyecto.id == proy_id, Proyecto.owner_id == current_user.id)).scalar_one_or_none()
    if not proyecto:
        raise HTTPException(status_code=404, detail="Proyecto no encontrado")
    return {
        "id": proyecto.id,
        "nombre": proyecto.nombre,
        "descripcion": proyecto.descripcion,
        "cliente": proyecto.cliente,
        "fecha_inicio": proyecto.fecha_inicio.isoformat(),
        "fecha_fin": proyecto.fecha_fin.isoformat() if proyecto.fecha_fin else None,
        "estado": proyecto.estado,
    }

@api_router.put("/proyectos/{proy_id}", tags=["proyectos"])
def update_proyecto(
    proy_id: int,
    nombre: str = Form(...),
    descripcion: str | None = Form(None),
    cliente: str | None = Form(None),
    fecha_fin: str | None = Form(None),
    estado: str = Form("activo"),
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    proyecto = db.execute(select(Proyecto).where(Proyecto.id == proy_id, Proyecto.owner_id == current_user.id)).scalar_one_or_none()
    if not proyecto:
        raise HTTPException(status_code=404, detail="Proyecto no encontrado")
    fecha_fin_dt = None
    if fecha_fin:
        try:
            fecha_fin_dt = datetime.fromisoformat(fecha_fin)
        except ValueError:
            raise HTTPException(status_code=400, detail="Formato de fecha_fin inválido, use ISO 8601")
    proyecto.nombre = nombre.strip()
    proyecto.descripcion = descripcion.strip() if descripcion else None
    proyecto.cliente = cliente.strip() if cliente else None
    proyecto.fecha_fin = fecha_fin_dt
    proyecto.estado = estado.strip()
    db.commit()
    db.refresh(proyecto)
    return {
        "id": proyecto.id,
        "nombre": proyecto.nombre,
        "descripcion": proyecto.descripcion,
        "cliente": proyecto.cliente,
        "fecha_inicio": proyecto.fecha_inicio.isoformat(),
        "fecha_fin": proyecto.fecha_fin.isoformat() if proyecto.fecha_fin else None,
        "estado": proyecto.estado,
    }

@api_router.delete("/proyectos/{proy_id}", status_code=204, tags=["proyectos"])
def delete_proyecto(proy_id: int, current_user: User = Depends(get_current_user), db: Session = Depends(get_db)):
    proyecto = db.execute(select(Proyecto).where(Proyecto.id == proy_id, Proyecto.owner_id == current_user.id)).scalar_one_or_none()
    if not proyecto:
        raise HTTPException(status_code=404, detail="Proyecto no encontrado")
    db.delete(proyecto)
    db.commit()
    return JSONResponse(status_code=204, content=None)

# Montar router en app con prefijo /api para todas las rutas
app.include_router(api_router)