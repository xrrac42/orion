import { useState } from 'react'

interface UploadBalanceteProps {
  clientId: string
  onUpload?: () => void
}

export default function UploadBalancete({ clientId, onUpload }: UploadBalanceteProps) {
  const [file, setFile] = useState<File | null>(null)
  const [uploading, setUploading] = useState(false)
  const [message, setMessage] = useState<string | null>(null)
  const [mes, setMes] = useState('')
  const [ano, setAno] = useState('')

  const handleFileChange = (e: React.ChangeEvent<HTMLInputElement>) => {
    if (e.target.files && e.target.files.length > 0) {
      setFile(e.target.files[0])
    }
  }

  const handleUpload = async () => {
    if (!file || !mes || !ano) {
      setMessage('Selecione o arquivo, mês e ano!')
      return
    }
    setUploading(true)
    setMessage('Enviando...')
    const formData = new FormData();
    formData.append('file', file);
    formData.append('client_id', clientId);
    formData.append('ano', ano);
    formData.append('mes', mes);
    // Enviar para o backend (rota atualizada /upload)
    const res = await fetch('http://localhost:8000/api/balancetes/upload', {
      method: 'POST',
      body: formData
    });
    if (!res.ok) {
      let err = 'Erro ao registrar balancete no backend';
      try { const j = await res.json(); if (j && j.detail) err = j.detail; } catch(_) {}
      setMessage(err);
      setUploading(false);
      return;
    }
    const json = await res.json();
    setMessage(json.message || 'Processando balancete...');
    if (onUpload) onUpload();
    setUploading(false);
    setFile(null);
    setMes('');
    setAno('');
  }

  return (
    <div className="space-y-4">
      <div>
        <label className="block text-sm font-medium text-gray-700 mb-1">Arquivo PDF do Balancete</label>
        <input
          type="file"
          accept="application/pdf"
          onChange={handleFileChange}
          disabled={uploading}
          className="w-full text-sm text-gray-500 file:mr-4 file:py-2 file:px-4 file:rounded-md file:border-0 file:text-sm file:font-semibold file:bg-blue-50 file:text-blue-700 hover:file:bg-blue-100"
        />
        {file && (
          <div className="mt-1 text-xs text-gray-600">Selecionado: {file.name} ({(file.size/1024).toFixed(1)} KB)</div>
        )}
      </div>
      <div className="flex gap-2">
        <select value={mes} onChange={e => setMes(e.target.value)} disabled={uploading} className="border rounded px-2 py-1">
          <option value="">Mês</option>
          {Array.from({ length: 12 }, (_, i) => (
            <option key={i+1} value={i+1}>{i+1}</option>
          ))}
        </select>
        <select value={ano} onChange={e => setAno(e.target.value)} disabled={uploading} className="border rounded px-2 py-1">
          <option value="">Ano</option>
          {Array.from({ length: 5 }, (_, i) => {
            const y = new Date().getFullYear() - i;
            return <option key={y} value={y}>{y}</option>
          })}
        </select>
      </div>
      <button onClick={handleUpload} disabled={uploading || !file || !mes || !ano} className="px-4 py-2 bg-indigo-600 text-white rounded w-full">
        {uploading ? 'Enviando...' : 'Enviar Balancete'}
      </button>
      {message && <div className="text-sm text-gray-600">{message}</div>}
    </div>
  )
}
