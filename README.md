# EDÉN - Asistente Empresarial Inteligente

EDÉN es una aplicación full-stack diseñada para empresas de servicios técnicos (instalaciones, mantenimiento y obras). Permite gestionar cotizaciones, proyectos, control de costos, tareas operativas y administración financiera mediante un sistema multiagente con módulos de comunicación integrados.

---

## Contenido del proyecto

- **Frontend:** SPA React 18 + Vite (JavaScript, CSS propio) en `src/`
- **Backend:** API FastAPI con autenticación JWT y persistencia en PostgreSQL o SQLite en `api/`
- **Servidor web:** Nginx sirve la SPA y proxya la API
- **Orquestación:** Docker Compose con tres servicios: `db`, `api` y `web`

---

## Requisitos previos

- Docker y Docker Compose instalados en su sistema
- Node.js (para desarrollo frontend local)
- Python 3.12 (para desarrollo backend local)

---

## Desarrollo local

### 1. Clonar el repositorio

```bash
git clone <url-del-repositorio>
cd <directorio-del-proyecto>
```

### 2. Backend (API)

Entrar en la carpeta `api`:

```bash
cd api
```

Instalar dependencias Python (recomendado en entorno virtual):

```bash
python -m venv venv
source venv/bin/activate  # Linux/macOS
venv\Scripts\activate     # Windows
pip install -r requirements.txt
```

Ejecutar la API localmente:

```bash
uvicorn app.main:app --reload --host 0.0.0.0 --port 8000
```

La API estará disponible en: `http://localhost:8000/api`

- Documentación automática Swagger: `http://localhost:8000/api/docs`
- OpenAPI JSON: `http://localhost:8000/api/openapi.json`

### 3. Frontend (SPA React)

En la raíz del proyecto:

```bash
npm install
npm run dev
```

La aplicación frontend estará disponible en: `http://localhost:5173`

### 4. Configuración de conexión API en desarrollo

El frontend hace peticiones a `/api/...` por defecto. Para desarrollo local, configure un proxy en `vite.config.js` o modifique las URLs en el código para apuntar a `http://localhost:8000/api`.

---

## Usuarios de prueba

Para facilitar pruebas, puede registrar usuarios nuevos mediante el formulario de registro en la SPA o usar los siguientes usuarios de ejemplo:

| Usuario  | Contraseña |
| -------- | ---------- |
| admin    | admin123   |
| usuario1 | prueba123  |

---

## Despliegue con Docker Compose

### 1. Construir y levantar los servicios

En la raíz del proyecto, ejecutar:

```bash
docker-compose up --build
```

Esto levantará tres servicios:

- **db:** PostgreSQL 16 con base de datos `producto`, usuario y contraseña `studio`
- **api:** FastAPI en `http://localhost:8000/api`
- **web:** Nginx sirviendo la SPA en `http://localhost:8080`

### 2. Acceso a la aplicación

Abrir en el navegador:

```
http://localhost:8080
```

La SPA se comunica con la API a través del proxy `/api`.

---

## Variables de entorno importantes

- `AUTH_SECRET`: Clave secreta para firmar tokens JWT (debe ser segura y secreta)
- `DATABASE_URL`: URL de conexión a la base de datos PostgreSQL, por ejemplo:
  ```
  postgresql+psycopg://studio:studio@db:5432/producto
  ```
  Si no está disponible, el backend usa SQLite local `./app.db` como fallback.

---

## Despliegue en Dokploy

Para desplegar EDÉN en Dokploy, siga estos pasos:

1. Suba el proyecto a un repositorio Git accesible por Dokploy.
2. Configure Dokploy para usar el archivo `docker-compose.yml` del proyecto.
3. Asigne el dominio deseado al puerto **8080** del servicio `web` (puerto 80 interno de Nginx mapeado a 8080 externo).
4. Defina las variables de entorno necesarias para el servicio `api`:
   - `AUTH_SECRET` (clave secreta JWT)
   - `DATABASE_URL` (cadena de conexión PostgreSQL)
5. Dokploy levantará los tres servicios automáticamente y gestionará dependencias y salud.

---

## Rutas API y autenticación

Todas las rutas del backend están bajo el prefijo `/api`.

- **Autenticación:**
  - `POST /api/auth/register` — Registro de usuario (form-urlencoded: username, password)
  - `POST /api/auth/login` — Login (form-urlencoded: username, password)
  - `GET /api/auth/me` — Información del usuario autenticado (requiere JWT)
- **Salud:**
  - `GET /api/health` — Estado del servicio (sin autenticación)
- **Rutas CRUD protegidas:** requieren token JWT en header `Authorization: Bearer <token>`

---

## Notas importantes

- El frontend guarda el token JWT en `localStorage` y lo envía en cada petición a la API.
- El backend usa bcrypt para el hash de contraseñas y python-jose para JWT.
- El servidor Nginx sirve la SPA y proxya las peticiones `/api` al backend.
- El proyecto está preparado para funcionar con PostgreSQL o SQLite sin fallos.
- No se usan librerías externas en el frontend salvo React y ReactDOM.

---

## Contacto

Para dudas o soporte, contacte con el equipo de desarrollo de YERUZZA STUDIO.

---

¡Gracias por usar EDÉN - Asistente Empresarial Inteligente!