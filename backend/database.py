# backend/database.py

import os
import json
import logging
from datetime import datetime
import re
from typing import Dict, Any, Generator
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from dotenv import load_dotenv
from supabase import create_client, Client
from postgrest.exceptions import APIError

load_dotenv()
logger = logging.getLogger(__name__)

SUPABASE_URL = os.getenv("SUPABASE_URL")
SUPABASE_SERVICE_KEY = os.getenv("SUPABASE_SERVICE_KEY")

def get_supabase_client() -> Client:
    return create_client(SUPABASE_URL, SUPABASE_SERVICE_KEY)


# --- SQLAlchemy session helper (used by routers that depend on get_db) ---
DATABASE_URL = os.getenv("DATABASE_URL")
SessionLocal = None
engine = None
if DATABASE_URL:
    try:
        engine = create_engine(DATABASE_URL)
        SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)
    except Exception:
        logger.exception("Falha ao criar engine SQLAlchemy a partir de DATABASE_URL")

def get_db() -> Generator:
    """Dependency for FastAPI: yields a SQLAlchemy Session if DATABASE_URL is configured.
    If DATABASE_URL is missing, raises a RuntimeError with a clear message.
    """
    if SessionLocal is None:
        raise RuntimeError("DATABASE_URL não está configurada; get_db não está disponível.")
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()

# Safety: ensure get_db is exported even if earlier edits removed it.
if 'get_db' not in globals():
    def get_db():
        """Fallback dependency: raises explicit error when DATABASE_URL is not configured."""
        raise RuntimeError("DATABASE_URL não está configurada; get_db não está disponível.")
    globals()['get_db'] = get_db
class AnalysisResult:
    def __init__(self, id):
        self.id = id

def _to_float_safe(v: Any) -> float:
    """
    Parse numbers coming from Brazilian-formatted strings like
    '1.496.228,79C' or '3.017.707,10' and return a float.
    Removes letters, thousand separators and converts comma decimal to dot.
    Falls back to 0.0 on failure.
    """
    try:
        if v is None:
            return 0.0
        if isinstance(v, (int, float)):
            return float(v)
        s = str(v).strip()
        # Remove trailing letters and non-numeric symbols except .,- and ,
        # common suffixes like 'C' or 'D' will be removed
        s = re.sub(r"[A-Za-z\s]", '', s)
        # Remove thousand separators (dots) and normalize decimal comma
        s = s.replace('.', '').replace(',', '.')
        # Extract the first numeric substring (handles negative values)
        m = re.search(r'-?\d+(?:\.\d+)?', s)
        if not m:
            return 0.0
        return float(m.group(0))
    except Exception:
        return 0.0

async def create_analysis_and_entries(client_id: str, file_upload_id: str, analysis_data: dict):
    """
    Cria a análise principal e insere todos os seus lançamentos financeiros detalhados.
    """
    supabase = get_supabase_client()
    
    # --- 1. Prepara os dados para a tabela principal 'monthly_analyses' ---
    # Accept multiple parser shapes: prefer canonical 'resumo_periodo',
    # but fall back to older parser keys like 'resumo_balancete' and 'valores_periodo'.
    summary = analysis_data.get('resumo_periodo', {}) or {}
    # If parser used different naming, try to normalize into 'summary'
    if not summary:
        # Example shape seen in tests:
        # { "resumo_balancete": { "ativo": "...", "passivo": "...", "despesa": "0,00D", "receita": "1.313.664,67D" },
        #   "valores_periodo": { "receita": "1.409.032,87C", "despesa_custo": "1.408.776,98D", "lucro": "255,89" } }
        rb = analysis_data.get('resumo_balancete') or {}
        vp = analysis_data.get('valores_periodo') or {}
        if rb or vp:
            # build a canonical summary mapping
            summary = {}
            # prefer valores_periodo for period totals when available
            if vp:
                if 'receita' in vp:
                    summary['total_receitas'] = vp.get('receita')
                if 'despesa_custo' in vp:
                    summary['total_despesas_custos'] = vp.get('despesa_custo')
                elif 'despesa' in vp:
                    summary['total_despesas_custos'] = vp.get('despesa')
                # optionally include lucro
                if 'lucro' in vp:
                    summary['lucro'] = vp.get('lucro')
            # fallbacks from resumo_balancete
            if rb and 'receita' in rb and 'total_receitas' not in summary:
                summary['total_receitas'] = rb.get('receita')
            if rb and 'despesa' in rb and 'total_despesas_custos' not in summary:
                summary['total_despesas_custos'] = rb.get('despesa')
            # write back into analysis_data for downstream code
            analysis_data['resumo_periodo'] = summary
    report_date_str = analysis_data.get("data_final")
    
    try:
        dt_obj = datetime.strptime(report_date_str, '%Y-%m-%d')
    except (ValueError, TypeError):
        try:
            dt_obj = datetime.strptime(report_date_str, '%d/%m/%Y')
        except (ValueError, TypeError):
            dt_obj = datetime.utcnow()

    report_date_iso = dt_obj.strftime('%Y-%m-%d')

    # Prioritize the year/month provided by the upload form (analysis_data)
    # Fallback order: form values -> parsed PDF date -> current UTC date
    now = datetime.utcnow()
    reference_year = analysis_data.get('reference_year') or (dt_obj.year if dt_obj else now.year)
    reference_month = analysis_data.get('reference_month') or (dt_obj.month if dt_obj else now.month)
    
    # Build payload but only include totals when parser provided them (avoid overwriting existing values with zeros)
    analysis_payload = {
        "client_id": client_id,
        "client_name": analysis_data.get("cliente", "Não Identificado"),
        "reference_year": reference_year,
        "reference_month": reference_month,
        "report_date": report_date_iso,
        "status": "completed",
        "source_file_path": f"public/{client_id}/{analysis_data.get('file_name', '')}",
        "source_file_name": analysis_data.get('file_name', 'arquivo.pdf'),
    }
    # Only set totals if the parser provided values (presence in dict)
    if 'total_receitas' in summary:
        analysis_payload['total_receitas'] = _to_float_safe(summary.get('total_receitas'))
    if 'total_despesas_custos' in summary:
        analysis_payload['total_despesas'] = _to_float_safe(summary.get('total_despesas_custos'))
    # DB defines 'lucro_bruto' as a generated column; do not attempt to insert into it.
    if 'lucro' in summary:
        logger.debug('Parser provided lucro=%s but lucro_bruto is a generated DB column; skipping explicit persist.', summary.get('lucro'))
    # Include raw analysis JSON and file_upload_id if present so we can inspect parser output later
    if 'raw_analysis' in analysis_data and analysis_data.get('raw_analysis') is not None:
        analysis_payload['raw_analysis'] = analysis_data.get('raw_analysis')
    # file_upload_id may be passed as the second parameter to this function
    if file_upload_id:
        analysis_payload['file_upload_id'] = file_upload_id

    # processing_started_at: use provided or set now
    if 'processing_started_at' in analysis_data and analysis_data.get('processing_started_at'):
        analysis_payload['processing_started_at'] = analysis_data.get('processing_started_at')
    else:
        analysis_payload['processing_started_at'] = datetime.utcnow().isoformat()

    # --- 2. Salva a análise principal (Upsert) ---
    analysis_resp = supabase.table("monthly_analyses").upsert(
        analysis_payload, on_conflict="client_id,reference_year,reference_month"
    ).execute()
    # Debug: log the payload we sent and the DB's response to detect mismatches
    try:
        logger.info('Upsert payload for monthly_analyses: %s', analysis_payload)
        logger.info('Upsert response: %s', getattr(analysis_resp, 'data', None))
    except Exception:
        logger.exception('Falha ao logar payload/response do upsert')
    
    if not hasattr(analysis_resp, "data") or not analysis_resp.data:
        raise Exception(f"Falha ao salvar a análise principal: {getattr(analysis_resp, 'error', 'Erro desconhecido')}")
    
    analysis_id = analysis_resp.data[0]["id"]
    logger.info(f"Análise (ID: {analysis_id}) salva. Processando lançamentos detalhados...")

    # --- 3. Limpa lançamentos antigos para evitar duplicatas em reprocessamentos ---
    supabase.table('financial_entries').delete().eq('analysis_id', analysis_id).execute()

    # --- 4. Prepara e insere a lista de 'financial_entries' ---
    entries_to_insert = []

    # Debug: log a small sample of incoming entries to aid diagnostics
    sample_entries = analysis_data.get('financial_entries')
    if sample_entries:
        try:
            logger.info('Received %d financial_entries; sample[0]=%s', len(sample_entries), sample_entries[0])
        except Exception:
            logger.info('Received financial_entries (could not pretty-print sample)')

    def _map_main_group(raw: str, inferred_movement: str) -> str:
        if not raw:
            return 'RECEITAS' if inferred_movement and inferred_movement.lower().startswith('r') else 'CUSTOS E DESPESAS'
        r = str(raw).upper()
        if 'RECEITA' in r:
            return 'RECEITAS'
        if 'DEDU' in r:
            return 'DEDUÇÕES DA RECEITA'
        if 'CUSTO' in r and 'DESP' not in r:
            return 'CUSTOS'
        if 'DESP' in r:
            return 'DESPESAS'
        if 'CUSTOS E DESPESAS' in r:
            return 'CUSTOS E DESPESAS'
        return 'RECEITAS' if inferred_movement and inferred_movement.lower().startswith('r') else 'CUSTOS E DESPESAS'

    def _map_movement_type(raw: str) -> str:
        if not raw:
            return 'Despesa'
        r = str(raw).strip().lower()
        if 'receit' in r or r == 'r':
            return 'Receita'
        if 'custo' in r:
            return 'Custo'
        if 'deduc' in r or 'dedução' in r:
            return 'Dedução'
        return 'Despesa'

    for conta in analysis_data.get("financial_entries", []):
        # Determine movement type early so recovery logic can reference it
        movement_raw = conta.get('movement_type') or conta.get('tipo') or conta.get('movimento')
        movement_type = _map_movement_type(movement_raw)

        # specific account name - accept several keys (used in logs/recovery)
        specific_account = conta.get('specific_account') or conta.get('conta_especifica') or conta.get('conta') or conta.get('descricao') or ''

        # Support multiple possible field names from different parsers
        period_value = None
        if 'period_value' in conta:
            period_value = _to_float_safe(conta.get('period_value'))
        elif 'valor' in conta:
            period_value = _to_float_safe(conta.get('valor'))
        else:
            # Fall back to debit/credit style
            valor_debito = _to_float_safe(conta.get("valor_debito", 0.0))
            valor_credito = _to_float_safe(conta.get("valor_credito", 0.0))
            if valor_debito > 0:
                period_value = valor_debito
            else:
                period_value = valor_credito

        # If parser produced zero, try to recover a numeric value from original_data
        if not period_value or period_value == 0:
            original = conta.get('original_data') or {}

            def _parse_localized_number(val) -> float:
                if val is None:
                    return 0.0
                # If already numeric
                try:
                    return float(val)
                except Exception:
                    s = str(val)
                    # Remove trailing letters like 'C' and whitespace
                    s = s.strip().upper().replace('C', '').replace('D', '')
                    # Remove thousand separators and normalize decimal comma
                    s = s.replace('.', '').replace(' ', '').replace(',', '.')
                    # Keep only digits, minus and dot
                    m = re.search(r'[-\d.]+', s)
                    if not m:
                        return 0.0
                    try:
                        return float(m.group(0))
                    except Exception:
                        return 0.0

            recovered = 0.0
            # Prefer debit/credit fields if present and movement suggests it
            if isinstance(original, dict):
                # Look for common localized fields
                if movement_type and movement_type.lower().startswith('d'):
                    recovered = _parse_localized_number(original.get('debito') or original.get('debts') or original.get('debit'))
                    if recovered == 0.0:
                        recovered = _parse_localized_number(original.get('valor') or original.get('saldo_atual') or original.get('saldo'))
                else:
                    recovered = _parse_localized_number(original.get('credito') or original.get('credit') or original.get('credito_ou'))
                    if recovered == 0.0:
                        recovered = _parse_localized_number(original.get('valor') or original.get('saldo_atual') or original.get('saldo'))

            if recovered and recovered > 0:
                period_value = recovered
                logger.debug('Recovered period_value=%s from original_data for account=%s', period_value, specific_account)
            else:
                # Still zero after attempts: log and skip to avoid inserting meaningless zeros
                logger.debug('Skipping entry with zero period_value and no recoverable original_data: %s', conta)
                continue

        # main_group: try explicit or infer
        main_raw = conta.get('main_group') or conta.get('grupo_principal')
        mapped_main = _map_main_group(main_raw, movement_type)

        entries_to_insert.append({
            "analysis_id": analysis_id,
            "client_id": client_id,
            "report_date": report_date_iso,
            "main_group": mapped_main,
            "subgroup_1": conta.get("subgroup_1"),
            "specific_account": specific_account,
            "movement_type": movement_type,
            "period_value": period_value,
            "original_data": conta.get('original_data') or conta
        })

    if entries_to_insert:
        logger.info('Inserting %d financial_entries (sample=%s)', len(entries_to_insert), entries_to_insert[:3])
        insert_resp = supabase.table('financial_entries').insert(entries_to_insert).execute()
        if not hasattr(insert_resp, "data"):
            # Se a inserção falhar, lança um erro para que o processo seja interrompido
            raise Exception(f"Falha ao inserir financial_entries: {getattr(insert_resp, 'error', 'Erro desconhecido')}")
        logger.info(f"Inseridos {len(insert_resp.data)} lançamentos para a análise {analysis_id}.")

    # mark monthly_analyses processing as completed and add a completion timestamp
    try:
        supabase.table('monthly_analyses').update({
            'processing_completed_at': datetime.utcnow().isoformat()
        }).eq('id', analysis_id).execute()
    except Exception:
        logger.exception('Falha ao atualizar processing_completed_at para monthly_analyses id=%s', analysis_id)

    # Some DB setups have triggers that recompute totals from financial_entries and
    # may overwrite parser-provided totals. If parser provided totals, re-apply them
    # after inserting entries so the stored totals match raw_analysis.
    try:
        totals_update = {}
        provided_total_receitas = analysis_payload.get('total_receitas') if 'analysis_payload' in locals() else None
        provided_total_despesas = analysis_payload.get('total_despesas') if 'analysis_payload' in locals() else None
        if provided_total_receitas is not None:
            totals_update['total_receitas'] = provided_total_receitas
        if provided_total_despesas is not None:
            totals_update['total_despesas'] = provided_total_despesas

        if totals_update:
            # also log intent for audit
            logger.info('Re-applying parser-provided totals to monthly_analyses id=%s: %s', analysis_id, totals_update)
            supabase.table('monthly_analyses').update(totals_update).eq('id', analysis_id).execute()
    except Exception:
        logger.exception('Falha ao re-aplicar totais para monthly_analyses id=%s', analysis_id)

    # --- 5. Atualiza o status do upload do arquivo ---
    supabase.table('file_uploads').update({
        'status': 'completed',
        'processing_completed_at': datetime.utcnow().isoformat()
    }).eq('id', file_upload_id).execute()

    return AnalysisResult(id=analysis_id)