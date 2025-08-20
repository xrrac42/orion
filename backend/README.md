# Backend Orion - Sistema de Processamento de Balancetes

Este é o backend do sistema Orion, responsável por processar balancetes contábeis em PDF usando IA (LLM) e armazenar os dados estruturados no Supabase.

## Arquitetura

O sistema funciona com a seguinte arquitetura:

1. **Upload de PDF** → Supabase Storage (bucket: `balancetes`)
2. **Trigger automático** → Supabase Edge Function
3. **Processamento** → Extração de texto + Análise com Gemini LLM
4. **Validação** → Regras de negócio e validação de dados
5. **Armazenamento** → PostgreSQL no Supabase

## Componentes Principais

### Core Processor (`core_processor.py`)
- Orquestra todo o fluxo de processamento
- Coordena extração, análise e armazenamento
- Gerencia erros e quarentena

### PDF Processor (`pdf_processor.py`) 
- Extrai texto de arquivos PDF
- Suporta PyPDF2 e pdfplumber
- Processa tabelas e texto estruturado

### LLM Analyzer (`llm_analyzer.py`)
- Integração com Google Gemini API
- Converte texto não estruturado em JSON
- Prompt engineering para balancetes contábeis

### Data Validator (`data_validator.py`)
- Valida estrutura e integridade dos dados
- Verifica formatos e tipos de dados
- Gera relatórios de validação

### Business Rules (`business_rules.py`)
- Aplica regras contábeis determinísticas
- Classifica receitas vs despesas
- Processa hierarquia de contas

### Database (`database.py`)
- Integração com Supabase via API REST
- Repositories para diferentes entidades
- Operações CRUD assíncronas

## Configuração

### 1. Variáveis de Ambiente

Crie um arquivo `.env` na pasta backend:

```env
# Supabase
SUPABASE_URL=https://seu-projeto.supabase.co
SUPABASE_ANON_KEY=sua-chave-anonima
SUPABASE_SERVICE_KEY=sua-chave-de-servico

# Gemini API
GEMINI_API_KEY=sua-chave-do-gemini
GEMINI_MODEL=gemini-1.5-flash

# Storage
BALANCETES_BUCKET=balancetes
QUARANTINE_BUCKET=quarantine

# Configurações
MAX_FILE_SIZE_MB=10
LOG_LEVEL=INFO
```

### 2. Estrutura do Banco de Dados (Supabase)

Execute os seguintes comandos SQL no editor SQL do Supabase:

```sql
-- Tabela de clientes
CREATE TABLE clients (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    nome TEXT NOT NULL,
    cnpj TEXT UNIQUE,
    email TEXT,
    telefone TEXT,
    endereco TEXT,
    is_active BOOLEAN DEFAULT true,
    created_at TIMESTAMPTZ DEFAULT NOW()
);

-- Tabela principal de entradas financeiras
CREATE TABLE financial_entries (
    id BIGINT PRIMARY KEY GENERATED ALWAYS AS IDENTITY,
    client_id UUID REFERENCES clients(id),
    report_date DATE NOT NULL,
    main_group TEXT NOT NULL,
    subgroup_1 TEXT,
    specific_account TEXT NOT NULL,
    movement_type TEXT NOT NULL CHECK (movement_type IN ('Receita', 'Despesa')),
    period_value DECIMAL(15, 2) NOT NULL,
    created_at TIMESTAMPTZ DEFAULT NOW(),
    original_data JSONB
);

-- Tabela de quarentena para arquivos com erro
CREATE TABLE quarantine_files (
    id BIGINT PRIMARY KEY GENERATED ALWAYS AS IDENTITY,
    file_path TEXT NOT NULL,
    error_message TEXT,
    quarantine_date TIMESTAMPTZ DEFAULT NOW(),
    original_path TEXT
);

-- Habilitar RLS (Row Level Security)
ALTER TABLE financial_entries ENABLE ROW LEVEL SECURITY;
ALTER TABLE clients ENABLE ROW LEVEL SECURITY;
ALTER TABLE quarantine_files ENABLE ROW LEVEL SECURITY;

-- Índices para performance
CREATE INDEX idx_financial_entries_client_date ON financial_entries(client_id, report_date);
CREATE INDEX idx_financial_entries_type ON financial_entries(movement_type);
CREATE INDEX idx_financial_entries_group ON financial_entries(main_group);
```

### 3. Storage Buckets

Configure os buckets no Supabase Storage:

1. **balancetes** - Para arquivos PDF enviados pelos usuários
2. **quarantine** - Para arquivos que falharam no processamento

### 4. Edge Function

Implante a Edge Function no Supabase:

```bash
# No diretório do projeto Supabase
supabase functions deploy process-balancete
```

### 5. Webhook do Storage

Configure um webhook no Supabase Storage para trigger automático:

1. Vá em Storage → Settings → Webhooks
2. Adicione webhook para evento `INSERT` na tabela `objects`
3. URL: `https://seu-projeto.supabase.co/functions/v1/process-balancete`

## Instalação Local

```bash
# Instalar dependências Python
pip install -r requirements.txt

# Configurar variáveis de ambiente
cp .env.example .env
# Editar .env com suas credenciais

# Testar configuração
python -c "from config import settings; print(settings.validate())"
```

## Uso

### Processamento Manual (para testes)

```python
from core_processor import BalanceteProcessor
import asyncio

async def test_processing():
    processor = BalanceteProcessor()
    result = await processor.process_balancete(
        file_path="/path/to/balancete.pdf",
        client_id="client-uuid"
    )
    print(result)

asyncio.run(test_processing())
```

### Via API REST (FastAPI)

```bash
# Iniciar servidor de desenvolvimento
uvicorn main:app --reload --port 8000

# Acessar documentação
# http://localhost:8000/docs
```

## Estrutura de Dados

### Entrada (JSON do LLM)
```json
{
  "cliente": "Empresa Exemplo LTDA",
  "data_final": "2024-12-31",
  "contas": [
    {
      "grupo_principal": "RECEITAS",
      "subgrupo_1": "Receita de Vendas",
      "conta_especifica": "Venda de Produtos",
      "valor_debito": 0.00,
      "valor_credito": 50000.00
    }
  ]
}
```

### Saída (Banco de Dados)
```json
{
  "id": "uuid",
  "client_id": "client-uuid",
  "report_date": "2024-12-31",
  "main_group": "RECEITAS",
  "subgroup_1": "Receita de Vendas",
  "specific_account": "Venda de Produtos",
  "movement_type": "Receita",
  "period_value": 50000.00,
  "created_at": "2024-12-31T23:59:59Z"
}
```

## Regras de Negócio

### Classificação de Movimento
- **RECEITAS** → `movement_type = "Receita"`, `period_value = valor_credito`
- **CUSTOS E DESPESAS** → `movement_type = "Despesa"`, `period_value = valor_debito`

### Validação
- Valores devem ser positivos
- Datas no formato YYYY-MM-DD
- Nomes de contas não podem estar vazios
- Grupos principais devem ser válidos

## Tratamento de Erros

### Quarentena
Arquivos que falham no processamento são movidos para quarentena com:
- Caminho original do arquivo
- Mensagem de erro detalhada
- Timestamp do erro

### Logs
Todos os eventos são logados com níveis apropriados:
- `INFO`: Processamento normal
- `WARNING`: Situações suspeitas mas não críticas
- `ERROR`: Falhas no processamento

## Monitoramento

### Métricas Importantes
- Taxa de sucesso do processamento
- Tempo médio de processamento
- Número de arquivos em quarentena
- Accuracy do LLM

### Logs do Supabase
Monitore logs das Edge Functions no dashboard do Supabase para acompanhar execuções.

## Desenvolvimento

### Estrutura do Projeto
```
backend/
├── core_processor.py      # Orquestrador principal
├── pdf_processor.py       # Extração de PDF
├── llm_analyzer.py        # Análise com LLM
├── data_validator.py      # Validação de dados
├── business_rules.py      # Regras de negócio
├── database.py           # Integração Supabase
├── config.py             # Configurações
├── models.py             # Modelos Pydantic
├── main.py               # FastAPI app
├── requirements.txt      # Dependências
└── supabase_edge_function.ts  # Edge Function
```

### Próximos Passos
1. Implementar autenticação e autorização
2. Adicionar testes unitários
3. Melhorar tratamento de diferentes formatos de PDF
4. Implementar cache para melhor performance
5. Adicionar métricas e monitoring
6. Criar interface para revisar arquivos em quarentena
