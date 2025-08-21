'use client'

import { createContext, useContext, useEffect, useState } from 'react'
import { User, Session, AuthError } from '@supabase/supabase-js'
import { createClient } from '@/lib/supabase/client'

type UserProfile = {
  id: string
  email: string
  nome: string
  empresa?: string
  cargo?: string
  telefone?: string
  avatar_url?: string
  role: 'admin' | 'user' | 'viewer'
  permissions: string[]
  created_at: string
  updated_at: string
}

interface AuthContextType {
  user: User | null
  userProfile: UserProfile | null
  session: Session | null
  loading: boolean
  signUp: (email: string, password: string, userData?: { nome: string; empresa?: string; cargo?: string }) => Promise<{ error: AuthError | null }>
  signIn: (email: string, password: string) => Promise<{ error: AuthError | null }>
  signOut: () => Promise<{ error: AuthError | null }>
  updateProfile: (updates: Partial<UserProfile>) => Promise<{ error: any }>
  resetPassword: (email: string) => Promise<{ error: AuthError | null }>
}

const AuthContext = createContext<AuthContextType | undefined>(undefined)

export function AuthProvider({ children }: { children: React.ReactNode }) {
  const [user, setUser] = useState<User | null>(null)
  const [userProfile, setUserProfile] = useState<UserProfile | null>(null)
  const [session, setSession] = useState<Session | null>(null)
  const [loading, setLoading] = useState(true)
  
  // Criar instância do cliente Supabase
  const supabase = createClient()

  // Função para buscar perfil do usuário
  const fetchUserProfile = async (userId: string) => {
    try {
      const response = await fetch(`http://localhost:8000/api/auth/profile/${userId}`)
      
      if (!response.ok) {
        console.error('Erro ao buscar perfil:', response.statusText)
        return
      }

      const data = await response.json()
      setUserProfile(data)
    } catch (error) {
      console.error('Erro ao buscar perfil do usuário:', error)
    }
  }

  useEffect(() => {
    // Obter sessão inicial
    const getInitialSession = async () => {
      try {
        const { data: { session } } = await supabase.auth.getSession()
        setSession(session)
        setUser(session?.user ?? null)

        if (session?.user) {
          await fetchUserProfile(session.user.id)
        }
      } catch (error) {
        console.error('Erro ao obter sessão inicial:', error)
      } finally {
        setLoading(false)
      }
    }

    getInitialSession()

    // Escutar mudanças de autenticação
    const { data: { subscription } } = supabase.auth.onAuthStateChange(
      async (event: any, session: Session | null) => {
        setSession(session)
        setUser(session?.user ?? null)

        if (session?.user) {
          await fetchUserProfile(session.user.id)
        } else {
          setUserProfile(null)
        }

        setLoading(false)
      }
    )

    return () => {
      subscription.unsubscribe()
    }
  }, [])

  // Função de cadastro
  const signUp = async (
    email: string, 
    password: string, 
    userData?: { nome: string; empresa?: string; cargo?: string }
  ) => {
    try {
      const { error } = await supabase.auth.signUp({
        email,
        password,
        options: {
          data: {
            nome: userData?.nome || '',
            empresa: userData?.empresa || '',
            cargo: userData?.cargo || ''
          }
        }
      })

      return { error }
    } catch (error) {
      console.error('Erro no cadastro:', error)
      return { error: error as AuthError }
    }
  }

  // Função de login
  const signIn = async (email: string, password: string) => {
    try {
      const { error } = await supabase.auth.signInWithPassword({
        email,
        password
      })

      return { error }
    } catch (error) {
      console.error('Erro no login:', error)
      return { error: error as AuthError }
    }
  }

  // Função de logout
  const signOut = async () => {
    try {
      const { error } = await supabase.auth.signOut()
      
      if (!error) {
        setUser(null)
        setUserProfile(null)
        setSession(null)
      }

      return { error }
    } catch (error) {
      console.error('Erro no logout:', error)
      return { error: error as AuthError }
    }
  }

  // Função para atualizar perfil
  const updateProfile = async (updates: Partial<UserProfile>) => {
    if (!user) {
      return { error: new Error('Usuário não autenticado') }
    }

    try {
      const { error } = await supabase
        .from('user_profiles')
        .update({
          ...updates,
          updated_at: new Date().toISOString()
        })
        .eq('id', user.id)

      if (!error && userProfile) {
        setUserProfile({ ...userProfile, ...updates })
      }

      return { error }
    } catch (error) {
      console.error('Erro ao atualizar perfil:', error)
      return { error }
    }
  }

  // Função para resetar senha
  const resetPassword = async (email: string) => {
    try {
      const { error } = await supabase.auth.resetPasswordForEmail(email, {
        redirectTo: `${window.location.origin}/reset-password`
      })

      return { error }
    } catch (error) {
      console.error('Erro ao resetar senha:', error)
      return { error: error as AuthError }
    }
  }

  const value = {
    user,
    userProfile,
    session,
    loading,
    signUp,
    signIn,
    signOut,
    updateProfile,
    resetPassword
  }

  return (
    <AuthContext.Provider value={value}>
      {children}
    </AuthContext.Provider>
  )
}

export function useAuth() {
  const context = useContext(AuthContext)
  if (context === undefined) {
    throw new Error('useAuth deve ser usado dentro de um AuthProvider')
  }
  return context
}
