"use client";

import { useState, useEffect } from 'react';
import { useParams } from 'next/navigation';
import MainLayout from '@/components/layout/MainLayout';
import { Card, CardContent, CardHeader, CardTitle } from '@/components/ui/Card';
import { Button } from '@/components/ui/Button';
import { formatDate, formatMonth, formatFileSize } from '@/lib/utils';
import UploadBalancete from '@/components/balancetes/UploadBalancete';
import Link from 'next/link';
import { 
  DocumentArrowUpIcon, 
  EyeIcon,
  ArrowDownTrayIcon,
  TrashIcon,
  ArrowLeftIcon,
  CalendarIcon
} from '@heroicons/react/24/outline';

interface Cliente {
  id: string;
  nome: string;
  cnpj: string;
  contato: string;
  email: string;
  telefone: string;
  created_at: string;
  updated_at: string;
}

interface Balancete {
  id: string;
  client_id: string;
  mes: number;
  ano: number;
  arquivo_nome: string;
  arquivo_tamanho: number;
  data_upload: string;
}

export default function ClienteBalancetesPage() {
  const params = useParams();
  const clienteId = params.id as string;
  const [cliente, setCliente] = useState<Cliente | null>(null);
  const [balancetes, setBalancetes] = useState<Balancete[]>([]);
  const [loading, setLoading] = useState(true);
  const [showUploadForm, setShowUploadForm] = useState(false);

  useEffect(() => {
    const fetchData = async () => {
      try {
        setLoading(true);
        
  // Buscar dados do cliente
  const clienteResponse = await fetch(`http://localhost:8000/api/clients/${clienteId}`);
        if (clienteResponse.ok) {
          const clienteData = await clienteResponse.json();
          setCliente(clienteData);
        }

  // Buscar balancetes do cliente
  const balancetesResponse = await fetch(`http://localhost:8000/api/balancetes/cliente/${clienteId}`);
        if (balancetesResponse.ok) {
          const balancetesData = await balancetesResponse.json();
          setBalancetes(balancetesData.sort((a: Balancete, b: Balancete) => {
            if (a.ano !== b.ano) return b.ano - a.ano;
            return b.mes - a.mes;
          }));
        }
      } catch (error) {
        console.error('Erro ao carregar dados:', error);
      } finally {
        setLoading(false);
      }
    };

    fetchData();
  }, [clienteId]);

  if (loading) {
    return (
      <MainLayout>
        <div className="py-6">
          <div className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8">
            <div className="text-center">
              <h1 className="text-2xl font-bold text-gray-900">Carregando...</h1>
            </div>
          </div>
        </div>
      </MainLayout>
    );
  }

  if (!cliente) {
    return (
      <MainLayout>
        <div className="py-6">
          <div className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8">
            <div className="text-center">
              <h1 className="text-2xl font-bold text-gray-900">Cliente não encontrado</h1>
              <Link href="/clientes">
                <Button className="mt-4">Voltar para Clientes</Button>
              </Link>
            </div>
          </div>
        </div>
      </MainLayout>
    );
  }

  // ...existing code...

  const meses = [
    { value: '1', label: 'Janeiro' },
    { value: '2', label: 'Fevereiro' },
    { value: '3', label: 'Março' },
    { value: '4', label: 'Abril' },
    { value: '5', label: 'Maio' },
    { value: '6', label: 'Junho' },
    { value: '7', label: 'Julho' },
    { value: '8', label: 'Agosto' },
    { value: '9', label: 'Setembro' },
    { value: '10', label: 'Outubro' },
    { value: '11', label: 'Novembro' },
    { value: '12', label: 'Dezembro' }
  ];

  const anos = Array.from({ length: 5 }, (_, i) => {
    const ano = new Date().getFullYear() - i;
    return { value: ano.toString(), label: ano.toString() };
  });

  return (
    <MainLayout>
      <div className="py-6">
        <div className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8">
          {/* Header */}
          <div className="mb-8 flex items-center justify-between">
            <div className="flex items-center">
              <Link href="/clientes">
                <Button variant="ghost" size="sm" className="mr-4">
                  <ArrowLeftIcon className="h-4 w-4 mr-2" />
                  Voltar
                </Button>
              </Link>
              <div>
                <h1 className="text-3xl font-bold text-gray-900">{cliente.nome}</h1>
                <p className="mt-2 text-gray-600">
                  Gestão de Balancetes • CNPJ: {cliente.cnpj}
                </p>
              </div>
            </div>
            <Button onClick={() => setShowUploadForm(true)}>
              <DocumentArrowUpIcon className="h-5 w-5 mr-2" />
              Novo Upload
            </Button>
          {/* Modal de Upload */}
          {showUploadForm && (
            <div className="fixed inset-0 bg-gray-600 bg-opacity-50 flex items-center justify-center p-4 z-50">
              <Card className="w-full max-w-md">
                <CardHeader>
                  <CardTitle>Upload de Balancete</CardTitle>
                </CardHeader>
                <CardContent>
                  <UploadBalancete clientId={clienteId} onUpload={() => setShowUploadForm(false)} />
                  <Button variant="outline" className="mt-4 w-full" onClick={() => setShowUploadForm(false)}>
                    Cancelar
                  </Button>
                </CardContent>
              </Card>
            </div>
          )}
          </div>

          {/* Informações do Cliente */}
          <Card className="mb-8">
            <CardContent className="p-6">
              <div className="grid grid-cols-1 md:grid-cols-3 gap-6">
                <div>
                  <h3 className="text-sm font-medium text-gray-500">Contato Principal</h3>
                  <p className="mt-1 text-sm text-gray-900">{cliente.contato}</p>
                  <p className="text-sm text-gray-500">{cliente.email}</p>
                  <p className="text-sm text-gray-500">{cliente.telefone}</p>
                </div>
                <div>
                  <h3 className="text-sm font-medium text-gray-500">Balancetes Enviados</h3>
                  <p className="mt-1 text-2xl font-bold text-gray-900">{balancetes.length}</p>
                </div>
                <div>
                  <h3 className="text-sm font-medium text-gray-500">Último Upload</h3>
                  <p className="mt-1 text-sm text-gray-900">
                    {balancetes.length > 0 
                      ? formatDate(new Date(balancetes[0].data_upload))
                      : 'Nenhum upload realizado'
                    }
                  </p>
                </div>
              </div>
            </CardContent>
          </Card>

          {/* Lista de Balancetes */}
          <Card>
            <CardHeader>
              <CardTitle>Histórico de Balancetes</CardTitle>
            </CardHeader>
            <CardContent>
              {balancetes.length > 0 ? (
                <div className="overflow-x-auto">
                  <table className="min-w-full divide-y divide-gray-200">
                    <thead className="bg-gray-50">
                      <tr>
                        <th className="px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase tracking-wider">
                          Período
                        </th>
                        <th className="px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase tracking-wider">
                          Data do Upload
                        </th>
                        <th className="px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase tracking-wider">
                          Arquivo
                        </th>
                        <th className="px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase tracking-wider">
                          Status
                        </th>
                        <th className="px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase tracking-wider">
                          Ações
                        </th>
                      </tr>
                    </thead>
                    <tbody className="bg-white divide-y divide-gray-200">
                      {balancetes.map((balancete) => (
                        <tr key={balancete.id} className="hover:bg-gray-50">
                          <td className="px-6 py-4 whitespace-nowrap">
                            <div className="flex items-center">
                              <CalendarIcon className="h-5 w-5 text-gray-400 mr-2" />
                              <div>
                                <div className="text-sm font-medium text-gray-900">
                                  {formatMonth(balancete.mes, balancete.ano)}
                                </div>
                              </div>
                            </div>
                          </td>
                          <td className="px-6 py-4 whitespace-nowrap text-sm text-gray-900">
                            {formatDate(new Date(balancete.data_upload))}
                          </td>
                          <td className="px-6 py-4 whitespace-nowrap">
                            <div>
                              <div className="text-sm text-gray-900">{balancete.arquivo_nome}</div>
                              <div className="text-sm text-gray-500">
                                {formatFileSize(balancete.arquivo_tamanho)}
                              </div>
                            </div>
                          </td>
                          <td className="px-6 py-4 whitespace-nowrap">
                            <span className="inline-flex px-2 py-1 text-xs font-semibold rounded-full bg-green-100 text-green-800">
                              Processado
                            </span>
                          </td>
                          <td className="px-6 py-4 whitespace-nowrap text-sm font-medium">
                            <div className="flex space-x-2">
                              <Link href={`/clientes/${clienteId}/dashboard?balancete=${balancete.id}`}>
                                <Button size="sm" variant="outline" title="Ver Dashboard">
                                  <EyeIcon className="h-4 w-4" />
                                </Button>
                              </Link>
                              <Button size="sm" variant="outline" title="Baixar PDF">
                                <ArrowDownTrayIcon className="h-4 w-4" />
                              </Button>
                              <Button size="sm" variant="danger" title="Excluir">
                                <TrashIcon className="h-4 w-4" />
                              </Button>
                            </div>
                          </td>
                        </tr>
                      ))}
                    </tbody>
                  </table>
                </div>
              ) : (
                <div className="text-center py-12">
                  <DocumentArrowUpIcon className="mx-auto h-12 w-12 text-gray-400" />
                  <h3 className="mt-2 text-sm font-medium text-gray-900">
                    Nenhum balancete enviado
                  </h3>
                  <p className="mt-1 text-sm text-gray-500">
                    Comece fazendo o upload do primeiro balancete deste cliente.
                  </p>
                  <div className="mt-6">
                    {/* Botão de upload removido, upload sempre visível */}
                  </div>
                </div>
              )}
            </CardContent>
          </Card>

          {/* Modal removido, upload sempre visível */}
        </div>
      </div>
    </MainLayout>
  );
}