from fastapi import APIRouter, HTTPException, Depends, status
from fastapi.security import HTTPBearer
from sqlalchemy.orm import Session
from sqlalchemy import text
from uuid import UUID, uuid4
from datetime import datetime
import os
from typing import List

from models.monthly_analysis import (
    MonthlyAnalysisCreate, 
    MonthlyAnalysisUpdate, 
    MonthlyAnalysisResponse,
    PreCheckRequest,
    PreCheckResponse,
    ProcessFileRequest,
    ProcessFileResponse
)
from services.ai_service import AIService, FileMetadata
from database import get_db
from auth import get_current_user

router = APIRouter(prefix="/api/monthly-analyses", tags=["Monthly Analyses"])
security = HTTPBearer()

# Initialize AI service
ai_service = AIService(api_key=os.getenv("GOOGLE_AI_API_KEY"))

@router.post("/pre-check", response_model=PreCheckResponse)
async def pre_check_file(
    request: PreCheckRequest,
    db: Session = Depends(get_db),
    current_user: dict = Depends(get_current_user)
):
    """
    Pre-check uploaded file for duplicates and extract metadata using AI
    """
    try:
        # Extract metadata using AI
        metadata = ai_service.extract_file_metadata(
            request.file_data, 
            request.file_name, 
            request.file_type
        )
        
        # Get existing analyses for this client and period
        existing_analyses_query = """
        SELECT ma.*, fu.pre_check_result
        FROM monthly_analyses ma
        LEFT JOIN file_uploads fu ON ma.id = fu.analysis_id
        WHERE ma.client_id = :client_id 
        AND ma.reference_month = :month 
        AND ma.reference_year = :year
        """
        
        result = db.execute(text(existing_analyses_query), {
            "client_id": str(request.client_id),
            "month": metadata.estimated_month,
            "year": metadata.estimated_year
        })
        
        existing_analyses = [dict(row._mapping) for row in result]
        
        # Check for duplicates using AI
        is_duplicate, confidence_score, duplicate_analysis_id = ai_service.check_for_duplicates(
            metadata, request.client_id, existing_analyses
        )
        
        if is_duplicate and duplicate_analysis_id:
            return PreCheckResponse(
                is_duplicate=True,
                analysis_id=duplicate_analysis_id,
                metadata=metadata.dict(),
                confidence_score=confidence_score,
                message=f"Arquivo duplicado detectado com {confidence_score*100:.1f}% de confiança"
            )
        
        # Create new monthly analysis if not duplicate
        analysis_id = uuid4()
        
        create_analysis_query = """
        INSERT INTO monthly_analyses (
            id, client_id, reference_month, reference_year, 
            status, metadata, created_by
        ) VALUES (
            :id, :client_id, :month, :year, 
            'pending', :metadata, :user_id
        )
        """
        
        db.execute(text(create_analysis_query), {
            "id": str(analysis_id),
            "client_id": str(request.client_id),
            "month": metadata.estimated_month,
            "year": metadata.estimated_year,
            "metadata": metadata.json(),
            "user_id": current_user["sub"]
        })
        
        # Create initial file upload record
        create_upload_query = """
        INSERT INTO file_uploads (
            id, analysis_id, file_name, file_type, file_size,
            status, pre_check_result, uploaded_by
        ) VALUES (
            :id, :analysis_id, :file_name, :file_type, :file_size,
            'pre_checked', :pre_check_result, :uploaded_by
        )
        """
        
        db.execute(text(create_upload_query), {
            "id": str(uuid4()),
            "analysis_id": str(analysis_id),
            "file_name": request.file_name,
            "file_type": request.file_type,
            "file_size": len(request.file_data),
            "pre_check_result": metadata.json(),
            "uploaded_by": current_user["sub"]
        })
        
        db.commit()
        
        return PreCheckResponse(
            is_duplicate=False,
            analysis_id=analysis_id,
            metadata=metadata.dict(),
            confidence_score=confidence_score,
            message="Arquivo aprovado para processamento completo"
        )
        
    except Exception as e:
        db.rollback()
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Erro na pré-verificação: {str(e)}"
        )

@router.post("/process", response_model=ProcessFileResponse)
async def process_file(
    request: ProcessFileRequest,
    db: Session = Depends(get_db),
    current_user: dict = Depends(get_current_user)
):
    """
    Process file completely with AI-powered analysis
    """
    try:
        # Verify analysis exists and belongs to user
        verify_analysis_query = """
        SELECT ma.*, c.created_by as client_owner
        FROM monthly_analyses ma
        JOIN clients c ON ma.client_id = c.id
        WHERE ma.id = :analysis_id 
        AND (c.created_by = :user_id OR :user_id IN (
            SELECT id FROM user_profiles WHERE role = 'admin'
        ))
        """
        
        result = db.execute(text(verify_analysis_query), {
            "analysis_id": str(request.analysis_id),
            "user_id": current_user["sub"]
        })
        
        analysis = result.fetchone()
        if not analysis:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Análise não encontrada ou acesso negado"
            )
        
        # Check if forcing process or if it's a new analysis
        if not request.force_process and analysis.status == 'completed':
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Análise já processada. Use force_process=true para reprocessar"
            )
        
        # Update status to processing
        db.execute(text("""
            UPDATE monthly_analyses 
            SET status = 'processing', updated_at = NOW()
            WHERE id = :analysis_id
        """), {"analysis_id": str(request.analysis_id)})
        
        # Process financial data with AI
        financial_entries, ai_summary = ai_service.process_financial_data(
            request.file_data,
            request.file_type,
            request.analysis_id
        )
        
        if not financial_entries:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Nenhum dado financeiro válido encontrado no arquivo"
            )
        
        # Insert financial entries
        errors = []
        warnings = []
        
        for entry in financial_entries:
            try:
                insert_entry_query = """
                INSERT INTO financial_entries (
                    id, analysis_id, specific_account, account_description,
                    movement_type, period_value, report_date, created_by
                ) VALUES (
                    :id, :analysis_id, :specific_account, :account_description,
                    :movement_type, :period_value, :report_date, :created_by
                )
                """
                
                db.execute(text(insert_entry_query), {
                    "id": str(uuid4()),
                    "analysis_id": str(request.analysis_id),
                    "specific_account": entry['specific_account'],
                    "account_description": entry['account_description'],
                    "movement_type": entry['movement_type'],
                    "period_value": entry['period_value'],
                    "report_date": entry['report_date'],
                    "created_by": current_user["sub"]
                })
                
            except Exception as e:
                errors.append(f"Erro na entrada {entry.get('specific_account', 'N/A')}: {str(e)}")
        
        # Calculate totals
        total_receitas = sum(e['period_value'] for e in financial_entries if e['movement_type'] == 'Receita')
        total_despesas = sum(e['period_value'] for e in financial_entries if e['movement_type'] == 'Despesa')
        total_entries = len(financial_entries)
        
        # Update analysis with results
        update_analysis_query = """
        UPDATE monthly_analyses 
        SET 
            status = 'completed',
            ai_summary = :ai_summary,
            total_receitas = :total_receitas,
            total_despesas = :total_despesas,
            total_entries = :total_entries,
            updated_at = NOW()
        WHERE id = :analysis_id
        """
        
        db.execute(text(update_analysis_query), {
            "analysis_id": str(request.analysis_id),
            "ai_summary": ai_summary,
            "total_receitas": total_receitas,
            "total_despesas": total_despesas,
            "total_entries": total_entries
        })
        
        # Update file upload status
        db.execute(text("""
            UPDATE file_uploads 
            SET status = 'completed', updated_at = NOW()
            WHERE analysis_id = :analysis_id AND file_name = :file_name
        """), {
            "analysis_id": str(request.analysis_id),
            "file_name": request.file_name
        })
        
        db.commit()
        
        return ProcessFileResponse(
            success=True,
            analysis_id=request.analysis_id,
            total_entries_processed=total_entries,
            errors=errors,
            warnings=warnings,
            ai_summary=ai_summary
        )
        
    except HTTPException:
        db.rollback()
        raise
    except Exception as e:
        db.rollback()
        # Update analysis status to error
        try:
            db.execute(text("""
                UPDATE monthly_analyses 
                SET status = 'error', updated_at = NOW()
                WHERE id = :analysis_id
            """), {"analysis_id": str(request.analysis_id)})
            db.commit()
        except:
            pass
            
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Erro no processamento: {str(e)}"
        )

@router.get("/", response_model=List[MonthlyAnalysisResponse])
async def list_analyses(
    client_id: UUID = None,
    status: str = None,
    year: int = None,
    month: int = None,
    db: Session = Depends(get_db),
    current_user: dict = Depends(get_current_user)
):
    """
    List monthly analyses with optional filters
    """
    try:
        query = """
        SELECT ma.*
        FROM monthly_analyses ma
        JOIN clients c ON ma.client_id = c.id
        WHERE (c.created_by = :user_id OR :user_id IN (
            SELECT id FROM user_profiles WHERE role = 'admin'
        ))
        """
        
        params = {"user_id": current_user["sub"]}
        
        if client_id:
            query += " AND ma.client_id = :client_id"
            params["client_id"] = str(client_id)
        
        if status:
            query += " AND ma.status = :status"
            params["status"] = status
        
        if year:
            query += " AND ma.reference_year = :year"
            params["year"] = year
        
        if month:
            query += " AND ma.reference_month = :month"
            params["month"] = month
        
        query += " ORDER BY ma.reference_year DESC, ma.reference_month DESC, ma.created_at DESC"
        
        result = db.execute(text(query), params)
        analyses = [dict(row._mapping) for row in result]
        
        return [MonthlyAnalysisResponse(**analysis) for analysis in analyses]
        
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Erro ao listar análises: {str(e)}"
        )

@router.get("/{analysis_id}", response_model=MonthlyAnalysisResponse)
async def get_analysis(
    analysis_id: UUID,
    db: Session = Depends(get_db),
    current_user: dict = Depends(get_current_user)
):
    """
    Get specific analysis details
    """
    try:
        query = """
        SELECT ma.*
        FROM monthly_analyses ma
        JOIN clients c ON ma.client_id = c.id
        WHERE ma.id = :analysis_id 
        AND (c.created_by = :user_id OR :user_id IN (
            SELECT id FROM user_profiles WHERE role = 'admin'
        ))
        """
        
        result = db.execute(text(query), {
            "analysis_id": str(analysis_id),
            "user_id": current_user["sub"]
        })
        
        analysis = result.fetchone()
        if not analysis:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Análise não encontrada"
            )
        
        return MonthlyAnalysisResponse(**dict(analysis._mapping))
        
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Erro ao buscar análise: {str(e)}"
        )

@router.put("/{analysis_id}", response_model=MonthlyAnalysisResponse)
async def update_analysis(
    analysis_id: UUID,
    update_data: MonthlyAnalysisUpdate,
    db: Session = Depends(get_db),
    current_user: dict = Depends(get_current_user)
):
    """
    Update analysis details
    """
    try:
        # Verify ownership
        verify_query = """
        SELECT ma.id
        FROM monthly_analyses ma
        JOIN clients c ON ma.client_id = c.id
        WHERE ma.id = :analysis_id 
        AND (c.created_by = :user_id OR :user_id IN (
            SELECT id FROM user_profiles WHERE role = 'admin'
        ))
        """
        
        result = db.execute(text(verify_query), {
            "analysis_id": str(analysis_id),
            "user_id": current_user["sub"]
        })
        
        if not result.fetchone():
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Análise não encontrada ou acesso negado"
            )
        
        # Build update query dynamically
        update_fields = []
        params = {"analysis_id": str(analysis_id)}
        
        if update_data.status is not None:
            update_fields.append("status = :status")
            params["status"] = update_data.status
        
        if update_data.ai_summary is not None:
            update_fields.append("ai_summary = :ai_summary")
            params["ai_summary"] = update_data.ai_summary
        
        if update_data.metadata is not None:
            update_fields.append("metadata = :metadata")
            params["metadata"] = update_data.metadata
        
        if update_data.total_receitas is not None:
            update_fields.append("total_receitas = :total_receitas")
            params["total_receitas"] = update_data.total_receitas
        
        if update_data.total_despesas is not None:
            update_fields.append("total_despesas = :total_despesas")
            params["total_despesas"] = update_data.total_despesas
        
        if update_data.total_entries is not None:
            update_fields.append("total_entries = :total_entries")
            params["total_entries"] = update_data.total_entries
        
        if not update_fields:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Nenhum campo para atualizar"
            )
        
        update_fields.append("updated_at = NOW()")
        
        query = f"""
        UPDATE monthly_analyses 
        SET {', '.join(update_fields)}
        WHERE id = :analysis_id
        RETURNING *
        """
        
        result = db.execute(text(query), params)
        updated_analysis = result.fetchone()
        db.commit()
        
        return MonthlyAnalysisResponse(**dict(updated_analysis._mapping))
        
    except HTTPException:
        db.rollback()
        raise
    except Exception as e:
        db.rollback()
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Erro ao atualizar análise: {str(e)}"
        )

@router.delete("/{analysis_id}")
async def delete_analysis(
    analysis_id: UUID,
    db: Session = Depends(get_db),
    current_user: dict = Depends(get_current_user)
):
    """
    Delete analysis and all related data
    """
    try:
        # Verify ownership
        verify_query = """
        SELECT ma.id
        FROM monthly_analyses ma
        JOIN clients c ON ma.client_id = c.id
        WHERE ma.id = :analysis_id 
        AND (c.created_by = :user_id OR :user_id IN (
            SELECT id FROM user_profiles WHERE role = 'admin'
        ))
        """
        
        result = db.execute(text(verify_query), {
            "analysis_id": str(analysis_id),
            "user_id": current_user["sub"]
        })
        
        if not result.fetchone():
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Análise não encontrada ou acesso negado"
            )
        
        # Delete in correct order (foreign key constraints)
        # 1. Financial entries
        db.execute(text("DELETE FROM financial_entries WHERE analysis_id = :analysis_id"), 
                  {"analysis_id": str(analysis_id)})
        
        # 2. File uploads
        db.execute(text("DELETE FROM file_uploads WHERE analysis_id = :analysis_id"), 
                  {"analysis_id": str(analysis_id)})
        
        # 3. Monthly analysis
        db.execute(text("DELETE FROM monthly_analyses WHERE id = :analysis_id"), 
                  {"analysis_id": str(analysis_id)})
        
        db.commit()
        
        return {"message": "Análise excluída com sucesso"}
        
    except HTTPException:
        db.rollback()
        raise
    except Exception as e:
        db.rollback()
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Erro ao excluir análise: {str(e)}"
        )
