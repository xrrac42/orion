# backend/database.py
import os
from dotenv import load_dotenv
from supabase import create_client, Client
import logging
from typing import Dict, Any
from datetime import datetime
import json
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from typing import Generator

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

def _to_float_safe(v: Any) -> float:
    """
    Converte uma string de moeda (formato brasileiro ou americano) para float de forma segura.
    """
    try:
        if v is None:
            return 0.0
        if isinstance(v, (int, float)):
            return float(v)
        
        s = str(v).strip()
        
        # Se a string contém vírgula, assume que é o separador decimal (formato BR)
        if ',' in s:
            # Remove pontos de milhar e substitui a vírgula decimal por ponto
            s = s.replace('.', '').replace(',', '.')
        # Se não tem vírgula, mas tem ponto, assume que é um formato já compatível
        # Apenas removemos vírgulas que possam ser usadas como separador de milhar (formato US)
        else:
            s = s.replace(',', '')
            
        return float(s)
    except (ValueError, TypeError):
        return 0.0
    
def save_monthly_report(client_id: str, file_upload_id: str, extracted_data: Dict[str, Any]):
    """
    Cria ou atualiza um relatório mensal na tabela 'monthly_reports'.
    """
    supabase = get_supabase_client()
    
    summary = extracted_data.get('resumo_periodo', {})
    report_date_str = extracted_data.get('data_final')
    
    try:
        dt_obj = datetime.fromisoformat(report_date_str)
        year = dt_obj.year
        month = dt_obj.month
    except (ValueError, TypeError):
        now = datetime.utcnow()
        year = now.year
        month = now.month

    report_payload = {
        "client_id": client_id,
        "reference_year": year,
        "reference_month": month,
        "report_date": report_date_str,
        "client_name": extracted_data.get('cliente'),
        "total_receitas": _to_float_safe(summary.get('total_receitas')),
        "total_despesas": _to_float_safe(summary.get('total_despesas_custos')),
        "lucro_periodo": _to_float_safe(summary.get('lucro_periodo')),
        "financial_entries": json.dumps(extracted_data.get('financial_entries', [])),
        "file_upload_id": file_upload_id
    }

    # 'Upsert' para inserir ou atualizar o relatório
    response = supabase.table("monthly_reports").upsert(
        report_payload, 
        on_conflict="client_id,reference_year,reference_month"
    ).execute()
    
    if not response.data:
        raise Exception(f"Falha ao salvar o relatório no banco: {getattr(response, 'error', 'Erro desconhecido')}")

    logger.info(f"Relatório para cliente {client_id} (Mês/Ano: {month}/{year}) salvo com sucesso.")
    return response.data[0]


class AnalysisResult:
    def __init__(self, id):
        self.id = id


async def create_analysis_and_entries(client_id: str, file_upload_id: str, analysis_data: dict):
    """
    Cria ou atualiza uma análise em monthly_analyses e insere todas as suas
    entradas detalhadas em financial_entries.
    """
    supabase = get_supabase_client()
    
    summary = analysis_data.get('resumo_periodo', {})
    report_date_str = analysis_data.get("data_final")
    
    # --- CORREÇÃO APLICADA AQUI ---
    try:
        # Tenta converter do formato DD/MM/YYYY para YYYY-MM-DD
        dt_obj = datetime.strptime(report_date_str, '%d/%m/%Y')
        report_date_iso = dt_obj.strftime('%Y-%m-%d')
    except (ValueError, TypeError):
        # Se falhar ou for nulo, usa a data de hoje
        dt_obj = datetime.utcnow()
        report_date_iso = dt_obj.date().isoformat()

    year, month = dt_obj.year, dt_obj.month
    
    # ... (o resto da função continua como antes, mas usando report_date_iso) ...
    analysis_payload = {
        "client_id": client_id,
        "client_name": analysis_data.get("cliente", "Não Identificado"),
        "reference_year": year,
        "reference_month": month,
        "report_date": report_date_iso, # <-- USA A DATA CORRIGIDA
        "status": "completed",
        "total_receitas": _to_float_safe(summary.get('total_receitas')),
        "total_despesas": _to_float_safe(summary.get('total_despesas_custos')),
        "source_file_path": f"public/{client_id}/{analysis_data.get('file_name', '')}",
        "source_file_name": analysis_data.get('file_name', 'arquivo.pdf'),
    }

    # ... (o resto da função para inserir/upsert e salvar os lançamentos continua igual,
    # apenas certifique-se que você está usando a variável `report_date_iso` ao popular
    # o campo 'report_date' dos financial_entries) ...

    # Inserir ou atualizar a análise principal
    analysis_resp = supabase.table("monthly_analyses").upsert(
        analysis_payload, on_conflict="client_id,reference_year,reference_month"
    ).execute()
    
    if not hasattr(analysis_resp, "data") or not analysis_resp.data:
        raise Exception(f"Falha ao salvar a análise: {getattr(analysis_resp, 'error', 'Erro desconhecido')}")
    
    analysis_id = analysis_resp.data[0]["id"]
    logger.info(f"Análise (ID: {analysis_id}) salva. Processando lançamentos...")

    # Limpar lançamentos antigos
    supabase.table('financial_entries').delete().eq('analysis_id', analysis_id).execute()

    entries_to_insert = []
    for conta in analysis_data.get("financial_entries", []):
        valor_debito = _to_float_safe(conta.get("valor_debito", 0.0))
        valor_credito = _to_float_safe(conta.get("valor_credito", 0.0))
        
        movement_type = "Despesa" if valor_debito > 0 else "Receita"
        period_value = valor_debito if valor_debito > 0 else valor_credito

        if period_value > 0:
            entries_to_insert.append({
                "analysis_id": analysis_id,
                "client_id": client_id,
                "report_date": report_date_iso, # <-- USA A DATA CORRIGIDA
                "main_group": conta.get("grupo_principal"),
                "subgroup_1": conta.get("subgroup_1"),
                "specific_account": conta.get("conta_especifica"),
                "movement_type": movement_type,
                "period_value": period_value
            })

    if entries_to_insert:
        insert_resp = supabase.table('financial_entries').insert(entries_to_insert).execute()
        if not hasattr(insert_resp, "data"):
            raise Exception(f"Falha ao inserir financial_entries: {getattr(insert_resp, 'error', 'Erro desconhecido')}")
        logger.info(f"Inseridos {len(insert_resp.data)} lançamentos para a análise {analysis_id}.")

    return AnalysisResult(id=analysis_id)