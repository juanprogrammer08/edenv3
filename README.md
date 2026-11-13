# EDÉN - Asistente Empresarial Inteligente

---

## Descripción General

EDÉN es una aplicación full-stack diseñada para empresas de servicios técnicos (instalaciones, mantenimiento y obras). Permite gestionar cotizaciones, proyectos, control de costos, tareas operativas y administración financiera mediante un sistema multiagente con módulos de comunicación integrados.

La aplicación consta de tres servicios coordinados:

- **Frontend:** SPA React 18 con Vite, que ofrece una interfaz moderna y reactiva.
- **Backend:** API FastAPI con autenticación JWT y persistencia en PostgreSQL o SQLite.
- **Servidor Web:** Nginx que sirve la SPA y proxya la API.

El despliegue se realiza mediante Docker Compose para facilitar la orquestación.

---

## Contenido del Repositorio

- `README.md` — Documentación y guía de uso.
- `api/` — Código backend FastAPI.
- `api/Dockerfile` — Dockerfile para construir la imagen del backend.
- `api/requirements.txt` — Dependencias Python para el backend.
- `docker-compose.yml` — Orquestación de los servicios.
- `index.html` — Archivo HTML principal para la SPA.
- `nginx.conf` — Configuración Nginx para servir SPA y proxy API.
- `package.json` — Dependencias y scripts frontend.
- `src/` — Código fuente React.
- `web.Dockerfile` — Dockerfile multi-stage para construir y servir la SPA React.

---

## Desarrollo Local

### Requisitos Previos

- Docker y Docker Compose instalados.
- Node.js (v18+) y npm para desarrollo frontend local.

### Levantar los servicios con Docker Compose

1. Clonar el repositorio:

```bash
git clone <url-del-repositorio>
cd <directorio-del-proyecto>
```

2. Construir y levantar los servicios:

```bash
docker-compose up --build
```

Esto iniciará tres servicios:

- **db:** PostgreSQL en el puerto 5432 (interno).
- **api:** Backend FastAPI en el puerto 8000 (interno).
- **web:** Servidor Nginx que sirve la SPA en el puerto 8080 (expuesto).

3. Acceder a la aplicación frontend en:

```
http://localhost:8080/
```

4. La API está disponible en:

```
http://localhost:8080/api/
```

> Nota: El backend monta todos sus endpoints bajo `/api`, incluyendo `/api/auth/*` y `/api/health`.

### Desarrollo Frontend

Para desarrollo frontend con recarga en caliente:

```bash
cd src
npm install
npm run dev
```

El frontend de desarrollo corre por defecto en `http://localhost:5173`.

### Desarrollo Backend

Para desarrollo backend:

```bash
cd api
python -m venv venv
source venv/bin/activate  # Linux/macOS
venv\Scripts\activate     # Windows
pip install -r requirements.txt
uvicorn app.main:app --reload --host 0.0.0.0 --port 8000
```

La API estará disponible en `http://localhost:8000/api`.

---

## Usuarios de Prueba

Para facilitar pruebas, puede usar las siguientes credenciales de usuario:

| Usuario  | Contraseña |
| -------- | ---------- |
| admin    | admin123   |
| usuario1 | password1  |

> Estos usuarios pueden ser creados manualmente mediante el endpoint `/api/auth/register` o directamente en la base de datos.

---

## Autenticación

- El sistema usa JWT para autenticación.
- Los endpoints `/api/auth/register` y `/api/auth/login` reciben datos con `application/x-www-form-urlencoded` (campos `username` y `password`).
- El token JWT se almacena en `localStorage` y se envía en cada petición protegida en el header `Authorization: Bearer <token>`.
- El endpoint `/api/auth/me` devuelve información del usuario autenticado.
- Todas las rutas CRUD están protegidas salvo `/api/health` y `/api/auth/*`.

---

## Rutas Principales de la API

- `POST /api/auth/register` — Registro de usuario.
- `POST /api/auth/login` — Login y obtención de token JWT.
- `GET /api/auth/me` — Información del usuario autenticado.
- `GET /api/health` — Estado de salud del backend.
- Rutas CRUD protegidas bajo `/api/*` (requieren token JWT).

---

## Despliegue en Dokploy

Para desplegar EDÉN en Dokploy, siga estos pasos:

1. Suba el repositorio o la imagen Docker al registro que use Dokploy.

2. Configure un nuevo proyecto en Dokploy con Docker Compose usando el fichero `docker-compose.yml` incluido.

3. Asigne el dominio deseado al puerto **8080** del servicio `web` para que la SPA sea accesible públicamente.

4. Configure las variables de entorno necesarias para el servicio `api`:

- `AUTH_SECRET`: Clave secreta para firmar los tokens JWT (ejemplo: `supersecretkey`).
- `DATABASE_URL`: URL de conexión a la base de datos PostgreSQL (ejemplo: `postgresql+psycopg://studio:studio@db:5432/producto`).

> Nota: El servicio `api` depende de que la base de datos `db` esté saludable antes de arrancar.

---

## Notas Adicionales

- El backend intenta conectarse a PostgreSQL y, en caso de fallo, usa SQLite local (`./app.db`) para evitar que la aplicación deje de funcionar.
- El frontend siempre intenta consumir la API en `/api`, y si no está disponible, usa datos de ejemplo como respaldo.
- La SPA usa React Router para navegación y guardias de rutas basadas en autenticación.
- El servidor Nginx está configurado para servir la SPA y redirigir todas las rutas no encontradas a `index.html` para soporte SPA.

---

## Contacto

Para soporte o consultas, contacte con el equipo de desarrollo de YERUZZA STUDIO.

---

¡Gracias por usar EDÉN - Asistente Empresarial Inteligente!