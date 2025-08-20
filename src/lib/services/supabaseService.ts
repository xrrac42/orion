import { createClient } from '@/lib/supabase/client'

const supabase = createClient()

// Tipos
export type Cliente = {
  id: string
  nome: string
  cnpj?: string
  cpf?: string
  email?: string
  telefone?: string
  endereco?: string
  cidade?: string
  estado?: string
  cep?: string
  is_active: boolean
  created_at: string
  updated_at: string
}

export type Balancete = {
  id: number
  client_id: string
  ano: number
  mes: number
  total_receitas: number
  total_despesas: number
  lucro_bruto: number
  total_entries: number
  created_at: string
  updated_at: string
}

export type BalanceteInput = {
  client_id: string
  ano: number
  mes: number
  total_receitas: number
  total_despesas: number
}

// Serviços de Clientes
export const clientService = {
  // Listar todos os clientes do usuário
  async getAll(): Promise<Cliente[]> {
    const { data, error } = await supabase
      .from('clients')
      .select('*')
      .eq('is_active', true)
      .order('nome')

    if (error) throw error
    return data || []
  },

  // Buscar cliente por ID
  async getById(id: string): Promise<Cliente | null> {
    const { data, error } = await supabase
      .from('clients')
      .select('*')
      .eq('id', id)
      .single()

    if (error) throw error
    return data
  },

  // Criar novo cliente
  async create(cliente: Omit<Cliente, 'id' | 'created_at' | 'updated_at'>): Promise<Cliente> {
    const { data: user } = await supabase.auth.getUser()
    
    const { data, error } = await supabase
      .from('clients')
      .insert({
        ...cliente,
        created_by: user.user?.id
      })
      .select()
      .single()

    if (error) throw error
    return data
  },

  // Atualizar cliente
  async update(id: string, updates: Partial<Cliente>): Promise<Cliente> {
    const { data, error } = await supabase
      .from('clients')
      .update(updates)
      .eq('id', id)
      .select()
      .single()

    if (error) throw error
    return data
  },

  // Deletar cliente (soft delete)
  async delete(id: string): Promise<void> {
    const { error } = await supabase
      .from('clients')
      .update({ is_active: false })
      .eq('id', id)

    if (error) throw error
  }
}

// Serviços de Balancetes
export const balanceteService = {
  // Listar balancetes de um cliente
  async getByClient(clientId: string): Promise<Balancete[]> {
    const { data, error } = await supabase
      .from('balancetes')
      .select('*')
      .eq('client_id', clientId)
      .order('ano', { ascending: false })
      .order('mes', { ascending: false })

    if (error) throw error
    return data || []
  },

  // Buscar balancete específico
  async getByClientAndPeriod(clientId: string, ano: number, mes: number): Promise<Balancete | null> {
    const { data, error } = await supabase
      .from('balancetes')
      .select('*')
      .eq('client_id', clientId)
      .eq('ano', ano)
      .eq('mes', mes)
      .single()

    if (error && error.code !== 'PGRST116') throw error
    return data
  },

  // Criar novo balancete
  async create(balancete: BalanceteInput): Promise<Balancete> {
    const { data: user } = await supabase.auth.getUser()
    
    const { data, error } = await supabase
      .from('balancetes')
      .insert({
        ...balancete,
        created_by: user.user?.id
      })
      .select()
      .single()

    if (error) throw error
    return data
  },

  // Atualizar balancete
  async update(id: number, updates: Partial<BalanceteInput>): Promise<Balancete> {
    const { data, error } = await supabase
      .from('balancetes')
      .update(updates)
      .eq('id', id)
      .select()
      .single()

    if (error) throw error
    return data
  },

  // Deletar balancete
  async delete(id: number): Promise<void> {
    const { error } = await supabase
      .from('balancetes')
      .delete()
      .eq('id', id)

    if (error) throw error
  },

  // Obter resumo geral
  async getSummary() {
    const { data, error } = await supabase
      .from('client_summary')
      .select('*')

    if (error) throw error
    return data || []
  },

  // Obter atividades recentes
  async getRecentActivities() {
    const { data, error } = await supabase
      .from('recent_activities')
      .select('*')
      .limit(10)

    if (error) throw error
    return data || []
  }
}
