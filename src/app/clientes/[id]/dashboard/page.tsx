"use client";

import { useState, useEffect } from 'react';
import { useParams, useSearchParams } from 'next/navigation';
import MainLayout from '@/components/layout/MainLayout';
import { Card, CardContent, CardHeader, CardTitle } from '@/components/ui/Card';
import { Button } from '@/components/ui/Button';
import Link from 'next/link';
import { formatCurrency, formatDate, formatMonth } from '@/lib/utils';
import { ArrowLeftIcon, CalendarIcon, ArrowTrendingUpIcon, ArrowTrendingDownIcon, BanknotesIcon } from '@heroicons/react/24/outline';
import FluxoCaixaChart from '@/components/charts/FluxoCaixaChart';
import PieChart from '@/components/charts/PieChart';

export default function ClienteDashboardPage() {
  const params = useParams();
  const searchParams = useSearchParams();
  const clienteId = params.id as string;
  const balanceteId = searchParams.get('balancete');

  const [cliente, setCliente] = useState(null);
  const [balancetes, setBalancetes] = useState<any[]>([]);
  const [selectedBalanceteId, setSelectedBalanceteId] = useState<string | null>(balanceteId);
  const [resumo, setResumo] = useState(null);
  const [fluxoCaixa, setFluxoCaixa] = useState([]);
  const [gastosPorCategoria, setGastosPorCategoria] = useState([]);
  const [formasPagamento, setFormasPagamento] = useState([]);
  const [motivosGasto, setMotivosGasto] = useState([]);
  const [lancamentos, setLancamentos] = useState([]);
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    async function fetchData() {
      setLoading(true);
      try {
        const clienteRes = await fetch(`http://localhost:8000/clients/${clienteId}`);
        const clienteData = await clienteRes.json();
        setCliente(clienteData);

        const balancetesRes = await fetch(`http://localhost:8000/balancetes?client_id=${clienteId}`);
        const balancetesData = await balancetesRes.json();
  setBalancetes(Array.isArray(balancetesData) ? balancetesData : []);

        let balanceteSelecionadoId = balanceteId;
        if (!balanceteSelecionadoId && balancetesData.length > 0) {
          balanceteSelecionadoId = balancetesData[0].id;
        }
        setSelectedBalanceteId(balanceteSelecionadoId);

        if (balanceteSelecionadoId) {
          const resumoRes = await fetch(`http://localhost:8000/financial_entries/summary?balancete_id=${balanceteSelecionadoId}`);
          setResumo(await resumoRes.json());

          const fluxoRes = await fetch(`http://localhost:8000/financial_entries/fluxo_caixa?balancete_id=${balanceteSelecionadoId}`);
          setFluxoCaixa(await fluxoRes.json());

          const gastosRes = await fetch(`http://localhost:8000/financial_entries/gastos_categoria?balancete_id=${balanceteSelecionadoId}`);
          setGastosPorCategoria(await gastosRes.json());

          const formasRes = await fetch(`http://localhost:8000/financial_entries/formas_pagamento?balancete_id=${balanceteSelecionadoId}`);
          setFormasPagamento(await formasRes.json());

          const motivosRes = await fetch(`http://localhost:8000/financial_entries/motivos_gasto?balancete_id=${balanceteSelecionadoId}`);
          setMotivosGasto(await motivosRes.json());

          const lancamentosRes = await fetch(`http://localhost:8000/financial_entries?balancete_id=${balanceteSelecionadoId}`);
          setLancamentos(await lancamentosRes.json());
        }
      } catch (e) {
        // erro
      } finally {
        setLoading(false);
      }
    }
    if (clienteId) fetchData();
  }, [clienteId, balanceteId]);

  useEffect(() => {
    async function fetchBalanceteData() {
      if (!selectedBalanceteId) return;
      setLoading(true);
      try {
        const resumoRes = await fetch(`http://localhost:8000/financial_entries/summary?balancete_id=${selectedBalanceteId}`);
        setResumo(await resumoRes.json());
        const fluxoRes = await fetch(`http://localhost:8000/financial_entries/fluxo_caixa?balancete_id=${selectedBalanceteId}`);
        setFluxoCaixa(await fluxoRes.json());
        const gastosRes = await fetch(`http://localhost:8000/financial_entries/gastos_categoria?balancete_id=${selectedBalanceteId}`);
        setGastosPorCategoria(await gastosRes.json());
        const formasRes = await fetch(`http://localhost:8000/financial_entries/formas_pagamento?balancete_id=${selectedBalanceteId}`);
        setFormasPagamento(await formasRes.json());
        const motivosRes = await fetch(`http://localhost:8000/financial_entries/motivos_gasto?balancete_id=${selectedBalanceteId}`);
        setMotivosGasto(await motivosRes.json());
        const lancamentosRes = await fetch(`http://localhost:8000/financial_entries?balancete_id=${selectedBalanceteId}`);
        setLancamentos(await lancamentosRes.json());
      } catch (e) {
        // erro
      } finally {
        setLoading(false);
      }
    }
    if (selectedBalanceteId) fetchBalanceteData();
  }, [selectedBalanceteId]);

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

  if (!balancetes || balancetes.length === 0) {
    return (
      <MainLayout>
        <div className="py-6">
          <div className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8">
            <div className="mb-8 flex items-center">
              <Link href="/clientes">
                <Button variant="ghost" size="sm" className="mr-4">
                  <ArrowLeftIcon className="h-4 w-4 mr-2" />
                  Voltar
                </Button>
              </Link>
              <div>
                <h1 className="text-3xl font-bold text-gray-900">{cliente.nome}</h1>
                <p className="mt-2 text-gray-600">Dashboard Financeiro</p>
              </div>
            </div>
            <Card>
              <CardContent className="text-center py-12">
                <CalendarIcon className="mx-auto h-12 w-12 text-gray-400" />
                <h3 className="mt-2 text-sm font-medium text-gray-900">
                  Nenhum balancete processado
                </h3>
                <p className="mt-1 text-sm text-gray-500">
                  É necessário fazer upload e processar um balancete para visualizar o dashboard.
                </p>
                <div className="mt-6">
                  <Link href={`/clientes/${clienteId}/balancetes`}>
                    <Button>Gerenciar Balancetes</Button>
                  </Link>
                </div>
              </CardContent>
            </Card>
          </div>
        </div>
      </MainLayout>
    );
  }

  const selectedBalancete = balancetes.find((b: any) => b.id === selectedBalanceteId) || balancetes[0];

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
                  Dashboard Financeiro • {selectedBalancete ? formatMonth(selectedBalancete.mes, selectedBalancete.ano) : ''}
                </p>
              </div>
            </div>
            {/* Seletor de Balancete */}
            {balancetes.length > 1 && (
              <div className="flex items-center space-x-2">
                <CalendarIcon className="h-5 w-5 text-gray-400" />
                <select
                  value={selectedBalanceteId || ''}
                  onChange={(e) => setSelectedBalanceteId(e.target.value)}
                  className="rounded-md border border-gray-300 px-3 py-2 text-sm focus:border-blue-500 focus:ring-blue-500"
                >
                  {balancetes.map((balancete: any) => (
                    <option key={balancete.id} value={balancete.id}>
                      {formatMonth(balancete.mes, balancete.ano)}
                    </option>
                  ))}
                </select>
              </div>
            )}
          </div>

          {/* Resumo Financeiro */}
          {resumo && (
            <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-4 gap-6 mb-8">
              <Card>
                <CardContent className="p-6">
                  <div className="flex items-center">
                    <ArrowTrendingDownIcon className="h-8 w-8 text-red-600" />
                    <div className="ml-4">
                      <p className="text-sm font-medium text-gray-500">Valor Gasto Total</p>
                      <p className="text-2xl font-bold text-gray-900">
                        {formatCurrency(resumo.totalGasto)}
                      </p>
                    </div>
                  </div>
                </CardContent>
              </Card>
              <Card>
                <CardContent className="p-6">
                  <div className="flex items-center">
                    <ArrowTrendingUpIcon className="h-8 w-8 text-green-600" />
                    <div className="ml-4">
                      <p className="text-sm font-medium text-gray-500">Receita Total</p>
                      <p className="text-2xl font-bold text-gray-900">
                        {formatCurrency(resumo.totalReceita)}
                      </p>
                    </div>
                  </div>
                </CardContent>
              </Card>
              <Card>
                <CardContent className="p-6">
                  <div className="flex items-center">
                    <BanknotesIcon className="h-8 w-8 text-blue-600" />
                    <div className="ml-4">
                      <p className="text-sm font-medium text-gray-500">Lucro</p>
                      <p className="text-2xl font-bold text-green-600">
                        {formatCurrency(resumo.lucro)}
                      </p>
                    </div>
                  </div>
                </CardContent>
              </Card>
              <Card>
                <CardContent className="p-6">
                  <div className="flex items-center">
                    <div className="w-8 h-8 bg-purple-600 rounded-lg flex items-center justify-center">
                      <span className="text-white font-bold text-sm">%</span>
                    </div>
                    <div className="ml-4">
                      <p className="text-sm font-medium text-gray-500">Margem de Lucro</p>
                      <p className="text-2xl font-bold text-gray-900">
                        {resumo.totalReceita > 0 ? ((resumo.lucro / resumo.totalReceita) * 100).toFixed(1) : '0.0'}%
                      </p>
                    </div>
                  </div>
                </CardContent>
              </Card>
            </div>
          )}

          {/* Gráficos */}
          <div className="grid grid-cols-1 lg:grid-cols-2 gap-8 mb-8">
            <Card>
              <CardHeader>
                <CardTitle>Fluxo de Caixa</CardTitle>
              </CardHeader>
              <CardContent>
                <FluxoCaixaChart data={fluxoCaixa} />
              </CardContent>
            </Card>
            <Card>
              <CardHeader>
                <CardTitle>Distribuição de Gastos por Categoria</CardTitle>
              </CardHeader>
              <CardContent>
                <PieChart data={gastosPorCategoria} title="Gastos por Categoria" />
              </CardContent>
            </Card>
          </div>
          <div className="grid grid-cols-1 lg:grid-cols-2 gap-8 mb-8">
            <Card>
              <CardHeader>
                <CardTitle>Formas de Pagamento</CardTitle>
              </CardHeader>
              <CardContent>
                <PieChart data={formasPagamento.map((fp: any) => ({ categoria: fp.tipo, valor: fp.valor, percentual: fp.percentual, cor: fp.cor }))} title="Formas de Pagamento" />
              </CardContent>
            </Card>
            <Card>
              <CardHeader>
                <CardTitle>Motivo do Gasto</CardTitle>
              </CardHeader>
              <CardContent>
                <div className="space-y-4">
                  {motivosGasto.map((motivo: any, index: number) => (
                    <div key={index} className="flex items-center justify-between">
                      <div className="flex-1">
                        <p className="text-sm font-medium text-gray-900">{motivo.motivo}</p>
                        <div className="w-full bg-gray-200 rounded-full h-2 mt-1">
                          <div className="bg-blue-600 h-2 rounded-full" style={{ width: `${motivo.percentual}%` }} />
                        </div>
                      </div>
                      <div className="ml-4 text-right">
                        <p className="text-sm font-medium text-gray-900">{formatCurrency(motivo.valor)}</p>
                        <p className="text-xs text-gray-500">{motivo.percentual}%</p>
                      </div>
                    </div>
                  ))}
                </div>
              </CardContent>
            </Card>
          </div>
          {/* Tabelas de Detalhes */}
          <div className="grid grid-cols-1 gap-8">
            <Card>
              <CardHeader>
                <CardTitle>Lançamentos Contábeis</CardTitle>
              </CardHeader>
              <CardContent>
                <div className="overflow-x-auto">
                  <table className="min-w-full divide-y divide-gray-200">
                    <thead className="bg-gray-50">
                      <tr>
                        <th className="px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase tracking-wider">Descrição</th>
                        <th className="px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase tracking-wider">Saldo Anterior</th>
                        <th className="px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase tracking-wider">Débito</th>
                        <th className="px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase tracking-wider">Crédito</th>
                        <th className="px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase tracking-wider">Saldo Atual</th>
                        <th className="px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase tracking-wider">Categoria</th>
                      </tr>
                    </thead>
                    <tbody className="bg-white divide-y divide-gray-200">
                      {lancamentos.map((lancamento: any) => (
                        <tr key={lancamento.id} className="hover:bg-gray-50">
                          <td className="px-6 py-4 whitespace-nowrap">
                            <div>
                              <div className="text-sm font-medium text-gray-900">{lancamento.descricao}</div>
                              <div className="text-sm text-gray-500">{formatDate(new Date(lancamento.data))}</div>
                            </div>
                          </td>
                          <td className="px-6 py-4 whitespace-nowrap text-sm text-gray-900">{formatCurrency(lancamento.saldoAnterior)}</td>
                          <td className="px-6 py-4 whitespace-nowrap text-sm text-red-600">{lancamento.debito > 0 ? formatCurrency(lancamento.debito) : '-'}</td>
                          <td className="px-6 py-4 whitespace-nowrap text-sm text-green-600">{lancamento.credito > 0 ? formatCurrency(lancamento.credito) : '-'}</td>
                          <td className="px-6 py-4 whitespace-nowrap text-sm font-medium text-gray-900">{formatCurrency(lancamento.saldoAtual)}</td>
                          <td className="px-6 py-4 whitespace-nowrap">
                            <span className={`inline-flex px-2 py-1 text-xs font-semibold rounded-full ${
                              lancamento.categoria === 'Receita' ? 'bg-green-100 text-green-800' :
                              lancamento.categoria === 'Despesa' ? 'bg-red-100 text-red-800' :
                              lancamento.categoria === 'Ativo' ? 'bg-blue-100 text-blue-800' :
                              'bg-gray-100 text-gray-800'
                            }`}>
                              {lancamento.categoria}
                            </span>
                          </td>
                        </tr>
                      ))}
                    </tbody>
                  </table>
                </div>
              </CardContent>
            </Card>
            {/* Informações do Balancete */}
            {resumo && (
              <Card>
                <CardHeader>
                  <CardTitle>Resumo do Balancete Analítico</CardTitle>
                </CardHeader>
                <CardContent>
                  <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-4 gap-6">
                    <div className="text-center p-4 bg-blue-50 rounded-lg">
                      <h3 className="text-lg font-semibold text-blue-900">Ativo Total</h3>
                      <p className="text-2xl font-bold text-blue-600">{formatCurrency(resumo?.totalAtivo)}</p>
                    </div>
                    <div className="text-center p-4 bg-red-50 rounded-lg">
                      <h3 className="text-lg font-semibold text-red-900">Passivo Total</h3>
                      <p className="text-2xl font-bold text-red-600">{formatCurrency(resumo?.totalPassivo)}</p>
                    </div>
                    <div className="text-center p-4 bg-green-50 rounded-lg">
                      <h3 className="text-lg font-semibold text-green-900">Receita Total</h3>
                      <p className="text-2xl font-bold text-green-600">{formatCurrency(resumo.totalReceita)}</p>
                    </div>
                    <div className="text-center p-4 bg-purple-50 rounded-lg">
                      <h3 className="text-lg font-semibold text-purple-900">Despesa Total</h3>
                      <p className="text-2xl font-bold text-purple-600">{formatCurrency(resumo?.totalDespesa)}</p>
                    </div>
                  </div>
                  <div className="mt-6 text-center p-6 bg-gradient-to-r from-green-50 to-blue-50 rounded-lg">
                    <h3 className="text-xl font-bold text-gray-900">Resultado do Período</h3>
                    <p className="text-3xl font-bold text-green-600 mt-2">{formatCurrency(resumo.lucro)}</p>
                    <p className="text-sm text-gray-600 mt-1">{selectedBalancete ? formatMonth(selectedBalancete.mes, selectedBalancete.ano) : ''}</p>
                  </div>
                </CardContent>
              </Card>
            )}
          </div>
        </div>
      </div>
    </MainLayout>
  );
}