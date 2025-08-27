'use client';

import { useState, ChangeEvent } from 'react';
import { Button } from '@/components/ui/Button';
import { Input } from '@/components/ui/Input';

interface UploadBalanceteProps {
  clientId: string;
  onUploadSuccess: () => void;
}

// Componente de Modal Simples
const ConfirmationModal = ({ message, onConfirm, onCancel }: { message: string, onConfirm: () => void, onCancel: () => void }) => (
  <div className="fixed inset-0 bg-black bg-opacity-50 flex justify-center items-center z-50">
    <div className="bg-white p-6 rounded-lg shadow-xl max-w-sm w-full">
      <h3 className="text-lg font-semibold mb-4">Confirmação Necessária</h3>
      <p className="mb-6">{message}</p>
      <div className="flex justify-end space-x-4">
        <Button onClick={onCancel} variant="outline">Cancelar</Button>
        <Button onClick={onConfirm}>Sim, Sobrescrever</Button>
      </div>
    </div>
  </div>
);


export default function UploadBalancete({ clientId, onUploadSuccess }: UploadBalanceteProps) {
  const [file, setFile] = useState<File | null>(null);
  const [ano, setAno] = useState<number>(new Date().getFullYear());
  const [mes, setMes] = useState<number>(new Date().getMonth() + 1);
  const [isLoading, setIsLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [showConfirmModal, setShowConfirmModal] = useState(false);

  const handleFileChange = (e: ChangeEvent<HTMLInputElement>) => {
    if (e.target.files) {
      setFile(e.target.files[0]);
    }
  };

  const proceedWithUpload = async (overwrite = false) => {
    if (!file) {
      setError('Por favor, selecione um arquivo.');
      return;
    }
    setIsLoading(true);
    setError(null);
    setShowConfirmModal(false);

    const formData = new FormData();
    formData.append('client_id', clientId);
    formData.append('ano', String(ano));
    formData.append('mes', String(mes));
    formData.append('file', file);
    formData.append('overwrite', String(overwrite));

    try {
      // Usar a URL completa do seu backend. Ajuste se necessário.
      const response = await fetch('http://127.0.0.1:8000/api/balancetes/upload', {
        method: 'POST',
        body: formData,
      });

      if (!response.ok) {
        const errorData = await response.json();
        throw new Error(errorData.detail || 'Falha no upload do arquivo.');
      }

      // Sucesso
      alert('Upload realizado com sucesso!');
      onUploadSuccess();
      setFile(null); 
      // Reseta o input de arquivo
      const fileInput = document.getElementById('file') as HTMLInputElement;
      if (fileInput) fileInput.value = '';


    } catch (err: any) {
      setError(err.message);
    } finally {
      setIsLoading(false);
    }
  };

  const handleUpload = async () => {
    if (!file) {
      setError('Por favor, selecione um arquivo.');
      return;
    }
    
    setIsLoading(true);
    setError(null);

    try {
      // 1. Verifica se já existe um balancete para este período
      const checkResponse = await fetch(`http://127.0.0.1:8000/api/balancetes/check?client_id=${clientId}&ano=${ano}&mes=${mes}`);
      
      if (!checkResponse.ok) {
          throw new Error('Não foi possível verificar o balancete. Tente novamente.');
      }
      
      const { exists } = await checkResponse.json();

      if (exists) {
        // 2. Se existir, mostra o modal de confirmação
        setShowConfirmModal(true);
      } else {
        // 3. Se não existir, faz o upload direto
        await proceedWithUpload(false);
      }
    } catch (err: any) {
      setError(err.message);
    } finally {
      setIsLoading(false);
    }
  };

  return (
    <div className="p-4 border rounded-lg bg-gray-50">
      <h3 className="text-lg font-semibold mb-4">Enviar Novo Balancete</h3>
      <div className="space-y-4">
        <div className="grid grid-cols-2 gap-4">
          <div>
            <label htmlFor="ano" className="block text-sm font-medium text-gray-700">Ano</label>
            <Input
              id="ano"
              type="number"
              value={ano}
              onChange={(e) => setAno(Number(e.target.value))}
              placeholder="AAAA"
            />
          </div>
          <div>
            <label htmlFor="mes" className="block text-sm font-medium text-gray-700">Mês</label>
            <Input
              id="mes"
              type="number"
              value={mes}
              onChange={(e) => setMes(Number(e.target.value))}
              placeholder="MM"
              min="1"
              max="12"
            />
          </div>
        </div>
        <div>
          <label htmlFor="file" className="block text-sm font-medium text-gray-700">Arquivo PDF</label>
          <Input
            id="file"
            type="file"
            onChange={handleFileChange}
            accept=".pdf"
          />
        </div>
        <Button onClick={handleUpload} disabled={isLoading || !file}>
          {isLoading ? 'Enviando...' : 'Enviar Arquivo'}
        </Button>
        {error && <p className="text-sm text-red-600">{error}</p>}
      </div>

      {showConfirmModal && (
        <ConfirmationModal
          message="Já existe um balancete registrado para este período. Deseja sobrescrever com o novo arquivo?"
          onConfirm={() => proceedWithUpload(true)}
          onCancel={() => {
              setShowConfirmModal(false);
              setIsLoading(false);
          }}
        />
      )}
    </div>
  );
}
