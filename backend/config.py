"""
Configurações do sistema e variáveis de ambiente
"""

import os
from typing import Dict, Any

class Settings:
    """Configurações centralizadas do sistema"""
    
    # Supabase
    SUPABASE_URL: str = os.getenv("SUPABASE_URL", "https://your-project.supabase.co")
    SUPABASE_ANON_KEY: str = os.getenv("SUPABASE_ANON_KEY", "your-anon-key")
    SUPABASE_SERVICE_KEY: str = os.getenv("SUPABASE_SERVICE_KEY", "your-service-key")
    
    # Gemini API
    GEMINI_API_KEY: str = os.getenv("GEMINI_API_KEY", "")
    GEMINI_MODEL: str = os.getenv("GEMINI_MODEL", "gemini-1.5-flash")
    
    # Storage
    BALANCETES_BUCKET: str = os.getenv("BALANCETES_BUCKET", "balancetes")
    QUARANTINE_BUCKET: str = os.getenv("QUARANTINE_BUCKET", "quarantine")
    
    # Processamento
    MAX_FILE_SIZE_MB: int = int(os.getenv("MAX_FILE_SIZE_MB", "10"))
    SUPPORTED_FILE_TYPES: list = [".pdf"]
    
    # Logging
    LOG_LEVEL: str = os.getenv("LOG_LEVEL", "INFO")
    
    @classmethod
    def validate(cls) -> Dict[str, Any]:
        """Valida se as configurações necessárias estão presentes"""
        missing = []
        warnings = []
        
        # Verificar configurações obrigatórias
        if not cls.SUPABASE_URL or cls.SUPABASE_URL == "https://your-project.supabase.co":
            missing.append("SUPABASE_URL")
        
        if not cls.SUPABASE_SERVICE_KEY or cls.SUPABASE_SERVICE_KEY == "your-service-key":
            missing.append("SUPABASE_SERVICE_KEY")
        
        if not cls.GEMINI_API_KEY:
            missing.append("GEMINI_API_KEY")
        
        # Verificar configurações opcionais
        if not cls.SUPABASE_ANON_KEY or cls.SUPABASE_ANON_KEY == "your-anon-key":
            warnings.append("SUPABASE_ANON_KEY não configurada")
        
        return {
            "valid": len(missing) == 0,
            "missing": missing,
            "warnings": warnings
        }

# Instância global das configurações
settings = Settings()
