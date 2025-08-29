from fastapi import APIRouter, HTTPException, Depends, UploadFile, File, Form, status, Body
from typing import List, Optional
from pydantic import BaseModel
from database import get_supabase_client, _to_float_safe
import json
import logging
from core_processor import CoreProcessor
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
    supabase = get_supabase_client()
    logger.info(f"Recebido upload de balancete para o cliente: {client_id}")
    try:
        file_bytes = await file.read()
        if not file_bytes:
            raise HTTPException(status_code=400, detail="Arquivo PDF está vazio.")

        file_path = f"public/{client_id}/{file.filename}"
        supabase.storage.from_('balancetes').upload(file_path, file_bytes, {'content-type': file.content_type, 'upsert': 'true'})
        
        upload_insert_resp = supabase.table('file_uploads').insert({
            'client_id': client_id, 'file_name': file.filename, 'file_path': file_path, 'status': 'processing'
        }).execute()
        
        if not hasattr(upload_insert_resp, 'data') or not upload_insert_resp.data:
            raise HTTPException(status_code=500, detail="Falha ao criar registro de upload.")
            
        file_upload_id = upload_insert_resp.data[0]['id']
        
        processor = CoreProcessor()
        
        # --- CORREÇÃO APLICADA AQUI ---
        # Garantindo que os nomes dos argumentos são os corretos
        result = await processor.process_pdf_file(
            file_content=file_bytes,
            client_id=client_id,
            file_upload_id=file_upload_id,
            file_name=file.filename,
            reference_year=ano, # <--- CORRIGIDO
            reference_month=mes # <--- CORRIGIDO
        )

        if result.get("status") == "error":
            supabase.table('file_uploads').update({'status': 'failed', 'error_message': result.get('message')}).eq('id', file_upload_id).execute()
            raise HTTPException(status_code=500, detail=f"Erro no processamento: {result.get('message')}")

        analysis_id = result.get("analysis_id")
        if not analysis_id:
            raise HTTPException(status_code=500, detail="Processamento não retornou um ID de análise.")

        return {
            "message": "Balancete enviado e processado com sucesso!",
            "file_upload_id": file_upload_id,
            "analysis_id": analysis_id
        }

    except Exception as e:
        logger.exception(f"Erro catastrófico no endpoint de upload: {e}")
        raise HTTPException(status_code=500, detail=str(e))


# O resto do arquivo (get_balancetes_cliente, get_upload_status) permanece o mesmo
@router.get("/cliente/{client_id}", response_model=List[BalanceteResponse])
async def get_balancetes_cliente(client_id: str):
    supabase = get_supabase_client()
    try:
        # Validate client_id early to avoid passing invalid UUIDs to the DB client
        if not client_id or client_id in ('undefined', 'null'):
            logger.warning(f'get_balancetes_cliente called with invalid client_id: {client_id}')
            raise HTTPException(status_code=400, detail='client_id inválido')

        # Optional: quick UUID format validation to return 400 instead of 500
        try:
            import uuid
            uuid.UUID(client_id)
        except Exception:
            logger.warning(f'get_balancetes_cliente received non-UUID client_id: {client_id}')
            raise HTTPException(status_code=400, detail='client_id deve ser um UUID válido')
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


@router.post('/debug/repopulate_entries')
def debug_repopulate_entries(payload: dict = Body(...)):
    """Debug helper: repopula `financial_entries` para uma analysis_id.

    Payload:
      { "analysis_id": "<uuid>", "entries": [ ... ] }

    If `entries` omitted, function will try to read `monthly_reports` for the same
    client_id/year/month and extract `financial_entries` stored there.
    """
    supabase = get_supabase_client()
    try:
        analysis_id = payload.get('analysis_id')
        if not analysis_id:
            raise HTTPException(status_code=400, detail='analysis_id é obrigatório')

        # 1) fetch analysis to get client_id/year/month
        aresp = supabase.table('monthly_analyses').select('id,client_id,reference_year,reference_month').eq('id', analysis_id).maybe_single().execute()
        if not getattr(aresp, 'data', None):
            raise HTTPException(status_code=404, detail='analysis_id não encontrada')
        analysis = aresp.data
        client_id = analysis.get('client_id')
        year = analysis.get('reference_year')
        month = analysis.get('reference_month')

        # 2) determine source entries
        entries_source = payload.get('entries')
        if entries_source is None:
            # try monthly_reports
            mr = supabase.table('monthly_reports').select('financial_entries').eq('client_id', client_id).eq('reference_year', year).eq('reference_month', month).maybe_single().execute()
            if not getattr(mr, 'data', None):
                raise HTTPException(status_code=404, detail='monthly_reports com financial_entries não encontrado')
            raw = mr.data.get('financial_entries')
            # stored as JSON string sometimes
            try:
                if isinstance(raw, str):
                    entries_source = json.loads(raw)
                else:
                    entries_source = raw or []
            except Exception:
                entries_source = []

        # 3) normalize & prepare inserts
        entries_to_insert = []
        for conta in entries_source:
            # tolerant mapping (similar to create_analysis_and_entries)
            def getf(*keys):
                for k in keys:
                    if k in conta and conta[k] is not None:
                        return conta[k]
                return None

            valor_debito = _to_float_safe(getf('valor_debito','debito'))
            valor_credito = _to_float_safe(getf('valor_credito','credito'))
            single_val = _to_float_safe(getf('valor','value') or 0)

            if valor_debito == 0 and valor_credito == 0 and single_val != 0:
                if single_val < 0:
                    movement_type = 'Despesa'
                    period_value = abs(single_val)
                else:
                    movement_type = 'Receita'
                    period_value = single_val
            else:
                if valor_debito > 0:
                    movement_type = 'Despesa'
                    period_value = valor_debito
                else:
                    movement_type = 'Receita'
                    period_value = valor_credito

            main_group = getf('grupo_principal','main_group','grupo')
            subgroup_1 = getf('subgroup_1','subgrupo','categoria') or 'Outros'
            specific_account = getf('conta_especifica','specific_account','conta')

            if period_value and period_value > 0:
                entries_to_insert.append({
                    'analysis_id': analysis_id,
                    'client_id': client_id,
                    'report_date': f"{year:04d}-{int(month):02d}-01",
                    'main_group': main_group,
                    'subgroup_1': subgroup_1,
                    'specific_account': specific_account,
                    'movement_type': movement_type,
                    'period_value': period_value
                })

        # 4) replace existing entries and insert
        supabase.table('financial_entries').delete().eq('analysis_id', analysis_id).execute()
        inserted = 0
        if entries_to_insert:
            ins = supabase.table('financial_entries').insert(entries_to_insert).execute()
            if getattr(ins, 'data', None):
                inserted = len(ins.data)
        # update summary
        try:
            supabase.table('monthly_analyses').update({'total_entries': inserted}).eq('id', analysis_id).execute()
        except Exception:
            logger.debug('Não foi possível atualizar total_entries (campo pode não existir)')

        return {'inserted': inserted, 'sample': entries_to_insert[:10]}
    except HTTPException:
        raise
    except Exception as e:
        logger.exception(f'Erro em debug_repopulate_entries: {e}')
        raise HTTPException(status_code=500, detail=str(e))
