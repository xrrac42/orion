import { createClient } from '@supabase/supabase-js'

const supabaseUrl = process.env.NEXT_PUBLIC_SUPABASE_URL!
const supabaseAnonKey = process.env.NEXT_PUBLIC_SUPABASE_ANON_KEY!

export const supabase = createClient(supabaseUrl, supabaseAnonKey, {
  auth: {
    autoRefreshToken: true,
    persistSession: true,
    detectSessionInUrl: true
  }
})

// Types para TypeScript
export type Database = {
  public: {
    Tables: {
      user_profiles: {
        Row: {
          id: string
          nome: string
          sobrenome: string | null
          telefone: string | null
          empresa: string | null
          cargo: string | null
          avatar_url: string | null
          role: 'admin' | 'user' | 'viewer'
          is_active: boolean
          created_at: string
          updated_at: string
        }
        Insert: {
          id: string
          nome: string
          sobrenome?: string | null
          telefone?: string | null
          empresa?: string | null
          cargo?: string | null
          avatar_url?: string | null
          role?: 'admin' | 'user' | 'viewer'
          is_active?: boolean
        }
        Update: {
          nome?: string
          sobrenome?: string | null
          telefone?: string | null
          empresa?: string | null
          cargo?: string | null
          avatar_url?: string | null
          role?: 'admin' | 'user' | 'viewer'
          is_active?: boolean
        }
      }
      clients: {
        Row: {
          id: string
          nome: string
          cnpj: string | null
          cpf: string | null
          email: string | null
          telefone: string | null
          endereco: string | null
          cidade: string | null
          estado: string | null
          cep: string | null
          is_active: boolean
          created_by: string | null
          created_at: string
          updated_at: string
        }
        Insert: {
          nome: string
          cnpj?: string | null
          cpf?: string | null
          email?: string | null
          telefone?: string | null
          endereco?: string | null
          cidade?: string | null
          estado?: string | null
          cep?: string | null
          is_active?: boolean
          created_by?: string | null
        }
        Update: {
          nome?: string
          cnpj?: string | null
          cpf?: string | null
          email?: string | null
          telefone?: string | null
          endereco?: string | null
          cidade?: string | null
          estado?: string | null
          cep?: string | null
          is_active?: boolean
        }
      }
      financial_entries: {
        Row: {
          id: number
          client_id: string
          report_date: string
          main_group: 'RECEITAS' | 'CUSTOS E DESPESAS'
          subgroup_1: string | null
          specific_account: string
          movement_type: 'Receita' | 'Despesa'
          period_value: number
          original_data: any | null
          created_by: string | null
          created_at: string
        }
        Insert: {
          client_id: string
          report_date: string
          main_group: 'RECEITAS' | 'CUSTOS E DESPESAS'
          subgroup_1?: string | null
          specific_account: string
          movement_type: 'Receita' | 'Despesa'
          period_value: number
          original_data?: any | null
          created_by?: string | null
        }
      }
      file_uploads: {
        Row: {
          id: string
          client_id: string
          file_name: string
          file_path: string
          file_size: number | null
          mime_type: string | null
          status: 'pending' | 'processing' | 'completed' | 'failed' | 'quarantine'
          processing_started_at: string | null
          processing_completed_at: string | null
          entries_created: number
          error_message: string | null
          uploaded_by: string | null
          created_at: string
        }
        Insert: {
          client_id: string
          file_name: string
          file_path: string
          file_size?: number | null
          mime_type?: string | null
          status?: 'pending' | 'processing' | 'completed' | 'failed' | 'quarantine'
          uploaded_by?: string | null
        }
      }
      balancetes: {
        Row: {
          id: number
          client_id: string
          ano: number
          mes: number
          total_receitas: number
          total_despesas: number
          lucro_bruto: number
          total_entries: number
          file_upload_id: string | null
          created_by: string | null
          created_at: string
          updated_at: string
        }
      }
    }
    Views: {
      client_summary: {
        Row: {
          id: string
          nome: string
          cnpj: string | null
          is_active: boolean
          total_balancetes: number
          total_entries: number
          receitas_total: number
          despesas_total: number
          lucro_total: number
          ultima_entrada: string | null
        }
      }
      recent_activities: {
        Row: {
          activity_type: string
          activity_id: string
          client_name: string
          description: string
          status: string
          created_at: string
        }
      }
    }
  }
}
