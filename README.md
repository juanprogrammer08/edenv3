# EDÉN - Asistente Empresarial Inteligente

## Descripción General

EDÉN es una aplicación full-stack diseñada para empresas de servicios técnicos (instalaciones, mantenimiento y obras). Permite gestionar cotizaciones, proyectos, control de costos, tareas operativas y administración financiera mediante un asistente empresarial inteligente. La aplicación consta de tres servicios coordinados:

- **Frontend:** SPA React 18 con Vite, que ofrece interfaz de usuario con login/registro y guardia de rutas basada en token JWT.
- **Backend:** API FastAPI con autenticación JWT, persistencia en PostgreSQL o SQLite y rutas protegidas para la gestión de datos.
- **Servidor Web:** Nginx que sirve la SPA y proxya las peticiones a la API.

El despliegue se realiza mediante Docker Compose con los tres servicios: base de datos, API y frontend.

---

## Contenido del repositorio

- `README.md` — Documentación en español.
- `api/` — Código backend FastAPI.
- `api/Dockerfile` — Dockerfile para backend.
- `api/requirements.txt` — Dependencias Python backend.
- `docker-compose.yml` — Orquestación de servicios.
- `index.html` — Archivo HTML principal SPA.
- `nginx.conf` — Configuración Nginx para SPA y proxy API.
- `package.json` — Dependencias y scripts frontend.
- `src/` — Código fuente React.
- `src/App.jsx` — Componente principal React.
- `src/main.jsx` — Punto de entrada React.
- `src/style.css` — Estilos CSS frontend.
- `vite.config.js` — Configuración Vite.
- `web.Dockerfile` — Dockerfile multi-stage para frontend.

---

## Desarrollo local

### Requisitos previos

- Docker y Docker Compose instalados.
- Node.js 18+ y npm (para desarrollo frontend local).
- Python 3.12+ (opcional para desarrollo backend local sin Docker).

### Levantar la aplicación con Docker Compose

Desde la raíz del proyecto, ejecutar:

```bash
docker-compose up --build
```

Esto iniciará tres servicios:

- **db:** PostgreSQL 16 con base de datos `producto`, usuario y contraseña `studio`.
- **api:** Backend FastAPI en `http://localhost:8000/api`.
- **web:** Servidor Nginx que sirve la SPA en `http://localhost:8080`.

El frontend se conecta automáticamente a la API en `/api`.

### Acceder a la aplicación

Abrir en el navegador:

```
http://localhost:8080
```

### Documentación API

La API FastAPI expone su documentación Swagger en:

```
http://localhost:8000/api/docs
```

---

## Usuarios de prueba

Para facilitar pruebas, puede registrar usuarios nuevos desde la pantalla de registro en la SPA.

Ejemplo de usuario de prueba (si se desea crear manualmente en base de datos):

| Usuario  | Contraseña |
| -------- | ---------- |
| admin    | admin123   |
| usuario1 | prueba123  |

---

## Uso de la aplicación

- **Registro y Login:** Se accede mediante formularios que envían datos con `application/x-www-form-urlencoded`.
- **Autenticación:** Se usa token JWT almacenado en `localStorage` y enviado en cada petición a la API como header `Authorization: Bearer <token>`.
- **Guardia de rutas:** Solo usuarios autenticados pueden acceder a las rutas protegidas.
- **Datos de ejemplo:** El frontend usa datos de ejemplo si la API no responde.

---

## Despliegue en Dokploy

Para desplegar en Dokploy, siga estos pasos:

1. Suba el repositorio al repositorio Git que Dokploy pueda acceder.
2. Configure Dokploy para construir y ejecutar el `docker-compose.yml` del proyecto.
3. En la configuración del servicio web, asigne el dominio deseado apuntando al puerto **8080** del servicio `web` (no al 80 interno).
4. Asegúrese de definir las variables de entorno necesarias para el servicio `api`:
   - `AUTH_SECRET`: clave secreta para JWT (por ejemplo, una cadena larga aleatoria).
   - `DATABASE_URL`: cadena de conexión a la base de datos PostgreSQL (por defecto `postgresql+psycopg://studio:studio@db:5432/producto`).
5. Dokploy levantará los tres servicios: base de datos, backend y frontend.
6. El frontend estará disponible en el dominio asignado, y la API bajo `/api`.

---

## Notas importantes

- La API siempre está bajo el prefijo `/api`.
- El backend soporta fallback a SQLite local si PostgreSQL no está disponible, para evitar fallos en el arranque.
- El frontend no usa librerías externas para routing ni UI, solo React y CSS propios.
- Las rutas de autenticación `/auth/register`, `/auth/login` reciben datos en formato `application/x-www-form-urlencoded`.
- El servidor Nginx está configurado para servir la SPA y proxy las peticiones `/api` al backend.
- Para desarrollo frontend sin Docker, puede ejecutar:

```bash
cd src
npm install
npm run dev
```

y configurar el proxy manualmente para `/api`.

---

## Contacto

Para soporte o consultas sobre EDÉN, contacte con el equipo de desarrollo en:

- Email: soporte@yeruzza.studio
- Web: https://yeruzza.studio

---

¡Gracias por usar EDÉN - Asistente Empresarial Inteligente!