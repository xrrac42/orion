# Sistema de Análises Mensais - Arquitetura e Documentação

## Visão Geral

O novo sistema de análises mensais foi desenvolvido para otimizar o processamento de dados financeiros, implementando:

1. **Pacotes Mensais Discretos**: Cada mês de cada cliente é tratado como uma análise independente
2. **Detecção Inteligente de Duplicatas**: IA para identificar arquivos duplicados antes do processamento
3. **Processamento em Duas Etapas**: Pré-verificação + processamento completo
4. **Análise com IA**: Extração automática de metadados e geração de resumos executivos

## Arquitetura do Sistema

### 1. Estrutura de Dados

#### Tabela `monthly_analyses`
- **Propósito**: Registro principal de cada análise mensal
- **Campos Principais**:
  - `client_id` + `reference_month` + `reference_year`: Chave única para o período
  - `status`: pending, processing, completed, error
  - `ai_summary`: Resumo executivo gerado pela IA
  - `metadata`: Metadados extraídos do arquivo
  - `total_receitas`, `total_despesas`, `total_entries`: Totalizadores calculados

#### Tabela `financial_entries` (atualizada)
- **Mudança Principal**: Agora vinculada a `analysis_id` em vez de diretamente ao cliente
- **Benefício**: Dados organizados por período de análise

#### Tabela `file_uploads` (aprimorada)
- **Novos Campos**:
  - `analysis_id`: Vinculação com a análise
  - `pre_check_result`: Metadados da pré-verificação
  - `status`: uploaded, pre_checked, processing, completed, error

### 2. Fluxo de Processamento

#### Etapa 1: Pré-verificação (`POST /api/monthly-analyses/pre-check`)
```json
{
  "client_id": "uuid",
  "file_data": "base64_encoded_file",
  "file_name": "balancete_janeiro_2024.xlsx",
  "file_type": "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"
}
```

**Processos da IA:**
1. **Extração de Metadados**:
   - Hash do arquivo para detecção de duplicatas
   - Identificação automática do período (mês/ano)
   - Análise da qualidade dos dados
   - Contagem de linhas e validação do conteúdo
   - Identificação do nome da empresa

2. **Detecção de Duplicatas**:
   - Comparação por hash (duplicatas exatas)
   - Análise semântica com IA (duplicatas conceituais)
   - Score de confiança da duplicação

**Retorno:**
```json
{
  "is_duplicate": false,
  "analysis_id": "new_uuid",
  "metadata": {
    "file_hash": "sha256_hash",
    "estimated_month": 1,
    "estimated_year": 2024,
    "total_rows": 150,
    "has_financial_data": true,
    "company_name": "Empresa ABC LTDA",
    "data_quality_score": 0.85
  },
  "confidence_score": 0.0,
  "message": "Arquivo aprovado para processamento completo"
}
```

#### Etapa 2: Processamento Completo (`POST /api/monthly-analyses/process`)
```json
{
  "client_id": "uuid",
  "analysis_id": "uuid_from_precheck",
  "file_data": "base64_encoded_file",
  "file_name": "balancete_janeiro_2024.xlsx",
  "file_type": "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
  "force_process": false
}
```

**Processos da IA:**
1. **Mapeamento Inteligente de Colunas**:
   - Identificação automática das colunas relevantes
   - Mapeamento para campos padrão do sistema
   - Normalização de tipos de movimento (receita/despesa)

2. **Processamento de Dados**:
   - Inserção das entradas financeiras
   - Cálculo automático de totalizadores
   - Validação e tratamento de erros

3. **Geração de Resumo Executivo**:
   - Análise automática dos dados processados
   - Identificação de insights financeiros
   - Detecção de anomalias
   - Recomendações gerais

**Retorno:**
```json
{
  "success": true,
  "analysis_id": "uuid",
  "total_entries_processed": 150,
  "errors": [],
  "warnings": [],
  "ai_summary": "Análise do período de Janeiro/2024 para Empresa ABC LTDA...\n\n**Visão Geral:**\n- Total de 150 entradas processadas\n- Receitas: R$ 125.000,00 (45 entradas)\n- Despesas: R$ 87.500,00 (105 entradas)\n- Resultado: R$ 37.500,00 (positivo)\n\n**Principais Insights:**\n- Crescimento de 15% nas receitas comparado ao período anterior\n- Categoria de despesas 'Marketing' representa 23% do total\n- Fluxo de caixa positivo em todo o período\n\n**Recomendações:**\n- Monitorar despesas de marketing para otimização\n- Considerar investimentos adicionais em vendas\n- Manter controle rigoroso do fluxo de caixa"
}
```

### 3. Endpoints Disponíveis

#### GET `/api/monthly-analyses/`
Lista análises com filtros opcionais:
- `client_id`: Filtrar por cliente
- `status`: Filtrar por status
- `year`: Filtrar por ano
- `month`: Filtrar por mês

#### GET `/api/monthly-analyses/{analysis_id}`
Detalhes de uma análise específica

#### PUT `/api/monthly-analyses/{analysis_id}`
Atualizar dados da análise (status, resumo, metadados, etc.)

#### DELETE `/api/monthly-analyses/{analysis_id}`
Excluir análise e todos os dados relacionados

## Configuração e Deploy

### 1. Variáveis de Ambiente Necessárias
```bash
# IA
GOOGLE_AI_API_KEY=sua-chave-do-gemini

# Banco de Dados
SUPABASE_URL=https://seu-projeto.supabase.co
SUPABASE_ANON_KEY=sua-chave-anonima
SUPABASE_SERVICE_KEY=sua-chave-de-servico

# Autenticação
SECRET_KEY=sua-chave-secreta-jwt
```

### 2. Instalação de Dependências
```bash
pip install google-generativeai==0.3.2
pip install pandas==2.1.4
pip install sqlalchemy==2.0.23
```

### 3. Aplicação do Schema no Banco
Execute o script `database_schema.sql` completo no Supabase SQL Editor.

### 4. Configuração do Storage
Crie os buckets no Supabase Storage:
- `balancetes` (privado)
- `quarantine` (privado)

## Benefícios da Nova Arquitetura

### 1. **Organização Melhorada**
- Dados organizados por pacotes mensais discretos
- Histórico completo de cada análise
- Facilita comparações período a período

### 2. **Prevenção de Duplicatas**
- Detecção inteligente antes do processamento
- Economia de recursos computacionais
- Evita inconsistências nos dados

### 3. **Processamento Inteligente**
- Mapeamento automático de colunas
- Normalização consistente de dados
- Redução de erros humanos

### 4. **Insights Automáticos**
- Resumos executivos gerados por IA
- Identificação automática de padrões
- Recomendações baseadas nos dados

### 5. **Escalabilidade**
- Processamento assíncrono
- Arquitetura preparada para grandes volumes
- Monitoramento detalhado do status

## Migração de Dados Existentes

Para migrar dados do sistema antigo:

```sql
-- Criar análises mensais a partir dos balancetes existentes
INSERT INTO monthly_analyses (
    id, client_id, reference_month, reference_year,
    status, total_receitas, total_despesas, total_entries,
    created_by, created_at
)
SELECT 
    gen_random_uuid(),
    client_id,
    mes,
    ano,
    'completed',
    total_receitas,
    total_despesas,
    total_entries,
    created_by,
    created_at
FROM balancetes;

-- Atualizar financial_entries com analysis_id
UPDATE financial_entries fe
SET analysis_id = ma.id
FROM monthly_analyses ma
WHERE fe.client_id = ma.client_id
AND EXTRACT(MONTH FROM fe.report_date) = ma.reference_month
AND EXTRACT(YEAR FROM fe.report_date) = ma.reference_year;
```

## Próximos Passos

1. **Testes**: Implementar testes unitários e de integração
2. **Monitoramento**: Adicionar logs detalhados e métricas
3. **Cache**: Implementar cache Redis para consultas frequentes
4. **Webhooks**: Notificações automáticas de status de processamento
5. **Dashboard**: Atualizar frontend para usar a nova API
6. **Relatórios**: Gerar relatórios comparativos entre períodos

## Exemplos de Uso

### Frontend Integration
```typescript
// Pré-verificação
const preCheckResponse = await fetch('/api/monthly-analyses/pre-check', {
  method: 'POST',
  headers: {
    'Content-Type': 'application/json',
    'Authorization': `Bearer ${token}`
  },
  body: JSON.stringify({
    client_id: clientId,
    file_data: base64File,
    file_name: fileName,
    file_type: fileType
  })
});

const preCheck = await preCheckResponse.json();

if (!preCheck.is_duplicate) {
  // Processar arquivo
  const processResponse = await fetch('/api/monthly-analyses/process', {
    method: 'POST',
    headers: {
      'Content-Type': 'application/json',
      'Authorization': `Bearer ${token}`
    },
    body: JSON.stringify({
      client_id: clientId,
      analysis_id: preCheck.analysis_id,
      file_data: base64File,
      file_name: fileName,
      file_type: fileType
    })
  });
  
  const result = await processResponse.json();
  console.log('Processamento concluído:', result.ai_summary);
}
```

Esta arquitetura proporciona um sistema robusto, inteligente e escalável para o processamento de análises financeiras mensais.
