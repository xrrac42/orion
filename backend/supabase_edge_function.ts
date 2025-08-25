/**
 * Supabase Edge Function para processar balancetes
 * Este arquivo deve ser implantado como uma Edge Function no Supabase
 * 
 * Caminho: supabase/functions/process-balancete/index.ts
 */

// This file is a Supabase Edge Function (Deno runtime). Next.js typechecker
// can't resolve Deno std imports. Keep the original import here for the
// function runtime but avoid letting Next.js try to typecheck it.
// import { serve } from "https://deno.land/std@0.168.0/http/server.ts"
import { createClient } from 'https://esm.sh/@supabase/supabase-js@2'
// @ts-nocheck

const corsHeaders = {
  'Access-Control-Allow-Origin': '*',
  'Access-Control-Allow-Headers': 'authorization, x-client-info, apikey, content-type',
}

interface WebhookPayload {
  type: string
  table: string
  record: any
  schema: string
  old_record: any
}

serve(async (req) => {
  // Handle CORS
  if (req.method === 'OPTIONS') {
    return new Response('ok', { headers: corsHeaders })
  }

  try {
    // Inicializar cliente Supabase
    const supabaseUrl = Deno.env.get('SUPABASE_URL')!
    const supabaseKey = Deno.env.get('SUPABASE_SERVICE_ROLE_KEY')!
    const supabase = createClient(supabaseUrl, supabaseKey)

    // Parse do payload do webhook
    const payload: WebhookPayload = await req.json()
    
    console.log('Webhook recebido:', payload)

    // Verificar se é um evento de upload de arquivo
    if (payload.type !== 'INSERT' || payload.table !== 'objects') {
      return new Response(
        JSON.stringify({ message: 'Evento ignorado' }),
        { headers: { ...corsHeaders, 'Content-Type': 'application/json' } }
      )
    }

    const file = payload.record
    
    // Verificar se é um PDF no bucket correto
    if (!file.name?.endsWith('.pdf') || file.bucket_id !== 'balancetes') {
      return new Response(
        JSON.stringify({ message: 'Arquivo ignorado - não é PDF ou bucket incorreto' }),
        { headers: { ...corsHeaders, 'Content-Type': 'application/json' } }
      )
    }

    // Extrair client_id do caminho do arquivo
    const pathParts = file.name.split('/')
    if (pathParts.length < 2) {
      throw new Error('Estrutura de pasta inválida')
    }
    
    const clientId = pathParts[0]
    
    console.log(`Processando arquivo ${file.name} para cliente ${clientId}`)

    // Baixar arquivo do Storage
    const { data: fileData, error: downloadError } = await supabase.storage
      .from('balancetes')
      .download(file.name)

    if (downloadError) {
      throw new Error(`Erro ao baixar arquivo: ${downloadError.message}`)
    }

    // Converter para texto (aqui você integraria com uma biblioteca de PDF)
    // Por ora, vamos simular o processamento
    const textContent = await extractTextFromPDF(fileData)
    
    // Analisar com LLM (Gemini)
    const structuredData = await analyzeWithGemini(textContent)
    
    // Processar e armazenar dados
    const processedEntries = await processAndStore(structuredData, clientId, supabase)

    // Resposta de sucesso
    return new Response(
      JSON.stringify({
        success: true,
        message: 'Balancete processado com sucesso',
        client_id: clientId,
        file_name: file.name,
        entries_processed: processedEntries.length
      }),
      { headers: { ...corsHeaders, 'Content-Type': 'application/json' } }
    )

  } catch (error) {
    console.error('Erro no processamento:', error)
    
    return new Response(
      JSON.stringify({
        success: false,
        error: error.message
      }),
      { 
        status: 500,
        headers: { ...corsHeaders, 'Content-Type': 'application/json' } 
      }
    )
  }
})

/**
 * Extrai texto de arquivo PDF
 * NOTA: Esta é uma implementação placeholder
 * Em produção, use uma biblioteca adequada para Deno
 */
async function extractTextFromPDF(fileData: Blob): Promise<string> {
  // Placeholder - implementar extração real de PDF
  console.log('Extraindo texto do PDF...')
  
  // Simular extração de texto
  return `
    BALANCETE DE VERIFICAÇÃO
    EMPRESA EXEMPLO LTDA
    PERÍODO: 01/01/2024 a 31/12/2024
    
    RECEITAS
    Receita de Vendas                     50000.00
    Receita de Serviços                   30000.00
    
    CUSTOS E DESPESAS
    Custo dos Produtos Vendidos          -20000.00
    Despesas Administrativas              -15000.00
    Despesas Comerciais                   -10000.00
  `
}

/**
 * Analisa texto com Gemini API
 */
async function analyzeWithGemini(textContent: string): Promise<any> {
  const geminiApiKey = Deno.env.get('GEMINI_API_KEY')
  
  if (!geminiApiKey) {
    throw new Error('GEMINI_API_KEY não configurada')
  }

  const prompt = `
Analise o seguinte texto extraído de um balancete contábil. Sua tarefa é extrair as seguintes informações:

1. O nome da empresa cliente
2. A data final do período do balancete (formato YYYY-MM-DD)
3. Uma lista de todas as contas de resultado (Receitas, Custos e Despesas) que possuem movimentação no período

Para cada conta, retorne sua hierarquia de grupos. O formato de saída deve ser um único objeto JSON com a seguinte estrutura:

{
  "cliente": "Nome da Empresa",
  "data_final": "YYYY-MM-DD",
  "contas": [
    {
      "grupo_principal": "RECEITAS" ou "CUSTOS E DESPESAS",
      "subgrupo_1": "Primeiro Subgrupo (se existir)",
      "conta_especifica": "Nome da Conta Final",
      "valor_debito": 0.00,
      "valor_credito": 1234.56
    }
  ]
}

Texto do balancete:
"""
${textContent}
"""

RESPOSTA (apenas JSON):
`

  const response = await fetch(
    `https://generativelanguage.googleapis.com/v1beta/models/gemini-1.5-flash:generateContent?key=${geminiApiKey}`,
    {
      method: 'POST',
      headers: {
        'Content-Type': 'application/json',
      },
      body: JSON.stringify({
        contents: [
          {
            parts: [
              {
                text: prompt
              }
            ]
          }
        ],
        generationConfig: {
          temperature: 0.1,
          topK: 1,
          topP: 0.8,
          maxOutputTokens: 8192,
        }
      })
    }
  )

  if (!response.ok) {
    throw new Error(`Erro na API Gemini: ${response.statusText}`)
  }

  const result = await response.json()
  
  if (result.candidates && result.candidates[0]?.content?.parts[0]?.text) {
    const textResponse = result.candidates[0].content.parts[0].text
    
    // Extrair JSON da resposta
    const jsonMatch = textResponse.match(/\{[\s\S]*\}/)
    if (jsonMatch) {
      return JSON.parse(jsonMatch[0])
    }
  }
  
  throw new Error('Não foi possível extrair dados estruturados do LLM')
}

/**
 * Processa dados estruturados e armazena no banco
 */
async function processAndStore(structuredData: any, clientId: string, supabase: any): Promise<any[]> {
  const entries = []
  
  for (const conta of structuredData.contas) {
    let movementType: string
    let periodValue: number
    
    // Aplicar regras de negócio
    if (conta.grupo_principal === 'RECEITAS') {
      movementType = 'Receita'
      periodValue = parseFloat(conta.valor_credito) || 0
    } else {
      movementType = 'Despesa' 
      periodValue = parseFloat(conta.valor_debito) || 0
    }
    
    if (periodValue > 0) {
      const entry = {
        client_id: clientId,
        report_date: structuredData.data_final,
        main_group: conta.grupo_principal,
        subgroup_1: conta.subgrupo_1 || null,
        specific_account: conta.conta_especifica,
        movement_type: movementType,
        period_value: periodValue,
        created_at: new Date().toISOString()
      }
      
      entries.push(entry)
    }
  }

  // Inserir no banco de dados
  if (entries.length > 0) {
    const { error } = await supabase
      .from('financial_entries')
      .insert(entries)
    
    if (error) {
      throw new Error(`Erro ao inserir no banco: ${error.message}`)
    }
  }

  return entries
}

/* Para deployar esta função:
1. Criar o arquivo em supabase/functions/process-balancete/index.ts
2. Executar: supabase functions deploy process-balancete
3. Configurar webhook no Storage para chamar esta função
*/
