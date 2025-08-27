# -*- coding: utf-8 -*-
"""
Módulo central que orquestra o processo de análise de um PDF,
confiando na IA para extrair os dados já processados.
"""
import logging
from pdf_processor import extract_structured_text_from_pdf
from llm_analyzer import GeminiAnalyzer
from database import create_analysis_and_entries # Usando a função de banco de dados que faz o "upsert"

logger = logging.getLogger(__name__)

class CoreProcessor:
    def __init__(self):
        self.llm_analyzer = GeminiAnalyzer()

    async def process_pdf_file(self, file_content: bytes, client_id: str, file_upload_id: str, file_name: str = None):
        """
        Processa um arquivo PDF do início ao fim, chamando o método de extração correto.
        """
        try:
            # 1. Extrair texto estruturado do PDF
            text_content = extract_structured_text_from_pdf(file_content)
            if not text_content:
                raise ValueError("Não foi possível extrair texto estruturado do PDF.")

            # 2. IA analisa e extrai os dados do texto
            # CORREÇÃO DEFINITIVA: Chamando o método renomeado 'extract_data_from_text'
            analysis_data = await self.llm_analyzer.extract_data_from_text(text_content)
            if not analysis_data:
                raise ValueError("A análise com IA falhou ou retornou dados vazios.")

            # 3. Adiciona o nome do arquivo aos dados para salvar no banco
            if file_name:
                analysis_data["file_name"] = file_name

            # 4. Salva a análise e suas entradas no banco de dados
            # A função create_analysis_and_entries já está preparada para o formato extraído
            new_analysis = await create_analysis_and_entries(
                client_id=client_id,
                file_upload_id=file_upload_id,
                analysis_data=analysis_data
            )
            
            logger.info(f"Processamento e salvamento concluídos com sucesso para a análise {new_analysis.id}.")
            return {"status": "success", "analysis_id": new_analysis.id}

        except Exception as e:
            logger.exception(f"Falha no processamento do arquivo para o upload {file_upload_id}: {e}")
            # Retorna um erro claro para a rota
            return {"status": "error", "message": str(e)}