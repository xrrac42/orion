# -*- coding: utf-8 -*-
"""
Módulo central que orquestra o processo de análise de um PDF.
Agora simplificado para confiar na análise completa do LLM.
"""
import logging
from .pdf_processor import extract_structured_text_from_pdf
from .llm_analyzer import GeminiAnalyzer
from .database import create_analysis_and_entries # Nova função de banco de dados

logger = logging.getLogger(__name__)

class CoreProcessor:
    def __init__(self):
        self.llm_analyzer = GeminiAnalyzer()

    async def process_pdf_file(self, file_content: bytes, client_id: str, file_upload_id: str):
        """
        Processa um arquivo PDF do início ao fim usando a abordagem LLM-centric.
        """
        try:
            # 1. Extrair texto estruturado do PDF
            text_content = extract_structured_text_from_pdf(file_content)
            if not text_content:
                raise ValueError("Não foi possível extrair texto estruturado do PDF.")

            # 2. IA analisa, calcula e estrutura TUDO
            analysis_data = await self.llm_analyzer.analyze_and_structure_balancete(text_content)
            if not analysis_data:
                raise ValueError("A análise completa com IA falhou ou retornou dados vazios.")

            # 3. Salva a análise e suas entradas no banco de dados de uma vez
            # Esta nova função em database.py usará uma transação para garantir a consistência
            new_analysis = await create_analysis_and_entries(
                client_id=client_id,
                file_upload_id=file_upload_id,
                analysis_data=analysis_data
            )
            
            logger.info(f"Processamento e salvamento concluídos com sucesso para a análise {new_analysis.id}.")
            return {"status": "success", "analysis_id": new_analysis.id}

        except Exception as e:
            logger.exception(f"Falha no processamento do arquivo para o upload {file_upload_id}: {e}")
            # Aqui você deve atualizar o status do 'file_upload' para 'failed'
            return {"status": "error", "message": str(e)}
