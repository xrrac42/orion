'use client';

import MainLayout from '@/components/layout/MainLayout';
import { Card, CardContent, CardHeader, CardTitle } from '@/components/ui/Card';
import { Button } from '@/components/ui/Button';
import { Input } from '@/components/ui/Input';
import { mockClientes, mockBalancetes } from '@/lib/mockData';
import { formatDate, formatMonth } from '@/lib/utils';
import Link from 'next/link';
import { 
  UsersIcon, 
  DocumentTextIcon, 
  ExclamationTriangleIcon,
  CheckCircleIcon 
} from '@heroicons/react/24/outline';

export default function DashboardPage() {
  const totalClientes = mockClientes.length;
  const balancetesPendentes = mockClientes.filter(cliente => {
    const ultimoBalancete = mockBalancetes
      .filter(b => b.clienteId === cliente.id)
      .sort((a, b) => new Date(b.dataUpload).getTime() - new Date(a.dataUpload).getTime())[0];
    
    if (!ultimoBalancete) return true;
    
    const hoje = new Date();
    const mesAtual = hoje.getMonth() + 1;
    const anoAtual = hoje.getFullYear();
    
    return ultimoBalancete.mes !== mesAtual || ultimoBalancete.ano !== anoAtual;
  }).length;
  
  const uploadsRecentes = mockBalancetes
    .sort((a, b) => new Date(b.dataUpload).getTime() - new Date(a.dataUpload).getTime())
    .slice(0, 5);

  return (
    <MainLayout>
      <div className="py-6">
        <div className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8">
          <div className="mb-8">
            <h1 className="text-3xl font-bold text-gray-900">Dashboard</h1>
            <p className="mt-2 text-gray-600">
              Visão geral da gestão contábil dos seus clientes
            </p>
          </div>

          {/* KPIs */}
          <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-4 gap-6 mb-8">
            <Card>
              <CardContent className="flex items-center p-6">
                <div className="flex items-center">
                  <UsersIcon className="h-8 w-8 text-blue-600" />
                  <div className="ml-4">
                    <p className="text-sm font-medium text-gray-500">Total de Clientes</p>
                    <p className="text-2xl font-bold text-gray-900">{totalClientes}</p>
                  </div>
                </div>
              </CardContent>
            </Card>

            <Card>
              <CardContent className="flex items-center p-6">
                <div className="flex items-center">
                  <DocumentTextIcon className="h-8 w-8 text-green-600" />
                  <div className="ml-4">
                    <p className="text-sm font-medium text-gray-500">Balancetes Enviados</p>
                    <p className="text-2xl font-bold text-gray-900">{mockBalancetes.length}</p>
                  </div>
                </div>
              </CardContent>
            </Card>

            <Card>
              <CardContent className="flex items-center p-6">
                <div className="flex items-center">
                  <ExclamationTriangleIcon className="h-8 w-8 text-orange-600" />
                  <div className="ml-4">
                    <p className="text-sm font-medium text-gray-500">Balancetes Pendentes</p>
                    <p className="text-2xl font-bold text-gray-900">{balancetesPendentes}</p>
                  </div>
                </div>
              </CardContent>
            </Card>

            <Card>
              <CardContent className="flex items-center p-6">
                <div className="flex items-center">
                  <CheckCircleIcon className="h-8 w-8 text-blue-600" />
                  <div className="ml-4">
                    <p className="text-sm font-medium text-gray-500">Processados</p>
                    <p className="text-2xl font-bold text-gray-900">
                      {mockBalancetes.filter(b => b.processado).length}
                    </p>
                  </div>
                </div>
              </CardContent>
            </Card>
          </div>

          <div className="grid grid-cols-1 lg:grid-cols-2 gap-8">
            {/* Uploads Recentes */}
            <Card>
              <CardHeader>
                <CardTitle>Uploads Recentes</CardTitle>
              </CardHeader>
              <CardContent>
                <div className="space-y-4">
                  {uploadsRecentes.map((balancete) => {
                    const cliente = mockClientes.find(c => c.id === balancete.clienteId);
                    return (
                      <div key={balancete.id} className="flex items-center justify-between p-4 bg-gray-50 rounded-lg">
                        <div>
                          <p className="font-medium text-gray-900">{cliente?.nome}</p>
                          <p className="text-sm text-gray-500">
                            {formatMonth(balancete.mes, balancete.ano)} • {formatDate(balancete.dataUpload)}
                          </p>
                        </div>
                        <div className="flex items-center space-x-2">
                          <span className={`inline-flex px-2 py-1 text-xs font-semibold rounded-full ${
                            balancete.processado 
                              ? 'bg-green-100 text-green-800' 
                              : 'bg-yellow-100 text-yellow-800'
                          }`}>
                            {balancete.processado ? 'Processado' : 'Pendente'}
                          </span>
                          <Link href={`/clientes/${balancete.clienteId}/dashboard?balancete=${balancete.id}`}>
                            <Button size="sm" variant="outline">
                              Ver Dashboard
                            </Button>
                          </Link>
                        </div>
                      </div>
                    );
                  })}
                </div>
              </CardContent>
            </Card>

            {/* Pesquisa Rápida de Clientes */}
            <Card>
              <CardHeader>
                <CardTitle>Pesquisa Rápida</CardTitle>
              </CardHeader>
              <CardContent>
                <div className="space-y-4">
                  <Input
                    placeholder="Buscar cliente por nome ou CNPJ..."
                    className="w-full"
                  />
                  
                  <div className="space-y-3">
                    {mockClientes.slice(0, 3).map((cliente) => (
                      <div key={cliente.id} className="flex items-center justify-between p-4 bg-gray-50 rounded-lg">
                        <div>
                          <p className="font-medium text-gray-900">{cliente.nome}</p>
                          <p className="text-sm text-gray-500">{cliente.cnpj}</p>
                        </div>
                        <Link href={`/clientes/${cliente.id}`}>
                          <Button size="sm" variant="outline">
                            Gerenciar
                          </Button>
                        </Link>
                      </div>
                    ))}
                  </div>

                  <Link href="/clientes">
                    <Button className="w-full" variant="outline">
                      Ver Todos os Clientes
                    </Button>
                  </Link>
                </div>
              </CardContent>
            </Card>
          </div>

          {/* Alertas */}
          {balancetesPendentes > 0 && (
            <Card className="mt-8 border-orange-200 bg-orange-50">
              <CardContent className="p-6">
                <div className="flex items-center">
                  <ExclamationTriangleIcon className="h-6 w-6 text-orange-600 mr-3" />
                  <div>
                    <h3 className="text-lg font-medium text-orange-900">
                      Atenção: Balancetes Pendentes
                    </h3>
                    <p className="text-orange-700">
                      Existem {balancetesPendentes} cliente(s) com balancetes pendentes para o mês atual.
                    </p>
                  </div>
                </div>
              </CardContent>
            </Card>
          )}
        </div>
      </div>
    </MainLayout>
  );
}
