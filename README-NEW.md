# Orion - Sistema de Gestão Financeira

Sistema completo de gestão contábil e financeira com processamento inteligente de balancetes em PDF usando IA.

## 📋 Visão Geral

O Orion é uma plataforma moderna que automatiza o processamento de balancetes contábeis, extraindo dados de PDFs usando IA (Google Gemini) e fornecendo dashboards intuitivos para análise financeira.

### ✨ Principais Funcionalidades

- 🤖 **Processamento Automático de PDFs** - IA extrai dados de balancetes
- 📊 **Dashboard Interativo** - Visualizações em tempo real
- 👥 **Gestão de Clientes** - Controle completo de carteira
- 🔐 **Autenticação Segura** - Sistema robusto via Supabase
- 📈 **Relatórios Detalhados** - Análises financeiras completas
- 🎯 **Interface Moderna** - UX/UI responsiva e intuitiva

## 🏗️ Arquitetura

### Frontend (Next.js 15)
- **Framework**: Next.js com App Router
- **UI**: Tailwind CSS + Headless UI
- **Charts**: Chart.js + React Chart.js 2
- **Auth**: Supabase Auth com React Context

### Backend (FastAPI + Supabase)
- **API**: FastAPI para endpoints customizados
- **Database**: PostgreSQL via Supabase
- **Storage**: Supabase Storage para PDFs
- **AI**: Google Gemini para análise de documentos
- **Serverless**: Supabase Edge Functions

### Fluxo de Processamento
```
PDF Upload → Storage → Webhook → Edge Function → AI Analysis → Validation → Database → Dashboard
```

## 🚀 Configuração Rápida

### 1. Pré-requisitos

- Node.js 18+ 
- Python 3.9+ (para backend)
- Conta no Supabase
- Chave API do Google Gemini

### 2. Configuração do Supabase

Siga o guia detalhado: [SUPABASE_SETUP.md](./SUPABASE_SETUP.md)

### 3. Instalação Frontend

```bash
# Clone o repositório
git clone https://github.com/seu-usuario/orion.git
cd orion

# Instale dependências
npm install

# Configure variáveis de ambiente
cp .env.example .env.local
```

Edite `.env.local`:
```env
NEXT_PUBLIC_SUPABASE_URL=https://seu-projeto.supabase.co
NEXT_PUBLIC_SUPABASE_ANON_KEY=sua_chave_anon
```

### 4. Configuração Backend

```bash
cd backend

# Crie ambiente virtual Python
python -m venv venv
source venv/bin/activate  # Linux/Mac
venv\Scripts\activate     # Windows

# Instale dependências
pip install -r requirements.txt

# Configure variáveis de ambiente
cp .env.example .env
```

Edite `backend/.env`:
```env
SUPABASE_URL=https://seu-projeto.supabase.co
SUPABASE_SERVICE_KEY=sua_chave_service_role
GEMINI_API_KEY=sua_chave_gemini
```

### 5. Executar o Sistema

```bash
# Frontend (terminal 1)
npm run dev

# Backend (terminal 2)
cd backend
uvicorn main:app --reload

# Acessar: http://localhost:3000
```

## 📁 Estrutura do Projeto

```
orion/
├── src/                          # Frontend Next.js
│   ├── app/                      # App Router pages
│   │   ├── login/               # Página de login
│   │   ├── cadastro/            # Página de cadastro
│   │   ├── dashboard/           # Dashboard principal
│   │   ├── clientes/            # Gestão de clientes
│   │   └── relatorios/          # Relatórios
│   ├── components/              # Componentes React
│   │   ├── auth/                # Componentes de autenticação
│   │   ├── charts/              # Gráficos e visualizações
│   │   ├── layout/              # Layout e navegação
│   │   └── ui/                  # Componentes base
│   ├── contexts/                # React Contexts
│   │   └── AuthContext.tsx      # Contexto de autenticação
│   ├── lib/                     # Utilitários
│   │   ├── supabase.ts          # Cliente Supabase
│   │   └── utils.ts             # Funções utilitárias
│   └── types/                   # Tipos TypeScript
├── backend/                      # Backend Python
│   ├── core_processor.py        # Processador principal
│   ├── pdf_processor.py         # Extração de PDF
│   ├── llm_analyzer.py          # Análise com IA
│   ├── data_validator.py        # Validação de dados
│   ├── business_rules.py        # Regras de negócio
│   ├── database.py              # Integração Supabase
│   ├── config.py                # Configurações
│   ├── main.py                  # FastAPI app
│   ├── requirements.txt         # Dependências Python
│   ├── database_schema.sql      # Schema do banco
│   └── supabase_edge_function.ts # Edge Function
├── public/                       # Assets estáticos
├── docs/                        # Documentação
├── SUPABASE_SETUP.md            # Guia de configuração
└── README.md                    # Este arquivo
```

## 🔧 Desenvolvimento

### Scripts Disponíveis

```bash
# Frontend
npm run dev          # Desenvolvimento
npm run build        # Build produção
npm run start        # Executar build
npm run lint         # Linting

# Backend
cd backend
uvicorn main:app --reload            # Desenvolvimento
python core_processor.py            # Teste processamento
```

### Variáveis de Ambiente

#### Frontend (.env.local)
```env
NEXT_PUBLIC_SUPABASE_URL=          # URL do projeto Supabase
NEXT_PUBLIC_SUPABASE_ANON_KEY=     # Chave pública Supabase
```

#### Backend (.env)
```env
SUPABASE_URL=                      # URL do projeto Supabase
SUPABASE_SERVICE_KEY=              # Chave de serviço Supabase
GEMINI_API_KEY=                    # Chave API Google Gemini
BALANCETES_BUCKET=balancetes       # Bucket para PDFs
QUARANTINE_BUCKET=quarantine       # Bucket para arquivos com erro
```

## 🎯 Como Usar

### 1. Primeiro Acesso

1. Acesse `http://localhost:3000/cadastro`
2. Crie sua conta com email e senha
3. Confirme o email (verifique spam)
4. Faça login em `http://localhost:3000/login`

### 2. Cadastrar Cliente

1. Vá em **Clientes** → **Novo Cliente**
2. Preencha dados básicos (nome, CNPJ, contato)
3. Salve o cliente

### 3. Upload de Balancete

1. Acesse **Clientes** → selecione um cliente
2. Vá na aba **Balancetes**
3. Clique em **Upload PDF**
4. Selecione arquivo PDF do balancete
5. Aguarde processamento automático

### 4. Visualizar Resultados

1. Dashboard mostra resumo geral
2. **Clientes** → **Balancetes** mostra dados por cliente
3. **Relatórios** oferece análises detalhadas

## 🤖 Processamento de IA

### Como Funciona

1. **Upload**: PDF é salvo no Supabase Storage
2. **Trigger**: Webhook dispara Edge Function
3. **Extração**: Texto é extraído do PDF
4. **IA**: Gemini analisa e estrutura dados
5. **Validação**: Sistema valida dados retornados
6. **Regras**: Aplica regras contábeis específicas
7. **Storage**: Dados são salvos no banco

### Dados Extraídos

- Nome da empresa
- Período do balancete
- Contas de receita (valor crédito)
- Contas de despesa (valor débito)
- Hierarquia de grupos contábeis

## 📊 Dashboard

### Visão Geral
- Total de clientes ativos
- Receitas vs Despesas
- Crescimento mensal
- Últimas atividades

### Por Cliente
- Balancetes processados
- Evolução mensal
- Breakdown por tipo de conta
- Status dos uploads

### Relatórios
- Comparativo entre clientes
- Análise temporal
- Exportação de dados
- Gráficos interativos

## 🔐 Segurança

### Autenticação
- JWT tokens via Supabase Auth
- Sessões seguras com refresh automático
- Proteção de rotas no frontend

### Autorização
- Row Level Security (RLS) no banco
- Políticas granulares por tabela
- Controle de acesso por role (admin/user/viewer)

### Storage
- Upload apenas de PDFs
- Isolamento por usuário
- Quarentena para arquivos com erro

## 🚀 Deploy

### Frontend (Vercel)
```bash
# Deploy automático via Git
git push origin main

# Configurar variáveis no Vercel:
# NEXT_PUBLIC_SUPABASE_URL
# NEXT_PUBLIC_SUPABASE_ANON_KEY
```

### Backend (Opcional)
```bash
# Railway, Render, ou similar
# Configurar variáveis de ambiente
# Deploy via Git ou Docker
```

### Edge Functions (Supabase)
```bash
supabase functions deploy process-balancete
```

## 🤝 Contribuição

1. Fork o projeto
2. Crie uma branch: `git checkout -b feature/nova-feature`
3. Commit mudanças: `git commit -m 'Add nova feature'`
4. Push para branch: `git push origin feature/nova-feature`
5. Abra um Pull Request

## 📝 Licença

Este projeto está sob a licença MIT.

## 🆘 Suporte

- **Documentação**: Consulte os arquivos de documentação
- **Issues**: Reporte problemas via GitHub Issues
- **Email**: Entre em contato para suporte

---

**Desenvolvido com ❤️ para revolucionar a gestão contábil**
