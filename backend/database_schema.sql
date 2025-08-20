-- =======================================================
-- SCRIPT SQL PARA CRIAÇÃO DAS TABELAS NO SUPABASE
-- Sistema Orion - Processamento de Balancetes
-- =======================================================

-- Habilitar extensões necessárias
CREATE EXTENSION IF NOT EXISTS "uuid-ossp";

-- =======================================================
-- 1. TABELA DE USUÁRIOS (usando auth.users do Supabase)
-- =======================================================

-- Tabela de perfis de usuário (complementa auth.users)
CREATE TABLE public.user_profiles (
    id UUID REFERENCES auth.users(id) PRIMARY KEY,
    nome TEXT NOT NULL,
    sobrenome TEXT,
    telefone TEXT,
    empresa TEXT,
    cargo TEXT,
    avatar_url TEXT,
    role TEXT NOT NULL DEFAULT 'user' CHECK (role IN ('admin', 'user', 'viewer')),
    is_active BOOLEAN DEFAULT true,
    created_at TIMESTAMPTZ DEFAULT NOW(),
    updated_at TIMESTAMPTZ DEFAULT NOW()
);

-- =======================================================
-- 2. TABELA DE CLIENTES
-- =======================================================

CREATE TABLE public.clients (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    nome TEXT NOT NULL,
    cnpj TEXT UNIQUE,
    cpf TEXT,
    email TEXT,
    telefone TEXT,
    endereco TEXT,
    cidade TEXT,
    estado TEXT,
    cep TEXT,
    is_active BOOLEAN DEFAULT true,
    created_by UUID REFERENCES auth.users(id),
    created_at TIMESTAMPTZ DEFAULT NOW(),
    updated_at TIMESTAMPTZ DEFAULT NOW()
);

-- =======================================================
-- 3. TABELA DE ENTRADAS FINANCEIRAS (PRINCIPAL)
-- =======================================================

CREATE TABLE public.financial_entries (
    id BIGINT PRIMARY KEY GENERATED ALWAYS AS IDENTITY,
    client_id UUID REFERENCES public.clients(id) ON DELETE CASCADE,
    report_date DATE NOT NULL,
    main_group TEXT NOT NULL CHECK (main_group IN ('RECEITAS', 'CUSTOS E DESPESAS')),
    subgroup_1 TEXT,
    specific_account TEXT NOT NULL,
    movement_type TEXT NOT NULL CHECK (movement_type IN ('Receita', 'Despesa')),
    period_value DECIMAL(15, 2) NOT NULL CHECK (period_value >= 0),
    original_data JSONB,
    created_by UUID REFERENCES auth.users(id),
    created_at TIMESTAMPTZ DEFAULT NOW()
);

-- =======================================================
-- 4. TABELA DE UPLOADS/PROCESSAMENTO DE ARQUIVOS
-- =======================================================

CREATE TABLE public.file_uploads (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    client_id UUID REFERENCES public.clients(id) ON DELETE CASCADE,
    file_name TEXT NOT NULL,
    file_path TEXT NOT NULL,
    file_size BIGINT,
    mime_type TEXT,
    status TEXT NOT NULL DEFAULT 'pending' CHECK (status IN ('pending', 'processing', 'completed', 'failed', 'quarantine')),
    processing_started_at TIMESTAMPTZ,
    processing_completed_at TIMESTAMPTZ,
    entries_created INTEGER DEFAULT 0,
    error_message TEXT,
    uploaded_by UUID REFERENCES auth.users(id),
    created_at TIMESTAMPTZ DEFAULT NOW()
);

-- =======================================================
-- 5. TABELA DE QUARENTENA
-- =======================================================

CREATE TABLE public.quarantine_files (
    id BIGINT PRIMARY KEY GENERATED ALWAYS AS IDENTITY,
    file_upload_id UUID REFERENCES public.file_uploads(id),
    file_path TEXT NOT NULL,
    error_message TEXT,
    error_details JSONB,
    quarantine_date TIMESTAMPTZ DEFAULT NOW(),
    reviewed_by UUID REFERENCES auth.users(id),
    reviewed_at TIMESTAMPTZ,
    resolution_status TEXT DEFAULT 'pending' CHECK (resolution_status IN ('pending', 'resolved', 'ignored')),
    resolution_notes TEXT
);

-- =======================================================
-- 6. TABELA DE BALANCETES (RESUMOS MENSAIS)
-- =======================================================

CREATE TABLE public.balancetes (
    id BIGINT PRIMARY KEY GENERATED ALWAYS AS IDENTITY,
    client_id UUID REFERENCES public.clients(id) ON DELETE CASCADE,
    ano INTEGER NOT NULL,
    mes INTEGER NOT NULL CHECK (mes BETWEEN 1 AND 12),
    total_receitas DECIMAL(15, 2) DEFAULT 0,
    total_despesas DECIMAL(15, 2) DEFAULT 0,
    lucro_bruto DECIMAL(15, 2) GENERATED ALWAYS AS (total_receitas - total_despesas) STORED,
    total_entries INTEGER DEFAULT 0,
    file_upload_id UUID REFERENCES public.file_uploads(id),
    created_by UUID REFERENCES auth.users(id),
    created_at TIMESTAMPTZ DEFAULT NOW(),
    updated_at TIMESTAMPTZ DEFAULT NOW(),
    UNIQUE(client_id, ano, mes)
);

-- =======================================================
-- 7. TABELA DE LOGS DE AUDITORIA
-- =======================================================

CREATE TABLE public.audit_logs (
    id BIGINT PRIMARY KEY GENERATED ALWAYS AS IDENTITY,
    table_name TEXT NOT NULL,
    record_id TEXT NOT NULL,
    action TEXT NOT NULL CHECK (action IN ('INSERT', 'UPDATE', 'DELETE')),
    old_values JSONB,
    new_values JSONB,
    user_id UUID REFERENCES auth.users(id),
    created_at TIMESTAMPTZ DEFAULT NOW()
);

-- =======================================================
-- ÍNDICES PARA PERFORMANCE
-- =======================================================

-- Índices para financial_entries
CREATE INDEX idx_financial_entries_client_date ON public.financial_entries(client_id, report_date);
CREATE INDEX idx_financial_entries_type ON public.financial_entries(movement_type);
CREATE INDEX idx_financial_entries_group ON public.financial_entries(main_group);
CREATE INDEX idx_financial_entries_created_at ON public.financial_entries(created_at);

-- Índices para clients
CREATE INDEX idx_clients_cnpj ON public.clients(cnpj) WHERE cnpj IS NOT NULL;
CREATE INDEX idx_clients_active ON public.clients(is_active);
CREATE INDEX idx_clients_created_by ON public.clients(created_by);

-- Índices para file_uploads
CREATE INDEX idx_file_uploads_client ON public.file_uploads(client_id);
CREATE INDEX idx_file_uploads_status ON public.file_uploads(status);
CREATE INDEX idx_file_uploads_created_at ON public.file_uploads(created_at);

-- Índices para balancetes
CREATE INDEX idx_balancetes_client_periodo ON public.balancetes(client_id, ano, mes);
CREATE INDEX idx_balancetes_periodo ON public.balancetes(ano, mes);

-- =======================================================
-- ROW LEVEL SECURITY (RLS)
-- =======================================================

-- Habilitar RLS em todas as tabelas
ALTER TABLE public.user_profiles ENABLE ROW LEVEL SECURITY;
ALTER TABLE public.clients ENABLE ROW LEVEL SECURITY;
ALTER TABLE public.financial_entries ENABLE ROW LEVEL SECURITY;
ALTER TABLE public.file_uploads ENABLE ROW LEVEL SECURITY;
ALTER TABLE public.quarantine_files ENABLE ROW LEVEL SECURITY;
ALTER TABLE public.balancetes ENABLE ROW LEVEL SECURITY;
ALTER TABLE public.audit_logs ENABLE ROW LEVEL SECURITY;

-- =======================================================
-- POLÍTICAS RLS
-- =======================================================

-- Políticas para user_profiles
CREATE POLICY "Usuários podem ver próprio perfil" ON public.user_profiles
    FOR SELECT USING (auth.uid() = id);

CREATE POLICY "Usuários podem atualizar próprio perfil" ON public.user_profiles
    FOR UPDATE USING (auth.uid() = id);

CREATE POLICY "Admins podem ver todos os perfis" ON public.user_profiles
    FOR ALL USING (
        EXISTS (
            SELECT 1 FROM public.user_profiles 
            WHERE id = auth.uid() AND role = 'admin'
        )
    );

-- Políticas para clients
CREATE POLICY "Usuários podem ver clientes que criaram" ON public.clients
    FOR SELECT USING (
        created_by = auth.uid() OR
        EXISTS (
            SELECT 1 FROM public.user_profiles 
            WHERE id = auth.uid() AND role = 'admin'
        )
    );

CREATE POLICY "Usuários podem criar clientes" ON public.clients
    FOR INSERT WITH CHECK (created_by = auth.uid());

CREATE POLICY "Usuários podem atualizar clientes próprios" ON public.clients
    FOR UPDATE USING (
        created_by = auth.uid() OR
        EXISTS (
            SELECT 1 FROM public.user_profiles 
            WHERE id = auth.uid() AND role = 'admin'
        )
    );

-- Políticas para financial_entries
CREATE POLICY "Ver entradas de clientes próprios" ON public.financial_entries
    FOR SELECT USING (
        EXISTS (
            SELECT 1 FROM public.clients 
            WHERE id = client_id AND (
                created_by = auth.uid() OR
                EXISTS (
                    SELECT 1 FROM public.user_profiles 
                    WHERE id = auth.uid() AND role = 'admin'
                )
            )
        )
    );

CREATE POLICY "Inserir entradas para clientes próprios" ON public.financial_entries
    FOR INSERT WITH CHECK (
        EXISTS (
            SELECT 1 FROM public.clients 
            WHERE id = client_id AND created_by = auth.uid()
        )
    );

-- Políticas para file_uploads
CREATE POLICY "Ver uploads próprios" ON public.file_uploads
    FOR SELECT USING (
        uploaded_by = auth.uid() OR
        EXISTS (
            SELECT 1 FROM public.user_profiles 
            WHERE id = auth.uid() AND role = 'admin'
        )
    );

CREATE POLICY "Fazer upload de arquivos" ON public.file_uploads
    FOR INSERT WITH CHECK (uploaded_by = auth.uid());

CREATE POLICY "Atualizar status de uploads próprios" ON public.file_uploads
    FOR UPDATE USING (
        uploaded_by = auth.uid() OR
        EXISTS (
            SELECT 1 FROM public.user_profiles 
            WHERE id = auth.uid() AND role = 'admin'
        )
    );

-- Políticas para balancetes
CREATE POLICY "Ver balancetes de clientes próprios" ON public.balancetes
    FOR SELECT USING (
        EXISTS (
            SELECT 1 FROM public.clients 
            WHERE id = client_id AND (
                created_by = auth.uid() OR
                EXISTS (
                    SELECT 1 FROM public.user_profiles 
                    WHERE id = auth.uid() AND role = 'admin'
                )
            )
        )
    );

-- =======================================================
-- FUNÇÕES E TRIGGERS
-- =======================================================

-- Função para atualizar updated_at automaticamente
CREATE OR REPLACE FUNCTION public.handle_updated_at()
RETURNS TRIGGER AS $$
BEGIN
    NEW.updated_at = NOW();
    RETURN NEW;
END;
$$ LANGUAGE plpgsql;

-- Triggers para updated_at
CREATE TRIGGER handle_updated_at_user_profiles
    BEFORE UPDATE ON public.user_profiles
    FOR EACH ROW EXECUTE FUNCTION public.handle_updated_at();

CREATE TRIGGER handle_updated_at_clients
    BEFORE UPDATE ON public.clients
    FOR EACH ROW EXECUTE FUNCTION public.handle_updated_at();

CREATE TRIGGER handle_updated_at_balancetes
    BEFORE UPDATE ON public.balancetes
    FOR EACH ROW EXECUTE FUNCTION public.handle_updated_at();

-- Função para criar perfil de usuário automaticamente
CREATE OR REPLACE FUNCTION public.handle_new_user()
RETURNS TRIGGER AS $$
BEGIN
    INSERT INTO public.user_profiles (id, nome, role)
    VALUES (
        NEW.id,
        COALESCE(NEW.raw_user_meta_data->>'nome', NEW.email),
        COALESCE(NEW.raw_user_meta_data->>'role', 'user')
    );
    RETURN NEW;
END;
$$ LANGUAGE plpgsql SECURITY DEFINER;

-- Trigger para criar perfil automaticamente
CREATE TRIGGER on_auth_user_created
    AFTER INSERT ON auth.users
    FOR EACH ROW EXECUTE FUNCTION public.handle_new_user();

-- Função para atualizar resumos de balancetes
CREATE OR REPLACE FUNCTION public.update_balancete_summary()
RETURNS TRIGGER AS $$
DECLARE
    client_uuid UUID;
    report_year INTEGER;
    report_month INTEGER;
    receitas_total DECIMAL(15,2);
    despesas_total DECIMAL(15,2);
    entries_count INTEGER;
BEGIN
    -- Extrair dados da nova entrada
    client_uuid := NEW.client_id;
    report_year := EXTRACT(YEAR FROM NEW.report_date);
    report_month := EXTRACT(MONTH FROM NEW.report_date);
    
    -- Calcular totais para o período
    SELECT 
        COALESCE(SUM(CASE WHEN movement_type = 'Receita' THEN period_value ELSE 0 END), 0),
        COALESCE(SUM(CASE WHEN movement_type = 'Despesa' THEN period_value ELSE 0 END), 0),
        COUNT(*)
    INTO receitas_total, despesas_total, entries_count
    FROM public.financial_entries
    WHERE client_id = client_uuid 
    AND EXTRACT(YEAR FROM report_date) = report_year
    AND EXTRACT(MONTH FROM report_date) = report_month;
    
    -- Inserir ou atualizar balancete
    INSERT INTO public.balancetes (client_id, ano, mes, total_receitas, total_despesas, total_entries, created_by)
    VALUES (client_uuid, report_year, report_month, receitas_total, despesas_total, entries_count, NEW.created_by)
    ON CONFLICT (client_id, ano, mes)
    DO UPDATE SET
        total_receitas = receitas_total,
        total_despesas = despesas_total,
        total_entries = entries_count,
        updated_at = NOW();
    
    RETURN NEW;
END;
$$ LANGUAGE plpgsql;

-- Trigger para atualizar balancetes automaticamente
CREATE TRIGGER update_balancete_on_entry_insert
    AFTER INSERT ON public.financial_entries
    FOR EACH ROW EXECUTE FUNCTION public.update_balancete_summary();

-- =======================================================
-- VIEWS PARA DASHBOARD
-- =======================================================

-- View para resumo geral por cliente
CREATE VIEW public.client_summary AS
SELECT 
    c.id,
    c.nome,
    c.cnpj,
    c.is_active,
    COUNT(DISTINCT b.id) as total_balancetes,
    COUNT(DISTINCT fe.id) as total_entries,
    COALESCE(SUM(b.total_receitas), 0) as receitas_total,
    COALESCE(SUM(b.total_despesas), 0) as despesas_total,
    COALESCE(SUM(b.lucro_bruto), 0) as lucro_total,
    MAX(fe.created_at) as ultima_entrada
FROM public.clients c
LEFT JOIN public.balancetes b ON c.id = b.client_id
LEFT JOIN public.financial_entries fe ON c.id = fe.client_id
GROUP BY c.id, c.nome, c.cnpj, c.is_active;

-- View para últimas atividades
CREATE VIEW public.recent_activities AS
SELECT 
    'upload' as activity_type,
    fu.id::text as activity_id,
    c.nome as client_name,
    fu.file_name as description,
    fu.status,
    fu.created_at
FROM public.file_uploads fu
JOIN public.clients c ON fu.client_id = c.id
UNION ALL
SELECT 
    'processing' as activity_type,
    fe.id::text as activity_id,
    c.nome as client_name,
    fe.specific_account as description,
    'completed' as status,
    fe.created_at
FROM public.financial_entries fe
JOIN public.clients c ON fe.client_id = c.id
ORDER BY created_at DESC
LIMIT 50;

-- =======================================================
-- DADOS INICIAIS (OPCIONAL)
-- =======================================================

-- Inserir dados de exemplo (descomente se necessário)
/*
INSERT INTO public.clients (nome, cnpj, email, telefone) VALUES
('Empresa Exemplo LTDA', '12.345.678/0001-90', 'contato@exemplo.com', '(11) 99999-9999'),
('Consultoria ABC', '98.765.432/0001-10', 'admin@abc.com', '(11) 88888-8888');
*/

-- =======================================================
-- BUCKETS DE STORAGE
-- =======================================================

-- Criar buckets (execute no painel do Supabase Storage)
/*
1. Vá em Storage no painel do Supabase
2. Crie os seguintes buckets:
   - balancetes (público: false)
   - quarantine (público: false)
   - avatars (público: true)
*/

-- =======================================================
-- WEBHOOKS E EDGE FUNCTIONS
-- =======================================================

/*
Para configurar o processamento automático:

1. Deploy da Edge Function:
   supabase functions deploy process-balancete

2. Configurar Webhook no Storage:
   - Evento: INSERT na tabela storage.objects
   - URL: https://seu-projeto.supabase.co/functions/v1/process-balancete
   - Filtros: bucket_id = 'balancetes'
*/

-- =======================================================
-- COMENTÁRIOS FINAIS
-- =======================================================

/*
Este script cria uma estrutura completa para o sistema Orion:

✅ Tabelas principais com relacionamentos
✅ Row Level Security (RLS) configurado
✅ Índices para performance
✅ Triggers para automação
✅ Views para dashboard
✅ Auditoria e logs
✅ Integração com auth.users do Supabase

Para usar:
1. Copie e cole este script no SQL Editor do Supabase
2. Execute em partes ou completo
3. Configure os buckets de storage
4. Deploy das Edge Functions
5. Configure webhooks se necessário

Próximos passos:
- Implementar autenticação no frontend
- Configurar RLS policies mais específicas se necessário
- Adicionar mais campos conforme necessário
- Implementar backup e restore procedures
*/
