# -*- coding: utf-8 -*-
"""
Módulo para extrair texto de PDFs de forma estruturada, preservando tabelas.
"""
import logging
import io
import pdfplumber # Biblioteca especialista em tabelas de PDF
from typing import Optional

logger = logging.getLogger(__name__)

def extract_structured_text_from_pdf(file_content: bytes) -> Optional[str]:
    """
    Extrai texto de um PDF usando pdfplumber para preservar a estrutura das tabelas.
    Converte as tabelas em um formato de texto limpo, separado por pipes (|),
    para facilitar a análise pela IA.

    Args:
        file_content: O conteúdo do arquivo PDF em bytes.

    Returns:
        Uma string única contendo todo o texto estruturado do PDF, ou None se falhar.
    """
    if not file_content:
        logger.error("O conteúdo do arquivo PDF está vazio.")
        return None

    all_text_parts = []
    try:
        # Abre o PDF a partir dos bytes em memória
        with pdfplumber.open(io.BytesIO(file_content)) as pdf:
            logger.info(f"Iniciando extração de {len(pdf.pages)} páginas.")
            for i, page in enumerate(pdf.pages):
                all_text_parts.append(f"\n--- INÍCIO DA PÁGINA {i+1} ---\n")
                
                # Extrai as tabelas da página com configurações para layout
                # Isso ajuda a capturar corretamente as colunas do balancete
                tables = page.extract_tables(table_settings={
                    "vertical_strategy": "lines",
                    "horizontal_strategy": "text",
                })

                # Se a extração principal falhar, tenta uma estratégia mais simples
                if not tables:
                    tables = page.extract_tables()

                # Formata cada tabela encontrada em um texto limpo
                for table in tables:
                    all_text_parts.append("\n--- INÍCIO DA TABELA ---\n")
                    for row in table:
                        # Limpa cada célula e une a linha com um separador claro
                        clean_row = [str(cell).replace('\n', ' ').strip() if cell is not None else "" for cell in row]
                        all_text_parts.append(" | ".join(clean_row))
                    all_text_parts.append("--- FIM DA TABELA ---\n")
        
        full_text = "\n".join(all_text_parts)
        logger.info("Extração de texto estruturado do PDF concluída com sucesso.")
        return full_text

    except Exception as e:
        logger.exception(f"Falha crítica ao processar o arquivo PDF com pdfplumber: {e}")
        return None
