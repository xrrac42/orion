'use client';

import { useState } from 'react';
import { useParams } from 'next/navigation';
import MainLayout from '@/components/layout/MainLayout';
import { Card, CardContent, CardHeader, CardTitle } from '@/components/ui/Card';
import { Button } from '@/components/ui/Button';
import { mockClientes, mockBalancetes } from '@/lib/mockData';
import { formatDate, formatMonth, formatFileSize } from '@/lib/utils';
import Link from 'next/link';
import { 
  DocumentArrowUpIcon, 
  EyeIcon,
  ArrowDownTrayIcon,
  TrashIcon,
  ArrowLeftIcon,
  CalendarIcon
} from '@heroicons/react/24/outline';

export default function ClienteBalancetesPage() {
  const params = useParams();
  const clienteId = params.id as string;
  const [showUploadForm, setShowUploadForm] = useState(false);
  const [selectedFile, setSelectedFile] = useState<File | null>(null);
  const [selectedMes, setSelectedMes] = useState('');
  const [selectedAno, setSelectedAno] = useState('');

  const cliente = mockClientes.find(c => c.id === clienteId);
  const balancetes = mockBalancetes
    .filter(b => b.clienteId === clienteId)
    .sort((a, b) => {
      if (a.ano !== b.ano) return b.ano - a.ano;
      return b.mes - a.mes;
    });

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

  const handleFileChange = (e: React.ChangeEvent<HTMLInputElement>) => {
    const file = e.target.files?.[0];
    if (file && file.type === 'application/pdf') {
      setSelectedFile(file);
    } else {
      alert('Por favor, selecione um arquivo PDF.');
    }
  };

  const handleUpload = (e: React.FormEvent) => {
    e.preventDefault();
    if (!selectedFile || !selectedMes || !selectedAno) {
      alert('Por favor, preencha todos os campos.');
      return;
    }
    
    // Aqui seria a lógica de upload
    alert('Upload realizado com sucesso!');
    setShowUploadForm(false);
    setSelectedFile(null);
    setSelectedMes('');
    setSelectedAno('');
  };

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
                      ? formatDate(balancetes[0].dataUpload)
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
                            {formatDate(balancete.dataUpload)}
                          </td>
                          <td className="px-6 py-4 whitespace-nowrap">
                            <div>
                              <div className="text-sm text-gray-900">{balancete.arquivo}</div>
                              <div className="text-sm text-gray-500">
                                {formatFileSize(balancete.tamanhoArquivo)}
                              </div>
                            </div>
                          </td>
                          <td className="px-6 py-4 whitespace-nowrap">
                            <span className={`inline-flex px-2 py-1 text-xs font-semibold rounded-full ${
                              balancete.processado 
                                ? 'bg-green-100 text-green-800' 
                                : 'bg-yellow-100 text-yellow-800'
                            }`}>
                              {balancete.processado ? 'Processado' : 'Processando'}
                            </span>
                          </td>
                          <td className="px-6 py-4 whitespace-nowrap text-sm font-medium">
                            <div className="flex space-x-2">
                              {balancete.processado && (
                                <Link href={`/clientes/${clienteId}/dashboard?balancete=${balancete.id}`}>
                                  <Button size="sm" variant="outline" title="Ver Dashboard">
                                    <EyeIcon className="h-4 w-4" />
                                  </Button>
                                </Link>
                              )}
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
                    <Button onClick={() => setShowUploadForm(true)}>
                      <DocumentArrowUpIcon className="h-5 w-5 mr-2" />
                      Fazer Upload
                    </Button>
                  </div>
                </div>
              )}
            </CardContent>
          </Card>

          {/* Modal de Upload */}
          {showUploadForm && (
            <div className="fixed inset-0 bg-gray-600 bg-opacity-50 flex items-center justify-center p-4 z-50">
              <Card className="w-full max-w-md">
                <CardHeader>
                  <CardTitle>Upload de Balancete</CardTitle>
                </CardHeader>
                <CardContent>
                  <form onSubmit={handleUpload} className="space-y-4">
                    <div className="grid grid-cols-2 gap-4">
                      <div>
                        <label className="block text-sm font-medium text-gray-700 mb-1">
                          Mês
                        </label>
                        <select
                          value={selectedMes}
                          onChange={(e) => setSelectedMes(e.target.value)}
                          className="w-full rounded-md border border-gray-300 px-3 py-2 text-sm focus:border-blue-500 focus:ring-blue-500"
                          required
                        >
                          <option value="">Selecione</option>
                          {meses.map((mes) => (
                            <option key={mes.value} value={mes.value}>
                              {mes.label}
                            </option>
                          ))}
                        </select>
                      </div>
                      <div>
                        <label className="block text-sm font-medium text-gray-700 mb-1">
                          Ano
                        </label>
                        <select
                          value={selectedAno}
                          onChange={(e) => setSelectedAno(e.target.value)}
                          className="w-full rounded-md border border-gray-300 px-3 py-2 text-sm focus:border-blue-500 focus:ring-blue-500"
                          required
                        >
                          <option value="">Selecione</option>
                          {anos.map((ano) => (
                            <option key={ano.value} value={ano.value}>
                              {ano.label}
                            </option>
                          ))}
                        </select>
                      </div>
                    </div>

                    <div>
                      <label className="block text-sm font-medium text-gray-700 mb-1">
                        Arquivo PDF do Balancete
                      </label>
                      <input
                        type="file"
                        accept=".pdf"
                        onChange={handleFileChange}
                        className="w-full text-sm text-gray-500 file:mr-4 file:py-2 file:px-4 file:rounded-md file:border-0 file:text-sm file:font-semibold file:bg-blue-50 file:text-blue-700 hover:file:bg-blue-100"
                        required
                      />
                      <p className="mt-1 text-xs text-gray-500">
                        Apenas arquivos PDF são aceitos
                      </p>
                    </div>

                    {selectedFile && (
                      <div className="p-3 bg-gray-50 rounded-md">
                        <p className="text-sm text-gray-700">
                          <strong>Arquivo selecionado:</strong> {selectedFile.name}
                        </p>
                        <p className="text-xs text-gray-500">
                          Tamanho: {formatFileSize(selectedFile.size)}
                        </p>
                      </div>
                    )}
                    
                    <div className="flex space-x-3 pt-4">
                      <Button type="submit" className="flex-1">
                        Fazer Upload
                      </Button>
                      <Button 
                        type="button" 
                        variant="outline" 
                        onClick={() => setShowUploadForm(false)}
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
