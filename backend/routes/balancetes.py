from fastapi import APIRouter, HTTPException, Depends, UploadFile, File, Form, status
from typing import List, Optional
from pydantic import BaseModel
from database import get_supabase_client
import logging
from core_processor import CoreProcessor

router = APIRouter(
    tags=["Balancetes"]
)
logger = logging.getLogger(__name__)

# --- Modelos Pydantic ---
class BalanceteResponse(BaseModel):
    id: int
    client_id: str
    ano: int
    mes: int
    total_receitas: float
    total_despesas: float
    lucro_bruto: float
    analysis_id: Optional[int] = None

class BalanceteUploadResponse(BaseModel):
    message: str
    file_upload_id: str
    analysis_id: int

# --- Nova Função de Lógica de Negócio ---
def update_balancete_totals_from_entries(supabase, analysis_id: int):
    """
    Calcula os totais de receitas e despesas a partir dos financial_entries
    e atualiza a tabela monthly_analyses (que é a nova fonte da verdade).
    """
    logger.info(f"Iniciando recálculo de totais para a analysis_id: {analysis_id}")
    try:
        # 1. Buscar todos os lançamentos para a análise específica
        entries_resp = supabase.table('financial_entries').select('movement_type', 'period_value').eq('analysis_id', analysis_id).execute()
        
        if not hasattr(entries_resp, 'data'):
            raise Exception("Resposta inválida do Supabase ao buscar financial_entries")

        entries = entries_resp.data or []
        logger.info(f"Encontrados {len(entries)} lançamentos para a análise {analysis_id}")

        # 2. Calcular os totais em Python para garantir precisão
        receita_total = sum(float(e['period_value']) for e in entries if e['movement_type'] == 'Receita')
        despesa_total = sum(float(e['period_value']) for e in entries if e['movement_type'] == 'Despesa')

        logger.info(f"Cálculo finalizado: Receitas={receita_total}, Despesas={despesa_total}")

        # 3. Atualizar a tabela monthly_analyses com os valores corretos
        update_payload = {
            'total_receitas': receita_total,
            'total_despesas': despesa_total,
            'status': 'completed' # Garante que o status final seja 'completed'
        }
        
        update_resp = supabase.table('monthly_analyses').update(update_payload).eq('id', analysis_id).execute()

        if hasattr(update_resp, 'data') and update_resp.data:
            logger.info(f"Tabela 'monthly_analyses' atualizada com sucesso para a analysis_id: {analysis_id}")
            return True
        else:
            logger.error(f"Falha ao atualizar 'monthly_analyses' para a analysis_id: {analysis_id}. Resposta: {getattr(update_resp, 'error', 'sem erro')}")
            return False

    except Exception as e:
        logger.exception(f"Erro crítico ao recalcular totais para analysis_id {analysis_id}: {e}")
        # Atualiza o status para 'failed' para indicar que algo deu errado no cálculo
        supabase.table('monthly_analyses').update({'status': 'failed', 'error_message': str(e)}).eq('id', analysis_id).execute()
        return False


@router.post("/upload", response_model=BalanceteUploadResponse)
async def upload_balancete(
    client_id: str = Form(...),
    file: UploadFile = File(...)
):
    """
    Recebe um PDF, salva no storage e DISPARA o processo de análise completa com a IA.
    Esta é a única porta de entrada para novos balancetes.
    """
    supabase = get_supabase_client()
    logger.info(f"Recebido upload de balancete para o cliente: {client_id}")
    try:
        # 1. Validação e Upload do Arquivo
        file_bytes = await file.read()
        if not file_bytes:
            raise HTTPException(status_code=400, detail="Arquivo PDF está vazio.")
            
        file_path = f"public/{client_id}/{file.filename}"
        supabase.storage.from_('balancetes').upload(file_path, file_bytes, {'content-type': file.content_type, 'upsert': 'true'})
        logger.info(f"Arquivo salvo no storage em: {file_path}")

        # 2. Criar o registro em 'file_uploads' para rastreamento
        upload_insert_resp = supabase.table('file_uploads').insert({
            'client_id': client_id,
            'file_name': file.filename,
            'file_path': file_path,
            'status': 'processing' # O status inicial é 'processando'
        }).execute()
        
        if not hasattr(upload_insert_resp, 'data') or not upload_insert_resp.data:
            raise HTTPException(status_code=500, detail="Falha ao criar registro de upload.")
            
        file_upload_id = upload_insert_resp.data[0]['id']
        logger.info(f"Registro de upload criado com ID: {file_upload_id}")

        # --- PONTO CRÍTICO DA CORREÇÃO ---
        # 3. Chamar o CoreProcessor para iniciar a análise da IA
        logger.info("Disparando o CoreProcessor para análise do PDF...")
        processor = CoreProcessor()
        result = await processor.process_pdf_file(
            file_content=file_bytes,
            client_id=client_id,
            file_upload_id=file_upload_id 
        )

        # 4. Verificar o resultado do processamento
        if result.get("status") == "error":
            # Se a IA falhar, atualiza o status e levanta um erro
            supabase.table('file_uploads').update({'status': 'failed', 'error_message': result.get('message')}).eq('id', file_upload_id).execute()
            raise HTTPException(status_code=500, detail=f"Erro no processamento da IA: {result.get('message')}")

        analysis_id = result.get("analysis_id")
        if not analysis_id:
            raise HTTPException(status_code=500, detail="Processamento da IA não retornou um ID de análise.")

        logger.info(f"Processo concluído com sucesso. Nova analysis_id: {analysis_id}")
        # Atualiza o registro de file_uploads com o analysis_id e marca como completed
        try:
            supabase.table('file_uploads').update({'analysis_id': analysis_id, 'status': 'completed'}).eq('id', file_upload_id).execute()
        except Exception as e:
            logger.exception(f"Falha ao atualizar file_uploads com analysis_id {analysis_id}: {e}")

        return {
            "message": "Balancete enviado e processado com sucesso!",
            "file_upload_id": file_upload_id,
            "analysis_id": analysis_id
        }

    except HTTPException:
        raise
    except Exception as e:
        logger.exception(f"Erro catastrófico no endpoint de upload: {e}")
        raise HTTPException(status_code=500, detail="Erro interno do servidor durante o upload.")

@router.get("/cliente/{client_id}", response_model=List[BalanceteResponse])
async def get_balancetes_cliente(client_id: str):
    """
    Busca os balancetes de um cliente a partir da tabela 'monthly_analyses',
    que agora é a nossa fonte da verdade.
    """
    supabase = get_supabase_client()
    try:
        # A busca agora é feita na tabela de análises, que contém os totais corretos
        response = supabase.table('monthly_analyses')\
            .select('id, client_id, reference_year, reference_month, total_receitas, total_despesas, lucro_bruto, id')\
            .eq('client_id', client_id)\
            .eq('status', 'completed')\
            .order('reference_year', desc=True)\
            .order('reference_month', desc=True)\
            .execute()

        if not hasattr(response, 'data'):
            return []
        
        # Mapeia a resposta para o formato esperado (BalanceteResponse)
        balancetes_formatados = []
        for analysis in response.data:
            balancetes_formatados.append({
                "id": analysis['id'], # Usamos o ID da análise como ID principal
                "client_id": analysis['client_id'],
                "ano": analysis['reference_year'],
                "mes": analysis['reference_month'],
                "total_receitas": analysis['total_receitas'],
                "total_despesas": analysis['total_despesas'],
                "lucro_bruto": analysis['lucro_bruto'],
                "analysis_id": analysis['id']
            })
            
        return balancetes_formatados
    except Exception as e:
        logger.exception(f"Erro ao buscar balancetes do cliente {client_id}: {e}")
        raise HTTPException(status_code=500, detail="Erro interno do servidor")


@router.get('/status/{file_upload_id}')
def get_upload_status(file_upload_id: str):
    """
    Endpoint de debug: retorna o registro em `file_uploads`, a `monthly_analyses` ligada
    (se existir) e as `financial_entries` relacionadas.
    Útil para verificar para onde os dados foram gravados após o upload.
    """
    supabase = get_supabase_client()
    try:
        fu = supabase.table('file_uploads').select('*').eq('id', file_upload_id).single().execute()
        if not fu or not getattr(fu, 'data', None):
            raise HTTPException(status_code=404, detail='file_upload not found')
        file_upload = fu.data

        analysis = None
        entries = []
        analysis_id = file_upload.get('analysis_id')
        if analysis_id:
            aresp = supabase.table('monthly_analyses').select('*').eq('id', analysis_id).single().execute()
            if aresp and getattr(aresp, 'data', None):
                analysis = aresp.data
            eres = supabase.table('financial_entries').select('*').eq('analysis_id', analysis_id).execute()
            if eres and getattr(eres, 'data', None):
                entries = eres.data

        return {
            'file_upload': file_upload,
            'analysis': analysis,
            'financial_entries_count': len(entries),
            'financial_entries_sample': entries[:50]
        }
    except HTTPException:
        raise
    except Exception as e:
        logger.exception(f'Erro ao buscar status do upload {file_upload_id}: {e}')
        raise HTTPException(status_code=500, detail='Erro interno ao buscar status do upload')
