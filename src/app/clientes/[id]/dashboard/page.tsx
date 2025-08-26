"use client";

import { useState, useEffect } from 'react';
import { useParams } from 'next/navigation';
import Link from 'next/link';

// Importe seus componentes de UI e ícones
import MainLayout from '@/components/layout/MainLayout';
import { Card, CardContent, CardHeader, CardTitle } from '@/components/ui/Card';
import { Button } from '@/components/ui/Button';
import { Input } from '@/components/ui/Input';
import { ArrowLeftIcon, MagnifyingGlassIcon, CalendarIcon } from '@heroicons/react/24/outline';

import { formatCurrency } from '@/lib/utils';
// Supondo que você tenha componentes de gráficos
// import { PieChart } from '@/components/charts/PieChart';
// import { BarChart } from '@/components/charts/BarChart';

// --- ARQUITETURA DE API CORRETA E FINAL ---
const API_BASE_URL = "http://localhost:8000";

// Funções de serviço que consomem as rotas corretas do backend
async function getClientById(id: string) {
  const res = await fetch(`${API_BASE_URL}/api/clients/${id}`);
  if (!res.ok) throw new Error(`Falha ao buscar dados do cliente (status: ${res.status})`);
  return res.json();
}

async function getAvailableAnalyses(clientId: string) {
  // Esta função busca a lista de balancetes JÁ PROCESSADOS para o seletor de período
  const res = await fetch(`${API_BASE_URL}/api/balancetes/cliente/${clientId}`);
  if (!res.ok) throw new Error(`Falha ao buscar lista de balancetes (status: ${res.status})`);
  return res.json();
}

// --- CORREÇÃO APLICADA AQUI ---
// A função agora aceita e envia o clientId, conforme exigido pelo backend.
async function getDashboardData(analysisId: string, clientId: string) {
  const params = new URLSearchParams({
    analysis_id: analysisId,
    client_id: clientId
  });
  const url = `${API_BASE_URL}/api/dashboard/?${params.toString()}`;
  console.log('[dashboard] GET', url);
  const res = await fetch(url);
  if (!res.ok) throw new Error(`Falha ao buscar dados do dashboard (status: ${res.status})`);
  return res.json();
}

async function getFinancialEntriesForTable(analysisId: string, clientId: string) {
  // Busca os detalhes brutos APENAS para a tabela de detalhes
  const res = await fetch(`${API_BASE_URL}/api/financial-entries/?analysis_id=${analysisId}&client_id=${clientId}`);
  if (!res.ok) throw new Error(`Falha ao buscar detalhes das contas (status: ${res.status})`);
  return res.json();
}

// --- Interfaces de Tipagem ---
interface Cliente { id: string; nome: string; }
interface Balancete { id: string; ano: number; mes: number; analysis_id?: number; }
interface KPIData { receita_total: number; despesa_total: number; resultado_periodo: number; }
interface ChartData { categoria: string; valor: number; }
interface ContaDetalhe { conta: string; valor: number; subgrupo: string; }

// --- Componente Principal ---
export default function DashboardFinanceiro() {
  const params = useParams();
  const clienteId = params.id as string;
  
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [cliente, setCliente] = useState<Cliente | null>(null);
  const [availableAnalyses, setAvailableAnalyses] = useState<Balancete[]>([]);
  const [selectedAnalysisId, setSelectedAnalysisId] = useState<string>('');
  
  const [kpiData, setKpiData] = useState<KPIData | null>(null);
  const [receitasComposicao, setReceitasComposicao] = useState<ChartData[]>([]);
  const [despesasPrincipais, setDespesasPrincipais] = useState<ChartData[]>([]);
  
  const [contasDetalhes, setContasDetalhes] = useState<ContaDetalhe[]>([]);
  const [contasFiltered, setContasFiltered] = useState<ContaDetalhe[]>([]);
  const [buscaConta, setBuscaConta] = useState<string>('');

  const formatMonth = (mes: number, ano: number) => {
    const meses = ['Janeiro', 'Fevereiro', 'Março', 'Abril', 'Maio', 'Junho', 'Julho', 'Agosto', 'Setembro', 'Outubro', 'Novembro', 'Dezembro'];
    return `${meses[mes - 1]} de ${ano}`;
  };

  // 1. Busca os dados iniciais: cliente e a lista de análises disponíveis
  useEffect(() => {
    async function fetchInitialData() {
      if (!clienteId) return;
      try {
        setLoading(true);
        setError(null);
        const [clienteData, analysesData] = await Promise.all([
          getClientById(clienteId),
          getAvailableAnalyses(clienteId)
        ]);
        
        setCliente(clienteData);
        analysesData.sort((a: Balancete, b: Balancete) => (b.ano * 100 + b.mes) - (a.ano * 100 + a.mes));
        setAvailableAnalyses(analysesData);
        
        if (analysesData.length > 0 && analysesData[0].analysis_id) {
          setSelectedAnalysisId(String(analysesData[0].analysis_id));
        } else {
          setLoading(false);
        }
      } catch (error) {
        console.error('Erro ao carregar dados iniciais:', error);
        setError(error instanceof Error ? error.message : 'Erro desconhecido');
        setLoading(false);
      }
    }
    fetchInitialData();
  }, [clienteId]);

  // 2. Busca os dados do dashboard e os detalhes da tabela QUANDO uma análise é selecionada
  useEffect(() => {
    async function fetchDashboardDetails() {
      if (!selectedAnalysisId) return;
      try {
        setLoading(true);
        setError(null);
        
        // --- CORREÇÃO APLICADA AQUI ---
        // Passando o clienteId para a função de busca do dashboard.
        const [dashboardData, entriesData] = await Promise.all([
          getDashboardData(selectedAnalysisId, clienteId),
          getFinancialEntriesForTable(selectedAnalysisId, clienteId)
        ]);

        if (dashboardData) {
          setKpiData(dashboardData.kpis);
          setReceitasComposicao(dashboardData.grafico_receitas || []);
          setDespesasPrincipais(dashboardData.grafico_despesas || []);
        }

        if (entriesData) {
          const detalhes = entriesData
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
        setLoading(false);
      }
    }
    fetchDashboardDetails();
  }, [selectedAnalysisId, clienteId]);

  // 3. Filtra a tabela de detalhes
  useEffect(() => {
    let filtered = contasDetalhes;
    if (buscaConta) {
      filtered = filtered.filter(conta => 
        conta.conta.toLowerCase().includes(buscaConta.toLowerCase())
      );
    }
    setContasFiltered(filtered);
  }, [buscaConta, contasDetalhes]);

  // --- Lógica de Renderização ---
  const selectedBalanceteInfo = availableAnalyses.find(b => b.analysis_id && String(b.analysis_id) === selectedAnalysisId);

  if (loading) {
    return <MainLayout><div className="p-8 text-center">Carregando...</div></MainLayout>;
  }
  
  if (error) {
    return <MainLayout><div className="p-8 text-center text-red-500">Erro: {error}</div></MainLayout>;
  }

  if (!cliente || !selectedBalanceteInfo) {
    return (
        <MainLayout>
            <div className="p-8 text-center">
                <h1 className="text-2xl font-bold mb-4">Cliente: {cliente?.nome || '...'}</h1>
                <p>Nenhum balancete analisado encontrado para este cliente.</p>
                <Link href={`/clientes/${clienteId}/balancetes`}>
                    <Button className="mt-4">Gerenciar Balancetes</Button>
                </Link>
            </div>
        </MainLayout>
    );
  }

  return (
    <MainLayout>
      <div className="py-6">
        <div className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8">
          
          <div className="mb-8 flex items-center justify-between">
            <div>
              <h1 className="text-3xl font-bold text-gray-900">Dashboard: {cliente.nome}</h1>
              <p className="mt-2 text-gray-600">
                Período: {formatMonth(selectedBalanceteInfo.mes, selectedBalanceteInfo.ano)}
              </p>
            </div>
            {availableAnalyses.length > 1 && (
              <select
                value={selectedAnalysisId}
                onChange={(e) => setSelectedAnalysisId(e.target.value)}
                className="rounded-md border border-gray-300 px-3 py-2 text-sm"
              >
                {availableAnalyses.map((b) => (
                  <option key={String(b.analysis_id)} value={String(b.analysis_id)}>
                    {formatMonth(b.mes, b.ano)}
                  </option>
                ))}
              </select>
            )}
          </div>

          <div className="grid grid-cols-1 md:grid-cols-3 gap-6 mb-8">
            <Card className="border-l-4 border-green-500">
              <CardContent className="p-6">
                <p className="text-sm font-medium text-gray-500">Receita Total</p>
                <p className="text-3xl font-bold text-green-600">{formatCurrency(kpiData?.receita_total || 0)}</p>
              </CardContent>
            </Card>
            <Card className="border-l-4 border-red-500">
              <CardContent className="p-6">
                <p className="text-sm font-medium text-gray-500">Despesa Total</p>
                <p className="text-3xl font-bold text-red-600">{formatCurrency(kpiData?.despesa_total || 0)}</p>
              </CardContent>
            </Card>
            <Card className={`border-l-4 ${(kpiData?.resultado_periodo || 0) >= 0 ? 'border-green-500' : 'border-red-500'}`}>
              <CardContent className="p-6">
                <p className="text-sm font-medium text-gray-500">Resultado do Período</p>
                <p className={`text-3xl font-bold ${(kpiData?.resultado_periodo || 0) >= 0 ? 'text-green-600' : 'text-red-600'}`}>{formatCurrency(kpiData?.resultado_periodo || 0)}</p>
              </CardContent>
            </Card>
          </div>

          <div className="grid grid-cols-1 lg:grid-cols-2 gap-8 mb-8">
            <Card>
              <CardHeader><CardTitle>De Onde Vieram suas Receitas?</CardTitle></CardHeader>
              <CardContent>
                {/* Aqui vai seu componente de Gráfico de Pizza, ex: <PieChart data={receitasComposicao} /> */}
                {/* Placeholder para evitar erro de children */}
                <></>
              </CardContent>
            </Card>
            <Card>
              <CardHeader><CardTitle>Para Onde Foi seu Dinheiro?</CardTitle></CardHeader>
              <CardContent>
                {/* Aqui vai seu componente de Gráfico de Barras, ex: <BarChart data={despesasPrincipais} /> */}
                <></>
              </CardContent>
            </Card>
          </div>

          <Card>
            <CardHeader><CardTitle>Detalhes por Conta</CardTitle></CardHeader>
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
