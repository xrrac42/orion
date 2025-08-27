from fastapi import APIRouter, HTTPException, Depends, UploadFile, File, Form, status
from typing import List, Optional
from pydantic import BaseModel
from database import get_supabase_client
import logging
from pdf_processor import CoreProcessor
from datetime import datetime

router = APIRouter(
    tags=["Balancetes"]
)
logger = logging.getLogger(__name__)

# --- Modelos Pydantic (sem alteração) ---
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

@router.post("/upload", response_model=BalanceteUploadResponse)
async def upload_balancete(
    client_id: str = Form(...),
    ano: int = Form(...),
    mes: int = Form(...),
    file: UploadFile = File(...)
):
    """
    Salva o PDF no bucket, recupera o conteúdo salvo e então dispara a análise.
    """
    supabase = get_supabase_client()
    
    # --- LÓGICA DE RENOMEAR O ARQUIVO ---
    ano_curto = str(ano)[-2:]
    safe_original_name = "".join(c for c in file.filename if c.isalnum() or c in ('.', '_')).rstrip()
    new_file_name = f"{mes:02d}-{ano_curto}-{safe_original_name}"
    file_path = f"{client_id}/{new_file_name}"

    logger.info(f"Iniciando upload para o cliente: {client_id}")
    logger.info(f"Arquivo original: '{file.filename}', será salvo como: '{file_path}'")

    file_upload_id = None # Inicializa para o bloco de erro
    try:
        # 1. LER E SALVAR O ARQUIVO NO BUCKET
        file_bytes_to_upload = await file.read()
        if not file_bytes_to_upload:
            raise HTTPException(status_code=400, detail="Arquivo PDF está vazio.")
            
        supabase.storage.from_('balancetes').upload(
            path=file_path, 
            file=file_bytes_to_upload, 
            file_options={'content-type': file.content_type, 'upsert': 'true'} # Upsert true para facilitar testes
        )
        logger.info(f"Arquivo inserido com sucesso no bucket: {file_path}")

        # 2. CRIAR REGISTRO DE CONTROLE NA TABELA 'file_uploads'
        upload_insert_resp = supabase.table('file_uploads').insert({
            'client_id': client_id,
            'file_name': new_file_name,
            'file_path': file_path,
            'status': 'processing' # Status inicial válido conforme o schema do banco
        }).execute()
        
        if not hasattr(upload_insert_resp, 'data') or not upload_insert_resp.data:
            raise HTTPException(status_code=500, detail="Falha ao criar registro de controle do upload.")
            
        file_upload_id = upload_insert_resp.data[0]['id']
        logger.info(f"Registro de upload criado com ID: {file_upload_id}. Status: 'processing'")

        # 3. RECUPERAR O ARQUIVO DO BUCKET PARA ANÁLISE
        logger.info(f"Recuperando arquivo '{file_path}' do bucket para análise...")
        
        response = supabase.storage.from_('balancetes').download(path=file_path)
        file_content_from_bucket = response
        
        if not file_content_from_bucket:
             raise ValueError(f"Não foi possível recuperar o arquivo {file_path} do bucket para análise.")
        
        logger.info("Arquivo recuperado do bucket com sucesso. Disparando o CoreProcessor...")
        
        # 4. ENVIAR CONTEÚDO RECUPERADO PARA ANÁLISE
        processor = CoreProcessor()
        result = await processor.process_pdf_file(
            file_content=file_content_from_bucket,
            client_id=client_id,
            file_upload_id=file_upload_id,
            file_name=new_file_name
        )

        # 5. TRATAR O RESULTADO DA ANÁLISE
        if result.get("status") == "error":
            supabase.table('file_uploads').update({'status': 'failed', 'error_message': result.get('message')}).eq('id', file_upload_id).execute()
            raise HTTPException(status_code=500, detail=f"Erro no processamento da IA: {result.get('message')}")

        analysis_id = result.get("analysis_id")
        if not analysis_id:
            raise HTTPException(status_code=500, detail="Processamento da IA não retornou um ID de análise.")

        logger.info(f"Processo concluído com sucesso. Nova analysis_id: {analysis_id}")
        
        supabase.table('file_uploads').update({'analysis_id': analysis_id, 'status': 'completed'}).eq('id', file_upload_id).execute()

        return {
            "message": "Balancete enviado e processado com sucesso!",
            "file_upload_id": file_upload_id,
            "analysis_id": analysis_id
        }

    except HTTPException:
        raise
    except Exception as e:
        logger.exception(f"Erro catastrófico no endpoint de upload: {e}")
        if file_upload_id:
            supabase.table('file_uploads').update({'status': 'failed', 'error_message': str(e)}).eq('id', file_upload_id).execute()
        raise HTTPException(status_code=500, detail=f"Erro interno do servidor: {e}")


# O resto do arquivo (get_balancetes_cliente, get_upload_status) permanece o mesmo
@router.get("/cliente/{client_id}", response_model=List[BalanceteResponse])
async def get_balancetes_cliente(client_id: str):
    supabase = get_supabase_client()
    try:
        response = supabase.table('monthly_analyses')\
            .select('id, client_id, reference_year, reference_month, total_receitas, total_despesas, lucro_bruto, id')\
            .eq('client_id', client_id)\
            .eq('status', 'completed')\
            .order('reference_year', desc=True)\
            .order('reference_month', desc=True)\
            .execute()

        if not hasattr(response, 'data'):
            return []
        
        balancetes_formatados = []
        for analysis in response.data:
            balancetes_formatados.append({
                "id": analysis['id'],
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


@router.get('/check')
async def check_balancete(client_id: str, ano: int, mes: int):
    """Verifica se existe análise concluída para o client_id, ano e mês informados.
    Sempre retorna 200 com { exists: bool, analysis_id?: int, status?: str }.
    Isso evita 404 no frontend e permite o fluxo de confirmação/overwrite.
    """
    supabase = get_supabase_client()
    try:
        resp = supabase.table('monthly_analyses')\
            .select('id,status')\
            .eq('client_id', client_id)\
            .eq('reference_year', ano)\
            .eq('reference_month', mes)\
            .limit(1)\
            .execute()

        if not resp or not getattr(resp, 'data', None) or len(resp.data) == 0:
            # Não encontrou: retorna exists=false (HTTP 200) para facilitar o fluxo no frontend
            return { 'exists': False }

        row = resp.data[0]
        return { 'exists': True, 'analysis_id': row.get('id'), 'status': row.get('status') }
    except Exception as e:
        logger.exception(f'Erro ao verificar análise para cliente {client_id} {ano}/{mes}: {e}')
        # Em caso de erro interno, retornamos 500 — frontend deve mostrar erro
        raise HTTPException(status_code=500, detail='Erro interno ao verificar análise')
