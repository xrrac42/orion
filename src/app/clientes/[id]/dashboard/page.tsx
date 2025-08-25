"use client";

import { useState, useEffect } from 'react';
import { useParams } from 'next/navigation';
import Link from 'next/link';

// Importe seus componentes de UI e ícones
import MainLayout from '@/components/layout/MainLayout';
import { Card, CardContent, CardHeader, CardTitle } from '@/components/ui/Card';
import { Button } from '@/components/ui/Button';
import { Input } from '@/components/ui/Input';
import { ArrowLeftIcon, ArrowTrendingUpIcon, ArrowTrendingDownIcon, BanknotesIcon, MagnifyingGlassIcon, CalendarIcon } from '@heroicons/react/24/outline';

import { formatCurrency } from '@/lib/utils';

// --- ARQUITETURA DE API CORRIGIDA E FINAL ---
const API_BASE_URL = "http://localhost:8000";

// Funções de serviço alinhadas com as rotas do seu main.py
async function getClientById(id: string) {
  const res = await fetch(`${API_BASE_URL}/api/clients/${id}`);
  if (!res.ok) throw new Error(`Falha ao buscar dados do cliente (status: ${res.status})`);
  return res.json();
}

async function getBalancetesForClient(clientId: string) {
  const res = await fetch(`${API_BASE_URL}/api/balancetes/cliente/${clientId}`);
  if (!res.ok) throw new Error(`Falha ao buscar lista de balancetes (status: ${res.status})`);
  return res.json();
}

async function getDashboardDataQuery(analysisId?: string, balanceteId?: string, month?: number | null, year?: number | null) {
  const params = new URLSearchParams();
  if (analysisId) params.set('analysis_id', analysisId);
  if (balanceteId) params.set('balancete_id', balanceteId);
  if (month) params.set('month', String(month));
  if (year) params.set('year', String(year));
  const url = `${API_BASE_URL}/api/dashboard?${params.toString()}`;
  console.debug('[dashboard] GET', url);
  const res = await fetch(url);
  if (!res.ok) throw new Error(`Falha ao buscar dados do dashboard (status: ${res.status})`);
  return res.json();
}

// --- CORREÇÃO APLICADA AQUI ---
// A função agora aceita clientId e o inclui na URL da requisição.
async function getFinancialEntries(analysisId: string, clientId: string) {
  const res = await fetch(`${API_BASE_URL}/api/financial-entries/?analysis_id=${analysisId}&client_id=${clientId}`);
  if (!res.ok) throw new Error(`Falha ao buscar detalhes das contas (status: ${res.status})`);
  return res.json();
}

// --- Interfaces de Tipagem ---
interface Cliente {
  id: string;
  nome: string;
}

interface Balancete {
  id: string;
  ano: number;
  mes: number;
  status: string;
  analysis_id?: number;
}

interface KPIData {
  receita_total: number;
  despesa_total: number;
  resultado_periodo: number;
}

interface ChartData {
  categoria: string;
  valor: number;
}

interface ContaDetalhe {
  conta: string;
  valor: number;
  subgrupo: string;
}

// --- Componente Principal ---
export default function DashboardFinanceiro() {
  const params = useParams();
  const clienteId = params.id as string;
  
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [cliente, setCliente] = useState<Cliente | null>(null);
  const [balancetes, setBalancetes] = useState<Balancete[]>([]);
  const [selectedBalanceteId, setSelectedBalanceteId] = useState<string>('');
  
  const [kpiData, setKpiData] = useState<KPIData | null>(null);
  const [receitasComposicao, setReceitasComposicao] = useState<ChartData[]>([]);
  const [despesasPrincipais, setDespesasPrincipais] = useState<ChartData[]>([]);
  
  const [contasDetalhes, setContasDetalhes] = useState<ContaDetalhe[]>([]);
  const [contasFiltered, setContasFiltered] = useState<ContaDetalhe[]>([]);
  const [filtroSubgrupo, setFiltroSubgrupo] = useState<string>('');
  const [buscaConta, setBuscaConta] = useState<string>('');

  const formatMonth = (mes: number, ano: number) => {
    const meses = ['Janeiro', 'Fevereiro', 'Março', 'Abril', 'Maio', 'Junho', 'Julho', 'Agosto', 'Setembro', 'Outubro', 'Novembro', 'Dezembro'];
    return `${meses[mes - 1]} de ${ano}`;
  };

  // 1. Busca os dados iniciais
  useEffect(() => {
    async function fetchInitialData() {
      if (!clienteId) return;
      try {
  console.debug('[dashboard] initial fetch: setLoading(true)');
  setLoading(true);
        setError(null);
        const [clienteData, balancetesData] = await Promise.all([
          getClientById(clienteId),
          getBalancetesForClient(clienteId)
        ]);

        setCliente(clienteData);
        balancetesData.sort((a: Balancete, b: Balancete) => (b.ano * 100 + b.mes) - (a.ano * 100 + a.mes));
        setBalancetes(balancetesData);

        // Select the first balancete that already has an analysis_id.
        const firstWithAnalysis = balancetesData.find((b: Balancete) => b.analysis_id !== undefined && b.analysis_id !== null);
        if (firstWithAnalysis) {
          setSelectedBalanceteId(String(firstWithAnalysis.analysis_id));
        } else {
          setSelectedBalanceteId('');
        }
      } catch (error) {
        console.error('Erro ao carregar dados iniciais:', error);
        setError(error instanceof Error ? error.message : 'Erro desconhecido');
      } finally {
        console.debug('[dashboard] initial fetch: setLoading(false)');
        setLoading(false);
      }
    }
    fetchInitialData();
  }, [clienteId]);

  // 2. Busca os dados do dashboard quando a análise/seleção/filtros mudam
  const [activeAnalysisId, setActiveAnalysisId] = useState<string>('');
  const [filterMonth, setFilterMonth] = useState<number | null>(null);
  const [filterYear, setFilterYear] = useState<number | null>(null);

  // Auto-activate the selected balancete so the dashboard loads immediately
  useEffect(() => {
    if (selectedBalanceteId) {
      console.debug('[dashboard] auto-activating analysis id from selectedBalanceteId', selectedBalanceteId);
      setActiveAnalysisId(selectedBalanceteId);
    }
  }, [selectedBalanceteId]);

  useEffect(() => {
    async function fetchDashboardDetails() {
      if ((!activeAnalysisId && !selectedBalanceteId) || !clienteId) return;
      try {
        console.debug('[dashboard] fetchDetails: setLoading(true)');
        setLoading(true);
        setError(null);

        const analysisParam = activeAnalysisId || undefined;
        const balanceteParam = activeAnalysisId ? undefined : (selectedBalanceteId || undefined);

        const dashboardData = await getDashboardDataQuery(analysisParam, balanceteParam, filterMonth, filterYear);

        if (dashboardData) {
          setKpiData(dashboardData.kpis);
          setReceitasComposicao(dashboardData.grafico_receitas || []);
          setDespesasPrincipais(dashboardData.grafico_despesas || []);

          const detalhes = (dashboardData.entries || [])
            .filter((e: any) => e.movement_type === 'Despesa')
            .map((entry: any) => ({
              conta: entry.specific_account,
              valor: entry.period_value,
              subgrupo: entry.subgroup_1 || 'N/A'
            }));
          setContasDetalhes(detalhes);
        }
      } catch (error) {
        console.error('Erro ao carregar dados do balancete:', error);
        setError(error instanceof Error ? error.message : 'Erro desconhecido');
      } finally {
        console.debug('[dashboard] fetchDetails: setLoading(false)');
        setLoading(false);
      }
    }
    fetchDashboardDetails();
  }, [activeAnalysisId, selectedBalanceteId, filterMonth, filterYear, clienteId]);

  // 3. Filtra a tabela de detalhes
  useEffect(() => {
    let filtered = contasDetalhes;
    if (filtroSubgrupo) {
      filtered = filtered.filter(conta => conta.subgrupo === filtroSubgrupo);
    }
    if (buscaConta) {
      filtered = filtered.filter(conta => 
        conta.conta.toLowerCase().includes(buscaConta.toLowerCase())
      );
    }
    setContasFiltered(filtered);
  }, [filtroSubgrupo, buscaConta, contasDetalhes]);

  // --- Lógica de Renderização ---
  // selectedBalanceteId may contain an analysis_id (stringified) or a balancete.id
  const selectedBalancete = balancetes.find(b => String(b.id) === selectedBalanceteId || (b.analysis_id && String(b.analysis_id) === selectedBalanceteId));

  if (loading) {
    return <MainLayout><div className="p-8 text-center">Carregando...</div></MainLayout>;
  }
  
  if (error) {
    return <MainLayout><div className="p-8 text-center text-red-500">Erro: {error}</div></MainLayout>;
  }

  if (!cliente || balancetes.length === 0) {
    return (
        <MainLayout>
            <div className="p-8 text-center">
                <h1 className="text-2xl font-bold mb-4">Cliente: {cliente?.nome || '...'}</h1>
                <p>Nenhum balancete encontrado para este cliente.</p>
                <Link href={`/clientes/${clienteId}/balancetes`}>
                    <Button className="mt-4">Gerenciar Balancetes</Button>
                </Link>
            </div>
        </MainLayout>
    );
  }

  return (
    <MainLayout>
      <h1>teste</h1>
      <div className="py-6">
        <div className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8">
          
          <div className="mb-8 flex items-center justify-between">
            <div>
              <h1 className="text-3xl font-bold text-gray-900">
                Dashboard: {cliente.nome}
              </h1>
              {selectedBalancete && (
                <p className="mt-2 text-gray-600">
                  Período: {formatMonth(selectedBalancete.mes, selectedBalancete.ano)}
                </p>
              )}
            </div>
              {balancetes.some(b => b.analysis_id) && (
              <div className="flex items-center gap-2">
                <select
                  value={selectedBalanceteId}
                  onChange={(e) => setSelectedBalanceteId(e.target.value)}
                  className="rounded-md border border-gray-300 px-3 py-2 text-sm"
                >
                  <option value="">-- Selecione --</option>
                  {balancetes.filter(b => b.analysis_id).map((b) => (
                    <option key={String(b.analysis_id)} value={String(b.analysis_id)}>
                      {formatMonth(b.mes, b.ano)}
                    </option>
                  ))}
                </select>

                <input
                  type="number"
                  placeholder="Mês"
                  min={1}
                  max={12}
                  value={filterMonth ?? ''}
                  onChange={(e) => setFilterMonth(e.target.value ? Number(e.target.value) : null)}
                  className="rounded-md border border-gray-300 px-2 py-1 w-20"
                />

                <input
                  type="number"
                  placeholder="Ano"
                  min={1900}
                  value={filterYear ?? ''}
                  onChange={(e) => setFilterYear(e.target.value ? Number(e.target.value) : null)}
                  className="rounded-md border border-gray-300 px-2 py-1 w-24"
                />

                <Button onClick={() => setActiveAnalysisId(selectedBalanceteId)}>Carregar</Button>
              </div>
            )}
          </div>

          <div className="grid grid-cols-1 md:grid-cols-3 gap-6 mb-8">
            <Card className="border-l-4 border-green-500">
              <CardContent className="p-6">
                <p className="text-sm font-medium text-gray-500">Receita Total</p>
                <p className="text-3xl font-bold text-green-600">
                  {formatCurrency(kpiData?.receita_total || 0)}
                </p>
              </CardContent>
            </Card>
            <Card className="border-l-4 border-red-500">
              <CardContent className="p-6">
                <p className="text-sm font-medium text-gray-500">Despesa Total</p>
                <p className="text-3xl font-bold text-red-600">
                  {formatCurrency(kpiData?.despesa_total || 0)}
                </p>
              </CardContent>
            </Card>
            <Card className={`border-l-4 ${(kpiData?.resultado_periodo || 0) >= 0 ? 'border-green-500' : 'border-red-500'}`}>
              <CardContent className="p-6">
                <p className="text-sm font-medium text-gray-500">Resultado do Período</p>
                <p className={`text-3xl font-bold ${(kpiData?.resultado_periodo || 0) >= 0 ? 'text-green-600' : 'text-red-600'}`}>
                  {formatCurrency(kpiData?.resultado_periodo || 0)}
                </p>
              </CardContent>
            </Card>
          </div>

          <div className="grid grid-cols-1 lg:grid-cols-2 gap-8 mb-8">
            <Card>
              <CardHeader><CardTitle>De Onde Vieram suas Receitas?</CardTitle></CardHeader>
              <CardContent>
                {receitasComposicao.map(r => <div key={r.categoria}>{r.categoria}: {formatCurrency(r.valor)}</div>)}
              </CardContent>
            </Card>
            <Card>
              <CardHeader><CardTitle>Para Onde Foi seu Dinheiro?</CardTitle></CardHeader>
              <CardContent>
                {despesasPrincipais.map(d => <div key={d.categoria}>{d.categoria}: {formatCurrency(d.valor)}</div>)}
              </CardContent>
            </Card>
          </div>

          <Card>
            <CardHeader>
              <CardTitle>Detalhes por Conta</CardTitle>
            </CardHeader>
            <CardContent>
               <table className="min-w-full divide-y divide-gray-200">
                  <thead className="bg-gray-50">
                    <tr>
                      <th className="px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase">Conta</th>
                      <th className="px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase">Categoria</th>
                      <th className="px-6 py-3 text-right text-xs font-medium text-gray-500 uppercase">Valor</th>
                    </tr>
                  </thead>
                  <tbody className="bg-white divide-y divide-gray-200">
                    {contasFiltered.map((conta, index) => (
                      <tr key={index}>
                        <td className="px-6 py-4 whitespace-nowrap text-sm text-gray-900">{conta.conta}</td>
                        <td className="px-6 py-4 whitespace-nowrap text-sm text-gray-500">{conta.subgrupo}</td>
                        <td className="px-6 py-4 whitespace-nowrap text-sm text-right text-red-600">{formatCurrency(conta.valor)}</td>
                      </tr>
                    ))}
                  </tbody>
                </table>
            </CardContent>
          </Card>

        </div>
      </div>
    </MainLayout>
  );
}
