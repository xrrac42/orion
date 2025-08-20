'use client';

import { useRef } from 'react';
import {
  Chart as ChartJS,
  ArcElement,
  Tooltip,
  Legend,
  TooltipItem,
} from 'chart.js';
import { Doughnut } from 'react-chartjs-2';
import { GastoPorCategoria } from '@/types';
import { formatCurrency } from '@/lib/utils';

ChartJS.register(ArcElement, Tooltip, Legend);

interface PieChartProps {
  data: GastoPorCategoria[];
  title: string;
}

export default function PieChart({ data, title }: PieChartProps) {
  const chartRef = useRef<ChartJS<'doughnut'> | null>(null);

  const chartData = {
    labels: data.map(item => item.categoria),
    datasets: [
      {
        data: data.map(item => item.valor),
        backgroundColor: data.map(item => item.cor),
        borderColor: data.map(item => item.cor),
        borderWidth: 2,
        hoverBorderWidth: 3,
      },
    ],
  };

  const options = {
    responsive: true,
    maintainAspectRatio: false,
    plugins: {
      legend: {
        position: 'bottom' as const,
        labels: {
          padding: 20,
          usePointStyle: true,
          font: {
            size: 12,
          },
        },
      },
      title: {
        display: true,
        text: title,
        font: {
          size: 16,
          weight: 'bold' as const,
        },
        padding: {
          bottom: 20,
        },
      },
      tooltip: {
        callbacks: {
          label: (context: TooltipItem<'doughnut'>) => {
            const label = context.label || '';
            const value = formatCurrency(context.parsed);
            const percentage = data[context.dataIndex]?.percentual.toFixed(1);
            return `${label}: ${value} (${percentage}%)`;
          },
        },
      },
    },
    cutout: '50%',
  };

  return (
    <div className="h-80">
      <Doughnut ref={chartRef} data={chartData} options={options} />
    </div>
  );
}
