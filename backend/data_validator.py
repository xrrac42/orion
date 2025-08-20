"""
Módulo responsável pela validação de dados estruturados
Garante a integridade dos dados antes do processamento das regras de negócio
"""

import logging
import re
from typing import Dict, Any, List, Optional, NamedTuple
from datetime import datetime
from decimal import Decimal, InvalidOperation

logger = logging.getLogger(__name__)

class ValidationResult(NamedTuple):
    """Resultado da validação"""
    is_valid: bool
    errors: List[str]
    warnings: List[str]

class DataValidator:
    """
    Classe responsável por validar dados estruturados do balancete
    """
    
    def __init__(self):
        self.valid_grupos_principais = ["RECEITAS", "CUSTOS E DESPESAS"]
        self.min_client_name_length = 3
        self.max_client_name_length = 200
    
    def validate_structure(self, data: Dict[str, Any]) -> ValidationResult:
        """
        Valida a estrutura completa dos dados do balancete
        
        Args:
            data: Dados estruturados do balancete
            
        Returns:
            ValidationResult com resultado da validação
        """
        errors = []
        warnings = []
        
        try:
            # Validar estrutura básica
            basic_errors = self._validate_basic_structure(data)
            errors.extend(basic_errors)
            
            # Se estrutura básica é inválida, parar aqui
            if basic_errors:
                return ValidationResult(False, errors, warnings)
            
            # Validar cliente
            client_errors, client_warnings = self._validate_cliente(data["cliente"])
            errors.extend(client_errors)
            warnings.extend(client_warnings)
            
            # Validar data
            date_errors = self._validate_data_final(data["data_final"])
            errors.extend(date_errors)
            
            # Validar contas
            contas_errors, contas_warnings = self._validate_contas(data["contas"])
            errors.extend(contas_errors)
            warnings.extend(contas_warnings)
            
            # Verificar se há pelo menos uma conta válida
            if not errors and len(data["contas"]) == 0:
                warnings.append("Nenhuma conta encontrada no balancete")
            
            is_valid = len(errors) == 0
            
            if is_valid:
                logger.info(f"Validação bem-sucedida: {len(data['contas'])} contas validadas")
            else:
                logger.error(f"Validação falhou com {len(errors)} erros")
            
            return ValidationResult(is_valid, errors, warnings)
            
        except Exception as e:
            logger.error(f"Erro inesperado na validação: {str(e)}")
            return ValidationResult(False, [f"Erro interno na validação: {str(e)}"], warnings)
    
    def _validate_basic_structure(self, data: Dict[str, Any]) -> List[str]:
        """Valida estrutura básica do JSON"""
        errors = []
        
        # Verificar se é um dicionário
        if not isinstance(data, dict):
            errors.append("Dados devem ser um objeto JSON")
            return errors
        
        # Verificar campos obrigatórios
        required_fields = ["cliente", "data_final", "contas"]
        for field in required_fields:
            if field not in data:
                errors.append(f"Campo obrigatório ausente: {field}")
        
        # Verificar tipo dos campos
        if "cliente" in data and not isinstance(data["cliente"], str):
            errors.append("Campo 'cliente' deve ser uma string")
        
        if "data_final" in data and not isinstance(data["data_final"], str):
            errors.append("Campo 'data_final' deve ser uma string")
        
        if "contas" in data and not isinstance(data["contas"], list):
            errors.append("Campo 'contas' deve ser uma lista")
        
        return errors
    
    def _validate_cliente(self, cliente: str) -> tuple[List[str], List[str]]:
        """Valida dados do cliente"""
        errors = []
        warnings = []
        
        # Verificar se não está vazio
        if not cliente or not cliente.strip():
            errors.append("Nome do cliente não pode estar vazio")
            return errors, warnings
        
        cliente_clean = cliente.strip()
        
        # Verificar comprimento
        if len(cliente_clean) < self.min_client_name_length:
            errors.append(f"Nome do cliente muito curto (mínimo: {self.min_client_name_length} caracteres)")
        
        if len(cliente_clean) > self.max_client_name_length:
            errors.append(f"Nome do cliente muito longo (máximo: {self.max_client_name_length} caracteres)")
        
        # Verificar caracteres suspeitos
        if re.search(r'[<>{}[\]\\]', cliente_clean):
            warnings.append("Nome do cliente contém caracteres suspeitos")
        
        # Verificar se parece com nome de empresa
        if not re.search(r'[a-zA-ZÀ-ÿ]', cliente_clean):
            warnings.append("Nome do cliente não contém letras válidas")
        
        return errors, warnings
    
    def _validate_data_final(self, data_final: str) -> List[str]:
        """Valida formato da data"""
        errors = []
        
        if not data_final or not data_final.strip():
            errors.append("Data final não pode estar vazia")
            return errors
        
        # Verificar formato YYYY-MM-DD
        date_pattern = r'^\d{4}-\d{2}-\d{2}$'
        if not re.match(date_pattern, data_final.strip()):
            errors.append("Data final deve estar no formato YYYY-MM-DD")
            return errors
        
        # Tentar converter para data válida
        try:
            date_obj = datetime.strptime(data_final.strip(), '%Y-%m-%d')
            
            # Verificar se a data não é muito antiga (mais de 10 anos)
            current_year = datetime.now().year
            if date_obj.year < (current_year - 10):
                errors.append(f"Data parece muito antiga: {data_final}")
            
            # Verificar se a data não é futura (mais de 1 ano)
            if date_obj.year > (current_year + 1):
                errors.append(f"Data parece ser futura demais: {data_final}")
                
        except ValueError:
            errors.append(f"Data inválida: {data_final}")
        
        return errors
    
    def _validate_contas(self, contas: List[Dict[str, Any]]) -> tuple[List[str], List[str]]:
        """Valida lista de contas"""
        errors = []
        warnings = []
        
        if not isinstance(contas, list):
            errors.append("Contas deve ser uma lista")
            return errors, warnings
        
        for i, conta in enumerate(contas):
            conta_errors, conta_warnings = self._validate_conta(conta, i)
            errors.extend(conta_errors)
            warnings.extend(conta_warnings)
        
        # Verificar duplicatas
        duplicates = self._check_duplicate_contas(contas)
        if duplicates:
            warnings.extend([f"Conta duplicada encontrada: {dup}" for dup in duplicates])
        
        return errors, warnings
    
    def _validate_conta(self, conta: Dict[str, Any], index: int) -> tuple[List[str], List[str]]:
        """Valida uma conta individual"""
        errors = []
        warnings = []
        
        prefix = f"Conta {index + 1}"
        
        # Verificar se é um dicionário
        if not isinstance(conta, dict):
            errors.append(f"{prefix}: deve ser um objeto")
            return errors, warnings
        
        # Campos obrigatórios
        required_fields = ["grupo_principal", "conta_especifica", "valor_debito", "valor_credito"]
        for field in required_fields:
            if field not in conta:
                errors.append(f"{prefix}: campo obrigatório ausente: {field}")
        
        # Se campos obrigatórios ausentes, parar validação desta conta
        if any(field not in conta for field in required_fields):
            return errors, warnings
        
        # Validar grupo principal
        grupo_errors = self._validate_grupo_principal(conta["grupo_principal"], prefix)
        errors.extend(grupo_errors)
        
        # Validar conta específica
        conta_errors = self._validate_conta_especifica(conta["conta_especifica"], prefix)
        errors.extend(conta_errors)
        
        # Validar valores
        valor_errors, valor_warnings = self._validate_valores(
            conta["valor_debito"], conta["valor_credito"], prefix
        )
        errors.extend(valor_errors)
        warnings.extend(valor_warnings)
        
        return errors, warnings
    
    def _validate_grupo_principal(self, grupo: Any, prefix: str) -> List[str]:
        """Valida grupo principal da conta"""
        errors = []
        
        if not isinstance(grupo, str):
            errors.append(f"{prefix}: grupo_principal deve ser uma string")
            return errors
        
        grupo_clean = grupo.strip().upper()
        
        if not grupo_clean:
            errors.append(f"{prefix}: grupo_principal não pode estar vazio")
            return errors
        
        if grupo_clean not in self.valid_grupos_principais:
            errors.append(
                f"{prefix}: grupo_principal inválido '{grupo}'. "
                f"Valores válidos: {', '.join(self.valid_grupos_principais)}"
            )
        
        return errors
    
    def _validate_conta_especifica(self, conta: Any, prefix: str) -> List[str]:
        """Valida nome da conta específica"""
        errors = []
        
        if not isinstance(conta, str):
            errors.append(f"{prefix}: conta_especifica deve ser uma string")
            return errors
        
        conta_clean = conta.strip()
        
        if not conta_clean:
            errors.append(f"{prefix}: conta_especifica não pode estar vazia")
            return errors
        
        if len(conta_clean) < 3:
            errors.append(f"{prefix}: conta_especifica muito curta (mínimo 3 caracteres)")
        
        if len(conta_clean) > 200:
            errors.append(f"{prefix}: conta_especifica muito longa (máximo 200 caracteres)")
        
        return errors
    
    def _validate_valores(self, valor_debito: Any, valor_credito: Any, prefix: str) -> tuple[List[str], List[str]]:
        """Valida valores de débito e crédito"""
        errors = []
        warnings = []
        
        # Validar valor_debito
        debito_errors, debito_warnings, debito_decimal = self._validate_single_valor(
            valor_debito, f"{prefix}: valor_debito"
        )
        errors.extend(debito_errors)
        warnings.extend(debito_warnings)
        
        # Validar valor_credito
        credito_errors, credito_warnings, credito_decimal = self._validate_single_valor(
            valor_credito, f"{prefix}: valor_credito"
        )
        errors.extend(credito_errors)
        warnings.extend(credito_warnings)
        
        # Verificar lógica de negócio dos valores
        if debito_decimal is not None and credito_decimal is not None:
            if debito_decimal == 0 and credito_decimal == 0:
                warnings.append(f"{prefix}: ambos os valores são zero")
            elif debito_decimal > 0 and credito_decimal > 0:
                warnings.append(f"{prefix}: ambos os valores são positivos")
        
        return errors, warnings
    
    def _validate_single_valor(self, valor: Any, prefix: str) -> tuple[List[str], List[str], Optional[Decimal]]:
        """Valida um valor individual"""
        errors = []
        warnings = []
        decimal_value = None
        
        # Verificar tipo
        if not isinstance(valor, (int, float, str)):
            errors.append(f"{prefix}: deve ser um número ou string numérica")
            return errors, warnings, None
        
        # Tentar converter para Decimal
        try:
            if isinstance(valor, str):
                # Limpar string numérica
                cleaned_valor = self._clean_numeric_string(valor)
                decimal_value = Decimal(cleaned_valor)
            else:
                decimal_value = Decimal(str(valor))
            
            # Verificar se é negativo
            if decimal_value < 0:
                warnings.append(f"{prefix}: valor negativo convertido para positivo")
                decimal_value = abs(decimal_value)
            
            # Verificar valores muito grandes
            if decimal_value > Decimal('999999999999.99'):
                warnings.append(f"{prefix}: valor muito grande: {decimal_value}")
            
        except (InvalidOperation, ValueError) as e:
            errors.append(f"{prefix}: valor inválido '{valor}': {str(e)}")
        
        return errors, warnings, decimal_value
    
    def _clean_numeric_string(self, value: str) -> str:
        """Limpa string numérica para conversão"""
        if not isinstance(value, str):
            return str(value)
        
        # Remover espaços
        cleaned = value.strip()
        
        # Remover parênteses (números negativos)
        cleaned = cleaned.replace('(', '').replace(')', '')
        
        # Detectar formato brasileiro (1.234,56) vs americano (1,234.56)
        if ',' in cleaned and '.' in cleaned:
            # Se tem ambos, verificar qual é o separador decimal
            last_comma = cleaned.rfind(',')
            last_dot = cleaned.rfind('.')
            
            if last_comma > last_dot:
                # Formato brasileiro: 1.234,56
                cleaned = cleaned.replace('.', '').replace(',', '.')
            else:
                # Formato americano: 1,234.56
                cleaned = cleaned.replace(',', '')
        elif ',' in cleaned:
            # Só vírgula - assumir formato brasileiro se houver exatamente 2 dígitos após vírgula
            parts = cleaned.split(',')
            if len(parts) == 2 and len(parts[1]) == 2:
                cleaned = cleaned.replace(',', '.')
            else:
                # Vírgula como separador de milhares
                cleaned = cleaned.replace(',', '')
        
        # Remover caracteres não numéricos exceto ponto e sinal negativo
        cleaned = re.sub(r'[^\d.-]', '', cleaned)
        
        return cleaned
    
    def _check_duplicate_contas(self, contas: List[Dict[str, Any]]) -> List[str]:
        """Verifica contas duplicadas"""
        seen = set()
        duplicates = []
        
        for conta in contas:
            if not isinstance(conta, dict):
                continue
            
            # Criar chave única baseada no grupo e conta específica
            key = (
                conta.get("grupo_principal", "").strip().upper(),
                conta.get("conta_especifica", "").strip().upper()
            )
            
            if key in seen and key[1]:  # Só reportar se conta_especifica não está vazia
                duplicates.append(f"{key[0]} - {key[1]}")
            else:
                seen.add(key)
        
        return list(set(duplicates))  # Remover duplicatas da lista de duplicatas
