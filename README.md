# EDÉN - Asistente Empresarial Inteligente

## Descripción General

EDÉN es una aplicación full-stack diseñada para empresas de servicios técnicos (instalaciones, mantenimiento y obras). Permite gestionar cotizaciones, proyectos, control de costos, tareas operativas y administración financiera mediante un asistente empresarial inteligente. La aplicación cuenta con un frontend SPA en React 18 y Vite, un backend API en FastAPI con autenticación JWT y persistencia en PostgreSQL o SQLite, y un servidor web Nginx que sirve la SPA y proxya la API. El despliegue se realiza mediante Docker Compose con tres servicios coordinados: base de datos, API y frontend.

---

## Contenido del repositorio

- `README.md` — Documentación y guía de uso.
- `docker-compose.yml` — Orquestación de servicios: base de datos, API y frontend.
- `api/` — Backend FastAPI.
  - `Dockerfile` — Imagen del backend.
  - `app/main.py` — Código principal del backend.
  - `requirements.txt` — Dependencias Python.
- `web.Dockerfile` — Dockerfile multi-stage para construir y servir la SPA React con Nginx.
- `nginx.conf` — Configuración de Nginx para servir la SPA y proxy de la API.
- `index.html` — Archivo HTML principal que carga la SPA React.
- `package.json` — Dependencias y scripts del frontend React.
- `vite.config.js` — Configuración del bundler Vite para React.
- `src/` — Código fuente frontend React.
  - `main.jsx` — Punto de entrada React.
  - `App.jsx` — Componente principal con rutas y autenticación.
  - `style.css` — Estilos CSS propios.

---

## Requisitos previos

- Docker y Docker Compose instalados en el sistema.
- Node.js y npm (para desarrollo local del frontend).
- Python 3.12 (para desarrollo local del backend).
- Acceso a un entorno PostgreSQL (opcional, la app puede usar SQLite como fallback).

---

## Desarrollo local

### 1. Clonar el repositorio

```bash
git clone <url-del-repositorio>
cd <nombre-del-repositorio>
```

### 2. Backend FastAPI

#### Instalación de dependencias

```bash
cd api
python -m venv venv
source venv/bin/activate  # En Windows: venv\Scripts\activate
pip install -r requirements.txt
```

#### Variables de entorno para desarrollo

Crear un archivo `.env` en `api/` con al menos:

```
AUTH_SECRET=tu_clave_secreta_jwt
DATABASE_URL=sqlite+aiosqlite:///./app.db
```

> Nota: Para usar PostgreSQL local, configure `DATABASE_URL` con la cadena adecuada.

#### Ejecutar backend

```bash
uvicorn app.main:app --reload --host 0.0.0.0 --port 8000
```

El backend estará disponible en `http://localhost:8000/api`.

### 3. Frontend React

#### Instalación de dependencias

```bash
cd ../
npm install
```

#### Ejecutar frontend en modo desarrollo

```bash
npm run dev
```

La SPA estará disponible en `http://localhost:5173` (o el puerto que indique Vite).

### 4. Uso conjunto con Docker Compose (opcional)

Para levantar todos los servicios (PostgreSQL, API y frontend) en contenedores Docker:

```bash
docker-compose up --build
```

- La base de datos PostgreSQL estará en el servicio `db`.
- La API FastAPI en `http://localhost:8000/api`.
- La SPA React servida por Nginx en `http://localhost:8080`.

---

## Usuarios de prueba

Para facilitar pruebas, puede registrar usuarios desde la interfaz de login o mediante curl:

### Registro

```bash
curl -X POST http://localhost:8000/api/auth/register \
  -H "Content-Type: application/x-www-form-urlencoded" \
  -d "username=usuario1&password=clave123"
```

### Login

```bash
curl -X POST http://localhost:8000/api/auth/login \
  -H "Content-Type: application/x-www-form-urlencoded" \
  -d "username=usuario1&password=clave123"
```

La respuesta incluye un token JWT que el frontend guarda en `localStorage` y usa para autenticar las peticiones.

---

## Despliegue en Dokploy

### 1. Construcción y despliegue

Suba el repositorio a Dokploy y configure el despliegue para que ejecute:

```bash
docker-compose up --build -d
```

### 2. Configuración del dominio

En Dokploy, asigne el dominio deseado al puerto **8080** del servicio `web` para que la SPA React sea accesible públicamente.

### 3. Variables de entorno

Configure las variables de entorno para el servicio `api` en Dokploy:

- `AUTH_SECRET`: clave secreta para JWT (debe ser segura y privada).
- `DATABASE_URL`: cadena de conexión a PostgreSQL (si usa base de datos externa) o deje vacío para usar SQLite local.

### 4. Acceso a la aplicación

Una vez desplegado, la aplicación estará disponible en:

```
http://<tu-dominio>/
```

La SPA se comunica con la API mediante el proxy configurado en Nginx (`/api`).

---

## Rutas API relevantes

- `POST /api/auth/register` — Registro de usuario (form-urlencoded: username, password).
- `POST /api/auth/login` — Login (form-urlencoded: username, password).
- `GET /api/auth/me` — Información del usuario autenticado (requiere token JWT).
- `GET /api/health` — Estado de salud del backend.
- Rutas CRUD protegidas bajo `/api/*` (requieren token JWT en header `Authorization: Bearer <token>`).

---

## Notas importantes

- El frontend sólo usa dependencias React oficiales y CSS propio. No se usan librerías externas para routing ni UI.
- El backend monta todos sus endpoints bajo `/api` para facilitar el proxy inverso.
- El backend intenta conectar a PostgreSQL y si falla, usa SQLite local para garantizar que la app siempre arranque.
- El token JWT se guarda en `localStorage` y se envía en cada petición protegida.
- La SPA es servida por Nginx con configuración para rutas SPA y proxy a la API.

---

## Contacto y soporte

Para dudas o soporte, contacte con el equipo de desarrollo de YERUZZA STUDIO.

---

¡Gracias por usar EDÉN - Asistente Empresarial Inteligente!