"""
Utils - Funções utilitárias
"""

import sys
from typing import List, Optional
from .models import CANMessage


def get_platform_display_name() -> str:
    """Return display name for current OS (e.g. macOS, Linux, Windows)."""
    return {"darwin": "macOS", "linux": "Linux", "win32": "Windows"}.get(
        sys.platform, sys.platform.capitalize()
    )


def calculate_toyota_crc(data: bytes, indices: List[int]) -> int:
    """
    Calcula CRC Toyota (soma módulo 256)
    
    Args:
        data: Bytes de dados
        indices: Índices dos bytes a incluir no cálculo
    
    Returns:
        Valor CRC (0-255)
    """
    crc = 0
    for i in indices:
        if i < len(data):
            crc = (crc + data[i]) & 0xFF
    return crc


def calculate_iso_j1850_crc(data: bytes) -> int:
    """
    Calcula CRC ISO J1850
    
    Args:
        data: Bytes de dados (primeiros 7 bytes)
    
    Returns:
        Valor CRC para o 8º byte
    """
    crc = 0xFF
    for byte in data[:7]:
        crc ^= byte
        for _ in range(8):
            if crc & 0x80:
                crc = (crc << 1) ^ 0x1D
            else:
                crc = crc << 1
            crc &= 0xFF
    return crc


def validate_hex_input(text: str, max_bytes: int = 8) -> tuple[bool, Optional[bytes]]:
    """
    Valida entrada hexadecimal
    
    Args:
        text: String com bytes hex (ex: "00 11 22 33")
        max_bytes: Número máximo de bytes
    
    Returns:
        (válido, bytes ou None)
    """
    try:
        # Remover espaços e converter
        hex_str = text.replace(" ", "").replace("0x", "")
        
        # Verificar se é hex válido
        if not all(c in '0123456789ABCDEFabcdef' for c in hex_str):
            return False, None
        
        # Verificar tamanho
        if len(hex_str) > max_bytes * 2:
            return False, None
        
        # Converter para bytes
        data = bytes.fromhex(hex_str)
        return True, data
        
    except Exception:
        return False, None


def format_can_id(can_id: int, is_29bit: bool = False) -> str:
    """
    Formata ID CAN para exibição
    
    Args:
        can_id: ID CAN
        is_29bit: Se é ID de 29 bits
    
    Returns:
        String formatada (ex: "0x123" ou "0x00000123")
    """
    if is_29bit:
        return f"0x{can_id:08X}"
    else:
        return f"0x{can_id:03X}"


def parse_can_id(text: str) -> tuple[bool, Optional[int], bool]:
    """
    Faz parse de ID CAN de string
    
    Args:
        text: String com ID (ex: "123", "0x123", "0x00000123")
    
    Returns:
        (válido, id ou None, is_29bit)
    """
    try:
        # Remover 0x se presente
        text = text.strip().replace("0x", "").replace("0X", "")
        
        # Converter para int
        can_id = int(text, 16)
        
        # Determinar se é 29 bits baseado no valor
        is_29bit = can_id > 0x7FF
        
        # Validar range
        if is_29bit and can_id > 0x1FFFFFFF:
            return False, None, False
        if not is_29bit and can_id > 0x7FF:
            return False, None, False
        
        return True, can_id, is_29bit
        
    except Exception:
        return False, None, False


def calculate_baudrate_divisor(target_baudrate: int, clock_freq: int = 16000000) -> tuple[bool, int, int]:
    """
    Calcula divisor de clock para baudrate CAN customizado
    
    Args:
        target_baudrate: Baudrate desejado em bps
        clock_freq: Frequência do clock em Hz (padrão 16MHz)
    
    Returns:
        (é_exato, divisor, baudrate_real)
    """
    # Fórmula simplificada: divisor = clock_freq / (baudrate * 16)
    divisor_float = clock_freq / (target_baudrate * 16)
    divisor = round(divisor_float)
    
    # Calcular baudrate real
    real_baudrate = clock_freq / (divisor * 16)
    
    # Verificar se é exato (margem de 1%)
    error_percent = abs(real_baudrate - target_baudrate) / target_baudrate * 100
    is_exact = error_percent < 1.0
    
    return is_exact, divisor, int(real_baudrate)


def filter_messages_by_id_range(
    messages: List[CANMessage],
    id_from: int,
    id_to: int,
    exclude_ids: Optional[List[int]] = None
) -> List[CANMessage]:
    """
    Filtra mensagens por range de ID
    
    Args:
        messages: Lista de mensagens
        id_from: ID inicial (inclusivo)
        id_to: ID final (inclusivo)
        exclude_ids: IDs para excluir
    
    Returns:
        Lista filtrada
    """
    exclude_ids = exclude_ids or []
    
    return [
        msg for msg in messages
        if id_from <= msg.can_id <= id_to and msg.can_id not in exclude_ids
    ]


def get_unique_ids(messages: List[CANMessage]) -> List[int]:
    """Retorna lista de IDs únicos ordenados"""
    return sorted(set(msg.can_id for msg in messages))


def format_timestamp(timestamp: float, format_type: str = "full") -> str:
    """
    Formata timestamp para exibição
    
    Args:
        timestamp: Timestamp Unix
        format_type: "full", "time", "ms"
    
    Returns:
        String formatada
    """
    from datetime import datetime
    
    dt = datetime.fromtimestamp(timestamp)
    
    if format_type == "full":
        return dt.strftime("%Y-%m-%d %H:%M:%S.%f")[:-3]
    elif format_type == "time":
        return dt.strftime("%H:%M:%S.%f")[:-3]
    elif format_type == "ms":
        return dt.strftime("%S.%f")[:-3]
    else:
        return str(timestamp)
