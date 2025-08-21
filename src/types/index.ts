export interface Cliente {
  id: string;
  nome: string;
  cnpj: string;
  contato: string;
  email: string;
  telefone: string;
  created_at: string;
  updated_at: string;
}

export interface Balancete {
  id: number;
  client_id: string;
  ano: number;
  mes: number;
  total_receitas: number;
  total_despesas: number;
  lucro_bruto: number;
  created_at?: string;
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
  total_receitas: number;
  total_despesas: number;
  lucro_bruto: number;
  total_lancamentos: number;
  receitas_operacionais: number;
  receitas_financeiras: number;
  custos_operacionais: number;
  despesas_operacionais: number;
}

export interface ContaDetalhada {
  conta: string;
  valor: number;
  percentual_categoria?: number;
  percentual_subgrupo?: number;
}

export interface GastoPorCategoria {
  categoria: string;
  valor: number;
  percentual: number;
  cor: string;
  contas_detalhadas: ContaDetalhada[];
}

export interface SubgrupoAnalise {
  nome: string;
  total: number;
  percentual_grupo: number;
  contas: ContaDetalhada[];
}

export interface GrupoAnalise {
  total: number;
  subgrupos: SubgrupoAnalise[];
}

export interface AnaliseDetalhada {
  receitas: GrupoAnalise;
  custos_despesas: GrupoAnalise;
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
