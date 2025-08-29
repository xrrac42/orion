'use client';

import { useEffect, useState } from 'react';
import { useParams } from 'next/navigation';
// import { getDashboardData } from '@/lib/services/supabaseService';
import { Card } from '@/components/ui/Card';
import { BarChart } from '@/components/charts/BarChart';
import PieChart from '@/components/charts/PieChart';

// Ajuste os tipos conforme o backend e os gráficos
import { GastoPorCategoria } from '@/types';

interface KpiData {
  receita_total: number;
  despesa_total: number;
  resultado_periodo: number;
}

interface DashboardData {
  cliente: string;
  periodo: string;
  kpis: KpiData;
  grafico_despesas: { categoria: string; valor: number; }[];
  grafico_receitas: { categoria: string; valor: number; }[];
}

export default function DashboardPage() {
  const params = useParams();
  const analysisId = params.analysisId as string;

  const [data, setData] = useState<DashboardData | null>(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    setLoading(false);
    setError('Função getDashboardData não implementada neste projeto. Implemente a busca dos dados do dashboard.');
  }, []);


  if (loading) {
    return (
      <div className="py-6">
        <div className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8">
          <div className="grid grid-cols-1 md:grid-cols-2 gap-6">
            {[...Array(4)].map((_, i) => (
              <div key={i} className="p-4 bg-gray-200 rounded animate-pulse h-24"></div>
            ))}
          </div>
        </div>
      </div>
    );
  }
  if (error) return <p>Erro ao carregar dados: {error}</p>;
  if (!data) return <p>Nenhum dado encontrado para este balancete.</p>;


  const { receita_total, despesa_total, resultado_periodo } = data.kpis;

  // Mapear dados para o formato esperado pelos gráficos
  const barChartData = data.grafico_despesas.map(item => ({
    name: item.categoria,
    value: item.valor,
    tipo: 'Despesa',
  }));
  // PieChart espera GastoPorCategoria[] (categoria, valor, percentual, cor, contas_detalhadas)
  // Aqui usamos cor padrão e percentual fictício para não quebrar
  const pieChartData: GastoPorCategoria[] = data.grafico_receitas.map(item => ({
    categoria: item.categoria,
    valor: item.valor,
    percentual: 0,
    cor: '#4f46e5',
    contas_detalhadas: [],
  }));

  return (
    <div className="container mx-auto p-4">
      <h1 className="text-2xl font-bold mb-2">Dashboard Financeiro: {data.cliente}</h1>
      <p className="text-gray-600 mb-6">Período: {data.periodo}</p>

      <div className="grid grid-cols-1 md:grid-cols-3 gap-4 mb-8">
        <Card title="Receita Total">
          <span className="text-2xl font-bold text-green-700">R$ {receita_total?.toLocaleString('pt-BR', { minimumFractionDigits: 2 })}</span>
        </Card>
        <Card title="Despesa Total">
          <span className="text-2xl font-bold text-red-700">R$ {despesa_total?.toLocaleString('pt-BR', { minimumFractionDigits: 2 })}</span>
        </Card>
        <Card title="Resultado do Período">
          <span className={`text-2xl font-bold ${resultado_periodo >= 0 ? 'text-green-700' : 'text-red-700'}`}>R$ {resultado_periodo?.toLocaleString('pt-BR', { minimumFractionDigits: 2 })}</span>
        </Card>
      </div>

      <div className="grid grid-cols-1 lg:grid-cols-2 gap-8">
        <div>
          <h2 className="text-xl font-semibold mb-4">De Onde Vieram suas Receitas?</h2>
          <PieChart data={pieChartData} title="Receitas" />
        </div>
        <div>
          <h2 className="text-xl font-semibold mb-4">Para Onde Foi seu Dinheiro?</h2>
          <BarChart data={barChartData} />
        </div>
      </div>
      {/* ... O resto da sua página, como a tabela de detalhes ... */}
    </div>
  );
}
