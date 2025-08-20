"""
Módulo responsável pelas regras de negócio do processamento de balancetes
Aplica lógica determinística para classificar e processar contas contábeis
"""

import logging
from typing import Dict, Any, List, Optional
from datetime import datetime
from decimal import Decimal
import uuid

logger = logging.getLogger(__name__)

class BusinessRuleEngine:
    """
    Classe responsável por aplicar regras de negócio aos dados validados
    """
    
    def __init__(self):
        # Mapeamento de grupos principais para tipos de movimento
        self.movement_type_mapping = {
            "RECEITAS": "Receita",
            "CUSTOS E DESPESAS": "Despesa"
        }
        
        # Subgrupos conhecidos para melhor categorização
        self.known_subgroups = {
            "RECEITAS": [
                "RECEITA DE VENDAS",
                "RECEITA DE SERVIÇOS", 
                "OUTRAS RECEITAS",
                "RECEITAS OPERACIONAIS",
                "RECEITAS NÃO OPERACIONAIS"
            ],
            "CUSTOS E DESPESAS": [
                "CUSTO DOS PRODUTOS VENDIDOS",
                "CUSTO DOS SERVIÇOS PRESTADOS",
                "DESPESAS OPERACIONAIS",
                "DESPESAS ADMINISTRATIVAS",
                "DESPESAS COMERCIAIS",
                "DESPESAS FINANCEIRAS",
                "OUTRAS DESPESAS"
            ]
        }
    
    def process_accounts(self, contas: List[Dict[str, Any]], client_id: str, data_final: str) -> List[Dict[str, Any]]:
        """
        Processa lista de contas aplicando regras de negócio
        
        Args:
            contas: Lista de contas validadas
            client_id: ID do cliente
            data_final: Data final do período
            
        Returns:
            Lista de entradas financeiras prontas para armazenamento
        """
        processed_entries = []
        
        try:
            logger.info(f"Processando {len(contas)} contas para cliente {client_id}")
            
            for i, conta in enumerate(contas):
                try:
                    entry = self._process_single_account(conta, client_id, data_final)
                    if entry:
                        processed_entries.append(entry)
                        logger.debug(f"Conta {i+1} processada: {conta.get('conta_especifica', 'N/A')}")
                    else:
                        logger.warning(f"Conta {i+1} não pôde ser processada")
                        
                except Exception as e:
                    logger.error(f"Erro ao processar conta {i+1}: {str(e)}")
                    continue
            
            logger.info(f"Processamento concluído: {len(processed_entries)} entradas criadas")
            return processed_entries
            
        except Exception as e:
            logger.error(f"Erro no processamento das contas: {str(e)}")
            return []
    
    def _process_single_account(self, conta: Dict[str, Any], client_id: str, data_final: str) -> Optional[Dict[str, Any]]:
        """
        Processa uma conta individual aplicando regras de negócio
        """
        try:
            # Extrair dados da conta
            grupo_principal = conta.get("grupo_principal", "").strip().upper()
            subgrupo_1 = conta.get("subgrupo_1", "").strip() if conta.get("subgrupo_1") else None
            conta_especifica = conta.get("conta_especifica", "").strip()
            valor_debito = self._convert_to_decimal(conta.get("valor_debito", 0))
            valor_credito = self._convert_to_decimal(conta.get("valor_credito", 0))
            
            # Aplicar regras de negócio para determinar movimento e valor
            movement_type, period_value = self._apply_movement_rules(
                grupo_principal, valor_debito, valor_credito
            )
            
            # Se não há valor de movimento, pular esta conta
            if period_value <= 0:
                logger.debug(f"Conta sem movimento pulada: {conta_especifica}")
                return None
            
            # Normalizar subgrupo
            normalized_subgroup = self._normalize_subgroup(grupo_principal, subgrupo_1)
            
            # Converter data
            report_date = self._convert_date(data_final)
            
            # Criar entrada financeira
            entry = {
                "id": str(uuid.uuid4()),  # ID único para a entrada
                "client_id": client_id,
                "report_date": report_date,
                "main_group": grupo_principal,
                "subgroup_1": normalized_subgroup,
                "specific_account": conta_especifica,
                "movement_type": movement_type,
                "period_value": float(period_value),
                "created_at": datetime.utcnow().isoformat(),
                # Dados originais para auditoria
                "original_data": {
                    "valor_debito": float(valor_debito),
                    "valor_credito": float(valor_credito)
                }
            }
            
            return entry
            
        except Exception as e:
            logger.error(f"Erro ao processar conta individual: {str(e)}")
            return None
    
    def _apply_movement_rules(self, grupo_principal: str, valor_debito: Decimal, valor_credito: Decimal) -> tuple[str, Decimal]:
        """
        Aplica regras de negócio para determinar tipo de movimento e valor
        
        Regras:
        - RECEITAS: movement_type = 'Receita', valor = valor_credito
        - CUSTOS E DESPESAS: movement_type = 'Despesa', valor = valor_debito
        """
        try:
            # Mapear grupo principal para tipo de movimento
            movement_type = self.movement_type_mapping.get(grupo_principal)
            
            if not movement_type:
                logger.warning(f"Grupo principal não reconhecido: {grupo_principal}")
                # Fallback: tentar inferir pelo comportamento dos valores
                if valor_credito > valor_debito:
                    movement_type = "Receita"
                    period_value = valor_credito
                else:
                    movement_type = "Despesa"
                    period_value = valor_debito
            else:
                # Aplicar regras específicas por tipo
                if movement_type == "Receita":
                    period_value = valor_credito
                else:  # Despesa
                    period_value = valor_debito
            
            # Garantir que o valor seja positivo
            period_value = abs(period_value)
            
            return movement_type, period_value
            
        except Exception as e:
            logger.error(f"Erro ao aplicar regras de movimento: {str(e)}")
            return "Despesa", abs(valor_debito + valor_credito)
    
    def _normalize_subgroup(self, grupo_principal: str, subgrupo_raw: Optional[str]) -> Optional[str]:
        """
        Normaliza subgrupo baseado em padrões conhecidos
        """
        if not subgrupo_raw:
            return None
        
        subgrupo_clean = subgrupo_raw.strip().upper()
        
        # Verificar se o subgrupo está na lista de conhecidos
        known_for_group = self.known_subgroups.get(grupo_principal, [])
        
        for known_subgroup in known_for_group:
            if known_subgroup.upper() in subgrupo_clean or subgrupo_clean in known_subgroup.upper():
                return known_subgroup
        
        # Se não encontrou correspondência, retornar o subgrupo limpo em título
        return subgrupo_clean.title()
    
    def _convert_to_decimal(self, value: Any) -> Decimal:
        """
        Converte valor para Decimal de forma segura
        """
        try:
            if isinstance(value, (int, float)):
                return Decimal(str(value))
            elif isinstance(value, str):
                # Limpar string numérica
                cleaned = value.strip().replace(',', '.')
                cleaned = ''.join(c for c in cleaned if c.isdigit() or c in '.-')
                return Decimal(cleaned) if cleaned else Decimal('0')
            else:
                return Decimal('0')
                
        except Exception:
            logger.warning(f"Não foi possível converter valor: {value}")
            return Decimal('0')
    
    def _convert_date(self, date_string: str) -> str:
        """
        Converte string de data para formato ISO
        """
        try:
            # Assumir que já está no formato YYYY-MM-DD (validado anteriormente)
            date_obj = datetime.strptime(date_string.strip(), '%Y-%m-%d')
            return date_obj.date().isoformat()
            
        except Exception as e:
            logger.error(f"Erro ao converter data: {str(e)}")
            # Fallback para data atual
            return datetime.utcnow().date().isoformat()
    
    def generate_summary(self, processed_entries: List[Dict[str, Any]]) -> Dict[str, Any]:
        """
        Gera resumo das entradas processadas
        """
        try:
            if not processed_entries:
                return {
                    "total_entries": 0,
                    "total_receitas": 0.0,
                    "total_despesas": 0.0,
                    "saldo_liquido": 0.0,
                    "grupos_principais": [],
                    "periodo": None
                }
            
            total_receitas = sum(
                entry["period_value"] 
                for entry in processed_entries 
                if entry["movement_type"] == "Receita"
            )
            
            total_despesas = sum(
                entry["period_value"] 
                for entry in processed_entries 
                if entry["movement_type"] == "Despesa"
            )
            
            grupos_principais = list(set(
                entry["main_group"] 
                for entry in processed_entries
            ))
            
            periodo = processed_entries[0]["report_date"] if processed_entries else None
            
            return {
                "total_entries": len(processed_entries),
                "total_receitas": total_receitas,
                "total_despesas": total_despesas,
                "saldo_liquido": total_receitas - total_despesas,
                "grupos_principais": grupos_principais,
                "periodo": periodo,
                "breakdown_by_type": {
                    "receitas": [
                        entry for entry in processed_entries 
                        if entry["movement_type"] == "Receita"
                    ],
                    "despesas": [
                        entry for entry in processed_entries 
                        if entry["movement_type"] == "Despesa"
                    ]
                }
            }
            
        except Exception as e:
            logger.error(f"Erro ao gerar resumo: {str(e)}")
            return {"error": str(e)}
    
    def validate_business_logic(self, processed_entries: List[Dict[str, Any]]) -> List[str]:
        """
        Valida lógica de negócio das entradas processadas
        """
        warnings = []
        
        try:
            if not processed_entries:
                return ["Nenhuma entrada processada"]
            
            # Verificar se há receitas e despesas
            has_receitas = any(entry["movement_type"] == "Receita" for entry in processed_entries)
            has_despesas = any(entry["movement_type"] == "Despesa" for entry in processed_entries)
            
            if not has_receitas:
                warnings.append("Nenhuma receita encontrada no balancete")
            
            if not has_despesas:
                warnings.append("Nenhuma despesa encontrada no balancete")
            
            # Verificar valores muito baixos ou muito altos
            for entry in processed_entries:
                valor = entry["period_value"]
                if valor < 0.01:
                    warnings.append(f"Valor muito baixo na conta: {entry['specific_account']}")
                elif valor > 100000000:  # 100 milhões
                    warnings.append(f"Valor muito alto na conta: {entry['specific_account']}")
            
            # Verificar datas inconsistentes
            dates = set(entry["report_date"] for entry in processed_entries)
            if len(dates) > 1:
                warnings.append("Múltiplas datas encontradas nas entradas")
            
            return warnings
            
        except Exception as e:
            logger.error(f"Erro na validação de lógica de negócio: {str(e)}")
            return [f"Erro na validação: {str(e)}"]
