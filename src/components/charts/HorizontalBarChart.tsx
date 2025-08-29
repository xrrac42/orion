"use client";

import { useRef, useMemo } from 'react';
import {
  Chart as ChartJS,
  BarElement,
  CategoryScale,
  LinearScale,
  Tooltip,
  Legend,
  Title
} from 'chart.js';
import { Bar } from 'react-chartjs-2';
import { GastoPorCategoria } from '@/types';
import { formatCurrency } from '@/lib/utils';

ChartJS.register(BarElement, CategoryScale, LinearScale, Tooltip, Legend, Title);

interface HorizontalBarChartProps {
  data: GastoPorCategoria[];
  title: string;
}

export default function HorizontalBarChart({ data, title }: HorizontalBarChartProps) {
  const chartRef = useRef<any>(null);

  // dynamic height: 40px per item + padding (clamped)
  const height = Math.min(800, Math.max(200, data.length * 40 + 80));

  const chartData = useMemo(() => ({
    labels: data.map(d => d.categoria),
    datasets: [
      {
        label: title,
        data: data.map(d => Number(d.valor || 0)),
        backgroundColor: data.map(d => d.cor || '#4f46e5'),
        borderColor: data.map(d => d.cor || '#4f46e5'),
        borderWidth: 1
      }
    ]
  }), [data, title]);

  const options = useMemo(() => ({
    indexAxis: 'y' as const,
    responsive: true,
    maintainAspectRatio: false,
    plugins: {
      legend: { display: false },
      title: {
        display: true,
        text: title,
        font: { size: 16, weight: 'bold' as any }
      },
      tooltip: {
        callbacks: {
          label: function(context: any) {
            const value = context.parsed.x ?? context.parsed ?? 0;
            return `${formatCurrency(Number(value || 0))}`;
          }
        }
      }
    },
    scales: {
      x: {
        ticks: {
          callback: function(this: any, value: any) { return value; }
        }
      },
      y: {
        ticks: {
          autoSkip: false
        }
      }
    }
  }), [title]);

  return (
    <div style={{ height, maxHeight: 800, overflowY: 'auto' }}>
      <Bar ref={chartRef} data={chartData} options={options} />
    </div>
  );
}
