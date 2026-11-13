from fastapi import FastAPI, Depends, HTTPException, status, Form, Request, APIRouter
from fastapi.security import OAuth2PasswordRequestForm
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
from jose import JWTError, jwt
from passlib.context import CryptContext
from sqlalchemy.ext.asyncio import AsyncSession, create_async_engine, async_sessionmaker
from sqlalchemy import select, update, delete
from sqlalchemy.exc import SQLAlchemyError
from sqlalchemy.orm import declarative_base, mapped_column
from sqlalchemy import Integer, String, Text, Float, DateTime, ForeignKey
from typing import Optional, List
from datetime import datetime, timedelta
import os
import asyncio

# Configuración y constantes
SECRET_KEY = os.getenv("AUTH_SECRET", "secret_dev_key_change_me")
ALGORITHM = "HS256"
ACCESS_TOKEN_EXPIRE_MINUTES = 60 * 24  # 1 día

DATABASE_URL = os.getenv(
    "DATABASE_URL",
    "sqlite+aiosqlite:///./app.db"
)

pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")

Base = declarative_base()

# Modelos SQLAlchemy

class User(Base):
    __tablename__ = "users"
    id = mapped_column(Integer, primary_key=True, index=True)
    username = mapped_column(String(50), unique=True, index=True, nullable=False)
    hashed_password = mapped_column(String(128), nullable=False)
    full_name = mapped_column(String(100), nullable=True)

class Quote(Base):
    __tablename__ = "quotes"
    id = mapped_column(Integer, primary_key=True, index=True)
    title = mapped_column(String(200), nullable=False)
    description = mapped_column(Text, nullable=True)
    client = mapped_column(String(100), nullable=True)
    amount = mapped_column(Float, nullable=True)
    created_at = mapped_column(DateTime, default=datetime.utcnow)
    owner_id = mapped_column(Integer, ForeignKey("users.id"), nullable=False)

class Project(Base):
    __tablename__ = "projects"
    id = mapped_column(Integer, primary_key=True, index=True)
    name = mapped_column(String(200), nullable=False)
    description = mapped_column(Text, nullable=True)
    status = mapped_column(String(50), default="pending")
    start_date = mapped_column(DateTime, nullable=True)
    end_date = mapped_column(DateTime, nullable=True)
    owner_id = mapped_column(Integer, ForeignKey("users.id"), nullable=False)

class Task(Base):
    __tablename__ = "tasks"
    id = mapped_column(Integer, primary_key=True, index=True)
    title = mapped_column(String(200), nullable=False)
    description = mapped_column(Text, nullable=True)
    status = mapped_column(String(50), default="pending")
    due_date = mapped_column(DateTime, nullable=True)
    project_id = mapped_column(Integer, ForeignKey("projects.id"), nullable=False)
    owner_id = mapped_column(Integer, ForeignKey("users.id"), nullable=False)

class Expense(Base):
    __tablename__ = "expenses"
    id = mapped_column(Integer, primary_key=True, index=True)
    concept = mapped_column(String(200), nullable=False)
    amount = mapped_column(Float, nullable=False)
    date = mapped_column(DateTime, default=datetime.utcnow)
    owner_id = mapped_column(Integer, ForeignKey("users.id"), nullable=False)

# Pydantic Schemas

from pydantic import BaseModel, Field

class Token(BaseModel):
    access_token: str
    token_type: str

class TokenData(BaseModel):
    username: Optional[str] = None

class UserCreate(BaseModel):
    username: str = Field(..., min_length=3, max_length=50)
    password: str = Field(..., min_length=6)
    full_name: Optional[str] = None

class UserOut(BaseModel):
    id: int
    username: str
    full_name: Optional[str] = None

    class Config:
        orm_mode = True

class QuoteCreate(BaseModel):
    title: str
    description: Optional[str] = None
    client: Optional[str] = None
    amount: Optional[float] = None

class QuoteOut(QuoteCreate):
    id: int
    created_at: datetime
    owner_id: int

    class Config:
        orm_mode = True

class ProjectCreate(BaseModel):
    name: str
    description: Optional[str] = None
    status: Optional[str] = "pending"
    start_date: Optional[datetime] = None
    end_date: Optional[datetime] = None

class ProjectOut(ProjectCreate):
    id: int
    owner_id: int

    class Config:
        orm_mode = True

class TaskCreate(BaseModel):
    title: str
    description: Optional[str] = None
    status: Optional[str] = "pending"
    due_date: Optional[datetime] = None
    project_id: int

class TaskOut(TaskCreate):
    id: int
    owner_id: int

    class Config:
        orm_mode = True

class ExpenseCreate(BaseModel):
    concept: str
    amount: float
    date: Optional[datetime] = None

class ExpenseOut(ExpenseCreate):
    id: int
    owner_id: int

    class Config:
        orm_mode = True

# Base de datos async

engine = create_async_engine(DATABASE_URL, echo=False, future=True)
async_session = async_sessionmaker(engine, expire_on_commit=False, class_=AsyncSession)

# Funciones de utilidad

def verify_password(plain_password, hashed_password) -> bool:
    return pwd_context.verify(plain_password, hashed_password)

def get_password_hash(password) -> str:
    return pwd_context.hash(password)

def create_access_token(data: dict, expires_delta: Optional[timedelta] = None):
    to_encode = data.copy()
    expire = datetime.utcnow() + (expires_delta if expires_delta else timedelta(minutes=15))
    to_encode.update({"exp": expire})
    encoded_jwt = jwt.encode(to_encode, SECRET_KEY, algorithm=ALGORITHM)
    return encoded_jwt

async def get_user_by_username(db: AsyncSession, username: str) -> Optional[User]:
    result = await db.execute(select(User).where(User.username == username))
    return result.scalars().first()

async def authenticate_user(db: AsyncSession, username: str, password: str) -> Optional[User]:
    user = await get_user_by_username(db, username)
    if not user:
        return None
    if not verify_password(password, user.hashed_password):
        return None
    return user

# Dependencias

from fastapi.security import OAuth2PasswordBearer

oauth2_scheme = OAuth2PasswordBearer(tokenUrl="/api/auth/login")

async def get_db() -> AsyncSession:
    async with async_session() as session:
        try:
            yield session
        except SQLAlchemyError:
            await session.rollback()
            raise
        finally:
            await session.close()

async def get_current_user(token: str = Depends(oauth2_scheme), db: AsyncSession = Depends(get_db)) -> User:
    credentials_exception = HTTPException(
        status_code=status.HTTP_401_UNAUTHORIZED,
        detail="No se pudo validar las credenciales",
        headers={"WWW-Authenticate": "Bearer"},
    )
    try:
        payload = jwt.decode(token, SECRET_KEY, algorithms=[ALGORITHM])
        username: str = payload.get("sub")
        if username is None:
            raise credentials_exception
        token_data = TokenData(username=username)
    except JWTError:
        raise credentials_exception
    user = await get_user_by_username(db, username=token_data.username)
    if user is None:
        raise credentials_exception
    return user

# Inicialización de la app

app = FastAPI(root_path="/api")

# CORS (permitir frontend local y otros orígenes si se desea)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # En producción restringir a dominios específicos
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Routers

api_router = APIRouter(prefix="/api")

# Rutas públicas

@api_router.get("/health", tags=["salud"])
async def health():
    return {"status": "ok"}

@api_router.post("/auth/register", tags=["auth"])
async def register(
    username: str = Form(...),
    password: str = Form(...),
    full_name: Optional[str] = Form(None),
    db: AsyncSession = Depends(get_db)
):
    existing_user = await get_user_by_username(db, username)
    if existing_user:
        raise HTTPException(status_code=400, detail="El usuario ya existe")
    hashed_password = get_password_hash(password)
    new_user = User(username=username, hashed_password=hashed_password, full_name=full_name)
    db.add(new_user)
    await db.commit()
    await db.refresh(new_user)
    return {"msg": "Usuario registrado correctamente"}

@api_router.post("/auth/login", response_model=Token, tags=["auth"])
async def login(form_data: OAuth2PasswordRequestForm = Depends(), db: AsyncSession = Depends(get_db)):
    user = await authenticate_user(db, form_data.username, form_data.password)
    if not user:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Usuario o contraseña incorrectos",
            headers={"WWW-Authenticate": "Bearer"},
        )
    access_token_expires = timedelta(minutes=ACCESS_TOKEN_EXPIRE_MINUTES)
    access_token = create_access_token(
        data={"sub": user.username},
        expires_delta=access_token_expires
    )
    return {"access_token": access_token, "token_type": "bearer"}

@api_router.get("/auth/me", response_model=UserOut, tags=["auth"])
async def read_users_me(current_user: User = Depends(get_current_user)):
    return current_user

# Rutas CRUD protegidas

# COTIZACIONES (Quotes)

@api_router.post("/quotes", response_model=QuoteOut, tags=["quotes"])
async def create_quote(quote: QuoteCreate, current_user: User = Depends(get_current_user), db: AsyncSession = Depends(get_db)):
    db_quote = Quote(**quote.dict(), owner_id=current_user.id)
    db.add(db_quote)
    await db.commit()
    await db.refresh(db_quote)
    return db_quote

@api_router.get("/quotes", response_model=List[QuoteOut], tags=["quotes"])
async def read_quotes(skip: int = 0, limit: int = 100, current_user: User = Depends(get_current_user), db: AsyncSession = Depends(get_db)):
    result = await db.execute(select(Quote).where(Quote.owner_id == current_user.id).offset(skip).limit(limit))
    return result.scalars().all()

@api_router.get("/quotes/{quote_id}", response_model=QuoteOut, tags=["quotes"])
async def read_quote(quote_id: int, current_user: User = Depends(get_current_user), db: AsyncSession = Depends(get_db)):
    result = await db.execute(select(Quote).where(Quote.id == quote_id, Quote.owner_id == current_user.id))
    quote = result.scalars().first()
    if not quote:
        raise HTTPException(status_code=404, detail="Cotización no encontrada")
    return quote

@api_router.put("/quotes/{quote_id}", response_model=QuoteOut, tags=["quotes"])
async def update_quote(quote_id: int, quote_in: QuoteCreate, current_user: User = Depends(get_current_user), db: AsyncSession = Depends(get_db)):
    result = await db.execute(select(Quote).where(Quote.id == quote_id, Quote.owner_id == current_user.id))
    quote = result.scalars().first()
    if not quote:
        raise HTTPException(status_code=404, detail="Cotización no encontrada")
    for key, value in quote_in.dict(exclude_unset=True).items():
        setattr(quote, key, value)
    await db.commit()
    await db.refresh(quote)
    return quote

@api_router.delete("/quotes/{quote_id}", status_code=204, tags=["quotes"])
async def delete_quote(quote_id: int, current_user: User = Depends(get_current_user), db: AsyncSession = Depends(get_db)):
    result = await db.execute(select(Quote).where(Quote.id == quote_id, Quote.owner_id == current_user.id))
    quote = result.scalars().first()
    if not quote:
        raise HTTPException(status_code=404, detail="Cotización no encontrada")
    await db.delete(quote)
    await db.commit()
    return JSONResponse(status_code=204, content=None)

# PROYECTOS (Projects)

@api_router.post("/projects", response_model=ProjectOut, tags=["projects"])
async def create_project(project: ProjectCreate, current_user: User = Depends(get_current_user), db: AsyncSession = Depends(get_db)):
    db_project = Project(**project.dict(), owner_id=current_user.id)
    db.add(db_project)
    await db.commit()
    await db.refresh(db_project)
    return db_project

@api_router.get("/projects", response_model=List[ProjectOut], tags=["projects"])
async def read_projects(skip: int = 0, limit: int = 100, current_user: User = Depends(get_current_user), db: AsyncSession = Depends(get_db)):
    result = await db.execute(select(Project).where(Project.owner_id == current_user.id).offset(skip).limit(limit))
    return result.scalars().all()

@api_router.get("/projects/{project_id}", response_model=ProjectOut, tags=["projects"])
async def read_project(project_id: int, current_user: User = Depends(get_current_user), db: AsyncSession = Depends(get_db)):
    result = await db.execute(select(Project).where(Project.id == project_id, Project.owner_id == current_user.id))
    project = result.scalars().first()
    if not project:
        raise HTTPException(status_code=404, detail="Proyecto no encontrado")
    return project

@api_router.put("/projects/{project_id}", response_model=ProjectOut, tags=["projects"])
async def update_project(project_id: int, project_in: ProjectCreate, current_user: User = Depends(get_current_user), db: AsyncSession = Depends(get_db)):
    result = await db.execute(select(Project).where(Project.id == project_id, Project.owner_id == current_user.id))
    project = result.scalars().first()
    if not project:
        raise HTTPException(status_code=404, detail="Proyecto no encontrado")
    for key, value in project_in.dict(exclude_unset=True).items():
        setattr(project, key, value)
    await db.commit()
    await db.refresh(project)
    return project

@api_router.delete("/projects/{project_id}", status_code=204, tags=["projects"])
async def delete_project(project_id: int, current_user: User = Depends(get_current_user), db: AsyncSession = Depends(get_db)):
    result = await db.execute(select(Project).where(Project.id == project_id, Project.owner_id == current_user.id))
    project = result.scalars().first()
    if not project:
        raise HTTPException(status_code=404, detail="Proyecto no encontrado")
    await db.delete(project)
    await db.commit()
    return JSONResponse(status_code=204, content=None)

# TAREAS (Tasks)

@api_router.post("/tasks", response_model=TaskOut, tags=["tasks"])
async def create_task(task: TaskCreate, current_user: User = Depends(get_current_user), db: AsyncSession = Depends(get_db)):
    # Verificar que el proyecto pertenece al usuario
    result = await db.execute(select(Project).where(Project.id == task.project_id, Project.owner_id == current_user.id))
    project = result.scalars().first()
    if not project:
        raise HTTPException(status_code=404, detail="Proyecto no encontrado o no autorizado")
    db_task = Task(**task.dict(), owner_id=current_user.id)
    db.add(db_task)
    await db.commit()
    await db.refresh(db_task)
    return db_task

@api_router.get("/tasks", response_model=List[TaskOut], tags=["tasks"])
async def read_tasks(skip: int = 0, limit: int = 100, current_user: User = Depends(get_current_user), db: AsyncSession = Depends(get_db)):
    result = await db.execute(select(Task).where(Task.owner_id == current_user.id).offset(skip).limit(limit))
    return result.scalars().all()

@api_router.get("/tasks/{task_id}", response_model=TaskOut, tags=["tasks"])
async def read_task(task_id: int, current_user: User = Depends(get_current_user), db: AsyncSession = Depends(get_db)):
    result = await db.execute(select(Task).where(Task.id == task_id, Task.owner_id == current_user.id))
    task = result.scalars().first()
    if not task:
        raise HTTPException(status_code=404, detail="Tarea no encontrada")
    return task

@api_router.put("/tasks/{task_id}", response_model=TaskOut, tags=["tasks"])
async def update_task(task_id: int, task_in: TaskCreate, current_user: User = Depends(get_current_user), db: AsyncSession = Depends(get_db)):
    result = await db.execute(select(Task).where(Task.id == task_id, Task.owner_id == current_user.id))
    task = result.scalars().first()
    if not task:
        raise HTTPException(status_code=404, detail="Tarea no encontrada")
    # Verificar proyecto si se cambia
    if task.project_id != task_in.project_id:
        result_proj = await db.execute(select(Project).where(Project.id == task_in.project_id, Project.owner_id == current_user.id))
        project = result_proj.scalars().first()
        if not project:
            raise HTTPException(status_code=404, detail="Proyecto no encontrado o no autorizado")
    for key, value in task_in.dict(exclude_unset=True).items():
        setattr(task, key, value)
    await db.commit()
    await db.refresh(task)
    return task

@api_router.delete("/tasks/{task_id}", status_code=204, tags=["tasks"])
async def delete_task(task_id: int, current_user: User = Depends(get_current_user), db: AsyncSession = Depends(get_db)):
    result = await db.execute(select(Task).where(Task.id == task_id, Task.owner_id == current_user.id))
    task = result.scalars().first()
    if not task:
        raise HTTPException(status_code=404, detail="Tarea no encontrada")
    await db.delete(task)
    await db.commit()
    return JSONResponse(status_code=204, content=None)

# GASTOS (Expenses)

@api_router.post("/expenses", response_model=ExpenseOut, tags=["expenses"])
async def create_expense(expense: ExpenseCreate, current_user: User = Depends(get_current_user), db: AsyncSession = Depends(get_db)):
    db_expense = Expense(**expense.dict(), owner_id=current_user.id)
    db.add(db_expense)
    await db.commit()
    await db.refresh(db_expense)
    return db_expense

@api_router.get("/expenses", response_model=List[ExpenseOut], tags=["expenses"])
async def read_expenses(skip: int = 0, limit: int = 100, current_user: User = Depends(get_current_user), db: AsyncSession = Depends(get_db)):
    result = await db.execute(select(Expense).where(Expense.owner_id == current_user.id).offset(skip).limit(limit))
    return result.scalars().all()

@api_router.get("/expenses/{expense_id}", response_model=ExpenseOut, tags=["expenses"])
async def read_expense(expense_id: int, current_user: User = Depends(get_current_user), db: AsyncSession = Depends(get_db)):
    result = await db.execute(select(Expense).where(Expense.id == expense_id, Expense.owner_id == current_user.id))
    expense = result.scalars().first()
    if not expense:
        raise HTTPException(status_code=404, detail="Gasto no encontrado")
    return expense

@api_router.put("/expenses/{expense_id}", response_model=ExpenseOut, tags=["expenses"])
async def update_expense(expense_id: int, expense_in: ExpenseCreate, current_user: User = Depends(get_current_user), db: AsyncSession = Depends(get_db)):
    result = await db.execute(select(Expense).where(Expense.id == expense_id, Expense.owner_id == current_user.id))
    expense = result.scalars().first()
    if not expense:
        raise HTTPException(status_code=404, detail="Gasto no encontrado")
    for key, value in expense_in.dict(exclude_unset=True).items():
        setattr(expense, key, value)
    await db.commit()
    await db.refresh(expense)
    return expense

@api_router.delete("/expenses/{expense_id}", status_code=204, tags=["expenses"])
async def delete_expense(expense_id: int, current_user: User = Depends(get_current_user), db: AsyncSession = Depends(get_db)):
    result = await db.execute(select(Expense).where(Expense.id == expense_id, Expense.owner_id == current_user.id))
    expense = result.scalars().first()
    if not expense:
        raise HTTPException(status_code=404, detail="Gasto no encontrado")
    await db.delete(expense)
    await db.commit()
    return JSONResponse(status_code=204, content=None)

# Eventos de arranque para crear tablas

@app.on_event("startup")
async def on_startup():
    try:
        async with engine.begin() as conn:
            await conn.run_sync(Base.metadata.create_all)
    except Exception:
        # Ignorar errores para fallback a SQLite o si DB no disponible
        pass

# Montar router principal con prefijo /api

app.include_router(api_router)