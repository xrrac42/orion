-- =======================================================
-- CORREÇÕES DAS POLÍTICAS RLS PARA BALANCETES
-- =======================================================

-- Remover políticas existentes para balancetes
DROP POLICY IF EXISTS "Ver balancetes de clientes próprios" ON public.balancetes;

-- Criar políticas mais permissivas para balancetes
CREATE POLICY "Usuários podem ver balancetes" ON public.balancetes
    FOR SELECT USING (true);

CREATE POLICY "Usuários podem criar balancetes" ON public.balancetes
    FOR INSERT WITH CHECK (true);

CREATE POLICY "Usuários podem atualizar balancetes" ON public.balancetes
    FOR UPDATE USING (true);

CREATE POLICY "Usuários podem deletar balancetes" ON public.balancetes
    FOR DELETE USING (true);

-- Políticas mais permissivas para file_uploads também
DROP POLICY IF EXISTS "Ver uploads próprios" ON public.file_uploads;
DROP POLICY IF EXISTS "Fazer upload de arquivos" ON public.file_uploads;
DROP POLICY IF EXISTS "Atualizar status de uploads próprios" ON public.file_uploads;

CREATE POLICY "Usuários podem ver uploads" ON public.file_uploads
    FOR SELECT USING (true);

CREATE POLICY "Usuários podem criar uploads" ON public.file_uploads
    FOR INSERT WITH CHECK (true);

CREATE POLICY "Usuários podem atualizar uploads" ON public.file_uploads
    FOR UPDATE USING (true);

CREATE POLICY "Usuários podem deletar uploads" ON public.file_uploads
    FOR DELETE USING (true);
