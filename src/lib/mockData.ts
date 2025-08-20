import { Cliente, Balancete, LancamentoContabil, ResumoFinanceiro, GastoPorCategoria, FormaPagamento, FluxoCaixa, MotivoGasto } from '@/types';

export const mockClientes: Cliente[] = [
  {
    id: '1',
    nome: 'MONTADORA ESTILO EVENTOS LTDA',
    cnpj: '12.345.678/0001-90',
    contato: 'João Silva',
    email: 'joao@montadoraestilo.com.br',
    telefone: '(11) 98765-4321',
    createdAt: new Date('2024-01-15'),
    updatedAt: new Date('2025-01-20')
  },
  {
    id: '2',
    nome: 'TECH SOLUTIONS LTDA',
    cnpj: '98.765.432/0001-10',
    contato: 'Maria Santos',
    email: 'maria@techsolutions.com.br',
    telefone: '(11) 91234-5678',
    createdAt: new Date('2024-03-10'),
    updatedAt: new Date('2025-01-18')
  },
  {
    id: '3',
    nome: 'COMERCIAL NOVA ERA LTDA',
    cnpj: '11.222.333/0001-44',
    contato: 'Pedro Oliveira',
    email: 'pedro@novaera.com.br',
    telefone: '(11) 99988-7766',
    createdAt: new Date('2024-02-20'),
    updatedAt: new Date('2025-01-15')
  }
];

export const mockBalancetes: Balancete[] = [
  {
    id: '1',
    clienteId: '1',
    mes: 1,
    ano: 2025,
    arquivo: 'balancete-jan-2025.pdf',
    dataUpload: new Date('2025-02-05'),
    tamanhoArquivo: 2048576, // 2MB
    processado: true
  },
  {
    id: '2',
    clienteId: '1',
    mes: 12,
    ano: 2024,
    arquivo: 'balancete-dez-2024.pdf',
    dataUpload: new Date('2025-01-08'),
    tamanhoArquivo: 1856734,
    processado: true
  },
  {
    id: '3',
    clienteId: '2',
    mes: 1,
    ano: 2025,
    arquivo: 'balancete-jan-2025.pdf',
    dataUpload: new Date('2025-02-03'),
    tamanhoArquivo: 1654321,
    processado: true
  }
];

export const mockResumoFinanceiro: ResumoFinanceiro = {
  totalGasto: 1951584.50,
  totalReceita: 2456789.30,
  lucro: 505204.80,
  totalAtivo: 5678901.20,
  totalPassivo: 3456789.10,
  totalDespesa: 1951584.50
};

export const mockGastosPorCategoria: GastoPorCategoria[] = [
  {
    categoria: 'Folha de Pagamento',
    valor: 750000.00,
    percentual: 38.4,
    cor: '#3B82F6'
  },
  {
    categoria: 'Fornecedores',
    valor: 580000.00,
    percentual: 29.7,
    cor: '#10B981'
  },
  {
    categoria: 'Impostos e Taxas',
    valor: 320000.00,
    percentual: 16.4,
    cor: '#F59E0B'
  },
  {
    categoria: 'Aluguel e Utilidades',
    valor: 180000.00,
    percentual: 9.2,
    cor: '#EF4444'
  },
  {
    categoria: 'Marketing e Publicidade',
    valor: 121584.50,
    percentual: 6.3,
    cor: '#8B5CF6'
  }
];

export const mockFormasPagamento: FormaPagamento[] = [
  {
    tipo: 'Transferência Bancária',
    valor: 980000.00,
    percentual: 50.2,
    cor: '#3B82F6'
  },
  {
    tipo: 'Boleto Bancário',
    valor: 486396.12,
    percentual: 24.9,
    cor: '#10B981'
  },
  {
    tipo: 'PIX',
    valor: 292975.07,
    percentual: 15.0,
    cor: '#F59E0B'
  },
  {
    tipo: 'Cartão de Crédito',
    valor: 136213.31,
    percentual: 7.0,
    cor: '#EF4444'
  },
  {
    tipo: 'Dinheiro',
    valor: 56000.00,
    percentual: 2.9,
    cor: '#8B5CF6'
  }
];

export const mockFluxoCaixa: FluxoCaixa[] = [
  { data: new Date('2025-01-01'), entradas: 456789.30, saidas: 234567.80, saldo: 222221.50 },
  { data: new Date('2025-01-08'), entradas: 345678.20, saidas: 298765.40, saldo: 269134.30 },
  { data: new Date('2025-01-15'), entradas: 567890.40, saidas: 456789.20, saldo: 380235.50 },
  { data: new Date('2025-01-22'), entradas: 234567.80, saidas: 345678.90, saldo: 269124.40 },
  { data: new Date('2025-01-29'), entradas: 678901.20, saidas: 567890.30, saldo: 380135.30 }
];

export const mockMotivosGasto: MotivoGasto[] = [
  {
    motivo: 'Salários e Encargos',
    valor: 750000.00,
    percentual: 38.4
  },
  {
    motivo: 'Matéria Prima',
    valor: 430000.00,
    percentual: 22.0
  },
  {
    motivo: 'Impostos Federais',
    valor: 320000.00,
    percentual: 16.4
  },
  {
    motivo: 'Serviços Terceirizados',
    valor: 180000.00,
    percentual: 9.2
  },
  {
    motivo: 'Aluguel',
    valor: 150000.00,
    percentual: 7.7
  },
  {
    motivo: 'Marketing Digital',
    valor: 121584.50,
    percentual: 6.3
  }
];

export const mockLancamentos: LancamentoContabil[] = [
  {
    id: '1',
    balanceteId: '1',
    descricao: 'Receita de Vendas',
    saldoAnterior: 1234567.89,
    debito: 0,
    credito: 456789.30,
    saldoAtual: 1691357.19,
    categoria: 'Receita',
    data: new Date('2025-01-15')
  },
  {
    id: '2',
    balanceteId: '1',
    descricao: 'Folha de Pagamento',
    saldoAnterior: 0,
    debito: 750000.00,
    credito: 0,
    saldoAtual: 750000.00,
    categoria: 'Despesa',
    data: new Date('2025-01-05')
  },
  {
    id: '3',
    balanceteId: '1',
    descricao: 'Fornecedores - Matéria Prima',
    saldoAnterior: 234567.89,
    debito: 430000.00,
    credito: 0,
    saldoAtual: 664567.89,
    categoria: 'Custo',
    data: new Date('2025-01-10')
  },
  {
    id: '4',
    balanceteId: '1',
    descricao: 'Impostos sobre Vendas',
    saldoAnterior: 89765.43,
    debito: 320000.00,
    credito: 0,
    saldoAtual: 409765.43,
    categoria: 'Despesa',
    data: new Date('2025-01-20')
  },
  {
    id: '5',
    balanceteId: '1',
    descricao: 'Caixa e Bancos',
    saldoAnterior: 567890.12,
    debito: 234567.80,
    credito: 456789.30,
    saldoAtual: 790111.62,
    categoria: 'Ativo',
    data: new Date('2025-01-31')
  }
];
