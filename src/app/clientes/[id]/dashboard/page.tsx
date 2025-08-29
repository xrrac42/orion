"use client";

import { useState, useEffect, useMemo, useRef } from 'react';
import { useParams } from 'next/navigation';
import Link from 'next/link';

// Importe seus componentes de UI e ícones
import MainLayout from '@/components/layout/MainLayout';
import { Card, CardContent, CardHeader, CardTitle } from '@/components/ui/Card';
import { Button } from '@/components/ui/Button';
import { Input } from '@/components/ui/Input';
import Select from '@/components/ui/Select';
import { Table, TableHeader, TableBody, TableRow, TableHead, TableCell } from '@/components/ui/Table';
import { ArrowLeftIcon, MagnifyingGlassIcon, CalendarIcon } from '@heroicons/react/24/outline';

import { formatCurrency } from '@/lib/utils';
import PieChart from '@/components/charts/PieChart';
import { GastoPorCategoria } from '@/types';

// Helpers para gráficos
const COLOR_PALETTE = ['#4f46e5', '#06b6d4', '#10b981', '#f59e0b', '#ef4444', '#8b5cf6', '#ec4899'];
function colorForIndex(i: number) { return COLOR_PALETTE[i % COLOR_PALETTE.length]; }
function pieGradient(list: { valor: number }[]) {
  const total = list.reduce((s, x) => s + (x.valor || 0), 0) || 1;
  let cum = 0;
  return list.map((item, i) => {
    const pct = (item.valor / total) * 100;
    const start = Math.round(cum * 100) / 100;
    cum += pct;
    const end = Math.round(cum * 100) / 100;
    return `${colorForIndex(i)} ${start}% ${end}%`;
  }).join(', ');
}
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

// Busca os dados do dashboard pelo client_id + year + month (ou por analysis_id quando disponível)
async function getDashboardData(clientId: string, year: number, month: number, analysisId?: number) {
  if (analysisId) {
    const res = await fetch(`${API_BASE_URL}/api/dashboard/${analysisId}`);
    if (!res.ok) throw new Error(`Falha ao buscar dados do dashboard por analysis_id (status: ${res.status})`);
    return res.json();
  }

  const params = new URLSearchParams({
    client_id: clientId,
    year: String(year),
    month: String(month)
  });
  const url = `${API_BASE_URL}/api/dashboard/?${params.toString()}`;
  const res = await fetch(url);
  if (!res.ok) throw new Error(`Falha ao buscar dados do dashboard (status: ${res.status})`);
  return res.json();
}

// --- Interfaces de Tipagem ---
interface Cliente { id: string; nome: string; }
interface Balancete { id: string; ano: number; mes: number; analysis_id?: number; }
interface KPIData { receita_total: number; despesa_total: number; resultado_periodo: number; }
interface ChartData { categoria: string; valor: number; }
interface ContaDetalhe { conta: string; valor: number; subgrupo: string; movement_type?: 'Receita' | 'Despesa' }

// --- Componente Principal ---
export default function DashboardFinanceiro() {
  const params = useParams();
  const clienteId = params.id as string;
  // Simple i18n map (replace with your i18n solution later if needed)
  const i18n = {
    selectPeriodsLabel: 'Selecione períodos:',
    selectAll: 'Selecionar todos',
    clearSelection: 'Limpar seleção',
    periodsSelected: 'Períodos selecionados',
    noReceita: 'Nenhuma receita encontrada para o(s) período(s) selecionado(s).',
    noDespesa: 'Nenhuma despesa encontrada para o(s) período(s) selecionado(s).',
    noLancamento: 'Nenhum lançamento encontrado para o(s) período(s) selecionado(s).'
  };
  
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [cliente, setCliente] = useState<Cliente | null>(null);
  const [availableAnalyses, setAvailableAnalyses] = useState<Balancete[]>([]);
  // selectedPeriods holds strings like '2024-12' for multi-select
  const [selectedPeriods, setSelectedPeriods] = useState<string[]>([]);
  const [periodsOpen, setPeriodsOpen] = useState(false);
  const dropdownRef = useRef<HTMLDivElement | null>(null);
  const [lastAggregatePayload, setLastAggregatePayload] = useState<any>(null);
  
  const [kpiData, setKpiData] = useState<KPIData | null>(null);
  const [receitasComposicao, setReceitasComposicao] = useState<ChartData[]>([]);
  const [despesasPrincipais, setDespesasPrincipais] = useState<ChartData[]>([]);
  
  const [contasDetalhes, setContasDetalhes] = useState<ContaDetalhe[]>([]);
  const [receitaChartState, setReceitaChartState] = useState<GastoPorCategoria[]>([]);
  const [despesaChartState, setDespesaChartState] = useState<GastoPorCategoria[]>([]);
  const [contasFiltered, setContasFiltered] = useState<ContaDetalhe[]>([]);
  const [buscaConta, setBuscaConta] = useState<string>('');

  // Build chart data and filtered entries using memo as suggested
  const [searchTerm, setSearchTerm] = useState<string>('');
  const { receitaChartData, despesaChartData, margemLucro, filteredEntries } = useMemo(() => {
    // Always compute chart aggregates from the full source: contasDetalhes
    const entries = contasDetalhes || [];

    // Accumulators
    let totalReceita = 0;
    let totalDespesa = 0;
    const receitaMap = new Map<string, number>();
    const despesaMap = new Map<string, number>();

    for (const raw of entries) {
      const e: any = raw;
      const mv = e.movement_type ? String(e.movement_type).trim().toLowerCase() : '';
      const val = Number(e.valor ?? 0) || 0;
      const sub = e.subgrupo || 'Outros';

      if (mv === 'receita') {
        totalReceita += val;
        receitaMap.set(sub, (receitaMap.get(sub) || 0) + val);
      } else {
        totalDespesa += val;
        despesaMap.set(sub, (despesaMap.get(sub) || 0) + val);
      }
    }

    const makeArray = (m: Map<string, number>, total: number, colors: string[]) => {
      return Array.from(m.entries())
        .sort((a, b) => b[1] - a[1])
        .map(([categoria, valor], idx) => ({
          categoria,
          valor,
          percentual: total && total > 0 ? (valor / total) * 100 : 0,
          cor: colors[idx % colors.length],
          contas_detalhadas: []
        }));
    };

    const receitaArr = (receitaChartState && receitaChartState.length > 0)
      ? receitaChartState
      : makeArray(receitaMap, (kpiData?.receita_total ?? totalReceita), ['#10B981', '#3B82F6', '#6366F1', '#8B5CF6', '#A855F7']);

    const despesaArr = (despesaChartState && despesaChartState.length > 0)
      ? despesaChartState
      : makeArray(despesaMap, (kpiData?.despesa_total ?? totalDespesa), ['#EF4444', '#F97316', '#F59E0B', '#EAB308', '#D97706']);

    const margem = (kpiData && kpiData.receita_total > 0)
      ? (kpiData.resultado_periodo / kpiData.receita_total) * 100
      : (totalReceita > 0 ? ((totalReceita - totalDespesa) / totalReceita) * 100 : 0);

    // filteredEntries should be a view of the full entries source filtered by searchTerm
    const filtered = entries.filter((entry: any) => {
      if (!searchTerm) return true;
      return (entry.conta || '').toLowerCase().includes(searchTerm.toLowerCase());
    });

    return { receitaChartData: receitaArr, despesaChartData: despesaArr, margemLucro: margem, filteredEntries: filtered };
  }, [contasDetalhes, kpiData, receitaChartState, despesaChartState, searchTerm]);

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
          // default to the most recent period
          setSelectedPeriods([`${analysesData[0].ano}-${analysesData[0].mes}`]);
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

  // close dropdown when clicking outside
  useEffect(() => {
    function handleClick(e: MouseEvent) {
      if (!dropdownRef.current) return;
      if (!(e.target instanceof Node)) return;
      if (!dropdownRef.current.contains(e.target as Node)) setPeriodsOpen(false);
    }
    document.addEventListener('mousedown', handleClick);
    return () => document.removeEventListener('mousedown', handleClick);
  }, []);

  // 2. Busca os dados do dashboard e os detalhes da tabela QUANDO uma análise é selecionada
  // When selectedPeriods changes, fetch all selected dashboards and aggregate
  useEffect(() => {
    async function fetchAggregated() {
      if (!clienteId || !selectedPeriods || selectedPeriods.length === 0) return;
      try {
        setLoading(true);
        setError(null);

        // Try server-side aggregated endpoint when possible (prefer single request)
        // Map selectedPeriods to analysis_ids if available in availableAnalyses
        const selectedAnalysisIds: number[] = [];
        selectedPeriods.forEach(p => {
          const [ano, mes] = p.split('-').map(x => Number(x));
          const found = availableAnalyses.find(a => a.ano === ano && a.mes === mes && a.analysis_id);
          if (found && found.analysis_id) selectedAnalysisIds.push(found.analysis_id as number);
        });

  if (selectedAnalysisIds.length === selectedPeriods.length) {
          // we have analysis_ids for all selected periods — call aggregate endpoint
          try {
            const res = await fetch(`${API_BASE_URL}/api/dashboard/aggregate`, {
              method: 'POST',
              headers: { 'Content-Type': 'application/json' },
              body: JSON.stringify({ analysis_ids: selectedAnalysisIds })
            });
            if (res.ok) {
              const payload = await res.json();
              console.debug('[dashboard] aggregate(payload):', payload);
              setLastAggregatePayload(payload);
              const k = payload.kpis || {};
              setKpiData({ receita_total: Number(k.receita_total || 0), despesa_total: Number(k.despesa_total || 0), resultado_periodo: Number(k.resultado_periodo || 0) });

              // use provided grafico arrays if present
              if (Array.isArray(payload.grafico_receitas)) setReceitaChartState(payload.grafico_receitas);
              else setReceitaChartState([]);
              if (Array.isArray(payload.grafico_despesas)) setDespesaChartState(payload.grafico_despesas);
              else setDespesaChartState([]);

              const detalhes = (payload.financial_entries || []).map((entry: any) => ({
                conta: entry.specific_account,
                valor: entry.period_value,
                subgrupo: entry.subgroup_1 || 'N/A',
                movement_type: entry.movement_type
              }));
              setContasDetalhes(detalhes);
              setLoading(false);
              return;
            }
            // else fallthrough to client-side aggregation
            console.warn('[dashboard] aggregate endpoint returned non-OK, falling back to client aggregation', res.status);
          } catch (e) {
            console.warn('[dashboard] aggregate endpoint failed, falling back to client aggregation', e);
          }
        }

          // If we couldn't call aggregate with analysis_ids, try calling aggregate with periods (server will resolve analysis_ids)
          try {
            const periodsPayload = selectedPeriods.map(p => {
              const [y, m] = p.split('-').map(x => Number(x));
              return { year: y, month: m, client_id: clienteId };
            });
            const res2 = await fetch(`${API_BASE_URL}/api/dashboard/aggregate`, {
              method: 'POST',
              headers: { 'Content-Type': 'application/json' },
              body: JSON.stringify({ periods: periodsPayload })
            });
            if (res2.ok) {
              const payload = await res2.json();
              console.debug('[dashboard] aggregate(periods) payload:', payload);
              setLastAggregatePayload(payload);
              const k = payload.kpis || {};
              setKpiData({ receita_total: Number(k.receita_total || 0), despesa_total: Number(k.despesa_total || 0), resultado_periodo: Number(k.resultado_periodo || 0) });
              if (Array.isArray(payload.grafico_receitas)) setReceitaChartState(payload.grafico_receitas);
              else setReceitaChartState([]);
              if (Array.isArray(payload.grafico_despesas)) setDespesaChartState(payload.grafico_despesas);
              else setDespesaChartState([]);
              const detalhes = (payload.financial_entries || []).map((entry: any) => ({
                conta: entry.specific_account,
                valor: entry.period_value,
                subgrupo: entry.subgroup_1 || 'N/A',
                movement_type: entry.movement_type
              }));
              setContasDetalhes(detalhes);
              setLoading(false);
              return;
            }
          } catch (err) {
            console.warn('[dashboard] aggregate by periods failed, falling back to client aggregation', err);
          }

          // fallback: perform per-period requests and aggregate on client
        const requests = selectedPeriods.map(p => {
          const [ano, mes] = p.split('-').map(x => Number(x));
          const found = availableAnalyses.find(a => a.ano === ano && a.mes === mes && a.analysis_id);
          const aid = found && found.analysis_id ? Number(found.analysis_id) : undefined;
          return getDashboardData(clienteId, Number(ano), Number(mes), aid);
        });

        const results = await Promise.allSettled(requests);

        // aggregate KPIs and entries
        let aggReceita = 0;
        let aggDespesa = 0;
        let aggResultado = 0;
        let allEntries: any[] = [];
        const receitaMap = new Map<string, number>();
        const despesaMap = new Map<string, number>();

        for (const r of results) {
          if (r.status === 'fulfilled') {
            const d = r.value;
            const k = d.kpis || {};
            aggReceita += Number(k.receita_total || 0);
            aggDespesa += Number(k.despesa_total || 0);
            aggResultado += Number(k.resultado_periodo || 0);
            allEntries = allEntries.concat(d.financial_entries || []);

            // Prefer API-provided pre-aggregated chart data when available
            if (d.grafico_receitas && Array.isArray(d.grafico_receitas)) {
              d.grafico_receitas.forEach((item: any) => {
                const key = item.categoria || 'Outros';
                receitaMap.set(key, (receitaMap.get(key) || 0) + Number(item.valor || 0));
              });
            }
            if (d.grafico_despesas && Array.isArray(d.grafico_despesas)) {
              d.grafico_despesas.forEach((item: any) => {
                const key = item.categoria || 'Outros';
                despesaMap.set(key, (despesaMap.get(key) || 0) + Number(item.valor || 0));
              });
            }
          } else {
            // log but continue
            console.warn('Falha ao buscar um período:', r.reason);
          }
        }

        setKpiData({ receita_total: aggReceita, despesa_total: aggDespesa, resultado_periodo: aggResultado });

        // build chart arrays from receitaMap/despesaMap if they were populated
        if (receitaMap.size > 0) {
          const receitaArr: GastoPorCategoria[] = Array.from(receitaMap.entries()).map(([categoria, valor], idx) => ({
            categoria,
            valor,
            percentual: aggReceita > 0 ? (valor / aggReceita) * 100 : 0,
            cor: colorForIndex(idx),
            contas_detalhadas: []
          }));
          setReceitaChartState(receitaArr);
        } else {
          setReceitaChartState([]);
        }

        if (despesaMap.size > 0) {
          const despesaArr: GastoPorCategoria[] = Array.from(despesaMap.entries()).map(([categoria, valor], idx) => ({
            categoria,
            valor,
            percentual: aggDespesa > 0 ? (valor / aggDespesa) * 100 : 0,
            cor: colorForIndex(idx),
            contas_detalhadas: []
          }));
          setDespesaChartState(despesaArr);
        } else {
          setDespesaChartState([]);
        }

        // if charts are empty, log payload for easier debugging
        if ((receitaMap.size === 0) && lastAggregatePayload) {
          console.debug('[dashboard] No receita chart data built; last aggregate payload:', lastAggregatePayload);
        }

        const detalhes = allEntries.map((entry: any) => ({
          conta: entry.specific_account,
          valor: entry.period_value,
          subgrupo: entry.subgroup_1 || 'N/A',
          movement_type: entry.movement_type
        }));
        setContasDetalhes(detalhes);

      } catch (err) {
        console.error('Erro ao agregar dados:', err);
        setError(err instanceof Error ? err.message : 'Erro desconhecido');
      } finally {
        setLoading(false);
      }
    }
    fetchAggregated();
  }, [selectedPeriods, clienteId]);

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
  const selectedBalanceteInfo = (() => {
    // show the most recent selected period's info (or the first available)
    const sel = (selectedPeriods && selectedPeriods.length > 0) ? selectedPeriods[0] : (availableAnalyses[0] ? `${availableAnalyses[0].ano}-${availableAnalyses[0].mes}` : null);
    if (!sel) return null;
    const [anoStr, mesStr] = sel.split('-');
    const ano = Number(anoStr);
    const mes = Number(mesStr);
    return availableAnalyses.find(b => b.ano === ano && b.mes === mes) || null;
  })();

  if (loading) {
    // lightweight skeletons inside the layout instead of a full-page loader
    return (
      <MainLayout>
        <div className="py-6">
          <div className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8">
            <div className="mb-8">
              <h1 className="text-3xl font-bold text-gray-900 animate-pulse bg-gray-200 rounded w-1/4 h-8"></h1>
              <div className="mt-2 h-4 w-48 bg-gray-200 rounded animate-pulse"></div>
            </div>

            <div className="grid grid-cols-1 md:grid-cols-4 gap-6 mb-8">
              {[0,1,2,3].map(i => (
                <div key={i} className="border-l-4 p-6 bg-white rounded shadow-sm">
                  <div className="h-5 w-32 bg-gray-200 rounded mb-4 animate-pulse"></div>
                  <div className="h-8 w-36 bg-gray-200 rounded animate-pulse"></div>
                </div>
              ))}
            </div>

            <div className="grid grid-cols-1 lg:grid-cols-2 gap-8 mb-8">
              <div className="p-6 bg-white rounded shadow-sm">
                <div className="h-6 w-48 bg-gray-200 rounded mb-4 animate-pulse"></div>
                <div className="flex items-center space-x-4">
                  <div className="h-40 w-40 bg-gray-200 rounded-full animate-pulse"></div>
                  <div className="flex-1">
                    <div className="h-4 bg-gray-200 rounded mb-2 animate-pulse"></div>
                    <div className="h-4 bg-gray-200 rounded mb-2 animate-pulse"></div>
                    <div className="h-4 bg-gray-200 rounded mb-2 animate-pulse"></div>
                  </div>
                </div>
              </div>

              <div className="p-6 bg-white rounded shadow-sm">
                <div className="h-6 w-48 bg-gray-200 rounded mb-4 animate-pulse"></div>
                <div className="flex items-center space-x-4">
                  <div className="h-40 w-40 bg-gray-200 rounded-full animate-pulse"></div>
                  <div className="flex-1">
                    <div className="h-4 bg-gray-200 rounded mb-2 animate-pulse"></div>
                    <div className="h-4 bg-gray-200 rounded mb-2 animate-pulse"></div>
                    <div className="h-4 bg-gray-200 rounded mb-2 animate-pulse"></div>
                  </div>
                </div>
              </div>
            </div>

            <div className="bg-white rounded shadow-sm p-6">
              <div className="h-6 w-48 bg-gray-200 rounded mb-4 animate-pulse"></div>
              <div className="space-y-2">
                {[0,1,2,3,4].map(i => (
                  <div key={i} className="h-4 bg-gray-200 rounded animate-pulse"></div>
                ))}
              </div>
            </div>
          </div>
        </div>
      </MainLayout>
    );
  }

  // Dev-only: show last aggregate payload for easier debugging in-app
  const DebugPanel = () => {
    if (!lastAggregatePayload) return null;
    return (
      <div className="mt-4 p-3 bg-gray-50 border border-gray-200 rounded text-sm text-gray-700">
        <strong>Debug: lastAggregatePayload</strong>
        <pre className="mt-2 max-h-72 overflow-auto text-xs">{JSON.stringify(lastAggregatePayload, null, 2)}</pre>
      </div>
    );
  };
  
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
              <div className="mt-2 text-gray-600">
                {selectedPeriods && selectedPeriods.length > 1 ? (
                  <div>
                    <span className="font-medium">{i18n.periodsSelected} ({selectedPeriods.length}):</span>
                    <div className="text-sm mt-1">
                      {selectedPeriods.map(p => {
                        const [y, m] = p.split('-').map(x => Number(x));
                        return (<span key={p} className="inline-block mr-2">{formatMonth(m, y)}</span>);
                      })}
                    </div>
                  </div>
                ) : (
                  <span>Período: {selectedBalanceteInfo ? formatMonth(selectedBalanceteInfo.mes, selectedBalanceteInfo.ano) : '—'}</span>
                )}
              </div>
            </div>
            {availableAnalyses.length > 0 && (
              <div className="relative" ref={dropdownRef}>
                <div className="flex items-center justify-between mb-2">
                  <label className="block text-base font-medium text-gray-700 mr-4">{i18n.selectPeriodsLabel}</label>
          <div className="flex items-center space-x-2">
          <Button 
  variant="outline" 
  size="sm"
  className="cursor-pointer"
  onClick={() => setPeriodsOpen(p => !p)}
>
        {selectedPeriods.length > 0 ? `${selectedPeriods.length} selecionado(s)` : 'Abrir'}
      </Button>

      <Button 
        variant="outline" 
        size="sm"
        className="cursor-pointer"
        onClick={() => setSelectedPeriods([])}
      >
        {i18n.clearSelection}
      </Button>
          </div>
                </div>

                {periodsOpen && (
                  <div className="absolute right-0 mt-2 w-80 bg-white border rounded-md shadow-lg z-20 p-3">
                    <div className="flex items-center justify-between mb-2">
                      <div className="text-base font-medium text-gray-700">{i18n.selectPeriodsLabel}</div>
                      <div className="space-x-2">
                        <button className="text-xs px-2 py-1 border border-gray-200 rounded text-blue-600 bg-white hover:bg-gray-50 cursor-pointer" onClick={() => setSelectedPeriods(availableAnalyses.map(a => `${a.ano}-${a.mes}`))}>{i18n.selectAll}</button>
                        <button className="text-xs px-2 py-1 border border-gray-200 rounded text-gray-700 bg-white hover:bg-gray-50 cursor-pointer" onClick={() => setSelectedPeriods([])}>{i18n.clearSelection}</button>
                      </div>
                    </div>
                    <div className="max-h-44 overflow-auto">
                      {availableAnalyses.map((b) => {
                        const val = `${b.ano}-${b.mes}`;
                        const checked = selectedPeriods.includes(val);
                        return (
                          <label key={val} className="flex items-center text-sm p-1">
                            <input
                              type="checkbox"
                              checked={checked}
                              onChange={() => {
                                setSelectedPeriods(prev => prev.includes(val) ? prev.filter(x => x !== val) : [...prev, val]);
                              }}
                              className="mr-2"
                            />
                            <span>{formatMonth(b.mes, b.ano)}</span>
                          </label>
                        );
                      })}
                    </div>
                  </div>
                )}
              </div>
            )}
          </div>

          <div className="grid grid-cols-1 md:grid-cols-4 gap-6 mb-8">
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
            <Card className="border-l-4 border-indigo-500">
              <CardContent className="p-6">
                <p className="text-sm font-medium text-gray-500">Margem de Lucro</p>
                <p className="text-3xl font-bold text-indigo-600">{(() => {
                  const receita = kpiData?.receita_total || 0;
                  const resultado = kpiData?.resultado_periodo || 0;
                  const margem = receita === 0 ? 0 : (resultado / receita) * 100;
                  return `${margem.toFixed(2)}%`;
                })()}</p>
              </CardContent>
            </Card>
          </div>

          <div className="grid grid-cols-1 lg:grid-cols-2 gap-8 mb-8">
            <Card>
              <CardHeader><CardTitle>De Onde Vieram suas Receitas?</CardTitle></CardHeader>
              <CardContent>
                {receitaChartData.length === 0 ? (
                  <p className="text-sm text-gray-500">Nenhuma receita encontrada para o(s) período(s) selecionado(s).</p>
                ) : (
                  <div className="flex items-center space-x-4">
                    <div style={{ width: 320, height: 320 }}>
                      <PieChart data={receitaChartData} title="Receitas por Categoria" />
                    </div>
                    <div>
                      {receitaChartData.map((r: GastoPorCategoria, idx: number) => (
                        <div key={r.categoria} className="flex items-center text-sm mb-2">
                          <span className="inline-block w-3 h-3 mr-2 rounded" style={{ background: r.cor }}></span>
                          <span className="font-medium mr-2">{r.categoria}</span>
                          <span className="text-gray-500">{formatCurrency(r.valor)}</span>
                        </div>
                      ))}
                    </div>
                  </div>
                )}
              </CardContent>
            </Card>
            <Card>
              <CardHeader><CardTitle>Para Onde Foi seu Dinheiro?</CardTitle></CardHeader>
              <CardContent>
                {despesaChartData.length === 0 ? (
                  <p className="text-sm text-gray-500">Nenhuma despesa encontrada para o(s) período(s) selecionado(s).</p>
                ) : (
                  <div className="flex items-center space-x-4">
                    <div style={{ width: 320, height: 320 }}>
                      <PieChart data={despesaChartData} title="Despesas por Categoria" />
                    </div>
                    <div>
                      {despesaChartData.map((r: GastoPorCategoria, idx: number) => (
                        <div key={r.categoria} className="flex items-center text-sm mb-2">
                          <span className="inline-block w-3 h-3 mr-2 rounded" style={{ background: r.cor }}></span>
                          <span className="font-medium mr-2">{r.categoria}</span>
                          <span className="text-gray-500">{formatCurrency(r.valor)}</span>
                        </div>
                      ))}
                    </div>
                  </div>
                )}
              </CardContent>
            </Card>
          </div>

          <Card>
            <CardHeader className="flex items-center justify-between"><CardTitle>Detalhes por Conta</CardTitle>
              <div className="flex items-center space-x-2">
                <div className="relative">
                  <Input
                    type="text"
                    value={searchTerm}
                    onChange={(e) => setSearchTerm(e.target.value)}
                    placeholder="Pesquisar conta..."
                    className="w-64"
                  />
                </div>
              </div>
            </CardHeader>
            <CardContent>
              <div className="overflow-x-auto">
                <Table>
                  <TableHeader>
                    <TableRow>
                      <TableHead>Conta Específica</TableHead>
                      <TableHead>Categoria</TableHead>
                      <TableHead>Tipo</TableHead>
                      <TableHead className="text-right">Valor</TableHead>
                    </TableRow>
                  </TableHeader>
                  <TableBody>
                    {filteredEntries.length > 0 ? (
                      filteredEntries.map((entry, index) => (
                        <TableRow key={index}>
                          <TableCell className="font-medium">{entry.conta}</TableCell>
                          <TableCell>{entry.subgrupo || '-'}</TableCell>
                          <TableCell>{(entry as any).movement_type}</TableCell>
                          <TableCell className={`text-right font-mono ${(entry as any).movement_type === 'Receita' ? 'text-green-600' : 'text-red-600'}`}>
                            {formatCurrency(entry.valor)}
                          </TableCell>
                        </TableRow>
                      ))
                    ) : (
                      <TableRow>
                        <TableCell colSpan={4} className="h-24 text-center">Nenhum lançamento encontrado para o(s) período(s) selecionado(s).</TableCell>
                      </TableRow>
                    )}
                  </TableBody>
                </Table>
              </div>
            </CardContent>
          </Card>

        </div>
      </div>
    </MainLayout>
  );
}
