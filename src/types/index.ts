export interface Cliente {
  id: string;
  nome: string;
  cnpj: string;
  contato: string;
  email: string;
  telefone: string;
  createdAt: Date;
  updatedAt: Date;
}

export interface Balancete {
  id: string;
  clienteId: string;
  mes: number;
  ano: number;
  arquivo: string;
  dataUpload: Date;
  tamanhoArquivo: number;
  processado: boolean;
}

export interface LancamentoContabil {
  id: string;
  balanceteId: string;
  descricao: string;
  saldoAnterior: number;
  debito: number;
  credito: number;
  saldoAtual: number;
  categoria: string;
  subcategoria?: string;
  data: Date;
}

export interface ResumoFinanceiro {
  totalGasto: number;
  totalReceita: number;
  lucro: number;
  totalAtivo: number;
  totalPassivo: number;
  totalDespesa: number;
}

export interface GastoPorCategoria {
  categoria: string;
  valor: number;
  percentual: number;
  cor: string;
}

export interface FormaPagamento {
  tipo: string;
  valor: number;
  percentual: number;
  cor: string;
}

export interface FluxoCaixa {
  data: Date;
  entradas: number;
  saidas: number;
  saldo: number;
}

export interface MotivoGasto {
  motivo: string;
  valor: number;
  percentual: number;
}

export interface User {
  id: string;
  email: string;
  nome: string;
  empresa: string;
  role: 'admin' | 'user';
}
