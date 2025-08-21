'use client';

import { useRef } from 'react';
import {
  Chart as ChartJS,
  CategoryScale,
  LinearScale,
  PointElement,
  LineElement,
  Title,
  Tooltip,
  Legend,
  Filler,
  TooltipItem,
} from 'chart.js';
import { Line } from 'react-chartjs-2';
import { FluxoCaixa } from '@/types';
import { formatCurrency } from '@/lib/utils';

ChartJS.register(
  CategoryScale,
  LinearScale,
  PointElement,
  LineElement,
  Title,
  Tooltip,
  Legend,
  Filler
);

interface FluxoCaixaItem {
  mes: string;
  receitas: number;
  despesas: number;
}

interface FluxoCaixaChartProps {
  data: FluxoCaixaItem[];
}

export default function FluxoCaixaChart({ data }: FluxoCaixaChartProps) {
  const chartRef = useRef<ChartJS<'line'> | null>(null);

  const chartData = {
    labels: data.map(item => item.mes),
    datasets: [
      {
        label: 'Receitas',
        data: data.map(item => item.receitas),
        borderColor: '#10B981',
        backgroundColor: 'rgba(16, 185, 129, 0.1)',
        fill: false,
        tension: 0.4,
      },
      {
        label: 'Despesas',
        data: data.map(item => item.despesas),
        borderColor: '#EF4444',
        backgroundColor: 'rgba(239, 68, 68, 0.1)',
        fill: false,
        tension: 0.4,
      },
      {
        label: 'Saldo',
        data: data.map(item => item.receitas - item.despesas),
        borderColor: '#3B82F6',
        backgroundColor: 'rgba(59, 130, 246, 0.1)',
        fill: true,
        tension: 0.4,
      },
    ],
  };

  const options = {
    responsive: true,
    maintainAspectRatio: false,
    plugins: {
      legend: {
        position: 'top' as const,
      },
      title: {
        display: true,
        text: 'Fluxo de Caixa Mensal',
        font: {
          size: 16,
          weight: 'bold' as const,
        },
      },
      tooltip: {
        callbacks: {
          label: (context: TooltipItem<'line'>) => {
            return `${context.dataset.label}: ${formatCurrency(context.parsed.y)}`;
          },
        },
      },
    },
    scales: {
      y: {
        beginAtZero: true,
        ticks: {
          callback: (value: string | number) => formatCurrency(Number(value)),
        },
      },
    },
  };

  return (
    <div className="h-80">
      <Line ref={chartRef} data={chartData} options={options} />
    </div>
  );
}
