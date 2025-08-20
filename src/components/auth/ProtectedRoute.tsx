'use client'

import { useEffect, useState } from 'react'
import { useRouter } from 'next/navigation'
import { useAuth } from '@/contexts/AuthContext'

interface ProtectedRouteProps {
  children: React.ReactNode
  redirectTo?: string
  requireAdmin?: boolean
}

export default function ProtectedRoute({ 
  children, 
  redirectTo = '/login', 
  requireAdmin = false 
}: ProtectedRouteProps) {
  const { user, userProfile, loading } = useAuth()
  const router = useRouter()
  const [isChecking, setIsChecking] = useState(true)

  useEffect(() => {
    if (!loading) {
      // Se não está autenticado
      if (!user) {
        router.push(redirectTo)
        return
      }

      // Se requer admin mas não é admin
      if (requireAdmin && userProfile?.role !== 'admin') {
        router.push('/dashboard') // Redirecionar para dashboard se não for admin
        return
      }

      setIsChecking(false)
    }
  }, [user, userProfile, loading, router, redirectTo, requireAdmin])

  // Mostrar loading enquanto verifica autenticação
  if (loading || isChecking) {
    return (
      <div className="min-h-screen flex items-center justify-center bg-white">
        <div className="text-center">
          <div className="animate-spin rounded-full h-12 w-12 border-b-2 border-indigo-600 mx-auto"></div>
          <p className="mt-4 text-gray-600">Verificando autenticação...</p>
        </div>
      </div>
    )
  }

  // Se passou em todas as verificações, mostrar o conteúdo
  return <>{children}</>
}

// Hook personalizado para verificar se usuário está autenticado
export function useRequireAuth() {
  const { user, loading } = useAuth()
  const router = useRouter()

  useEffect(() => {
    if (!loading && !user) {
      router.push('/login')
    }
  }, [user, loading, router])

  return { user, loading }
}

// Hook para verificar permissões específicas
export function usePermission(permission: string) {
  const { userProfile } = useAuth()

  const permissions = {
    'view_all_clients': userProfile?.role === 'admin',
    'create_clients': userProfile?.role !== 'viewer',
    'edit_clients': userProfile?.role !== 'viewer',
    'delete_clients': userProfile?.role === 'admin',
    'upload_files': userProfile?.role !== 'viewer',
    'manage_users': userProfile?.role === 'admin',
    'view_quarantine': userProfile?.role === 'admin'
  }

  return permissions[permission as keyof typeof permissions] || false
}
