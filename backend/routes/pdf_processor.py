# -*- coding: utf-8 -*-
"""
Módulo para extrair texto de PDFs de forma estruturada, preservando tabelas.
Usa uma abordagem tripla com pdfplumber (tabelas e texto) e PyPDF2 como fallback 
para garantir a máxima compatibilidade de extração.
"""
import logging
import io
import pdfplumber
from PyPDF2 import PdfReader
from typing import Optional
from fastapi import APIRouter, UploadFile, File, HTTPException

logger = logging.getLogger(__name__)

router = APIRouter(tags=["PDF Processing"])

def extract_structured_text_from_pdf(file_content: bytes) -> Optional[str]:
    """
    Extrai texto de um PDF usando múltiplas estratégias para máxima compatibilidade.
    """
    if not file_content:
        logger.error("O conteúdo do arquivo PDF está vazio.")
        return None

    # --- TENTATIVA 1: Extração de TABELAS com pdfplumber (melhor para balancetes) ---
    try:
        logger.info("Tentativa 1: Extraindo TABELAS com pdfplumber...")
        all_text_parts = []
        with pdfplumber.open(io.BytesIO(file_content)) as pdf:
            for i, page in enumerate(pdf.pages):
                # Configurações para extrair tabelas de forma mais precisa
                tables = page.extract_tables(table_settings={
                    "vertical_strategy": "lines",
                    "horizontal_strategy": "text",
                    "snap_tolerance": 5,
                })
                if not tables:
                    tables = page.extract_tables() # Tenta uma estratégia mais simples

                if tables:
                    all_text_parts.append(f"\n--- PÁGINA {i+1} ---\n")
                    for table in tables:
                        for row in table:
                            # Limpa e une as células da linha com um separador claro
                            clean_row = [str(cell).replace('\n', ' ').strip() if cell is not None else "" for cell in row]
                            all_text_parts.append(" | ".join(clean_row))
                        all_text_parts.append("\n") # Adiciona um espaço entre tabelas

        full_text = "\n".join(all_text_parts).strip()
        if full_text:
            logger.info("Texto extraído com sucesso usando a extração de TABELAS do pdfplumber.")
            return full_text
        else:
            logger.warning("Nenhuma tabela encontrada com pdfplumber. Partindo para extração de texto puro.")
            
    except Exception as e:
        logger.warning(f"A extração de tabelas com pdfplumber falhou: {e}. Partindo para a próxima estratégia.")

    # --- TENTATIVA 2: Extração de TEXTO PURO com pdfplumber ---
    try:
        logger.info("Tentativa 2: Extraindo TEXTO PURO com pdfplumber...")
        all_text_parts = []
        with pdfplumber.open(io.BytesIO(file_content)) as pdf:
            for i, page in enumerate(pdf.pages):
                page_text = page.extract_text()
                if page_text:
                    all_text_parts.append(f"\n--- PÁGINA {i+1} ---\n")
                    all_text_parts.append(page_text)
        
        full_text = "\n".join(all_text_parts).strip()
        if full_text:
            logger.info("Texto extraído com sucesso usando a extração de TEXTO PURO do pdfplumber.")
            return full_text
        else:
            logger.warning("pdfplumber não extraiu texto puro. Partindo para o fallback com PyPDF2.")
            
    except Exception as e:
        logger.warning(f"A extração de texto puro com pdfplumber falhou: {e}. Partindo para a próxima estratégia.")

    # --- TENTATIVA 3: Fallback com PyPDF2 ---
    try:
        logger.info("Tentativa 3: Extraindo texto com PyPDF2 (Fallback)...")
        all_text_parts = []
        pdf_reader = PdfReader(io.BytesIO(file_content))
        for i, page in enumerate(pdf_reader.pages):
            page_text = page.extract_text()
            if page_text:
                all_text_parts.append(f"\n--- PÁGINA {i+1} ---\n")
                all_text_parts.append(page_text)
        
        full_text = "\n".join(all_text_parts).strip()
        if full_text:
            logger.info("Texto extraído com sucesso usando PyPDF2.")
            return full_text
        else:
            logger.error("TODAS as estratégias de extração de PDF falharam. O arquivo pode estar vazio, ser uma imagem ou estar corrompido.")
            return None
            
    except Exception as e:
        logger.exception(f"Falha crítica ao processar o arquivo PDF com PyPDF2: {e}")
        return None


    @router.post("/extract")
    async def extract_file(file: UploadFile = File(...)):
        """Endpoint de debugging para extrair texto estruturado de um PDF."""
        try:
            content = await file.read()
            if not content:
                raise HTTPException(status_code=400, detail="Arquivo vazio")
            text = extract_structured_text_from_pdf(content)
            if text is None:
                raise HTTPException(status_code=500, detail="Falha ao extrair texto do PDF")
            return {"extracted": text}
        except HTTPException:
            raise
        except Exception as e:
            logger.exception(f"Erro no endpoint /extract: {e}")
            raise HTTPException(status_code=500, detail="Erro interno ao processar PDF")
