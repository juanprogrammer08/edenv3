import React, { useState, useEffect } from 'react';

// Componente principal de la aplicación EDÉN
export default function App() {
  // Estado para almacenar el token JWT
  const [token, setToken] = useState(localStorage.getItem('token') || '');
  // Estado para almacenar el usuario autenticado
  const [user, setUser] = useState(null);
  // Estados para formularios de login y registro
  const [formMode, setFormMode] = useState('login'); // 'login' o 'register'
  const [username, setUsername] = useState('');
  const [password, setPassword] = useState('');
  // Estado para mensajes de error o info
  const [message, setMessage] = useState('');
  // Estado para controlar carga de datos
  const [loading, setLoading] = useState(false);

  // Función para limpiar estado de formulario y mensajes
  function resetForm() {
    setUsername('');
    setPassword('');
    setMessage('');
  }

  // Función para guardar token en localStorage y estado
  function saveToken(newToken) {
    localStorage.setItem('token', newToken);
    setToken(newToken);
  }

  // Función para eliminar token y usuario (logout)
  function logout() {
    localStorage.removeItem('token');
    setToken('');
    setUser(null);
    resetForm();
  }

  // Función para obtener datos del usuario autenticado (/auth/me)
  async function fetchUser(token) {
    setLoading(true);
    try {
      const res = await fetch('/api/auth/me', {
        headers: { Authorization: `Bearer ${token}` },
      });
      if (!res.ok) throw new Error('No autorizado');
      const data = await res.json();
      setUser(data);
      setMessage('');
    } catch {
      logout();
    } finally {
      setLoading(false);
    }
  }

  // Efecto para cargar usuario si hay token
  useEffect(() => {
    if (token) {
      fetchUser(token);
    } else {
      setUser(null);
    }
  }, [token]);

  // Función para manejar login o registro
  async function handleSubmit(e) {
    e.preventDefault();
    setLoading(true);
    setMessage('');
    try {
      const url = formMode === 'login' ? '/api/auth/login' : '/api/auth/register';
      const body = new URLSearchParams();
      body.append('username', username);
      body.append('password', password);

      const res = await fetch(url, {
        method: 'POST',
        headers: { 'Content-Type': 'application/x-www-form-urlencoded' },
        body,
      });

      if (!res.ok) {
        if (res.status === 400) {
          const errData = await res.json().catch(() => null);
          setMessage(errData?.detail || 'Error en las credenciales');
        } else {
          setMessage('Error en la conexión con el servidor');
        }
        return;
      }

      const data = await res.json();

      if (formMode === 'login') {
        saveToken(data.access_token);
        setMessage('');
      } else {
        // Registro exitoso, cambiar a login para que inicie sesión
        setMessage('Registro exitoso. Por favor, inicie sesión.');
        setFormMode('login');
        resetForm();
      }
    } catch {
      setMessage('Error inesperado. Intente nuevamente.');
    } finally {
      setLoading(false);
    }
  }

  // Componente para mostrar formulario de login o registro
  function AuthForm() {
    return (
      <div className="auth-container">
        <h2>{formMode === 'login' ? 'Iniciar Sesión' : 'Registro'}</h2>
        <form onSubmit={handleSubmit} className="auth-form" autoComplete="off">
          <label htmlFor="username">Usuario</label>
          <input
            id="username"
            type="text"
            value={username}
            onChange={e => setUsername(e.target.value)}
            required
            autoFocus
            autoComplete="username"
            disabled={loading}
          />
          <label htmlFor="password">Contraseña</label>
          <input
            id="password"
            type="password"
            value={password}
            onChange={e => setPassword(e.target.value)}
            required
            autoComplete={formMode === 'login' ? 'current-password' : 'new-password'}
            disabled={loading}
          />
          <button type="submit" disabled={loading}>
            {loading ? 'Procesando...' : formMode === 'login' ? 'Entrar' : 'Registrar'}
          </button>
        </form>
        {message && <p className="message">{message}</p>}
        <p className="toggle-link">
          {formMode === 'login' ? (
            <>
              ¿No tienes cuenta?{' '}
              <button onClick={() => { setFormMode('register'); resetForm(); }} disabled={loading} className="link-button">
                Regístrate aquí
              </button>
            </>
          ) : (
            <>
              ¿Ya tienes cuenta?{' '}
              <button onClick={() => { setFormMode('login'); resetForm(); }} disabled={loading} className="link-button">
                Inicia sesión
              </button>
            </>
          )}
        </p>
      </div>
    );
  }

  // Componente para la pantalla principal protegida (ejemplo básico)
  function Dashboard() {
    // Estado para datos de ejemplo o reales
    const [data, setData] = useState(null);
    const [loadingData, setLoadingData] = useState(false);
    const [errorData, setErrorData] = useState('');

    // Ejemplo de fetch protegido a /api/protected (puede cambiarse por rutas reales)
    useEffect(() => {
      async function loadData() {
        setLoadingData(true);
        setErrorData('');
        try {
          const res = await fetch('/api/protected', {
            headers: { Authorization: `Bearer ${token}` },
          });
          if (!res.ok) throw new Error('No autorizado');
          const json = await res.json();
          setData(json);
        } catch {
          // Datos de ejemplo como respaldo
          setData({
            welcome: `Bienvenido, ${user.username}`,
            info: 'Esta es información de ejemplo porque no se pudo cargar la real.',
          });
          setErrorData('No se pudo cargar la información real.');
        } finally {
          setLoadingData(false);
        }
      }
      loadData();
    }, [token, user]);

    return (
      <div className="dashboard-container">
        <header className="dashboard-header">
          <h1>EDÉN - Asistente Empresarial Inteligente</h1>
          <div>
            <span>Usuario: {user.username}</span>{' '}
            <button onClick={logout} className="logout-button" title="Cerrar sesión">
              Salir
            </button>
          </div>
        </header>
        <main className="dashboard-main">
          {loadingData ? (
            <p>Cargando datos...</p>
          ) : (
            <>
              {errorData && <p className="error">{errorData}</p>}
              <section className="dashboard-welcome">
                <h2>{data?.welcome}</h2>
                <p>{data?.info}</p>
              </section>
              {/* Aquí se pueden agregar más componentes y rutas internas */}
            </>
          )}
        </main>
      </div>
    );
  }

  // Renderizado condicional según si hay usuario autenticado
  return (
    <div className="app-container">
      {user ? <Dashboard /> : <AuthForm />}
    </div>
  );
}