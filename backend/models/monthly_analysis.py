from pydantic import BaseModel, Field
from datetime import datetime
from typing import Optional, List
from uuid import UUID
from enum import Enum

class AnalysisStatus(str, Enum):
    PENDING = "pending"
    PROCESSING = "processing"
    COMPLETED = "completed"
    ERROR = "error"

class MonthlyAnalysisCreate(BaseModel):
    client_id: UUID
    reference_month: int = Field(..., ge=1, le=12)
    reference_year: int = Field(..., ge=2020, le=2030)
    status: AnalysisStatus = AnalysisStatus.PENDING
    ai_summary: Optional[str] = None
    metadata: Optional[dict] = None

class MonthlyAnalysisUpdate(BaseModel):
    status: Optional[AnalysisStatus] = None
    ai_summary: Optional[str] = None
    metadata: Optional[dict] = None
    total_receitas: Optional[float] = None
    total_despesas: Optional[float] = None
    total_entries: Optional[int] = None

class MonthlyAnalysisResponse(BaseModel):
    id: UUID
    client_id: UUID
    reference_month: int
    reference_year: int
    status: AnalysisStatus
    ai_summary: Optional[str]
    metadata: Optional[dict]
    total_receitas: Optional[float]
    total_despesas: Optional[float]
    total_entries: Optional[int]
    created_at: datetime
    updated_at: datetime
    created_by: UUID

    class Config:
        from_attributes = True

class PreCheckRequest(BaseModel):
    client_id: UUID
    file_data: str  # Base64 encoded file data
    file_name: str
    file_type: str

class PreCheckResponse(BaseModel):
    is_duplicate: bool
    analysis_id: Optional[UUID] = None
    metadata: dict
    confidence_score: float
    message: str

class ProcessFileRequest(BaseModel):
    client_id: UUID
    analysis_id: UUID
    file_data: str  # Base64 encoded file data
    file_name: str
    file_type: str
    force_process: bool = False  # Override duplicate detection

class ProcessFileResponse(BaseModel):
    success: bool
    analysis_id: UUID
    total_entries_processed: int
    errors: List[str] = []
    warnings: List[str] = []
    ai_summary: Optional[str] = None
