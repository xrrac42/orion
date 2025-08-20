import { useState } from 'react'
import { createClient } from '@supabase/supabase-js'

const supabaseUrl = process.env.NEXT_PUBLIC_SUPABASE_URL as string
const supabaseAnonKey = process.env.NEXT_PUBLIC_SUPABASE_ANON_KEY as string
const supabase = createClient(supabaseUrl, supabaseAnonKey)

interface UploadBalanceteProps {
  clientId: string
  onUpload?: () => void
}

export default function UploadBalancete({ clientId, onUpload }: UploadBalanceteProps) {
  const [file, setFile] = useState<File | null>(null)
  const [uploading, setUploading] = useState(false)
  const [message, setMessage] = useState<string | null>(null)

  const handleFileChange = (e: React.ChangeEvent<HTMLInputElement>) => {
    if (e.target.files && e.target.files.length > 0) {
      setFile(e.target.files[0])
    }
  }

  const handleUpload = async () => {
    if (!file) return
    setUploading(true)
    setMessage('Enviando...')
    const filePath = `public/${clientId}/${file.name}`
    const { error } = await supabase.storage.from('balancetes').upload(filePath, file, { upsert: true })
    if (error) {
      setMessage('Erro ao enviar arquivo: ' + error.message)
    } else {
      setMessage('Processando balancete...')
      if (onUpload) onUpload()
    }
    setUploading(false)
  }

  return (
    <div className="space-y-2">
      <input type="file" accept="application/pdf" onChange={handleFileChange} disabled={uploading} />
      <button onClick={handleUpload} disabled={uploading || !file} className="px-4 py-2 bg-indigo-600 text-white rounded">
        {uploading ? 'Enviando...' : 'Enviar Balancete'}
      </button>
      {message && <div className="text-sm text-gray-600">{message}</div>}
    </div>
  )
}
