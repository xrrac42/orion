from fastapi import APIRouter, HTTPException, Depends, UploadFile, File, Form
from typing import List, Optional
from pydantic import BaseModel
from database import get_supabase_client
import logging
import os

router = APIRouter()
logger = logging.getLogger(__name__)

# Modelos Pydantic
class BalanceteCreate(BaseModel):
    client_id: str
    ano: int
    mes: int
    total_receitas: float
    total_despesas: float

class BalanceteResponse(BaseModel):
    id: int  # BIGINT no banco = int no Python
    client_id: str
    ano: int
    mes: int
    total_receitas: float
    total_despesas: float
    lucro_bruto: float
    created_at: Optional[str] = None
    
class BalanceteUploadResponse(BaseModel):
    message: str
    balancete_id: int  # BIGINT no banco = int no Python
    file_path: str

# Novo endpoint para upload de balancete com arquivo PDF
@router.post("/", response_model=BalanceteUploadResponse)
async def upload_balancete(
    client_id: str = Form(...),
    ano: str = Form(...),
    mes: str = Form(...),
    file: UploadFile = File(...)
):
    """Recebe PDF, faz upload no Supabase Storage e registra balancete no banco."""
    try:
        supabase = get_supabase_client()
        # Verificar se cliente existe
        cliente_response = supabase.table('clients').select('id').eq('id', client_id).execute()
        if not cliente_response.data or len(cliente_response.data) == 0:
            raise HTTPException(status_code=404, detail="Cliente não encontrado")

        # Nome do arquivo e path
        filename = file.filename
        file_path = f"public/{client_id}/{ano}-{str(mes).zfill(2)}-{filename}"
        file_bytes = await file.read()

        # Upload para o Supabase Storage (bucket 'balancetes')
        storage_response = supabase.storage.from_('balancetes').upload(file_path, file_bytes, {'content-type': file.content_type, 'upsert': 'true'})
        
        # Verificar se houve erro no upload
        if hasattr(storage_response, 'error') and storage_response.error:
            raise HTTPException(status_code=400, detail=f"Erro ao enviar arquivo: {storage_response.error}")
        
        # Se a resposta é um dict, verificar se há erro
        if isinstance(storage_response, dict) and storage_response.get('error'):
            raise HTTPException(status_code=400, detail=f"Erro ao enviar arquivo: {storage_response['error']['message']}")

        # Criar registro de upload de arquivo
        file_upload_data = {
            'client_id': client_id,
            'file_name': filename,
            'file_path': file_path,
            'file_size': len(file_bytes),
            'mime_type': file.content_type,
            'status': 'completed',
            'processing_completed_at': 'now()',
            'entries_created': 0  # Será atualizado após processamento
        }
        upload_response = supabase.table('file_uploads').insert(file_upload_data).execute()
        if not upload_response.data or len(upload_response.data) == 0:
            raise HTTPException(status_code=400, detail="Erro ao registrar upload")
        
        file_upload_id = upload_response.data[0]['id']

        # Registrar balancete no banco (apenas campos básicos)
        balancete_data = {
            'client_id': client_id,
            'ano': int(ano),
            'mes': int(mes),
            'total_receitas': 0.0,  # Valor padrão, será atualizado depois do processamento
            'total_despesas': 0.0,  # Valor padrão, será atualizado depois do processamento
            'file_upload_id': file_upload_id
        }
        response = supabase.table('balancetes').insert(balancete_data).execute()
        if not response.data or len(response.data) == 0:
            raise HTTPException(status_code=400, detail="Erro ao criar balancete")
        
        balancete_id = response.data[0]['id']
        
        # Log do arquivo enviado para referência
        logger.info(f"Arquivo {filename} enviado para balancete {balancete_id} no path {file_path}")
        
        # Processar PDF automaticamente
        try:
            from routes.pdf_processor import PDFProcessor
            processor = PDFProcessor()
            
            # Buscar dados do file_upload para ter o file_path
            file_upload_response = supabase.table('file_uploads').select('*').eq('id', file_upload_id).execute()
            if file_upload_response.data:
                file_upload_data = file_upload_response.data[0]
                
                # Extrair texto do PDF
                text = processor.extract_text_from_pdf(file_path)
                
                if text:
                    # Extrair dados financeiros
                    financial_data = processor.extract_financial_data(text)
                    
                    # Atualizar balancete com dados extraídos
                    update_data = {
                        'total_receitas': financial_data['total_receitas'],
                        'total_despesas': financial_data['total_despesas']
                    }
                    
                    supabase.table('balancetes')\
                            .update(update_data)\
                            .eq('id', balancete_id)\
                            .execute()
                    
                    # Criar entradas financeiras detalhadas
                    entries = []
                    
                    # Receitas
                    for i, receita in enumerate(financial_data['receitas_detalhadas']):
                        entries.append({
                            'client_id': client_id,
                            'report_date': f"{ano}-{str(mes).zfill(2)}-01",
                            'main_group': 'RECEITAS',
                            'specific_account': f'Receita {i+1}',
                            'movement_type': 'Receita',
                            'period_value': receita
                        })
                    
                    # Despesas
                    for i, despesa in enumerate(financial_data['despesas_detalhadas']):
                        entries.append({
                            'client_id': client_id,
                            'report_date': f"{ano}-{str(mes).zfill(2)}-01",
                            'main_group': 'CUSTOS E DESPESAS',
                            'specific_account': f'Despesa {i+1}',
                            'movement_type': 'Despesa',
                            'period_value': despesa
                        })
                    
                    # Despesas por categoria
                    for categoria, valor in financial_data['categorias'].items():
                        entries.append({
                            'client_id': client_id,
                            'report_date': f"{ano}-{str(mes).zfill(2)}-01",
                            'main_group': 'CUSTOS E DESPESAS',
                            'subgroup_1': categoria.title(),
                            'specific_account': categoria.title(),
                            'movement_type': 'Despesa',
                            'period_value': valor
                        })
                    
                    # Inserir entradas financeiras
                    if entries:
                        supabase.table('financial_entries').insert(entries).execute()
                    
                    # Atualizar status do upload
                    supabase.table('file_uploads')\
                            .update({
                                'status': 'completed',
                                'entries_created': len(entries),
                                'processing_completed_at': 'now()'
                            })\
                            .eq('id', file_upload_id)\
                            .execute()
                    
                    logger.info(f"PDF processado automaticamente: {len(entries)} entradas criadas")
                    
        except Exception as processing_error:
            logger.error(f"Erro ao processar PDF automaticamente: {processing_error}")
            # Não falha o upload se o processamento der erro
        
        return {
            "message": "Balancete enviado e registrado com sucesso",
            "balancete_id": balancete_id,
            "file_path": file_path
        }
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Erro ao fazer upload do balancete: {e}")
        raise HTTPException(status_code=500, detail="Erro interno do servidor")

@router.get("/cliente/{client_id}", response_model=List[BalanceteResponse])
async def get_balancetes_cliente(client_id: str):
    """Buscar balancetes de um cliente"""
    try:
        supabase = get_supabase_client()
        
        # Log para debug
        logger.info(f"Buscando balancetes para cliente: {client_id}")
        
        response = supabase.table('balancetes')\
                          .select('*')\
                          .eq('client_id', client_id)\
                          .order('ano', desc=True)\
                          .order('mes', desc=True)\
                          .execute()
        
        logger.info(f"Resposta do Supabase: {response.data}")
        
        if response.data is None:
            return []
            
        return response.data
    except Exception as e:
        logger.error(f"Erro ao buscar balancetes do cliente {client_id}: {e}")
        raise HTTPException(status_code=500, detail="Erro interno do servidor")

@router.get("/", response_model=List[BalanceteResponse])
async def get_all_balancetes():
    """Buscar todos os balancetes (para debug)"""
    try:
        supabase = get_supabase_client()
        
        response = supabase.table('balancetes')\
                          .select('*')\
                          .order('created_at', desc=True)\
                          .execute()
        
        logger.info(f"Total de balancetes encontrados: {len(response.data) if response.data else 0}")
        
        if response.data is None:
            return []
            
        return response.data
    except Exception as e:
        logger.error(f"Erro ao buscar todos os balancetes: {e}")
        raise HTTPException(status_code=500, detail="Erro interno do servidor")

@router.post("/", response_model=BalanceteResponse)
async def create_balancete(balancete: BalanceteCreate):
    """Criar novo balancete"""
    try:
        supabase = get_supabase_client()
        
        # Verificar se cliente existe
        cliente_response = supabase.table('clients')\
                                  .select('id')\
                                  .eq('id', balancete.client_id)\
                                  .execute()
        
        if not cliente_response.data or len(cliente_response.data) == 0:
            raise HTTPException(status_code=404, detail="Cliente não encontrado")
        
        # Verificar se já existe balancete para esse período
        existing = supabase.table('balancetes')\
                          .select('id')\
                          .eq('client_id', balancete.client_id)\
                          .eq('ano', balancete.ano)\
                          .eq('mes', balancete.mes)\
                          .execute()
        
        if existing.data and len(existing.data) > 0:
            raise HTTPException(status_code=400, detail="Já existe balancete para este período")
        
        # Calcular lucro bruto
        lucro_bruto = balancete.total_receitas - balancete.total_despesas
        
        # Criar balancete
        balancete_data = balancete.dict()
        balancete_data['lucro_bruto'] = lucro_bruto
        
        response = supabase.table('balancetes')\
                          .insert(balancete_data)\
                          .execute()
        
        if not response.data or len(response.data) == 0:
            raise HTTPException(status_code=400, detail="Erro ao criar balancete")
        
        return response.data[0]
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Erro ao criar balancete: {e}")
        raise HTTPException(status_code=500, detail="Erro interno do servidor")

@router.get("/{balancete_id}", response_model=BalanceteResponse)
async def get_balancete(balancete_id: str):
    """Buscar balancete por ID"""
    try:
        supabase = get_supabase_client()
        
        response = supabase.table('balancetes')\
                          .select('*')\
                          .eq('id', balancete_id)\
                          .single()\
                          .execute()
        
        if not response.data:
            raise HTTPException(status_code=404, detail="Balancete não encontrado")
        
        return response.data
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Erro ao buscar balancete {balancete_id}: {e}")
        raise HTTPException(status_code=500, detail="Erro interno do servidor")

@router.delete("/{balancete_id}")
async def delete_balancete(balancete_id: str):
    """Excluir balancete"""
    try:
        supabase = get_supabase_client()
        
        # Verificar se balancete existe
        existing = supabase.table('balancetes')\
                          .select('id')\
                          .eq('id', balancete_id)\
                          .execute()
        
        if not existing.data or len(existing.data) == 0:
            raise HTTPException(status_code=404, detail="Balancete não encontrado")
        
        # Excluir balancete
        response = supabase.table('balancetes')\
                          .delete()\
                          .eq('id', balancete_id)\
                          .execute()
        
        return {"message": "Balancete excluído com sucesso"}
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Erro ao excluir balancete {balancete_id}: {e}")
        raise HTTPException(status_code=500, detail="Erro interno do servidor")

@router.get("/{balancete_id}/download")
async def download_balancete(balancete_id: str):
    """Obter URL de download do arquivo do balancete"""
    try:
        supabase = get_supabase_client()
        
        # Buscar informações do balancete e arquivo
        balancete_response = supabase.table('balancetes')\
                                   .select('id, client_id, ano, mes, file_upload_id')\
                                   .eq('id', balancete_id)\
                                   .single()\
                                   .execute()
        
        if not balancete_response.data:
            raise HTTPException(status_code=404, detail="Balancete não encontrado")
        
        balancete = balancete_response.data
        file_upload_id = balancete.get('file_upload_id')
        
        if not file_upload_id:
            raise HTTPException(status_code=404, detail="Arquivo não encontrado para este balancete")
        
        # Buscar informações do arquivo
        file_response = supabase.table('file_uploads')\
                               .select('file_path, file_name')\
                               .eq('id', file_upload_id)\
                               .single()\
                               .execute()
        
        if not file_response.data:
            raise HTTPException(status_code=404, detail="Dados do arquivo não encontrados")
        
        file_upload = file_response.data
        
        file_path = file_upload['file_path']
        file_name = file_upload['file_name']
        
        # Gerar URL de download temporária (válida por 1 hora)
        download_response = supabase.storage.from_('balancetes').create_signed_url(file_path, 3600)
        
        if hasattr(download_response, 'error') and download_response.error:
            raise HTTPException(status_code=400, detail=f"Erro ao gerar URL de download: {download_response.error}")
        
        # Verificar se a resposta é um dict com erro
        if isinstance(download_response, dict) and download_response.get('error'):
            raise HTTPException(status_code=400, detail=f"Erro ao gerar URL de download: {download_response['error']['message']}")
        
        download_url = download_response.get('signedURL') if isinstance(download_response, dict) else download_response.signed_url
        
        return {
            "download_url": download_url,
            "file_name": file_name,
            "expires_in": 3600  # 1 hora
        }
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Erro ao gerar download do balancete {balancete_id}: {e}")
        raise HTTPException(status_code=500, detail="Erro interno do servidor")
