"use client";

import { useState, useEffect } from 'react';
import { useParams } from 'next/navigation';
import MainLayout from '@/components/layout/MainLayout';
import { Card, CardContent, CardHeader, CardTitle } from '@/components/ui/Card';
import { Button } from '@/components/ui/Button';
import { Input } from '@/components/ui/Input';
import Link from 'next/link';
import { formatCurrency } from '@/lib/utils';
import { 
  ArrowLeftIcon, 
  ArrowTrendingUpIcon, 
  ArrowTrendingDownIcon, 
  BanknotesIcon,
  MagnifyingGlassIcon,
  CalendarIcon
} from '@heroicons/react/24/outline';

// Interfaces para tipagem
interface Cliente {
  id: string;
  nome: string;
  email?: string;
}

interface Balancete {
  id: string;
  ano: number;
  mes: number;
  status: string;
}

interface FinancialEntry {
  id: number;
  client_id: string;
  report_date: string;
  main_group: string;
  subgroup_1: string;
  specific_account: string;
  movement_type: 'Receita' | 'Despesa';
  period_value: number;
}

interface KPIData {
  receita_total: number;
  despesa_total: number;
  resultado_periodo: number;
}

interface ReceitaComposicao {
  subgrupo: string;
  valor: number;
  percentual: number;
}

interface DespesaPrincipal {
  subgrupo: string;
  valor: number;
}

interface ContaDetalhe {
  conta: string;
  valor: number;
  subgrupo: string;
}

export default function DashboardFinanceiro() {
  const params = useParams();
  const clienteId = params.id as string;
  
  // Estados
  const [loading, setLoading] = useState(true);
  const [cliente, setCliente] = useState<Cliente | null>(null);
  const [balancetes, setBalancetes] = useState<Balancete[]>([]);
  const [selectedBalanceteId, setSelectedBalanceteId] = useState<string>('');
  const [selectedBalancete, setSelectedBalancete] = useState<Balancete | null>(null);
  const [kpiData, setKpiData] = useState<KPIData | null>(null);
  const [receitasComposicao, setReceitasComposicao] = useState<ReceitaComposicao[]>([]);
  const [despesasPrincipais, setDespesasPrincipais] = useState<DespesaPrincipal[]>([]);
  const [contasDetalhes, setContasDetalhes] = useState<ContaDetalhe[]>([]);
  const [contasFiltered, setContasFiltered] = useState<ContaDetalhe[]>([]);
  const [filtroSubgrupo, setFiltroSubgrupo] = useState<string>('');
  const [buscaConta, setBuscaConta] = useState<string>('');

  // Funções utilitárias
  const formatMonth = (mes: number, ano: number) => {
    const meses = ['Janeiro', 'Fevereiro', 'Março', 'Abril', 'Maio', 'Junho',
                   'Julho', 'Agosto', 'Setembro', 'Outubro', 'Novembro', 'Dezembro'];
    return `${meses[mes - 1]} de ${ano}`;
  };

  const formatPeriod = (balancete: Balancete) => {
    const lastDay = new Date(balancete.ano, balancete.mes, 0).getDate();
    return `01/${balancete.mes.toString().padStart(2, '0')}/${balancete.ano} a ${lastDay}/${balancete.mes.toString().padStart(2, '0')}/${balancete.ano}`;
  };

  // Carregar dados iniciais
  useEffect(() => {
    async function fetchData() {
      try {
        setLoading(true);
        
        // Buscar cliente
        const clienteRes = await fetch(`http://localhost:8000/api/clientes/${clienteId}`);
        const clienteData = await clienteRes.json();
        setCliente(clienteData);

        // Buscar balancetes
        const balancetesRes = await fetch(`http://localhost:8000/api/balancetes/cliente/${clienteId}`);
        const balancetesData = await balancetesRes.json();
        setBalancetes(balancetesData);
        
        if (balancetesData.length > 0) {
          setSelectedBalanceteId(balancetesData[0].id);
          setSelectedBalancete(balancetesData[0]);
        }
      } catch (error) {
        console.error('Erro ao carregar dados:', error);
      } finally {
        setLoading(false);
      }
    }

    if (clienteId) {
      fetchData();
    }
  }, [clienteId]);

  // Carregar dados do balancete selecionado
  useEffect(() => {
    async function fetchBalanceteData() {
      if (!selectedBalanceteId) return;

      try {
        setLoading(true);

        // Buscar entradas financeiras
        const entriesRes = await fetch(`http://localhost:8000/api/financial-entries?client_id=${clienteId}&balancete_id=${selectedBalanceteId}`);
        const entries: FinancialEntry[] = await entriesRes.json();

        // Calcular KPIs
        const receitas = entries.filter(e => e.movement_type === 'Receita');
        const despesas = entries.filter(e => e.movement_type === 'Despesa');
        
        const receita_total = receitas.reduce((sum, e) => sum + e.period_value, 0);
        const despesa_total = despesas.reduce((sum, e) => sum + e.period_value, 0);
        
        setKpiData({
          receita_total,
          despesa_total,
          resultado_periodo: receita_total - despesa_total
        });

        // Calcular composição das receitas
        const receitasAgrupadas = receitas.reduce((acc, entry) => {
          const subgrupo = entry.subgroup_1;
          if (!acc[subgrupo]) {
            acc[subgrupo] = 0;
          }
          acc[subgrupo] += entry.period_value;
          return acc;
        }, {} as Record<string, number>);

        const receitasComposicaoData = Object.entries(receitasAgrupadas).map(([subgrupo, valor]) => ({
          subgrupo,
          valor,
          percentual: receita_total > 0 ? (valor / receita_total) * 100 : 0
        }));
        setReceitasComposicao(receitasComposicaoData);

        // Calcular principais despesas
        const despesasAgrupadas = despesas.reduce((acc, entry) => {
          const subgrupo = entry.subgroup_1;
          if (!acc[subgrupo]) {
            acc[subgrupo] = 0;
          }
          acc[subgrupo] += entry.period_value;
          return acc;
        }, {} as Record<string, number>);

        const despesasPrincipaisData = Object.entries(despesasAgrupadas)
          .map(([subgrupo, valor]) => ({ subgrupo, valor }))
          .sort((a, b) => b.valor - a.valor);
        setDespesasPrincipais(despesasPrincipaisData);

        // Preparar detalhes das contas (apenas despesas)
        const contasDetalhesData = despesas.map(entry => ({
          conta: entry.specific_account,
          valor: entry.period_value,
          subgrupo: entry.subgroup_1
        }));
        setContasDetalhes(contasDetalhesData);
        setContasFiltered(contasDetalhesData);

      } catch (error) {
        console.error('Erro ao carregar dados do balancete:', error);
      } finally {
        setLoading(false);
      }
    }

    fetchBalanceteData();
  }, [selectedBalanceteId, clienteId]);

  // Filtrar contas por subgrupo
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

  // Componente de Loading
  if (loading) {
    return (
      <MainLayout>
        <div className="py-6">
          <div className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8">
            <div className="animate-pulse">
              <div className="h-8 bg-gray-200 rounded w-1/2 mb-6"></div>
              <div className="grid grid-cols-1 md:grid-cols-3 gap-6 mb-8">
                {[1, 2, 3].map(i => (
                  <div key={i} className="h-32 bg-gray-200 rounded"></div>
                ))}
              </div>
              <div className="grid grid-cols-1 lg:grid-cols-2 gap-8">
                <div className="h-80 bg-gray-200 rounded"></div>
                <div className="h-80 bg-gray-200 rounded"></div>
              </div>
            </div>
          </div>
        </div>
      </MainLayout>
    );
  }

  // Se não há cliente ou balancetes
  if (!cliente || !balancetes.length) {
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
                <h1 className="text-3xl font-bold text-gray-900">
                  {cliente?.nome || 'Cliente não encontrado'}
                </h1>
              </div>
            </div>
            
            {!balancetes.length && (
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
            )}
          </div>
        </div>
      </MainLayout>
    );
  }

  return (
    <MainLayout>
      <div className="py-6">
        <div className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8">
          
          {/* COMPONENTE 1: Cabeçalho Dinâmico */}
          <div className="mb-8 flex items-center justify-between">
            <div className="flex items-center">
              <Link href="/clientes">
                <Button variant="ghost" size="sm" className="mr-4">
                  <ArrowLeftIcon className="h-4 w-4 mr-2" />
                  Voltar
                </Button>
              </Link>
              <div>
                <h1 className="text-3xl font-bold text-gray-900">
                  Dashboard Financeiro: {cliente.nome}
                </h1>
                <p className="mt-2 text-gray-600">
                  Período: {selectedBalancete ? formatPeriod(selectedBalancete) : ''}
                </p>
              </div>
            </div>

            {/* Seletor de Balancete */}
            {balancetes.length > 1 && (
              <div className="flex items-center space-x-2">
                <CalendarIcon className="h-5 w-5 text-gray-400" />
                <select
                  value={selectedBalanceteId}
                  onChange={(e) => {
                    setSelectedBalanceteId(e.target.value);
                    const balancete = balancetes.find(b => b.id === e.target.value);
                    setSelectedBalancete(balancete || null);
                  }}
                  className="rounded-md border border-gray-300 px-3 py-2 text-sm focus:border-blue-500 focus:ring-blue-500"
                >
                  {balancetes.map((balancete) => (
                    <option key={balancete.id} value={balancete.id}>
                      {formatMonth(balancete.mes, balancete.ano)}
                    </option>
                  ))}
                </select>
              </div>
            )}
          </div>

          {/* COMPONENTE 2: Cartões de KPIs (Indicadores Chave) */}
          <div className="mb-8">
            <h2 className="text-xl font-semibold text-gray-900 mb-4">Resumo do Período</h2>
            <div className="grid grid-cols-1 md:grid-cols-3 gap-6">
              {/* Cartão 1: Receita Total */}
              <Card className="border-l-4 border-green-500">
                <CardContent className="p-6">
                  <div className="flex items-center justify-between">
                    <div>
                      <p className="text-sm font-medium text-gray-500">Receita Total</p>
                      <p className="text-3xl font-bold text-green-600">
                        {formatCurrency(kpiData?.receita_total || 0)}
                      </p>
                    </div>
                    <ArrowTrendingUpIcon className="h-12 w-12 text-green-500" />
                  </div>
                </CardContent>
              </Card>

              {/* Cartão 2: Despesa Total */}
              <Card className="border-l-4 border-red-500">
                <CardContent className="p-6">
                  <div className="flex items-center justify-between">
                    <div>
                      <p className="text-sm font-medium text-gray-500">Despesa Total</p>
                      <p className="text-3xl font-bold text-red-600">
                        {formatCurrency(kpiData?.despesa_total || 0)}
                      </p>
                    </div>
                    <ArrowTrendingDownIcon className="h-12 w-12 text-red-500" />
                  </div>
                </CardContent>
              </Card>

              {/* Cartão 3: Resultado do Período */}
              <Card className={`border-l-4 ${(kpiData?.resultado_periodo || 0) >= 0 ? 'border-green-500' : 'border-red-500'}`}>
                <CardContent className="p-6">
                  <div className="flex items-center justify-between">
                    <div>
                      <p className="text-sm font-medium text-gray-500">Resultado do Período</p>
                      <p className={`text-3xl font-bold ${(kpiData?.resultado_periodo || 0) >= 0 ? 'text-green-600' : 'text-red-600'}`}>
                        {formatCurrency(kpiData?.resultado_periodo || 0)}
                      </p>
                      <p className="text-sm text-gray-500 mt-1">
                        {(kpiData?.resultado_periodo || 0) >= 0 ? 'Lucro' : 'Prejuízo'}
                      </p>
                    </div>
                    <BanknotesIcon className={`h-12 w-12 ${(kpiData?.resultado_periodo || 0) >= 0 ? 'text-green-500' : 'text-red-500'}`} />
                  </div>
                </CardContent>
              </Card>
            </div>
          </div>

          {/* SEÇÃO B: Análise Detalhada de Contas */}
          <div className="grid grid-cols-1 lg:grid-cols-2 gap-8 mb-8">
            
            {/* COMPONENTE 3: Gráfico de Composição das Receitas */}
            <Card>
              <CardHeader>
                <CardTitle className="text-green-700">De Onde Vieram suas Receitas?</CardTitle>
              </CardHeader>
              <CardContent>
                {receitasComposicao.length > 0 ? (
                  <div className="space-y-4">
                    {receitasComposicao.map((receita, index) => (
                      <div key={index} className="flex items-center justify-between p-4 bg-green-50 rounded-lg">
                        <div>
                          <h4 className="font-medium text-green-800">{receita.subgrupo}</h4>
                          <p className="text-sm text-green-600">{receita.percentual.toFixed(1)}% do total</p>
                        </div>
                        <div className="text-right">
                          <p className="text-lg font-bold text-green-900">
                            {formatCurrency(receita.valor)}
                          </p>
                        </div>
                      </div>
                    ))}
                  </div>
                ) : (
                  <div className="text-center py-8 text-gray-500">
                    Nenhuma receita encontrada
                  </div>
                )}
              </CardContent>
            </Card>

            {/* COMPONENTE 4: Gráfico de Principais Despesas */}
            <Card>
              <CardHeader>
                <CardTitle className="text-red-700">Para Onde Foi seu Dinheiro?</CardTitle>
              </CardHeader>
              <CardContent>
                {despesasPrincipais.length > 0 ? (
                  <div className="space-y-3">
                    {despesasPrincipais.map((despesa, index) => (
                      <div 
                        key={index} 
                        className="cursor-pointer hover:bg-red-50 p-3 rounded-lg transition-colors"
                        onClick={() => setFiltroSubgrupo(filtroSubgrupo === despesa.subgrupo ? '' : despesa.subgrupo)}
                      >
                        <div className="flex items-center justify-between">
                          <h4 className="font-medium text-red-800 truncate">{despesa.subgrupo}</h4>
                          <p className="text-lg font-bold text-red-900 ml-4">
                            {formatCurrency(despesa.valor)}
                          </p>
                        </div>
                        <div className="mt-2">
                          <div className="w-full bg-red-200 rounded-full h-2">
                            <div 
                              className="bg-red-600 h-2 rounded-full" 
                              style={{ 
                                width: `${kpiData?.despesa_total ? (despesa.valor / kpiData.despesa_total) * 100 : 0}%` 
                              }}
                            ></div>
                          </div>
                        </div>
                        {filtroSubgrupo === despesa.subgrupo && (
                          <p className="text-xs text-red-600 mt-1">
                            Clique novamente para ver todas as contas
                          </p>
                        )}
                      </div>
                    ))}
                  </div>
                ) : (
                  <div className="text-center py-8 text-gray-500">
                    Nenhuma despesa encontrada
                  </div>
                )}
              </CardContent>
            </Card>
          </div>

          {/* COMPONENTE 5: Tabela de Detalhes de Despesas */}
          <Card>
            <CardHeader>
              <CardTitle>Detalhes por Conta</CardTitle>
              <div className="flex items-center space-x-4 mt-4">
                <div className="relative flex-1">
                  <MagnifyingGlassIcon className="h-4 w-4 absolute left-3 top-1/2 transform -translate-y-1/2 text-gray-400" />
                  <Input
                    placeholder="Buscar conta..."
                    value={buscaConta}
                    onChange={(e) => setBuscaConta(e.target.value)}
                    className="pl-10"
                  />
                </div>
                {filtroSubgrupo && (
                  <Button 
                    variant="outline" 
                    size="sm"
                    onClick={() => setFiltroSubgrupo('')}
                  >
                    Limpar Filtro: {filtroSubgrupo}
                  </Button>
                )}
              </div>
            </CardHeader>
            <CardContent>
              {contasFiltered.length > 0 ? (
                <div className="overflow-x-auto">
                  <table className="min-w-full divide-y divide-gray-200">
                    <thead className="bg-gray-50">
                      <tr>
                        <th className="px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase tracking-wider">
                          Conta
                        </th>
                        <th className="px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase tracking-wider">
                          Categoria
                        </th>
                        <th className="px-6 py-3 text-right text-xs font-medium text-gray-500 uppercase tracking-wider">
                          Valor
                        </th>
                      </tr>
                    </thead>
                    <tbody className="bg-white divide-y divide-gray-200">
                      {contasFiltered
                        .sort((a, b) => b.valor - a.valor)
                        .map((conta, index) => (
                        <tr key={index} className="hover:bg-gray-50">
                          <td className="px-6 py-4 whitespace-nowrap text-sm text-gray-900">
                            {conta.conta}
                          </td>
                          <td className="px-6 py-4 whitespace-nowrap text-sm text-gray-500">
                            {conta.subgrupo}
                          </td>
                          <td className="px-6 py-4 whitespace-nowrap text-sm font-medium text-right text-red-600">
                            {formatCurrency(conta.valor)}
                          </td>
                        </tr>
                      ))}
                    </tbody>
                  </table>
                  <div className="mt-4 text-sm text-gray-500 text-center">
                    Mostrando {contasFiltered.length} conta(s)
                    {filtroSubgrupo && ` em ${filtroSubgrupo}`}
                  </div>
                </div>
              ) : (
                <div className="text-center py-8 text-gray-500">
                  {buscaConta || filtroSubgrupo ? 'Nenhuma conta encontrada com os filtros aplicados' : 'Nenhuma conta encontrada'}
                </div>
              )}
            </CardContent>
          </Card>

          {/* COMPONENTE 6: Nota sobre Evolução Mensal (Visão Futura) */}
          <Card className="mt-8">
            <CardContent className="text-center py-8">
              <div className="text-blue-600 mb-4">
                <svg className="mx-auto h-12 w-12" fill="none" viewBox="0 0 24 24" stroke="currentColor">
                  <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M9 19v-6a2 2 0 00-2-2H5a2 2 0 00-2 2v6a2 2 0 002 2h2a2 2 0 002-2zm0 0V9a2 2 0 012-2h2a2 2 0 012 2v10m-6 0a2 2 0 002 2h2a2 2 0 002-2m0 0V5a2 2 0 012-2h2a2 2 0 012 2v14a2 2 0 01-2 2h-2a2 2 0 01-2-2z" />
                </svg>
              </div>
              <h3 className="text-lg font-medium text-gray-900 mb-2">
                Evolução Mensal
              </h3>
              <p className="text-gray-600 mb-4">
                Envie mais balancetes para visualizar a evolução de suas receitas e despesas ao longo do tempo.
              </p>
              <Link href={`/clientes/${clienteId}/balancetes`}>
                <Button>Gerenciar Balancetes</Button>
              </Link>
            </CardContent>
          </Card>

        </div>
      </div>
    </MainLayout>
  );
}
