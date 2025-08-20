import { useState } from 'react';

interface DateRangePickerProps {
  value: { startDate: string; endDate: string } | null;
  onChange: (range: { startDate: string; endDate: string } | null) => void;
}

export function DateRangePicker({ value, onChange }: DateRangePickerProps) {
  const [start, setStart] = useState(value?.startDate || '');
  const [end, setEnd] = useState(value?.endDate || '');

  const handleChange = (type: 'start' | 'end', val: string) => {
    if (type === 'start') setStart(val);
    else setEnd(val);
    if (val && (type === 'start' ? end : start)) {
      onChange({ startDate: type === 'start' ? val : start, endDate: type === 'end' ? val : end });
    }
  };

  return (
    <div className="flex items-center gap-2">
      <input
        type="date"
        value={start}
        onChange={e => handleChange('start', e.target.value)}
        className="border rounded px-2 py-1"
      />
      <span className="mx-1">até</span>
      <input
        type="date"
        value={end}
        onChange={e => handleChange('end', e.target.value)}
        className="border rounded px-2 py-1"
      />
      <button
        className="ml-2 px-2 py-1 bg-gray-200 rounded"
        onClick={() => { setStart(''); setEnd(''); onChange(null); }}
      >Limpar</button>
    </div>
  );
}
