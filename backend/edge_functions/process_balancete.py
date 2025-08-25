import os
import json
import requests
from supabase import create_client
from dotenv import load_dotenv

load_dotenv(os.path.join(os.path.dirname(__file__), "../.env"))

SUPABASE_URL = os.getenv("SUPABASE_URL")
SUPABASE_SERVICE_KEY = os.getenv("SUPABASE_SERVICE_KEY")
GEMINI_API_KEY = os.getenv("GEMINI_API_KEY")

supabase = create_client(SUPABASE_URL, SUPABASE_SERVICE_KEY)

# Função para ser chamada por trigger do Supabase Storage
# Espera receber o caminho do arquivo PDF no Storage

def handler(event, context):
    file_path = event["file_path"]
    client_id = event.get("client_id")
    # 1. Baixar PDF do Storage
    res = supabase.storage.from_("balancetes").download(file_path)
    if not res:
        return {"error": "Arquivo não encontrado no storage."}
    pdf_bytes = res.read()

    # 2. Extrair texto do PDF
    from PyPDF2 import PdfReader
    import io
    reader = PdfReader(io.BytesIO(pdf_bytes))
    texto = "\n".join(page.extract_text() or '' for page in reader.pages)

    # 3. Chamar Gemini API
    prompt = f"""
Analise o texto de um balancete contábil brasileiro. Sua tarefa é retornar um objeto JSON.\nIdentifique o nome da empresa cliente e a data final do período (formato AAAA-MM-DD).\nDepois, encontre todas as contas de resultado (Receitas, Custos, Despesas) que tenham valores nas colunas \"Débito\" e \"Crédito\" do período.\nPara cada conta, capture a hierarquia de grupos acima dela. A estrutura do JSON de saída deve ser:\n{{\n  \"cliente\": \"Nome da Empresa\",\n  \"data_final\": \"AAAA-MM-DD\",\n  \"contas\": [\n    {{\n      \"grupo_principal\": \"Grupo Pai (ex: RECEITAS)\",\n      \"subgrupo_1\": \"Subgrupo (ex: RECEITAS OPERACIONAIS)\",\n      \"conta_especifica\": \"Nome da Conta\",\n      \"valor_debito\": 123.45,\n      \"valor_credito\": 123.45\n    }},\n  ]\n}}\nIgnore totais de grupos e contas do Ativo e Passivo. Foque apenas em contas de resultado com movimentação.\nTexto para análise:\n""" + texto
    gemini_url = "https://generativelanguage.googleapis.com/v1beta/models/gemini-pro:generateContent?key=" + GEMINI_API_KEY
    gemini_payload = {"contents": [{"parts": [{"text": prompt}]}]}
    gemini_headers = {"Content-Type": "application/json"}
    gemini_resp = requests.post(gemini_url, headers=gemini_headers, data=json.dumps(gemini_payload))
    gemini_json = gemini_resp.json()
    # Extrair JSON do texto retornado
    import re
    import ast
    match = re.search(r'\{.*\}', gemini_json["candidates"][0]["content"]["parts"][0]["text"], re.DOTALL)
    if not match:
        return {"error": "Gemini não retornou JSON válido."}
    llm_json = ast.literal_eval(match.group(0))

    # 4. Aplicar regras de negócio e transformar para formato final
    saida_final = []
    for conta in llm_json["contas"]:
        tipo = "Receita" if conta["grupo_principal"] == "RECEITAS" else "Despesa"
        valor = conta["valor_credito"] if tipo == "Receita" else conta["valor_debito"]
        saida_final.append({
            "client_id": client_id,
            "report_date": llm_json["data_final"],
            "main_group": conta["grupo_principal"],
            "subgroup_1": conta["subgrupo_1"],
            "specific_account": conta["conta_especifica"],
            "movement_type": tipo,
            "period_value": valor,
            "original_data": json.dumps(conta)
        })
    # 5. Tentar obter/gerar analysis_id e anexar a cada entrada
    analysis_id = None
    try:
        # Se o path contém ano-mes no nome, tentar inferir ou buscar balancete existente
        # Aqui não temos balancete_id, então fallback: criar um monthly_analysis simples
        # Extrair ano-mes da data_final
        data_final = llm_json.get('data_final')
        ref_year = None
        ref_month = None
        if data_final:
            parts = data_final.split('-')
            if len(parts) >= 2:
                ref_year = int(parts[0])
                ref_month = int(parts[1])

        analysis_payload = {
            'client_id': client_id,
            'report_date': data_final or None,
            'reference_month': ref_month,
            'reference_year': ref_year,
            'client_name': client_id,
            'status': 'completed'
        }
        create_resp = supabase.table('monthly_analyses').insert(analysis_payload).execute()
        if create_resp and getattr(create_resp, 'data', None) and len(create_resp.data) > 0:
            analysis_id = create_resp.data[0].get('id')
    except Exception:
        analysis_id = None

    if analysis_id:
        for item in saida_final:
            item['analysis_id'] = analysis_id

    # 6. Inserir no banco
    supabase.table("financial_entries").insert(saida_final).execute()
    return {"ok": True, "itens_inseridos": len(saida_final), 'analysis_id': analysis_id}
