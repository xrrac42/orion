import google.generativeai as genai
import json
import pandas as pd
import base64
import io
from typing import Dict, List, Tuple, Optional
from uuid import UUID
import hashlib
from datetime import datetime
from pydantic import BaseModel

class FileMetadata(BaseModel):
    file_hash: str
    estimated_month: int
    estimated_year: int
    total_rows: int
    has_financial_data: bool
    company_name: Optional[str] = None
    period_indicators: List[str] = []
    data_quality_score: float

class AIService:
    def __init__(self, api_key: str):
        genai.configure(api_key=api_key)
        self.model = genai.GenerativeModel('gemini-1.5-flash')
    
    def extract_file_metadata(self, file_data: str, file_name: str, file_type: str) -> FileMetadata:
        """
        Extract metadata from uploaded file using AI analysis
        """
        try:
            # Decode base64 file data
            file_bytes = base64.b64decode(file_data)
            
            # Calculate file hash for duplicate detection
            file_hash = hashlib.sha256(file_bytes).hexdigest()
            
            # Parse file content based on type
            if file_type in ['text/csv', 'application/csv']:
                df = pd.read_csv(io.BytesIO(file_bytes))
            elif file_type in ['application/vnd.openxmlformats-officedocument.spreadsheetml.sheet', 'application/vnd.ms-excel']:
                df = pd.read_excel(io.BytesIO(file_bytes))
            else:
                raise ValueError(f"Unsupported file type: {file_type}")
            
            # Prepare data sample for AI analysis
            sample_data = df.head(10).to_csv(index=False)
            column_names = list(df.columns)
            
            # AI prompt for metadata extraction
            prompt = f"""
            Analise este arquivo financeiro e extraia as seguintes informações:
            
            Nome do arquivo: {file_name}
            Colunas disponíveis: {column_names}
            Amostra dos dados (primeiras 10 linhas):
            {sample_data}
            
            Por favor, forneça uma análise em formato JSON com as seguintes informações:
            {{
                "estimated_month": número do mês (1-12) baseado nos dados,
                "estimated_year": ano baseado nos dados,
                "has_financial_data": true/false se contém dados financeiros válidos,
                "company_name": nome da empresa se identificado,
                "period_indicators": lista de indicadores de período encontrados,
                "data_quality_score": pontuação de 0-1 da qualidade dos dados,
                "summary": resumo breve do conteúdo
            }}
            
            Seja preciso na identificação do período e da qualidade dos dados.
            """
            
            response = self.model.generate_content(prompt)
            ai_result = json.loads(response.text)
            
            return FileMetadata(
                file_hash=file_hash,
                estimated_month=ai_result.get('estimated_month', datetime.now().month),
                estimated_year=ai_result.get('estimated_year', datetime.now().year),
                total_rows=len(df),
                has_financial_data=ai_result.get('has_financial_data', True),
                company_name=ai_result.get('company_name'),
                period_indicators=ai_result.get('period_indicators', []),
                data_quality_score=ai_result.get('data_quality_score', 0.5)
            )
            
        except Exception as e:
            # Fallback metadata if AI analysis fails
            file_hash = hashlib.sha256(base64.b64decode(file_data)).hexdigest()
            return FileMetadata(
                file_hash=file_hash,
                estimated_month=datetime.now().month,
                estimated_year=datetime.now().year,
                total_rows=0,
                has_financial_data=False,
                data_quality_score=0.0
            )
    
    def check_for_duplicates(self, metadata: FileMetadata, client_id: UUID, existing_analyses: List[dict]) -> Tuple[bool, float, Optional[UUID]]:
        """
        Check if this file is a duplicate of existing analyses using AI comparison
        """
        try:
            # Simple hash-based duplicate detection
            for analysis in existing_analyses:
                if analysis.get('metadata', {}).get('file_hash') == metadata.file_hash:
                    return True, 1.0, analysis['id']
            
            # AI-powered semantic duplicate detection
            if existing_analyses:
                comparison_prompt = f"""
                Analise se este novo arquivo é uma duplicata de análises existentes:
                
                Novo arquivo:
                - Hash: {metadata.file_hash}
                - Período: {metadata.estimated_month}/{metadata.estimated_year}
                - Linhas: {metadata.total_rows}
                - Empresa: {metadata.company_name}
                
                Análises existentes:
                {json.dumps([{
                    'period': f"{a.get('reference_month', 0)}/{a.get('reference_year', 0)}",
                    'metadata': a.get('metadata', {})
                } for a in existing_analyses[:5]], indent=2)}
                
                Responda em JSON:
                {{
                    "is_duplicate": true/false,
                    "confidence_score": 0.0-1.0,
                    "duplicate_analysis_id": "uuid se for duplicata",
                    "reason": "explicação da decisão"
                }}
                """
                
                response = self.model.generate_content(comparison_prompt)
                ai_result = json.loads(response.text)
                
                return (
                    ai_result.get('is_duplicate', False),
                    ai_result.get('confidence_score', 0.0),
                    UUID(ai_result['duplicate_analysis_id']) if ai_result.get('duplicate_analysis_id') else None
                )
            
            return False, 0.0, None
            
        except Exception as e:
            # Conservative approach: assume not duplicate if analysis fails
            return False, 0.0, None
    
    def process_financial_data(self, file_data: str, file_type: str, analysis_id: UUID) -> Tuple[List[dict], str]:
        """
        Process financial data and generate AI summary
        """
        try:
            # Decode and parse file
            file_bytes = base64.b64decode(file_data)
            
            if file_type in ['text/csv', 'application/csv']:
                df = pd.read_csv(io.BytesIO(file_bytes))
            elif file_type in ['application/vnd.openxmlformats-officedocument.spreadsheetml.sheet', 'application/vnd.ms-excel']:
                df = pd.read_excel(io.BytesIO(file_bytes))
            else:
                raise ValueError(f"Unsupported file type: {file_type}")
            
            # Process financial entries
            financial_entries = []
            
            # AI-powered column mapping
            mapping_prompt = f"""
            Analise estas colunas de dados financeiros e mapeie para os campos padrão:
            
            Colunas disponíveis: {list(df.columns)}
            Amostra dos dados:
            {df.head(5).to_csv(index=False)}
            
            Mapeie para estes campos em JSON:
            {{
                "data_mapping": {{
                    "specific_account": "nome_da_coluna_conta",
                    "account_description": "nome_da_coluna_descricao",
                    "movement_type": "nome_da_coluna_tipo",
                    "period_value": "nome_da_coluna_valor",
                    "report_date": "nome_da_coluna_data"
                }},
                "value_transformations": {{
                    "movement_type_values": {{
                        "receita": ["receita", "entrada", "credit"],
                        "despesa": ["despesa", "saida", "debit"]
                    }}
                }}
            }}
            """
            
            mapping_response = self.model.generate_content(mapping_prompt)
            mapping_result = json.loads(mapping_response.text)
            
            data_mapping = mapping_result.get('data_mapping', {})
            transformations = mapping_result.get('value_transformations', {})
            
            # Process each row
            for index, row in df.iterrows():
                try:
                    # Extract values using AI mapping
                    entry = {
                        'analysis_id': analysis_id,
                        'specific_account': str(row.get(data_mapping.get('specific_account', ''), '')),
                        'account_description': str(row.get(data_mapping.get('account_description', ''), '')),
                        'movement_type': self._normalize_movement_type(
                            str(row.get(data_mapping.get('movement_type', ''), '')),
                            transformations.get('movement_type_values', {})
                        ),
                        'period_value': float(row.get(data_mapping.get('period_value', ''), 0)),
                        'report_date': pd.to_datetime(row.get(data_mapping.get('report_date', ''), datetime.now())).isoformat()
                    }
                    
                    if entry['period_value'] != 0:  # Only include non-zero entries
                        financial_entries.append(entry)
                        
                except Exception as e:
                    continue  # Skip problematic rows
            
            # Generate AI summary
            summary_prompt = f"""
            Analise estes dados financeiros processados e gere um resumo executivo:
            
            Total de entradas processadas: {len(financial_entries)}
            
            Resumo por tipo:
            Receitas: {sum(1 for e in financial_entries if e['movement_type'] == 'Receita')} entradas
            Despesas: {sum(1 for e in financial_entries if e['movement_type'] == 'Despesa')} entradas
            
            Valor total:
            Receitas: R$ {sum(e['period_value'] for e in financial_entries if e['movement_type'] == 'Receita'):,.2f}
            Despesas: R$ {sum(e['period_value'] for e in financial_entries if e['movement_type'] == 'Despesa'):,.2f}
            
            Principais contas (primeiras 10):
            {json.dumps([e['specific_account'] for e in financial_entries[:10]], indent=2)}
            
            Gere um resumo executivo em português que destaque:
            1. Visão geral dos dados processados
            2. Principais insights financeiros
            3. Pontos de atenção ou anomalias
            4. Recomendações gerais
            """
            
            summary_response = self.model.generate_content(summary_prompt)
            ai_summary = summary_response.text
            
            return financial_entries, ai_summary
            
        except Exception as e:
            return [], f"Erro no processamento: {str(e)}"
    
    def _normalize_movement_type(self, value: str, transformations: dict) -> str:
        """
        Normalize movement type using AI transformations
        """
        value_lower = value.lower().strip()
        
        for standard_type, variants in transformations.items():
            if any(variant in value_lower for variant in variants):
                return standard_type.capitalize()
        
        # Default fallback
        if any(word in value_lower for word in ['receita', 'entrada', 'credit', 'recebimento']):
            return 'Receita'
        elif any(word in value_lower for word in ['despesa', 'saida', 'debit', 'pagamento']):
            return 'Despesa'
        else:
            return 'Despesa'  # Conservative default
