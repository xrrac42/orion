'use client'

import { useState, useEffect } from 'react'
import Link from 'next/link'
import MainLayout from '@/components/layout/MainLayout'
import { EyeIcon } from '@heroicons/react/24/outline'


export default function DashboardPage() {

  const [stats, setStats] = useState<any>({
    totalClientes: 0,
    totalBalancetes: 0,
    loading: true
  })

  useEffect(() => {
    const fetchStats = async () => {
      try {
  const res = await fetch('http://localhost:8000/api/home/stats');
        if (res.ok) {
          const data = await res.json();
          setStats({
            totalClientes: data.total_clientes || 0,
            totalBalancetes: data.total_balancetes || 0,
            recentUploads: data.recent_uploads || [],
            loading: false
          });
        } else {
          setStats((prev: any) => ({ ...prev, loading: false }));
        }
      } catch (error) {
        console.error('Erro ao buscar estatísticas:', error);
  setStats((prev: any) => ({ ...prev, loading: false }));
      }
    };
    fetchStats();
  }, []);

  if (stats.loading) {
    return (
      <div className="flex items-center justify-center min-h-screen">
        <div className="animate-spin rounded-full h-12 w-12 border-b-2 border-indigo-600"></div>
      </div>
    )
  }

  // Se não há dados, mostrar tela de boas-vindas
  if (stats.totalClientes === 0) {
    return (
      <div className="min-h-screen bg-gray-50 flex flex-col justify-center py-12 sm:px-6 lg:px-8">
        <div className="sm:mx-auto sm:w-full sm:max-w-md">
          <div className="text-center">
            <h1 className="text-4xl font-bold text-gray-900 mb-2">
              Bem-vindo ao Orion! 🚀
            </h1>
            <p className="text-lg text-gray-600 mb-8">
              Sua plataforma de gestão financeira está pronta para uso
            </p>
          </div>

          <div className="bg-white py-8 px-4 shadow sm:rounded-lg sm:px-10">
            <div className="space-y-6">
              <div className="text-center">
                <div className="mx-auto h-24 w-24 bg-indigo-100 rounded-full flex items-center justify-center mb-4">
                  <svg className="h-12 w-12 text-indigo-600" fill="none" viewBox="0 0 24 24" stroke="currentColor">
                    <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M9 19v-6a2 2 0 00-2-2H5a2 2 0 00-2 2v6a2 2 0 002 2h2a2 2 0 002-2zm0 0V9a2 2 0 012-2h2a2 2 0 012 2v10m-6 0a2 2 0 002 2h2a2 2 0 002-2m0 0V5a2 2 0 012-2h2a2 2 0 012 2v14a2 2 0 01-2 2h-2a2 2 0 01-2-2z" />
                  </svg>
                </div>
                <h2 className="text-xl font-semibold text-gray-900 mb-2">
                  Ainda não há números disponíveis
                </h2>
                <p className="text-gray-600 mb-6">
                  Para começar a ver seus dashboards e relatórios, você precisa cadastrar clientes e adicionar seus balancetes mensais.
                </p>
              </div>

              <div className="space-y-4">
                <h3 className="text-lg font-medium text-gray-900 text-center">
                  Primeiros passos:
                </h3>
                
                <div className="space-y-3">
                  <div className="flex items-center p-4 bg-gray-50 rounded-lg">
                    <div className="flex-shrink-0">
                      <div className="h-8 w-8 bg-indigo-600 rounded-full flex items-center justify-center">
                        <span className="text-white text-sm font-bold">1</span>
                      </div>
                    </div>
                    <div className="ml-4">
                      <p className="text-sm font-medium text-gray-900">Cadastre seus clientes</p>
                      <p className="text-sm text-gray-600">Adicione as empresas que você atende</p>
                    </div>
                  </div>

                  <div className="flex items-center p-4 bg-gray-50 rounded-lg">
                    <div className="flex-shrink-0">
                      <div className="h-8 w-8 bg-indigo-600 rounded-full flex items-center justify-center">
                        <span className="text-white text-sm font-bold">2</span>
                      </div>
                    </div>
                    <div className="ml-4">
                      <p className="text-sm font-medium text-gray-900">Adicione balancetes mensais</p>
                      <p className="text-sm text-gray-600">Insira receitas e despesas por mês/ano</p>
                    </div>
                  </div>

                  <div className="flex items-center p-4 bg-gray-50 rounded-lg">
                    <div className="flex-shrink-0">
                      <div className="h-8 w-8 bg-indigo-600 rounded-full flex items-center justify-center">
                        <span className="text-white text-sm font-bold">3</span>
                      </div>
                    </div>
                    <div className="ml-4">
                      <p className="text-sm font-medium text-gray-900">Visualize os insights</p>
                      <p className="text-sm text-gray-600">Acompanhe dashboards e relatórios automáticos</p>
                    </div>
                  </div>
                </div>
              </div>

              <div className="pt-4">
                <Link
                  href="/clientes"
                  className="w-full flex justify-center py-3 px-4 border border-transparent rounded-md shadow-sm text-sm font-medium text-white bg-indigo-600 hover:bg-indigo-700 focus:outline-none focus:ring-2 focus:ring-offset-2 focus:ring-indigo-500"
                >
                  🎯 Começar agora - Cadastrar primeiro cliente
                </Link>
              </div>
            </div>
          </div>
        </div>
      </div>
    )
  }

  // Dashboard com dados reais
  return (
    <MainLayout>
    <div className="p-6">
      <div className="mb-8">
        <h1 className="text-3xl font-bold text-gray-900">Início</h1>
        <p className="mt-2 text-gray-600">
          Visão geral da gestão contábil dos seus clientes
        </p>
      </div>

      {/* KPIs */}
      <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-4 gap-6 mb-8">
        <div className="bg-white overflow-hidden shadow rounded-lg">
          <div className="p-4 flex items-center justify-between">
            <div className="flex-1">
              <div className="text-lg font-medium text-gray-900">{stats.totalClientes}</div>
              <div className="text-sm text-gray-500 mt-1">Total de Clientes</div>
            </div>
            <div className="flex-shrink-0 text-gray-400 ml-4">
              <svg className="h-8 w-10" fill="none" viewBox="0 0 24 24" stroke="currentColor">
                <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M17 20h5v-2a3 3 0 00-5.356-1.857M17 20H7m10 0v-2c0-.656-.126-1.283-.356-1.857M7 20H2v-2a3 3 0 015.356-1.857M7 20v-2c0-.656.126-1.283.356-1.857m0 0a5.002 5.002 0 019.288 0M15 7a3 3 0 11-6 0 3 3 0 016 0zm6 3a2 2 0 11-4 0 2 2 0 014 0zM7 10a2 2 0 11-4 0 2 2 0 014 0z" />
              </svg>
            </div>
          </div>
        </div>

        <div className="bg-white overflow-hidden shadow rounded-lg">
          <div className="p-4 flex items-center justify-between">
            <div className="flex-1">
              <div className="text-lg font-medium text-gray-900">{stats.totalBalancetes}</div>
              <div className="text-sm text-gray-500 mt-1">Balancetes Cadastrados</div>
            </div>
            <div className="flex-shrink-0 text-gray-400 ml-4">
              <svg className="h-8 w-10" fill="none" viewBox="0 0 24 24" stroke="currentColor">
                <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M9 12h6m-6 4h6m2 5H7a2 2 0 01-2-2V5a2 2 0 012-2h5.586a1 1 0 01.707.293l5.414 5.414a1 1 0 01.293.707V19a2 2 0 01-2 2z" />
              </svg>
            </div>
          </div>
        </div>

        
      </div>

      {/* Recent uploads */}
    <div className="mt-6">
        <h3 className="text-lg font-medium text-gray-900 mb-4">Últimos uploads de balancete</h3>
        <div className="bg-white shadow rounded-lg p-4 mt-4">
      {Array.isArray((stats as any).recentUploads) && (stats as any).recentUploads.length > 0 ? (
            <ul className="divide-y divide-gray-100">
              {(stats as any).recentUploads.map((u: any) => (
                <li key={u.id} className="py-3 flex items-center justify-between">
                  <div>
                    <p className="text-sm font-medium text-gray-900">{u.file_name}</p>
                    <p className="text-xs text-gray-500">Cliente: {u.client_name}</p>
                  </div>
                  <div className="flex items-center space-x-3">
                    <div className="text-xs text-gray-400">{new Date(u.uploaded_at).toLocaleString()}</div>
                    {(() => {
                      const safeClientId = u.client_id || u.clientId || '';
                      if (!safeClientId) {
                        return <span className="text-sm text-gray-500">Cliente desconhecido</span>;
                      }

                      if (u.analysis_id) {
                        return (
                          <Link href={`/clientes/${safeClientId}/dashboard/${u.analysis_id}`}>
                            <button className="inline-flex items-center px-3 py-1 border rounded-md text-sm text-indigo-600 hover:bg-indigo-50 cursor-pointer">
                              <EyeIcon className="h-4 w-4" />
                            </button>
                          </Link>
                        );
                      }

                      return (
                        <Link href={`/clientes/${safeClientId}/balancetes`}>
                          <button className="inline-flex items-center px-3 py-1 border rounded-md text-sm text-gray-600 hover:bg-gray-50 cursor-pointer">
                            <EyeIcon className="h-4 w-4" />
                          </button>
                        </Link>
                      );
                    })()}

                  </div>
                </li>
              ))}
            </ul>
          ) : (
            <p className="text-sm text-gray-500">Nenhum upload recente encontrado.</p>
          )}
        </div>
      </div>

      {/* Links rápidos */}
  <div className="grid grid-cols-1 md:grid-cols-2 gap-6 mt-4">
        <div className="bg-white overflow-hidden shadow rounded-lg">
          <div className="p-6">
            <h3 className="text-lg font-medium text-gray-900 mb-4">Ações Rápidas</h3>
            <div className="space-y-3">
              <Link
                href="/clientes"
                className="block w-full text-left px-4 py-2 border border-gray-300 rounded-md hover:bg-gray-50"
              >
                📋 Gerenciar Clientes
              </Link>
              <Link
                href="/relatorios"
                className="block w-full text-left px-4 py-2 border border-gray-300 rounded-md hover:bg-gray-50"
              >
                📊 Ver Relatórios
              </Link>
            </div>
          </div>
        </div>

        <div className="bg-white overflow-hidden shadow rounded-lg">
          <div className="p-6">
            <h3 className="text-lg font-medium text-gray-900 mb-4">Status do Sistema</h3>
            <div className="space-y-3">
              <div className="flex items-center">
                <div className="h-2 w-2 bg-green-400 rounded-full mr-3"></div>
                <span className="text-sm text-gray-600">Banco de dados conectado</span>
              </div>
              <div className="flex items-center">
                <div className="h-2 w-2 bg-green-400 rounded-full mr-3"></div>
                <span className="text-sm text-gray-600">Sistema operacional</span>
              </div>
            </div>
          </div>
        </div>
      </div>
    </div>
    </MainLayout>
  )
}
