# -*- coding: utf-8 -*-
"""
Módulo para extrair texto de PDFs de forma estruturada, preservando tabelas.
Usa uma abordagem dupla com pdfplumber e PyPDF2 como fallback para garantir a extração.
"""
import logging
import io
import pdfplumber
from PyPDF2 import PdfReader
from typing import Optional

logger = logging.getLogger(__name__)

def extract_structured_text_from_pdf(file_content: bytes) -> Optional[str]:
    """
    Extrai texto de um PDF usando pdfplumber e, se falhar, tenta com PyPDF2.
    """
    if not file_content:
        logger.error("O conteúdo do arquivo PDF está vazio.")
        return None

    full_text = ""
    
    # --- TENTATIVA 1: pdfplumber (melhor para tabelas) ---
    try:
        logger.info("Tentando extrair texto com pdfplumber...")
        all_text_parts = []
        with pdfplumber.open(io.BytesIO(file_content)) as pdf:
            for i, page in enumerate(pdf.pages):
                page_text = page.extract_text()
                if page_text:
                    all_text_parts.append(f"\\n--- PÁGINA {i+1} ---\\n")
                    all_text_parts.append(page_text)
        
        full_text = "\\n".join(all_text_parts).strip()
        
        if full_text:
            logger.info("Texto extraído com sucesso usando pdfplumber.")
            return full_text
        else:
            logger.warning("pdfplumber não extraiu texto. Tentando fallback com PyPDF2.")
            
    except Exception as e:
        logger.warning(f"pdfplumber falhou com o erro: {e}. Tentando fallback com PyPDF2.")
        full_text = "" # Reseta o texto para garantir que o fallback seja executado

    # --- TENTATIVA 2: PyPDF2 (fallback) ---
    try:
        logger.info("Tentando extrair texto com PyPDF2...")
        all_text_parts = []
        pdf_reader = PdfReader(io.BytesIO(file_content))
        for i, page in enumerate(pdf_reader.pages):
            page_text = page.extract_text()
            if page_text:
                all_text_parts.append(f"\\n--- PÁGINA {i+1} ---\\n")
                all_text_parts.append(page_text)
        
        full_text = "\\n".join(all_text_parts).strip()

        if full_text:
            logger.info("Texto extraído com sucesso usando PyPDF2.")
            return full_text
        else:
            logger.error("Ambos pdfplumber e PyPDF2 falharam em extrair texto do PDF.")
            return None
            
    except Exception as e:
        logger.exception(f"Falha crítica ao processar o arquivo PDF com PyPDF2: {e}")
        return None
