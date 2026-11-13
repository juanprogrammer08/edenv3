import React, { useState, useEffect } from 'react';

// Componente principal de la aplicación EDÉN
export default function App() {
  // Estado para almacenar el token JWT y el usuario autenticado
  const [token, setToken] = useState(localStorage.getItem('token') || '');
  const [user, setUser] = useState(null);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState('');

  // Estados para formularios de login y registro
  const [formMode, setFormMode] = useState('login'); // 'login' o 'register'
  const [username, setUsername] = useState('');
  const [password, setPassword] = useState('');

  // Función para limpiar el estado de error
  function clearError() {
    setError('');
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
    setUsername('');
    setPassword('');
    setFormMode('login');
    setError('');
  }

  // Función para cargar datos del usuario autenticado (/auth/me)
  async function fetchUser(token) {
    setLoading(true);
    setError('');
    try {
      const res = await fetch('/api/auth/me', {
        headers: {
          Authorization: `Bearer ${token}`,
        },
      });
      if (!res.ok) {
        throw new Error('No autorizado');
      }
      const data = await res.json();
      setUser(data);
    } catch {
      // Token inválido o expirado, limpiar sesión
      logout();
    } finally {
      setLoading(false);
    }
  }

  // Al montar o cambiar token, intentar cargar usuario
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
    clearError();
    setLoading(true);
    const url = formMode === 'login' ? '/api/auth/login' : '/api/auth/register';
    const body = new URLSearchParams();
    body.append('username', username.trim());
    body.append('password', password);
    try {
      const res = await fetch(url, {
        method: 'POST',
        headers: {
          'Content-Type': 'application/x-www-form-urlencoded',
        },
        body,
      });
      if (!res.ok) {
        if (res.status === 400) {
          const errData = await res.json().catch(() => null);
          setError(errData?.detail || 'Error en los datos');
        } else if (res.status === 401) {
          setError('Credenciales incorrectas');
        } else {
          setError('Error en la comunicación con el servidor');
        }
        return;
      }
      const data = await res.json();
      if (data.access_token) {
        saveToken(data.access_token);
        setUsername('');
        setPassword('');
      } else {
        setError('Respuesta inesperada del servidor');
      }
    } catch {
      setError('No se pudo conectar con el servidor');
    } finally {
      setLoading(false);
    }
  }

  // Componente para mostrar el formulario de login o registro
  function AuthForm() {
    return (
      <div className="auth-container">
        <h2>{formMode === 'login' ? 'Iniciar sesión' : 'Registrar usuario'}</h2>
        <form onSubmit={handleSubmit} autoComplete="off">
          <label htmlFor="username">Usuario</label>
          <input
            id="username"
            name="username"
            type="text"
            value={username}
            onChange={e => setUsername(e.target.value)}
            required
            minLength={3}
            maxLength={32}
            autoComplete="username"
            disabled={loading}
          />
          <label htmlFor="password">Contraseña</label>
          <input
            id="password"
            name="password"
            type="password"
            value={password}
            onChange={e => setPassword(e.target.value)}
            required
            minLength={6}
            maxLength={128}
            autoComplete={formMode === 'login' ? 'current-password' : 'new-password'}
            disabled={loading}
          />
          {error && <p className="error">{error}</p>}
          <button type="submit" disabled={loading}>
            {loading ? 'Procesando...' : formMode === 'login' ? 'Entrar' : 'Registrar'}
          </button>
        </form>
        <p className="toggle-form">
          {formMode === 'login' ? (
            <>
              ¿No tienes cuenta?{' '}
              <button onClick={() => { clearError(); setFormMode('register'); }} disabled={loading} className="link-button">
                Regístrate aquí
              </button>
            </>
          ) : (
            <>
              ¿Ya tienes cuenta?{' '}
              <button onClick={() => { clearError(); setFormMode('login'); }} disabled={loading} className="link-button">
                Inicia sesión
              </button>
            </>
          )}
        </p>
      </div>
    );
  }

  // Componente para mostrar la pantalla principal tras login
  function Dashboard() {
    // Estado para datos de ejemplo y carga de datos reales
    const [data, setData] = useState(null);
    const [loadingData, setLoadingData] = useState(false);
    const [errorData, setErrorData] = useState('');

    // Datos de ejemplo como respaldo
    const exampleData = {
      cotizaciones: [
        { id: 1, cliente: 'Cliente A', total: 1200, estado: 'Pendiente' },
        { id: 2, cliente: 'Cliente B', total: 850, estado: 'Aprobada' },
      ],
      proyectos: [
        { id: 1, nombre: 'Instalación X', estado: 'En progreso' },
        { id: 2, nombre: 'Mantenimiento Y', estado: 'Finalizado' },
      ],
    };

    // Cargar datos protegidos de la API
    async function fetchData() {
      setLoadingData(true);
      setErrorData('');
      try {
        const res = await fetch('/api/protected/data', {
          headers: {
            Authorization: `Bearer ${token}`,
          },
        });
        if (!res.ok) {
          throw new Error('Error al obtener datos');
        }
        const json = await res.json();
        setData(json);
      } catch {
        // Usar datos de ejemplo si falla la API
        setData(exampleData);
        setErrorData('No se pudo cargar datos reales, mostrando datos de ejemplo.');
      } finally {
        setLoadingData(false);
      }
    }

    useEffect(() => {
      fetchData();
      // eslint-disable-next-line react-hooks/exhaustive-deps
    }, []);

    return (
      <div className="dashboard-container">
        <header>
          <h1>Bienvenido, {user?.username}</h1>
          <button onClick={logout} className="logout-button" title="Cerrar sesión">
            Cerrar sesión
          </button>
        </header>
        <main>
          <section>
            <h2>Cotizaciones</h2>
            {loadingData && <p>Cargando cotizaciones...</p>}
            {errorData && <p className="error">{errorData}</p>}
            <ul>
              {(data?.cotizaciones || []).map(cot => (
                <li key={cot.id}>
                  <strong>{cot.cliente}</strong>: ${cot.total} - {cot.estado}
                </li>
              ))}
              {!loadingData && data?.cotizaciones?.length === 0 && <li>No hay cotizaciones.</li>}
            </ul>
          </section>
          <section>
            <h2>Proyectos</h2>
            <ul>
              {(data?.proyectos || []).map(proy => (
                <li key={proy.id}>
                  <strong>{proy.nombre}</strong> - {proy.estado}
                </li>
              ))}
              {!loadingData && data?.proyectos?.length === 0 && <li>No hay proyectos.</li>}
            </ul>
          </section>
        </main>
      </div>
    );
  }

  // Renderizado condicional: si no hay token o usuario, mostrar formulario de autenticación
  if (!token || !user) {
    return <AuthForm />;
  }

  // Si está cargando datos del usuario, mostrar mensaje
  if (loading) {
    return (
      <div className="loading-screen">
        <p>Cargando usuario...</p>
      </div>
    );
  }

  // Mostrar dashboard principal
  return <Dashboard />;
}