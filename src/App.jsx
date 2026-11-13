import React, { useState, useEffect } from 'react';

// Componente principal de la aplicación EDÉN
export default function App() {
  // Estado para almacenar el token JWT
  const [token, setToken] = useState(localStorage.getItem('token') || '');
  // Estado para controlar si el usuario está autenticado
  const [isAuthenticated, setIsAuthenticated] = useState(false);
  // Estado para almacenar datos del usuario autenticado
  const [user, setUser] = useState(null);
  // Estado para controlar la carga de la app
  const [loading, setLoading] = useState(true);
  // Estado para controlar errores en login/registro
  const [error, setError] = useState('');

  // Datos de ejemplo para respaldo en caso de fallo de API
  const exampleData = {
    message: 'Bienvenido a EDÉN - Asistente Empresarial Inteligente',
  };

  // Función para validar el token y obtener datos del usuario
  async function fetchUser(token) {
    try {
      const res = await fetch('/api/auth/me', {
        headers: {
          Authorization: `Bearer ${token}`,
        },
      });
      if (!res.ok) throw new Error('Token inválido');
      const data = await res.json();
      setUser(data);
      setIsAuthenticated(true);
    } catch {
      setUser(null);
      setIsAuthenticated(false);
      setToken('');
      localStorage.removeItem('token');
    } finally {
      setLoading(false);
    }
  }

  // Efecto para validar token al montar el componente
  useEffect(() => {
    if (token) {
      fetchUser(token);
    } else {
      setLoading(false);
    }
  }, [token]);

  // Maneja el envío del formulario de login o registro
  async function handleAuth(event, mode) {
    event.preventDefault();
    setError('');
    const form = event.target;
    const formData = new URLSearchParams();
    formData.append('username', form.username.value.trim());
    formData.append('password', form.password.value);

    try {
      const res = await fetch(`/api/auth/${mode}`, {
        method: 'POST',
        headers: {
          'Content-Type': 'application/x-www-form-urlencoded',
        },
        body: formData.toString(),
      });
      if (!res.ok) {
        if (res.status === 400 || res.status === 401) {
          setError('Usuario o contraseña incorrectos');
        } else {
          setError('Error en el servidor, intente más tarde');
        }
        return;
      }
      const data = await res.json();
      if (data.access_token) {
        localStorage.setItem('token', data.access_token);
        setToken(data.access_token);
      } else {
        setError('Respuesta inválida del servidor');
      }
    } catch {
      setError('No se pudo conectar con el servidor');
    }
  }

  // Cierra sesión limpiando token y estado
  function handleLogout() {
    setToken('');
    setIsAuthenticated(false);
    setUser(null);
    localStorage.removeItem('token');
  }

  // Renderiza el formulario de login o registro
  function AuthForm({ mode }) {
    return (
      <form onSubmit={(e) => handleAuth(e, mode)} className="auth-form">
        <h2>{mode === 'login' ? 'Iniciar Sesión' : 'Registrar Usuario'}</h2>
        <label htmlFor="username">Usuario</label>
        <input id="username" name="username" type="text" required autoComplete="username" />
        <label htmlFor="password">Contraseña</label>
        <input id="password" name="password" type="password" required autoComplete={mode === 'login' ? 'current-password' : 'new-password'} />
        <button type="submit">{mode === 'login' ? 'Entrar' : 'Registrar'}</button>
        {error && <p className="error">{error}</p>}
      </form>
    );
  }

  // Componente protegido que muestra contenido tras login
  function ProtectedContent() {
    // Ejemplo simple de contenido protegido
    return (
      <div className="protected-content">
        <header>
          <h1>EDÉN - Asistente Empresarial Inteligente</h1>
          <p>Bienvenido, <strong>{user?.username}</strong></p>
          <button onClick={handleLogout} className="logout-button" aria-label="Cerrar sesión">Cerrar sesión</button>
        </header>
        <main>
          <section>
            <h2>Panel Principal</h2>
            <p>{exampleData.message}</p>
            {/* Aquí se pueden agregar más componentes y rutas protegidas */}
          </section>
        </main>
      </div>
    );
  }

  // Renderizado principal
  if (loading) {
    return <div className="loading">Cargando...</div>;
  }

  if (!isAuthenticated) {
    // Muestra login y registro en pestañas simples
    const [mode, setMode] = useState('login');
    return (
      <div className="auth-container">
        <nav className="auth-nav" role="tablist" aria-label="Autenticación">
          <button
            role="tab"
            aria-selected={mode === 'login'}
            onClick={() => setMode('login')}
            className={mode === 'login' ? 'active' : ''}
            id="tab-login"
            aria-controls="tabpanel-login"
            type="button"
          >
            Iniciar Sesión
          </button>
          <button
            role="tab"
            aria-selected={mode === 'register'}
            onClick={() => setMode('register')}
            className={mode === 'register' ? 'active' : ''}
            id="tab-register"
            aria-controls="tabpanel-register"
            type="button"
          >
            Registrar
          </button>
        </nav>
        <section
          role="tabpanel"
          id={`tabpanel-${mode}`}
          aria-labelledby={`tab-${mode}`}
          tabIndex={0}
          className="auth-tabpanel"
        >
          <AuthForm mode={mode} />
        </section>
      </div>
    );
  }

  return <ProtectedContent />;
}