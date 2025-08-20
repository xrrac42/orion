# Configuração do Supabase para Orion

## 1. Criando o Projeto no Supabase

1. Acesse [https://supabase.com](https://supabase.com)
2. Clique em "Start your project"
3. Crie uma nova organização (se necessário)
4. Clique em "New Project"
5. Escolha um nome (ex: "orion-prod")
6. Defina uma senha forte para o banco
7. Selecione uma região próxima ao Brasil
8. Clique em "Create new project"

## 2. Configurando as Tabelas

Após o projeto ser criado:

1. Vá na aba **SQL Editor**
2. Copie e cole o conteúdo do arquivo `backend/database_schema.sql`
3. Execute o script clicando em "Run"

⚠️ **Importante**: Execute o script completo de uma vez ou em seções para evitar erros de dependência.

## 3. Configurando Storage

### Criando os Buckets

1. Vá na aba **Storage**
2. Clique em "Create a new bucket"

Crie os seguintes buckets:

#### Bucket: `balancetes`
- **Name**: `balancetes`
- **Public**: ❌ (Privado)
- **File size limit**: 10 MB
- **Allowed MIME types**: `application/pdf`

#### Bucket: `quarantine`
- **Name**: `quarantine`
- **Public**: ❌ (Privado)
- **File size limit**: 10 MB

#### Bucket: `avatars` (opcional)
- **Name**: `avatars`
- **Public**: ✅ (Público)
- **File size limit**: 2 MB
- **Allowed MIME types**: `image/*`

### Configurando Políticas de Storage

No SQL Editor, execute:

```sql
-- Política para bucket balancetes
CREATE POLICY "Usuários podem fazer upload de PDFs" ON storage.objects
FOR INSERT WITH CHECK (
  bucket_id = 'balancetes' 
  AND auth.role() = 'authenticated'
  AND (storage.foldername(name))[1] = auth.uid()::text
);

CREATE POLICY "Usuários podem ver seus próprios arquivos" ON storage.objects
FOR SELECT USING (
  bucket_id = 'balancetes' 
  AND auth.role() = 'authenticated'
  AND (storage.foldername(name))[1] = auth.uid()::text
);

-- Política para bucket quarantine (apenas admins)
CREATE POLICY "Apenas admins podem acessar quarentena" ON storage.objects
FOR ALL USING (
  bucket_id = 'quarantine' 
  AND auth.role() = 'authenticated'
  AND EXISTS (
    SELECT 1 FROM public.user_profiles 
    WHERE id = auth.uid() AND role = 'admin'
  )
);

-- Política para avatars (público para leitura)
CREATE POLICY "Avatars são públicos para leitura" ON storage.objects
FOR SELECT USING (bucket_id = 'avatars');

CREATE POLICY "Usuários podem fazer upload do próprio avatar" ON storage.objects
FOR INSERT WITH CHECK (
  bucket_id = 'avatars' 
  AND auth.role() = 'authenticated'
  AND (storage.foldername(name))[1] = auth.uid()::text
);
```

## 4. Configurando Autenticação

### Configurações Básicas

1. Vá na aba **Authentication** → **Settings**
2. Configure:

#### Site URL
- **Site URL**: `http://localhost:3000` (desenvolvimento)
- **Site URL**: `https://seudominio.com` (produção)

#### Redirect URLs
Adicione as URLs de redirect:
- `http://localhost:3000/auth/callback`
- `https://seudominio.com/auth/callback`
- `http://localhost:3000/reset-password`
- `https://seudominio.com/reset-password`

#### Email Templates

Personalize os templates de email em **Authentication** → **Email Templates**:

##### Confirm Signup
```html
<h2>Bem-vindo ao Orion!</h2>
<p>Clique no link abaixo para confirmar sua conta:</p>
<p><a href="{{ .ConfirmationURL }}">Confirmar conta</a></p>
```

##### Reset Password
```html
<h2>Redefinir senha - Orion</h2>
<p>Clique no link abaixo para redefinir sua senha:</p>
<p><a href="{{ .ConfirmationURL }}">Redefinir senha</a></p>
```

## 5. Configurando Edge Functions

### Preparando o Ambiente

1. Instale a CLI do Supabase:
```bash
npm install -g supabase
```

2. Faça login:
```bash
supabase login
```

3. Conecte ao projeto:
```bash
supabase link --project-ref SEU_PROJECT_REF
```

### Criando a Edge Function

1. Crie a estrutura:
```bash
supabase functions new process-balancete
```

2. Substitua o conteúdo de `supabase/functions/process-balancete/index.ts` pelo código do arquivo `backend/supabase_edge_function.ts`

3. Configure as variáveis de ambiente:
```bash
supabase secrets set GEMINI_API_KEY=sua_chave_do_gemini
```

4. Deploy da função:
```bash
supabase functions deploy process-balancete
```

### Configurando Webhook

1. Vá na aba **Database** → **Webhooks**
2. Clique em "Create a new webhook"
3. Configure:
   - **Name**: `process-balancete-webhook`
   - **Table**: `storage.objects`
   - **Events**: `INSERT`
   - **Type**: `HTTP Request`
   - **HTTP URL**: `https://SEU_PROJECT_REF.supabase.co/functions/v1/process-balancete`
   - **HTTP Headers**: 
     ```
     Authorization: Bearer SEU_SERVICE_ROLE_KEY
     Content-Type: application/json
     ```
   - **Filters**: 
     ```sql
     bucket_id = 'balancetes'
     ```

## 6. Obtendo as Chaves

### Chaves Necessárias

1. Vá na aba **Settings** → **API**
2. Copie as seguintes informações:

- **Project URL**: `https://SEU_PROJECT_REF.supabase.co`
- **anon public**: Para uso no frontend
- **service_role**: Para uso no backend (⚠️ NUNCA exponha no frontend)

### Configurando Variáveis de Ambiente

#### Frontend (.env.local)
```env
NEXT_PUBLIC_SUPABASE_URL=https://SEU_PROJECT_REF.supabase.co
NEXT_PUBLIC_SUPABASE_ANON_KEY=sua_chave_anon_aqui
```

#### Backend (backend/.env)
```env
SUPABASE_URL=https://SEU_PROJECT_REF.supabase.co
SUPABASE_ANON_KEY=sua_chave_anon_aqui
SUPABASE_SERVICE_KEY=sua_chave_service_role_aqui
```

## 7. Testando a Configuração

### Teste de Autenticação

1. Inicie o frontend:
```bash
npm run dev
```

2. Acesse `http://localhost:3000/cadastro`
3. Crie uma conta de teste
4. Verifique se recebeu o email de confirmação
5. Confirme a conta
6. Faça login

### Teste de Upload

1. Faça login no sistema
2. Vá para a seção de upload de balancetes
3. Faça upload de um PDF de teste
4. Verifique se aparece na lista de arquivos
5. Verifique se a Edge Function foi executada (logs em **Edge Functions** → **Logs**)

### Verificação das Tabelas

No SQL Editor, execute:

```sql
-- Verificar usuários
SELECT * FROM auth.users;

-- Verificar perfis
SELECT * FROM public.user_profiles;

-- Verificar uploads
SELECT * FROM public.file_uploads;

-- Verificar arquivos no storage
SELECT * FROM storage.objects WHERE bucket_id = 'balancetes';
```

## 8. Monitoramento e Logs

### Logs Importantes

1. **Authentication Logs**: **Authentication** → **Logs**
2. **Edge Function Logs**: **Edge Functions** → **process-balancete** → **Logs**
3. **Database Logs**: **Settings** → **Logs**

### Métricas

Configure alertas para:
- Falhas de autenticação
- Erros na Edge Function
- Uso de storage
- Número de uploads por hora

## 9. Segurança e Backup

### Row Level Security (RLS)

Verifique se todas as políticas RLS estão ativas:

```sql
-- Verificar status do RLS
SELECT schemaname, tablename, rowsecurity 
FROM pg_tables 
WHERE schemaname = 'public';
```

### Backup

1. Configure backup automático em **Settings** → **Database**
2. Faça backup manual antes de mudanças importantes
3. Teste restore em ambiente de desenvolvimento

### Monitoramento de Segurança

1. Configure alertas para tentativas de login falhadas
2. Monitore uso de API keys
3. Revise logs regularmente
4. Mantenha as dependências atualizadas

## 10. Produção

### Checklist antes do Deploy

- [ ] Todas as tabelas criadas
- [ ] RLS configurado e testado
- [ ] Buckets de storage criados
- [ ] Edge Function deployada e testada
- [ ] Webhooks configurados
- [ ] URLs de produção configuradas
- [ ] Email templates personalizados
- [ ] Variáveis de ambiente configuradas
- [ ] Backup configurado
- [ ] Monitoramento ativo

### Domínio Personalizado

Para usar domínio próprio:

1. Configure DNS CNAME apontando para `SEU_PROJECT_REF.supabase.co`
2. Configure SSL/TLS
3. Atualize Site URL nas configurações
4. Teste todas as funcionalidades

---

## Troubleshooting

### Problemas Comuns

#### "Invalid JWT"
- Verifique se as chaves estão corretas
- Confirme se o usuário está autenticado
- Verifique expiração da sessão

#### "Row Level Security"
- Verifique se as políticas RLS estão corretas
- Teste com usuário admin
- Confira se o usuário tem permissões

#### "Function timeout"
- Aumente timeout da Edge Function
- Otimize processamento de PDF
- Verifique logs para gargalos

#### "Storage upload failed"
- Verifique políticas de storage
- Confirme tamanho e tipo do arquivo
- Teste permissões do bucket

### Contato

Para problemas específicos:
1. Verifique logs do Supabase
2. Consulte documentação oficial
3. Entre em contato com suporte se necessário
