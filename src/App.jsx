import React, { useState, useEffect } from 'react'
import { Routes, Route, Navigate, useNavigate } from 'react-router-dom'

// Estilos propios
import './style.css'

// Componentes de páginas
function Login({ onLogin }) {
  const [username, setUsername] = useState('')
  const [password, setPassword] = useState('')
  const [error, setError] = useState(null)
  const navigate = useNavigate()

  // Maneja el envío del formulario de login
  async function handleSubmit(e) {
    e.preventDefault()
    setError(null)
    try {
      const params = new URLSearchParams()
      params.append('username', username)
      params.append('password', password)

      const res = await fetch('/api/auth/login', {
        method: 'POST',
        headers: { 'Content-Type': 'application/x-www-form-urlencoded' },
        body: params.toString(),
      })

      if (!res.ok) {
        if (res.status === 401) {
          setError('Usuario o contraseña incorrectos')
        } else {
          setError('Error en el servidor, intente más tarde')
        }
        return
      }

      const data = await res.json()
      if (data.access_token) {
        localStorage.setItem('token', data.access_token)
        onLogin()
        navigate('/')
      } else {
        setError('Respuesta inválida del servidor')
      }
    } catch {
      setError('No se pudo conectar con el servidor')
    }
  }

  return (
    <div className="auth-container">
      <h2>Iniciar sesión</h2>
      <form onSubmit={handleSubmit} className="auth-form">
        <label>
          Usuario
          <input
            type="text"
            value={username}
            onChange={e => setUsername(e.target.value)}
            required
            autoComplete="username"
          />
        </label>
        <label>
          Contraseña
          <input
            type="password"
            value={password}
            onChange={e => setPassword(e.target.value)}
            required
            autoComplete="current-password"
          />
        </label>
        {error && <p className="error">{error}</p>}
        <button type="submit">Entrar</button>
      </form>
      <p>
        ¿No tienes cuenta? <a href="/register" onClick={e => { e.preventDefault(); navigate('/register') }}>Regístrate</a>
      </p>
    </div>
  )
}

function Register() {
  const [username, setUsername] = useState('')
  const [password, setPassword] = useState('')
  const [error, setError] = useState(null)
  const [success, setSuccess] = useState(null)
  const navigate = useNavigate()

  // Maneja el envío del formulario de registro
  async function handleSubmit(e) {
    e.preventDefault()
    setError(null)
    setSuccess(null)
    try {
      const params = new URLSearchParams()
      params.append('username', username)
      params.append('password', password)

      const res = await fetch('/api/auth/register', {
        method: 'POST',
        headers: { 'Content-Type': 'application/x-www-form-urlencoded' },
        body: params.toString(),
      })

      if (res.status === 201) {
        setSuccess('Registro exitoso. Ahora puedes iniciar sesión.')
        setUsername('')
        setPassword('')
        setTimeout(() => navigate('/login'), 2000)
      } else if (res.status === 400) {
        const data = await res.json()
        setError(data.detail || 'Error en los datos enviados')
      } else {
        setError('Error en el servidor, intente más tarde')
      }
    } catch {
      setError('No se pudo conectar con el servidor')
    }
  }

  return (
    <div className="auth-container">
      <h2>Registro de usuario</h2>
      <form onSubmit={handleSubmit} className="auth-form">
        <label>
          Usuario
          <input
            type="text"
            value={username}
            onChange={e => setUsername(e.target.value)}
            required
            autoComplete="username"
          />
        </label>
        <label>
          Contraseña
          <input
            type="password"
            value={password}
            onChange={e => setPassword(e.target.value)}
            required
            autoComplete="new-password"
          />
        </label>
        {error && <p className="error">{error}</p>}
        {success && <p className="success">{success}</p>}
        <button type="submit">Registrar</button>
      </form>
      <p>
        ¿Ya tienes cuenta? <a href="/login" onClick={e => { e.preventDefault(); navigate('/login') }}>Inicia sesión</a>
      </p>
    </div>
  )
}

// Componente para proteger rutas que requieren autenticación
function PrivateRoute({ children }) {
  const token = localStorage.getItem('token')
  if (!token) {
    return <Navigate to="/login" replace />
  }
  return children
}

// Página principal protegida (dashboard simplificado)
function Dashboard() {
  const [user, setUser] = useState(null)
  const [loading, setLoading] = useState(true)
  const [error, setError] = useState(null)
  const navigate = useNavigate()

  // Carga datos del usuario autenticado
  useEffect(() => {
    async function fetchUser() {
      const token = localStorage.getItem('token')
      if (!token) {
        setLoading(false)
        return
      }
      try {
        const res = await fetch('/api/auth/me', {
          headers: { Authorization: `Bearer ${token}` },
        })
        if (res.ok) {
          const data = await res.json()
          setUser(data)
        } else {
          // Token inválido o expirado
          localStorage.removeItem('token')
          navigate('/login')
        }
      } catch {
        setError('No se pudo conectar con el servidor')
      } finally {
        setLoading(false)
      }
    }
    fetchUser()
  }, [navigate])

  // Cierra sesión
  function logout() {
    localStorage.removeItem('token')
    navigate('/login')
  }

  if (loading) {
    return <div className="loading">Cargando...</div>
  }

  if (error) {
    return <div className="error">{error}</div>
  }

  return (
    <div className="dashboard">
      <header>
        <h1>Bienvenido, {user?.username || 'Usuario'}</h1>
        <button onClick={logout} className="btn-logout">Cerrar sesión</button>
      </header>
      <main>
        <p>Esta es la página principal del asistente empresarial EDÉN.</p>
        <p>Desde aquí podrás gestionar cotizaciones, proyectos, tareas y más.</p>
        {/* Aquí se pueden agregar más componentes y rutas internas */}
      </main>
    </div>
  )
}

export default function App() {
  const [isAuthenticated, setIsAuthenticated] = useState(false)

  // Verifica si hay token en localStorage al montar
  useEffect(() => {
    const token = localStorage.getItem('token')
    setIsAuthenticated(!!token)
  }, [])

  // Actualiza estado al iniciar sesión o registro exitoso
  function handleLogin() {
    setIsAuthenticated(true)
  }

  return (
    <Routes>
      <Route
        path="/login"
        element={
          isAuthenticated ? <Navigate to="/" replace /> : <Login onLogin={handleLogin} />
        }
      />
      <Route
        path="/register"
        element={
          isAuthenticated ? <Navigate to="/" replace /> : <Register />
        }
      />
      <Route
        path="/"
        element={
          <PrivateRoute>
            <Dashboard />
          </PrivateRoute>
        }
      />
      {/* Ruta comodín para redirigir a login si no está autenticado */}
      <Route
        path="*"
        element={
          isAuthenticated ? <Navigate to="/" replace /> : <Navigate to="/login" replace />
        }
      />
    </Routes>
  )
}