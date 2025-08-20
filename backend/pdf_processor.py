"""
Módulo responsável pela extração de texto de arquivos PDF
Utiliza bibliotecas específicas para processar balancetes contábeis
"""

import logging
from typing import Optional, Dict, Any
import os
import tempfile
from pathlib import Path

logger = logging.getLogger(__name__)

try:
    import PyPDF2
    PYPDF2_AVAILABLE = True
except ImportError:
    PYPDF2_AVAILABLE = False
    logger.warning("PyPDF2 não está disponível. Instale com: pip install PyPDF2")

try:
    import pdfplumber
    PDFPLUMBER_AVAILABLE = True
except ImportError:
    PDFPLUMBER_AVAILABLE = False
    logger.warning("pdfplumber não está disponível. Instale com: pip install pdfplumber")

class PDFProcessor:
    """
    Classe responsável por processar e extrair texto de arquivos PDF
    """
    
    def __init__(self):
        self.supported_formats = ['.pdf']
        
    async def extract_text(self, file_path: str) -> Optional[str]:
        """
        Extrai texto de um arquivo PDF
        
        Args:
            file_path: Caminho para o arquivo PDF
            
        Returns:
            Texto extraído do PDF ou None se houver erro
        """
        try:
            # Verificar se o arquivo existe e é um PDF
            if not self._validate_pdf_file(file_path):
                return None
            
            # Tentar diferentes métodos de extração
            text_content = None
            
            # Método 1: pdfplumber (melhor para tabelas)
            if PDFPLUMBER_AVAILABLE:
                text_content = await self._extract_with_pdfplumber(file_path)
                if text_content:
                    logger.info("Texto extraído com pdfplumber")
                    return text_content
            
            # Método 2: PyPDF2 (fallback)
            if PYPDF2_AVAILABLE:
                text_content = await self._extract_with_pypdf2(file_path)
                if text_content:
                    logger.info("Texto extraído com PyPDF2")
                    return text_content
            
            # Se nenhum método funcionou
            logger.error("Nenhum método de extração disponível ou bem-sucedido")
            return None
            
        except Exception as e:
            logger.error(f"Erro na extração de texto: {str(e)}")
            return None
    
    def _validate_pdf_file(self, file_path: str) -> bool:
        """
        Valida se o arquivo é um PDF válido
        """
        try:
            path = Path(file_path)
            
            # Verificar se existe
            if not path.exists():
                logger.error(f"Arquivo não encontrado: {file_path}")
                return False
            
            # Verificar extensão
            if path.suffix.lower() not in self.supported_formats:
                logger.error(f"Formato não suportado: {path.suffix}")
                return False
            
            # Verificar se não está vazio
            if path.stat().st_size == 0:
                logger.error("Arquivo PDF está vazio")
                return False
            
            return True
            
        except Exception as e:
            logger.error(f"Erro na validação do arquivo: {str(e)}")
            return False
    
    async def _extract_with_pdfplumber(self, file_path: str) -> Optional[str]:
        """
        Extrai texto usando pdfplumber (melhor para balancetes com tabelas)
        """
        try:
            import pdfplumber
            
            text_parts = []
            
            with pdfplumber.open(file_path) as pdf:
                for page_num, page in enumerate(pdf.pages):
                    # Extrair texto simples
                    page_text = page.extract_text()
                    if page_text:
                        text_parts.append(f"=== PÁGINA {page_num + 1} ===\n{page_text}")
                    
                    # Tentar extrair tabelas também
                    tables = page.extract_tables()
                    for table_num, table in enumerate(tables):
                        if table:
                            table_text = self._format_table_as_text(table, table_num + 1)
                            text_parts.append(table_text)
            
            return "\n\n".join(text_parts) if text_parts else None
            
        except Exception as e:
            logger.error(f"Erro com pdfplumber: {str(e)}")
            return None
    
    async def _extract_with_pypdf2(self, file_path: str) -> Optional[str]:
        """
        Extrai texto usando PyPDF2 (método fallback)
        """
        try:
            import PyPDF2
            
            text_parts = []
            
            with open(file_path, 'rb') as file:
                pdf_reader = PyPDF2.PdfReader(file)
                
                for page_num, page in enumerate(pdf_reader.pages):
                    page_text = page.extract_text()
                    if page_text:
                        text_parts.append(f"=== PÁGINA {page_num + 1} ===\n{page_text}")
            
            return "\n\n".join(text_parts) if text_parts else None
            
        except Exception as e:
            logger.error(f"Erro com PyPDF2: {str(e)}")
            return None
    
    def _format_table_as_text(self, table: list, table_num: int) -> str:
        """
        Formata uma tabela extraída como texto estruturado
        """
        try:
            if not table:
                return ""
            
            formatted_lines = [f"\n=== TABELA {table_num} ==="]
            
            for row_num, row in enumerate(table):
                if row and any(cell for cell in row if cell):  # Ignorar linhas vazias
                    # Limpar e formatar células
                    cleaned_row = []
                    for cell in row:
                        if cell:
                            cleaned_cell = str(cell).strip().replace('\n', ' ')
                            cleaned_row.append(cleaned_cell)
                        else:
                            cleaned_row.append("")
                    
                    # Juntar células com separador
                    row_text = " | ".join(cleaned_row)
                    formatted_lines.append(f"Linha {row_num + 1}: {row_text}")
            
            return "\n".join(formatted_lines)
            
        except Exception as e:
            logger.error(f"Erro ao formatar tabela: {str(e)}")
            return f"\n=== TABELA {table_num} (ERRO NA FORMATAÇÃO) ==="
    
    async def get_pdf_metadata(self, file_path: str) -> Dict[str, Any]:
        """
        Extrai metadados do PDF
        """
        try:
            metadata = {
                "file_size": 0,
                "num_pages": 0,
                "creation_date": None,
                "creator": None,
                "producer": None
            }
            
            # Obter tamanho do arquivo
            path = Path(file_path)
            metadata["file_size"] = path.stat().st_size
            
            # Tentar obter metadados com PyPDF2
            if PYPDF2_AVAILABLE:
                try:
                    import PyPDF2
                    with open(file_path, 'rb') as file:
                        pdf_reader = PyPDF2.PdfReader(file)
                        metadata["num_pages"] = len(pdf_reader.pages)
                        
                        if pdf_reader.metadata:
                            metadata.update({
                                "creation_date": pdf_reader.metadata.get('/CreationDate'),
                                "creator": pdf_reader.metadata.get('/Creator'),
                                "producer": pdf_reader.metadata.get('/Producer')
                            })
                except Exception as e:
                    logger.warning(f"Erro ao extrair metadados: {str(e)}")
            
            return metadata
            
        except Exception as e:
            logger.error(f"Erro ao obter metadados: {str(e)}")
            return {}
