from fastapi import FastAPI, Depends, HTTPException, status, Form, Request, APIRouter
from fastapi.security import OAuth2PasswordBearer
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
from jose import JWTError, jwt
from passlib.context import CryptContext
from sqlalchemy import create_engine, select, update, delete
from sqlalchemy.orm import sessionmaker, declarative_base, Session
from sqlalchemy.exc import SQLAlchemyError
from sqlalchemy import Column, Integer, String, Float, ForeignKey, DateTime, Boolean, Text
from sqlalchemy.orm import relationship
from datetime import datetime, timedelta
import os

# Configuración básica y constantes
AUTH_SECRET = os.getenv("AUTH_SECRET", "cambiameporunasecretomuyseguro")
ALGORITHM = "HS256"
ACCESS_TOKEN_EXPIRE_MINUTES = 60 * 24 * 7  # 7 días

DATABASE_URL = os.getenv(
    "DATABASE_URL",
    "sqlite:///./app.db"
)

# Motor y sesión SQLAlchemy con fallback a SQLite
try:
    engine = create_engine(DATABASE_URL, connect_args={"check_same_thread": False} if DATABASE_URL.startswith("sqlite") else {})
    # Test conexión
    with engine.connect() as conn:
        conn.execute("SELECT 1")
except Exception:
    # Fallback a SQLite local
    engine = create_engine("sqlite:///./app.db", connect_args={"check_same_thread": False})

SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)
Base = declarative_base()

# Contexto para hashing de contraseñas
pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")

oauth2_scheme = OAuth2PasswordBearer(tokenUrl="/api/auth/login")

app = FastAPI(root_path="/api")

# CORS (permitir frontend local y producción)
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # Ajustar en producción
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
    is_active = Column(Boolean, default=True)
    created_at = Column(DateTime, default=datetime.utcnow)

    cotizaciones = relationship("Cotizacion", back_populates="owner")
    proyectos = relationship("Proyecto", back_populates="owner")

class Cotizacion(Base):
    __tablename__ = "cotizaciones"
    id = Column(Integer, primary_key=True, index=True)
    titulo = Column(String(100), nullable=False)
    descripcion = Column(Text, nullable=True)
    monto_estimado = Column(Float, nullable=False)
    fecha_creacion = Column(DateTime, default=datetime.utcnow)
    estado = Column(String(30), default="pendiente")  # pendiente, aceptada, rechazada

    owner_id = Column(Integer, ForeignKey("users.id"))
    owner = relationship("User", back_populates="cotizaciones")

class Proyecto(Base):
    __tablename__ = "proyectos"
    id = Column(Integer, primary_key=True, index=True)
    nombre = Column(String(100), nullable=False)
    descripcion = Column(Text, nullable=True)
    fecha_inicio = Column(DateTime, nullable=True)
    fecha_fin = Column(DateTime, nullable=True)
    estado = Column(String(30), default="activo")  # activo, finalizado, cancelado

    owner_id = Column(Integer, ForeignKey("users.id"))
    owner = relationship("User", back_populates="proyectos")

# Crear tablas
Base.metadata.create_all(bind=engine)

# Funciones utilitarias

def get_password_hash(password: str) -> str:
    return pwd_context.hash(password)

def verify_password(plain_password: str, hashed_password: str) -> bool:
    return pwd_context.verify(plain_password, hashed_password)

def create_access_token(data: dict, expires_delta: timedelta | None = None):
    to_encode = data.copy()
    expire = datetime.utcnow() + (expires_delta if expires_delta else timedelta(minutes=15))
    to_encode.update({"exp": expire})
    encoded_jwt = jwt.encode(to_encode, AUTH_SECRET, algorithm=ALGORITHM)
    return encoded_jwt

def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()

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
    except JWTError:
        raise credentials_exception
    user = db.execute(select(User).where(User.username == username)).scalar_one_or_none()
    if user is None:
        raise credentials_exception
    if not user.is_active:
        raise HTTPException(status_code=400, detail="Usuario inactivo")
    return user

# Rutas públicas y de autenticación

router = APIRouter()

@router.get("/health")
async def health():
    return {"status": "ok"}

@router.post("/auth/register", status_code=201)
async def register(username: str = Form(...), password: str = Form(...), db: Session = Depends(get_db)):
    username = username.strip()
    if len(username) < 3 or len(password) < 6:
        raise HTTPException(status_code=400, detail="Usuario o contraseña demasiado cortos")
    existing_user = db.execute(select(User).where(User.username == username)).scalar_one_or_none()
    if existing_user:
        raise HTTPException(status_code=400, detail="El nombre de usuario ya existe")
    hashed_password = get_password_hash(password)
    user = User(username=username, hashed_password=hashed_password)
    db.add(user)
    db.commit()
    db.refresh(user)
    return {"msg": "Usuario registrado correctamente"}

@router.post("/auth/login")
async def login(username: str = Form(...), password: str = Form(...), db: Session = Depends(get_db)):
    user = db.execute(select(User).where(User.username == username)).scalar_one_or_none()
    if not user:
        raise HTTPException(status_code=400, detail="Usuario o contraseña incorrectos")
    if not verify_password(password, user.hashed_password):
        raise HTTPException(status_code=400, detail="Usuario o contraseña incorrectos")
    access_token_expires = timedelta(minutes=ACCESS_TOKEN_EXPIRE_MINUTES)
    access_token = create_access_token(data={"sub": user.username}, expires_delta=access_token_expires)
    return {"access_token": access_token, "token_type": "bearer"}

@router.get("/auth/me")
async def read_users_me(current_user: User = Depends(get_current_user)):
    return {
        "id": current_user.id,
        "username": current_user.username,
        "created_at": current_user.created_at.isoformat(),
        "is_active": current_user.is_active,
    }

# Rutas CRUD protegidas para Cotizaciones

@router.post("/cotizaciones", status_code=201)
async def create_cotizacion(
    titulo: str = Form(...),
    descripcion: str | None = Form(None),
    monto_estimado: float = Form(...),
    estado: str = Form("pendiente"),
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    if monto_estimado < 0:
        raise HTTPException(status_code=400, detail="El monto estimado debe ser positivo")
    cotizacion = Cotizacion(
        titulo=titulo.strip(),
        descripcion=descripcion.strip() if descripcion else None,
        monto_estimado=monto_estimado,
        estado=estado,
        owner_id=current_user.id
    )
    db.add(cotizacion)
    db.commit()
    db.refresh(cotizacion)
    return {
        "id": cotizacion.id,
        "titulo": cotizacion.titulo,
        "descripcion": cotizacion.descripcion,
        "monto_estimado": cotizacion.monto_estimado,
        "estado": cotizacion.estado,
        "fecha_creacion": cotizacion.fecha_creacion.isoformat(),
    }

@router.get("/cotizaciones")
async def list_cotizaciones(current_user: User = Depends(get_current_user), db: Session = Depends(get_db)):
    cotizaciones = db.execute(select(Cotizacion).where(Cotizacion.owner_id == current_user.id)).scalars().all()
    return [
        {
            "id": c.id,
            "titulo": c.titulo,
            "descripcion": c.descripcion,
            "monto_estimado": c.monto_estimado,
            "estado": c.estado,
            "fecha_creacion": c.fecha_creacion.isoformat(),
        }
        for c in cotizaciones
    ]

@router.get("/cotizaciones/{cotizacion_id}")
async def get_cotizacion(cotizacion_id: int, current_user: User = Depends(get_current_user), db: Session = Depends(get_db)):
    cotizacion = db.execute(
        select(Cotizacion).where(Cotizacion.id == cotizacion_id, Cotizacion.owner_id == current_user.id)
    ).scalar_one_or_none()
    if not cotizacion:
        raise HTTPException(status_code=404, detail="Cotización no encontrada")
    return {
        "id": cotizacion.id,
        "titulo": cotizacion.titulo,
        "descripcion": cotizacion.descripcion,
        "monto_estimado": cotizacion.monto_estimado,
        "estado": cotizacion.estado,
        "fecha_creacion": cotizacion.fecha_creacion.isoformat(),
    }

@router.put("/cotizaciones/{cotizacion_id}")
async def update_cotizacion(
    cotizacion_id: int,
    titulo: str = Form(...),
    descripcion: str | None = Form(None),
    monto_estimado: float = Form(...),
    estado: str = Form("pendiente"),
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    cotizacion = db.execute(
        select(Cotizacion).where(Cotizacion.id == cotizacion_id, Cotizacion.owner_id == current_user.id)
    ).scalar_one_or_none()
    if not cotizacion:
        raise HTTPException(status_code=404, detail="Cotización no encontrada")
    if monto_estimado < 0:
        raise HTTPException(status_code=400, detail="El monto estimado debe ser positivo")
    cotizacion.titulo = titulo.strip()
    cotizacion.descripcion = descripcion.strip() if descripcion else None
    cotizacion.monto_estimado = monto_estimado
    cotizacion.estado = estado
    db.add(cotizacion)
    db.commit()
    db.refresh(cotizacion)
    return {
        "id": cotizacion.id,
        "titulo": cotizacion.titulo,
        "descripcion": cotizacion.descripcion,
        "monto_estimado": cotizacion.monto_estimado,
        "estado": cotizacion.estado,
        "fecha_creacion": cotizacion.fecha_creacion.isoformat(),
    }

@router.delete("/cotizaciones/{cotizacion_id}", status_code=204)
async def delete_cotizacion(cotizacion_id: int, current_user: User = Depends(get_current_user), db: Session = Depends(get_db)):
    cotizacion = db.execute(
        select(Cotizacion).where(Cotizacion.id == cotizacion_id, Cotizacion.owner_id == current_user.id)
    ).scalar_one_or_none()
    if not cotizacion:
        raise HTTPException(status_code=404, detail="Cotización no encontrada")
    db.delete(cotizacion)
    db.commit()
    return JSONResponse(status_code=204, content=None)

# Rutas CRUD protegidas para Proyectos

@router.post("/proyectos", status_code=201)
async def create_proyecto(
    nombre: str = Form(...),
    descripcion: str | None = Form(None),
    fecha_inicio: str | None = Form(None),
    fecha_fin: str | None = Form(None),
    estado: str = Form("activo"),
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    try:
        fi = datetime.fromisoformat(fecha_inicio) if fecha_inicio else None
        ff = datetime.fromisoformat(fecha_fin) if fecha_fin else None
    except ValueError:
        raise HTTPException(status_code=400, detail="Formato de fecha inválido, usar ISO 8601")
    proyecto = Proyecto(
        nombre=nombre.strip(),
        descripcion=descripcion.strip() if descripcion else None,
        fecha_inicio=fi,
        fecha_fin=ff,
        estado=estado,
        owner_id=current_user.id
    )
    db.add(proyecto)
    db.commit()
    db.refresh(proyecto)
    return {
        "id": proyecto.id,
        "nombre": proyecto.nombre,
        "descripcion": proyecto.descripcion,
        "fecha_inicio": proyecto.fecha_inicio.isoformat() if proyecto.fecha_inicio else None,
        "fecha_fin": proyecto.fecha_fin.isoformat() if proyecto.fecha_fin else None,
        "estado": proyecto.estado,
    }

@router.get("/proyectos")
async def list_proyectos(current_user: User = Depends(get_current_user), db: Session = Depends(get_db)):
    proyectos = db.execute(select(Proyecto).where(Proyecto.owner_id == current_user.id)).scalars().all()
    return [
        {
            "id": p.id,
            "nombre": p.nombre,
            "descripcion": p.descripcion,
            "fecha_inicio": p.fecha_inicio.isoformat() if p.fecha_inicio else None,
            "fecha_fin": p.fecha_fin.isoformat() if p.fecha_fin else None,
            "estado": p.estado,
        }
        for p in proyectos
    ]

@router.get("/proyectos/{proyecto_id}")
async def get_proyecto(proyecto_id: int, current_user: User = Depends(get_current_user), db: Session = Depends(get_db)):
    proyecto = db.execute(
        select(Proyecto).where(Proyecto.id == proyecto_id, Proyecto.owner_id == current_user.id)
    ).scalar_one_or_none()
    if not proyecto:
        raise HTTPException(status_code=404, detail="Proyecto no encontrado")
    return {
        "id": proyecto.id,
        "nombre": proyecto.nombre,
        "descripcion": proyecto.descripcion,
        "fecha_inicio": proyecto.fecha_inicio.isoformat() if proyecto.fecha_inicio else None,
        "fecha_fin": proyecto.fecha_fin.isoformat() if proyecto.fecha_fin else None,
        "estado": proyecto.estado,
    }

@router.put("/proyectos/{proyecto_id}")
async def update_proyecto(
    proyecto_id: int,
    nombre: str = Form(...),
    descripcion: str | None = Form(None),
    fecha_inicio: str | None = Form(None),
    fecha_fin: str | None = Form(None),
    estado: str = Form("activo"),
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    proyecto = db.execute(
        select(Proyecto).where(Proyecto.id == proyecto_id, Proyecto.owner_id == current_user.id)
    ).scalar_one_or_none()
    if not proyecto:
        raise HTTPException(status_code=404, detail="Proyecto no encontrado")
    try:
        fi = datetime.fromisoformat(fecha_inicio) if fecha_inicio else None
        ff = datetime.fromisoformat(fecha_fin) if fecha_fin else None
    except ValueError:
        raise HTTPException(status_code=400, detail="Formato de fecha inválido, usar ISO 8601")
    proyecto.nombre = nombre.strip()
    proyecto.descripcion = descripcion.strip() if descripcion else None
    proyecto.fecha_inicio = fi
    proyecto.fecha_fin = ff
    proyecto.estado = estado
    db.add(proyecto)
    db.commit()
    db.refresh(proyecto)
    return {
        "id": proyecto.id,
        "nombre": proyecto.nombre,
        "descripcion": proyecto.descripcion,
        "fecha_inicio": proyecto.fecha_inicio.isoformat() if proyecto.fecha_inicio else None,
        "fecha_fin": proyecto.fecha_fin.isoformat() if proyecto.fecha_fin else None,
        "estado": proyecto.estado,
    }

@router.delete("/proyectos/{proyecto_id}", status_code=204)
async def delete_proyecto(proyecto_id: int, current_user: User = Depends(get_current_user), db: Session = Depends(get_db)):
    proyecto = db.execute(
        select(Proyecto).where(Proyecto.id == proyecto_id, Proyecto.owner_id == current_user.id)
    ).scalar_one_or_none()
    if not proyecto:
        raise HTTPException(status_code=404, detail="Proyecto no encontrado")
    db.delete(proyecto)
    db.commit()
    return JSONResponse(status_code=204, content=None)

# Montar router en la app principal
app.include_router(router)