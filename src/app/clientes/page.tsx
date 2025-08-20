'use client';

import { useState } from 'react';
import MainLayout from '@/components/layout/MainLayout';
import { Card, CardContent, CardHeader, CardTitle } from '@/components/ui/Card';
import { Button } from '@/components/ui/Button';
import { Input } from '@/components/ui/Input';
import { mockClientes, mockBalancetes } from '@/lib/mockData';
import { formatCNPJ, formatDate, formatMonth } from '@/lib/utils';
import Link from 'next/link';
import { 
  PlusIcon, 
  PencilIcon, 
  TrashIcon,
  EyeIcon,
  DocumentArrowUpIcon
} from '@heroicons/react/24/outline';

export default function ClientesPage() {
  const [searchTerm, setSearchTerm] = useState('');
  const [showAddForm, setShowAddForm] = useState(false);

  const filteredClientes = mockClientes.filter(cliente =>
    cliente.nome.toLowerCase().includes(searchTerm.toLowerCase()) ||
    cliente.cnpj.includes(searchTerm) ||
    cliente.contato.toLowerCase().includes(searchTerm.toLowerCase())
  );

  const getUltimoBalancete = (clienteId: string) => {
    return mockBalancetes
      .filter(b => b.clienteId === clienteId)
      .sort((a, b) => new Date(b.dataUpload).getTime() - new Date(a.dataUpload).getTime())[0];
  };

  return (
    <MainLayout>
      <div className="py-6">
        <div className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8">
          <div className="mb-8 flex items-center justify-between">
            <div>
              <h1 className="text-3xl font-bold text-gray-900">Gestão de Clientes</h1>
              <p className="mt-2 text-gray-600">
                Gerencie todos os clientes da sua empresa de contabilidade
              </p>
            </div>
            <Button onClick={() => setShowAddForm(true)}>
              <PlusIcon className="h-5 w-5 mr-2" />
              Novo Cliente
            </Button>
          </div>

          {/* Filtros e Pesquisa */}
          <Card className="mb-8">
            <CardContent className="p-6">
              <div className="flex flex-col sm:flex-row gap-4">
                <div className="flex-1">
                  <Input
                    placeholder="Buscar por nome, CNPJ ou contato..."
                    value={searchTerm}
                    onChange={(e) => setSearchTerm(e.target.value)}
                  />
                </div>
                <div className="flex gap-2">
                  <Button variant="outline">Filtros</Button>
                  <Button variant="outline">Exportar</Button>
                </div>
              </div>
            </CardContent>
          </Card>

          {/* Lista de Clientes */}
          <Card>
            <CardHeader>
              <CardTitle>Clientes ({filteredClientes.length})</CardTitle>
            </CardHeader>
            <CardContent>
              <div className="overflow-x-auto">
                <table className="min-w-full divide-y divide-gray-200">
                  <thead className="bg-gray-50">
                    <tr>
                      <th className="px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase tracking-wider">
                        Cliente
                      </th>
                      <th className="px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase tracking-wider">
                        CNPJ
                      </th>
                      <th className="px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase tracking-wider">
                        Contato
                      </th>
                      <th className="px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase tracking-wider">
                        Último Balancete
                      </th>
                      <th className="px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase tracking-wider">
                        Ações
                      </th>
                    </tr>
                  </thead>
                  <tbody className="bg-white divide-y divide-gray-200">
                    {filteredClientes.map((cliente) => {
                      const ultimoBalancete = getUltimoBalancete(cliente.id);
                      
                      return (
                        <tr key={cliente.id} className="hover:bg-gray-50">
                          <td className="px-6 py-4 whitespace-nowrap">
                            <div>
                              <div className="text-sm font-medium text-gray-900">
                                {cliente.nome}
                              </div>
                              <div className="text-sm text-gray-500">
                                Criado em {formatDate(cliente.createdAt)}
                              </div>
                            </div>
                          </td>
                          <td className="px-6 py-4 whitespace-nowrap text-sm text-gray-900">
                            {formatCNPJ(cliente.cnpj)}
                          </td>
                          <td className="px-6 py-4 whitespace-nowrap">
                            <div>
                              <div className="text-sm text-gray-900">{cliente.contato}</div>
                              <div className="text-sm text-gray-500">{cliente.email}</div>
                              <div className="text-sm text-gray-500">{cliente.telefone}</div>
                            </div>
                          </td>
                          <td className="px-6 py-4 whitespace-nowrap">
                            {ultimoBalancete ? (
                              <div>
                                <div className="text-sm text-gray-900">
                                  {formatMonth(ultimoBalancete.mes, ultimoBalancete.ano)}
                                </div>
                                <div className="text-sm text-gray-500">
                                  {formatDate(ultimoBalancete.dataUpload)}
                                </div>
                              </div>
                            ) : (
                              <span className="inline-flex px-2 py-1 text-xs font-semibold rounded-full bg-red-100 text-red-800">
                                Nenhum balancete
                              </span>
                            )}
                          </td>
                          <td className="px-6 py-4 whitespace-nowrap text-sm font-medium">
                            <div className="flex space-x-2">
                              <Link href={`/clientes/${cliente.id}/dashboard`}>
                                <Button size="sm" variant="outline" title="Ver Dashboard">
                                  <EyeIcon className="h-4 w-4" />
                                </Button>
                              </Link>
                              <Link href={`/clientes/${cliente.id}/balancetes`}>
                                <Button size="sm" variant="outline" title="Gerenciar Balancetes">
                                  <DocumentArrowUpIcon className="h-4 w-4" />
                                </Button>
                              </Link>
                              <Button size="sm" variant="outline" title="Editar Cliente">
                                <PencilIcon className="h-4 w-4" />
                              </Button>
                              <Button size="sm" variant="danger" title="Excluir Cliente">
                                <TrashIcon className="h-4 w-4" />
                              </Button>
                            </div>
                          </td>
                        </tr>
                      );
                    })}
                  </tbody>
                </table>
              </div>

              {filteredClientes.length === 0 && (
                <div className="text-center py-12">
                  <div className="text-gray-500">
                    {searchTerm ? 'Nenhum cliente encontrado com os critérios de busca.' : 'Nenhum cliente cadastrado.'}
                  </div>
                  <Button className="mt-4" onClick={() => setShowAddForm(true)}>
                    <PlusIcon className="h-5 w-5 mr-2" />
                    Adicionar Primeiro Cliente
                  </Button>
                </div>
              )}
            </CardContent>
          </Card>

          {/* Modal de Adicionar Cliente (simplificado) */}
          {showAddForm && (
            <div className="fixed inset-0 bg-gray-600 bg-opacity-50 flex items-center justify-center p-4 z-50">
              <Card className="w-full max-w-md">
                <CardHeader>
                  <CardTitle>Novo Cliente</CardTitle>
                </CardHeader>
                <CardContent>
                  <form className="space-y-4">
                    <Input label="Nome da Empresa" placeholder="Ex: Empresa LTDA" />
                    <Input label="CNPJ" placeholder="00.000.000/0000-00" />
                    <Input label="Nome do Contato" placeholder="João Silva" />
                    <Input label="E-mail" type="email" placeholder="contato@empresa.com" />
                    <Input label="Telefone" placeholder="(11) 99999-9999" />
                    
                    <div className="flex space-x-3 pt-4">
                      <Button type="submit" className="flex-1">
                        Salvar Cliente
                      </Button>
                      <Button 
                        type="button" 
                        variant="outline" 
                        onClick={() => setShowAddForm(false)}
                        className="flex-1"
                      >
                        Cancelar
                      </Button>
                    </div>
                  </form>
                </CardContent>
              </Card>
            </div>
          )}
        </div>
      </div>
    </MainLayout>
  );
}
