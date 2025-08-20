import { ResponsiveBar } from '@nivo/bar';

interface BarChartProps {
  data: { name: string; value: number; tipo: string }[];
}

export function BarChart({ data }: BarChartProps) {
  if (!data || data.length === 0) return <div className="text-center text-gray-400">Sem dados</div>;
  return (
    <div style={{ height: 300 }}>
      <ResponsiveBar
        data={data}
        keys={['value']}
        indexBy="name"
        margin={{ top: 20, right: 30, bottom: 60, left: 60 }}
        padding={0.3}
        colors={({ data }) => data.tipo === 'Receita' ? '#4f46e5' : '#f87171'}
        axisBottom={{ tickRotation: 30 }}
        axisLeft={{ legend: 'Valor', legendPosition: 'middle', legendOffset: -40 }}
        labelSkipWidth={12}
        labelSkipHeight={12}
        labelTextColor="#fff"
        tooltip={({ id, value, indexValue }) => (
          <strong>{indexValue}: {value}</strong>
        )}
      />
    </div>
  );
}
