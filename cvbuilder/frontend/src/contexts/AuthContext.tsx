import { createContext, useContext, useEffect, useState, useCallback } from 'react'
import type { ReactNode } from 'react'
import {
  type UserOut,
  loginUser,
  registerUser,
  getCurrentUser,
  setToken,
  clearToken,
  getToken,
} from '../lib/api'

interface AuthContextType {
  user: UserOut | null
  isLoading: boolean
  login: (email: string, password: string) => Promise<void>
  register: (email: string, password: string, fullName?: string) => Promise<void>
  logout: () => void
}

const AuthContext = createContext<AuthContextType | null>(null)

export function AuthProvider({ children }: { children: ReactNode }) {
  const [user, setUser] = useState<UserOut | null>(null)
  const [isLoading, setIsLoading] = useState(true)

  useEffect(() => {
    const token = getToken()
    if (!token) {
      setIsLoading(false)
      return
    }
    getCurrentUser()
      .then(setUser)
      .catch(() => clearToken())
      .finally(() => setIsLoading(false))
  }, [])

  const login = useCallback(async (email: string, password: string) => {
    const tokenData = await loginUser(email, password)
    setToken(tokenData.access_token)
    const me = await getCurrentUser()
    setUser(me)
  }, [])

  const register = useCallback(async (email: string, password: string, fullName?: string) => {
    await registerUser(email, password, fullName)
    // Auto-login after registration
    const tokenData = await loginUser(email, password)
    setToken(tokenData.access_token)
    const me = await getCurrentUser()
    setUser(me)
  }, [])

  const logout = useCallback(() => {
    clearToken()
    setUser(null)
    window.location.href = '/login'
  }, [])

  return (
    <AuthContext.Provider value={{ user, isLoading, login, register, logout }}>
      {children}
    </AuthContext.Provider>
  )
}

export function useAuth(): AuthContextType {
  const ctx = useContext(AuthContext)
  if (!ctx) throw new Error('useAuth must be used within AuthProvider')
  return ctx
}
