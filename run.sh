#!/bin/bash
# CAN Analyzer para macOS - Script de execução
# Automatiza a criação do venv e instalação de dependências

set -e
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
RED='\033[0;31m'
NC='\033[0m' # No Color

echo -e "${GREEN}CAN Analyzer para macOS${NC}"
echo "================================"

# Verificar se o venv existe
if [ ! -d "venv" ]; then
    echo -e "${YELLOW}Ambiente virtual não encontrado. Criando...${NC}"
    python3 -m venv venv
    
    if [ $? -ne 0 ]; then
        echo -e "${RED}Erro ao criar ambiente virtual!${NC}"
        exit 1
    fi
    
    echo -e "${GREEN}Ambiente virtual criado com sucesso!${NC}"
fi

# Ativar o ambiente virtual
echo -e "${YELLOW}Ativando ambiente virtual...${NC}"
source venv/bin/activate

# Verificar se as dependências estão instaladas
if ! python -c "import can" 2>/dev/null; then
    echo -e "${YELLOW}Instalando dependências de runtime...${NC}"
    pip install --upgrade pip
    pip install -r requirements.txt
    
    if [ $? -ne 0 ]; then
        echo -e "${RED}Erro ao instalar dependências!${NC}"
        exit 1
    fi
    
    echo -e "${GREEN}Dependências instaladas com sucesso!${NC}"
fi

# Executar a aplicação
echo -e "${GREEN}Iniciando CAN Analyzer...${NC}"
python can_analyzer_qt.py

# Desativar o ambiente virtual ao sair
deactivate
