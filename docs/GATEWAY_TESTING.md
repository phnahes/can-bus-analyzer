# CAN Gateway - Testing Guide & Feature Status

## 📋 Funcionalidades Implementadas

### ✅ 1. Transmissão Bidirecional
**Status**: IMPLEMENTADO E FUNCIONAL

**O que faz:**
- Controla o fluxo de mensagens entre dois barramentos CAN
- CAN1 → CAN2: Encaminha mensagens do barramento 1 para o barramento 2
- CAN2 → CAN1: Encaminha mensagens do barramento 2 para o barramento 1
- Controle independente para cada direção

**Como testar:**
1. Configure 2 barramentos CAN em Settings (ou use modo simulação)
2. Conecte aos barramentos
3. Abra Tools → Gateway (Ctrl+W)
4. Marque "Enable Gateway"
5. Marque "Transmit from CAN1 to CAN2" e/ou "Transmit from CAN2 to CAN1"
6. Envie mensagens em um barramento
7. Observe as mensagens aparecerem no outro barramento
8. Verifique estatísticas: "Forwarded" deve incrementar

**Código:**
- `can_bus_manager.py`: `_process_gateway_message()` linhas 387-422
- Lógica: Verifica source do canal e encaminha baseado na configuração

---

### ✅ 2. Bloqueio Estático de Mensagens
**Status**: IMPLEMENTADO E FUNCIONAL

**O que faz:**
- Bloqueia IDs específicos em canais específicos
- Múltiplas regras podem ser configuradas simultaneamente
- Cada regra pode ser habilitada/desabilitada individualmente

**Como testar:**
1. Abra Gateway dialog (Ctrl+W)
2. Na seção "Static Blocking Rules":
   - Selecione o canal (CAN1 ou CAN2)
   - Digite o ID a bloquear (ex: 0x100)
   - Clique "Lock"
3. Envie mensagens com esse ID no canal bloqueado
4. Verifique que a mensagem NÃO aparece no outro barramento
5. Estatísticas: "Blocked" deve incrementar

**Exemplo prático:**
```
Canal: CAN1
ID: 0x250
Resultado: Mensagens 0x250 de CAN1 não passam para CAN2
```

**Código:**
- `models.py`: `GatewayBlockRule.matches()` linhas 177-179
- `models.py`: `GatewayConfig.should_block()` linhas 265-278

---

### ✅ 3. Bloqueio Dinâmico (ID Cycling)
**Status**: IMPLEMENTADO E FUNCIONAL

**O que faz:**
- Bloqueia uma faixa de IDs automaticamente
- Cicla através dos IDs com período configurável
- Útil para testar resposta de ECUs a mensagens faltantes

**Como testar:**
1. Abra Gateway dialog (Ctrl+W)
2. Na seção "Dynamic Blocking":
   - Canal: CAN1
   - ID From: 0x100
   - ID To: 0x110
   - Period: 1000 (ms)
   - Clique "Start"
3. Envie mensagens com IDs 0x100-0x110 continuamente
4. Observe que a cada 1 segundo, um ID diferente é bloqueado
5. O ID bloqueado cicla: 0x100 → 0x101 → ... → 0x110 → 0x100

**Código:**
- `models.py`: `GatewayDynamicBlock` linhas 183-203
- `can_bus_manager.py`: `_dynamic_blocking_loop()` linhas 443-463
- Thread separada gerencia o cycling automático

---

### ✅ 4. Modificação de Mensagens (Framework)
**Status**: IMPLEMENTADO (Backend completo, UI parcial)

**O que faz:**
- Modifica ID da mensagem durante passagem
- Modifica bytes de dados específicos
- Usa máscaras para selecionar quais bytes modificar

**Backend implementado:**
- `GatewayModifyRule.apply()` - Aplica modificações
- Suporta mudança de ID
- Suporta mudança de bytes individuais com máscara

**UI implementada:**
- Tabela para regras de modificação (vazia no dialog atual)
- Estrutura de dados completa

**O que falta na UI:**
- Botões para adicionar/remover regras de modificação
- Campos para configurar new_id e data_mask
- Integração com o dialog

**Como testar (quando UI estiver completa):**
```python
# Exemplo de regra:
# ID 0x100 de CAN1 → vira 0x200 no CAN2
# Byte 0 = 0xFF (forçado)
```

**Código:**
- `models.py`: `GatewayModifyRule.apply()` linhas 217-243
- `can_bus_manager.py`: Aplicação em `_process_gateway_message()` linhas 398-401

---

### ✅ 5. Estatísticas em Tempo Real
**Status**: IMPLEMENTADO E FUNCIONAL

**O que faz:**
- Conta mensagens encaminhadas (forwarded)
- Conta mensagens bloqueadas (blocked)
- Conta mensagens modificadas (modified)
- Atualização em tempo real no dialog

**Como testar:**
1. Abra Gateway dialog (Ctrl+W)
2. Configure regras de transmissão e bloqueio
3. Envie mensagens
4. Observe a linha de estatísticas atualizar:
   ```
   Forwarded: 50 | Blocked: 10 | Modified: 0
   ```
5. Clique "Reset Statistics" para zerar

**Código:**
- `can_bus_manager.py`: `gateway_stats` dict linhas 217-221
- Incrementos em `_process_gateway_message()` linhas 394, 401, 422

---

## 🧪 Cenários de Teste Completos

### Teste 1: Gateway Básico (Passthrough)
**Objetivo**: Verificar encaminhamento simples

```
Setup:
- 2 barramentos CAN configurados
- Gateway enabled
- Transmit CAN1→CAN2: ON
- Transmit CAN2→CAN1: OFF
- Sem regras de bloqueio

Teste:
1. Envie mensagem 0x100 em CAN1
2. Verifique que aparece em CAN2
3. Envie mensagem 0x200 em CAN2
4. Verifique que NÃO aparece em CAN1

Resultado esperado:
- Forwarded: 1
- Blocked: 0
```

### Teste 2: Bloqueio Seletivo
**Objetivo**: Bloquear IDs específicos

```
Setup:
- Gateway enabled
- Transmit CAN1→CAN2: ON
- Block rule: ID 0x250 no CAN1

Teste:
1. Envie 0x100 em CAN1 → deve passar
2. Envie 0x250 em CAN1 → deve ser bloqueado
3. Envie 0x300 em CAN1 → deve passar

Resultado esperado:
- Forwarded: 2
- Blocked: 1
```

### Teste 3: Bloqueio Dinâmico
**Objetivo**: Testar cycling de IDs

```
Setup:
- Gateway enabled
- Transmit CAN1→CAN2: ON
- Dynamic block: 0x100-0x105, period=500ms

Teste:
1. Envie mensagens 0x100-0x105 continuamente (100ms cada)
2. Observe que a cada 500ms um ID diferente é bloqueado
3. Use Split-Screen para ver lado a lado

Resultado esperado:
- Padrão de bloqueio rotativo visível
- Blocked incrementa periodicamente
```

### Teste 4: Gateway Bidirecional
**Objetivo**: Comunicação nos dois sentidos

```
Setup:
- Gateway enabled
- Transmit CAN1→CAN2: ON
- Transmit CAN2→CAN1: ON

Teste:
1. Envie 0x100 em CAN1
2. Envie 0x200 em CAN2
3. Ambas devem aparecer nos dois barramentos

Resultado esperado:
- Forwarded: 2
- Ambos os canais veem todas as mensagens
```

### Teste 5: Isolamento Completo
**Objetivo**: Verificar que sem gateway não há comunicação

```
Setup:
- Gateway DISABLED
- Ou Transmit CAN1→CAN2: OFF e CAN2→CAN1: OFF

Teste:
1. Envie mensagens em ambos os barramentos
2. Cada barramento deve ver apenas suas próprias mensagens

Resultado esperado:
- Forwarded: 0
- Isolamento total entre redes
```

### Teste 6: Modificação de Mensagens com Bits
**Objetivo**: Testar modificação bit-a-bit

```
Setup:
- Gateway enabled
- Transmit CAN1→CAN2: ON
- Modify rule configurada:
  - Canal: CAN1
  - ID: 0x100
  - Modificações:
    - Byte 0: Bit 7 = 1, Bit 0 = 1 (0x81)
    - Byte 1: 0xFF (todos bits = 1)
    - Outros bytes: não modificados

Teste:
1. Envie mensagem 0x100 em CAN1 com data [00 00 00 00 00 00 00 00]
2. Em CAN2, observe mensagem modificada: [81 FF 00 00 00 00 00 00]
3. Verifique estatísticas: Modified = 1, Forwarded = 1

Resultado esperado:
- Mensagem aparece modificada em CAN2
- Bytes não marcados permanecem originais
- Preview no dialog mostra modificações corretamente
```

### Teste 7: Validação de Tipos de Arquivo
**Objetivo**: Verificar proteção contra carregamento incorreto

```
Teste A - Arquivo de TX no Tracer:
1. Salve uma lista de transmissão (Save Transmit List)
2. Mude para modo Tracer
3. Tente carregar o arquivo de TX
4. Deve mostrar erro: "Wrong file type! Expected: Tracer Log, Found: Transmit List"

Teste B - Arquivo de Tracer no Monitor:
1. Salve um log de Tracer
2. Mude para modo Monitor
3. Tente carregar o arquivo
4. Deve mostrar erro: "Wrong file type! Expected: Monitor Log, Found: Tracer Log"

Teste C - Arquivo de Gateway como TX:
1. Salve configuração do Gateway
2. Tente carregar em Load Transmit List
3. Deve mostrar erro apropriado

Resultado esperado:
- Proteção total contra carregamento incorreto
- Mensagens de erro claras e informativas
- Arquivos antigos (sem tipo) ainda funcionam
```

### Teste 8: Save/Load Configuração Gateway
**Objetivo**: Testar persistência de configuração

```
Setup:
- Configure Gateway complexo:
  - Transmit CAN1→CAN2: ON
  - 3 regras de bloqueio estático
  - 1 bloqueio dinâmico
  - 2 regras de modificação

Teste:
1. Clique "Save Gateway Configuration"
2. Salve como "test_profile.gwcfg"
3. Feche o dialog
4. Limpe todas as regras manualmente
5. Clique "Load Gateway Configuration"
6. Carregue "test_profile.gwcfg"
7. Verifique que TODAS as regras foram restauradas

Resultado esperado:
- Arquivo .gwcfg criado com sucesso
- Todas as regras restauradas exatamente como estavam
- Checkboxes de enabled preservados
- Valores de período, IDs, máscaras corretos
```

---

## ✅ Funcionalidades Recém-Implementadas

### Modificação de Mensagens com Máscaras de Bits
**Interface interativa completa!**

**Recursos:**
- Editor visual de 8 bytes
- Cada byte pode ser habilitado/desabilitado individualmente
- Edição em hex (2 dígitos) ou bit-a-bit (8 checkboxes)
- Preview em tempo real mostrando original vs modificado
- Suporte para mudança de ID
- Máscaras de bits para modificação seletiva

**Exemplo de uso:**
```
Mensagem original: ID=0x100, Data=[01 02 03 04 05 06 07 08]

Configuração:
- Change ID: ✓ New ID: 0x200
- Byte 0: ✓ Modify → 0xFF
- Byte 3: ✓ Modify → Bit 7=1, Bit 0=1 (resultado: 0x81)
- Bytes 1,2,4-7: não modificados

Resultado: ID=0x200, Data=[FF 02 03 81 05 06 07 08]
```

### Validação de Tipos de Arquivo
**Proteção contra carregamento incorreto!**

**O que foi implementado:**
- Todos os arquivos JSON salvos agora incluem campo `file_type`
- Tipos suportados:
  - `tracer`: Logs do modo Tracer
  - `monitor`: Logs do modo Monitor
  - `transmit`: Listas de transmissão
  - `gateway`: Configurações do Gateway
- Validação automática ao carregar
- Mensagem de erro clara se tipo incorreto
- Compatibilidade com arquivos antigos (sem tipo)

**Exemplos de validação:**
- Tentar carregar arquivo de TX no Tracer → ❌ Erro explicativo
- Tentar carregar arquivo de Tracer no Monitor → ❌ Erro explicativo
- Tentar carregar arquivo de Gateway como TX → ❌ Erro explicativo
- Carregar arquivo antigo (sem tipo) → ✅ Permitido (compatibilidade)

### Save/Load de Configuração do Gateway
**Perfis de Gateway persistentes!**

**Recursos:**
- Botões "Save Gateway Configuration" e "Load Gateway Configuration"
- Formato: `.gwcfg` (ou `.json`)
- Salva TUDO:
  - Estado de habilitação
  - Direções de transmissão
  - Todas as regras de bloqueio estático
  - Todos os bloqueios dinâmicos
  - Todas as regras de modificação
- Carregamento restaura interface completa
- Validação de tipo de arquivo

**Casos de uso:**
- Criar perfis para diferentes cenários de teste
- Compartilhar configurações entre membros da equipe
- Backup de configurações complexas
- Trocar rapidamente entre setups

## 🚧 Funcionalidades Pendentes

### 1. Interface de Modificação de Mensagens
**Status**: ✅ IMPLEMENTADO E FUNCIONAL

**O que tem:**
- ✅ Botão "Add Modify Rule" no dialog
- ✅ Dialog interativo `ModifyRuleDialog` com:
  - Checkbox para modificar ID (com campo para novo ID)
  - 8 editores de bytes individuais
  - Cada byte tem:
    - Checkbox "Modify this byte"
    - Campo hex (2 dígitos)
    - 8 checkboxes de bits (MSB→LSB)
    - Display decimal do valor
  - Preview em tempo real das modificações
- ✅ Tabela mostrando regras ativas
- ✅ Botão para remover regras
- ✅ Double-click para editar regras existentes

**Como usar:**
1. No Gateway dialog, seção "Message Modification"
2. Selecione canal e digite ID da mensagem
3. Clique "Add Modify Rule"
4. No dialog que abre:
   - Marque "Change ID" se quiser mudar o ID
   - Para cada byte que quer modificar:
     - Marque "Modify this byte"
     - Edite o valor hex OU
     - Toggle bits individuais (0-7)
   - Veja preview em tempo real
5. Clique OK para salvar

**Backend**: ✅ Completo
**UI**: ✅ Completo e interativo!

### 2. Filtros Avançados
**Ideias para futuro:**
- Filtrar por DLC
- Filtrar por conteúdo de dados (padrões)
- Filtrar por taxa de mensagens
- Whitelist/Blacklist mode

### 3. Salvamento de Configuração
**Status**: ✅ IMPLEMENTADO E FUNCIONAL

**O que faz:**
- Salva toda configuração do Gateway em arquivo (.gwcfg ou .json)
- Carrega configuração salva
- Validação de tipo de arquivo
- Permite criar perfis/cenários diferentes

**Como usar:**
1. Configure o Gateway (regras de bloqueio, transmissão, etc.)
2. No dialog Gateway, clique "Save Gateway Configuration"
3. Escolha nome e local do arquivo (ex: `gateway_profile_1.gwcfg`)
4. Para carregar: clique "Load Gateway Configuration"
5. Selecione o arquivo salvo
6. Todas as regras são restauradas automaticamente

**Formato do arquivo:**
```json
{
  "version": "1.0",
  "file_type": "gateway",
  "gateway_config": {
    "transmit_1_to_2": true,
    "transmit_2_to_1": false,
    "enabled": true,
    "block_rules": [...],
    "dynamic_blocks": [...],
    "modify_rules": [...]
  }
}
```

### 4. Logs do Gateway
**Ideias:**
- Log de mensagens bloqueadas
- Log de mensagens modificadas
- Exportar logs para análise

---

## 🔧 Testando com 3 Controladores CAN

### Configuração Avançada com 3 Barramentos

Com 3 controladores CAN, você pode criar cenários de teste muito mais realistas:

#### **Cenário 1: Gateway + Monitor Externo**
```
CAN1 (Rede A) ←→ Gateway ←→ CAN2 (Rede B)
                     ↓
                   CAN3 (Monitor)
```

**Setup:**
1. Configure 3 barramentos em Settings:
   - CAN1: `/dev/ttyUSB0` (Rede A)
   - CAN2: `/dev/ttyUSB1` (Rede B)
   - CAN3: `/dev/ttyUSB2` (Monitor/Sniffer)

2. Gateway configuration:
   - Transmit CAN1→CAN2: ON
   - Transmit CAN2→CAN1: ON
   - Regras de bloqueio/modificação conforme necessário

3. Conexões físicas:
   - CAN1 conectado à Rede A
   - CAN2 conectado à Rede B
   - CAN3 conectado a AMBAS as redes (via Y-cable ou hub)

**Vantagens:**
- CAN3 vê TODAS as mensagens (originais de ambas as redes)
- CAN1 e CAN2 veem apenas o que o Gateway permite
- Permite comparar mensagens originais vs modificadas
- Debugging completo do comportamento do Gateway

**Como testar:**
1. Use Split-Screen com CAN1 e CAN2 para ver o Gateway em ação
2. Use CAN3 em uma janela separada (ou terceiro painel) para ver tudo
3. Compare mensagens originais (CAN3) com modificadas (CAN1/CAN2)

#### **Cenário 2: Gateway em Cascata**
```
CAN1 → Gateway A → CAN2 → Gateway B → CAN3
```

**Setup:**
1. Configure 3 barramentos
2. Use o aplicativo para simular Gateway A (CAN1→CAN2)
3. Use hardware externo ou outro aplicativo para Gateway B (CAN2→CAN3)

**Teste:**
- Mensagem enviada em CAN1
- Modificada pelo Gateway A ao passar para CAN2
- Modificada novamente ao passar para CAN3
- Teste de múltiplas transformações

#### **Cenário 3: Teste de Injeção**
```
CAN1 (ECU Real) ←→ Gateway ←→ CAN2 (Teste)
                                    ↑
                                  CAN3 (Injetor)
```

**Setup:**
1. CAN1: Conectado a ECU real
2. CAN2: Rede de teste isolada
3. CAN3: Usado para injetar mensagens de teste

**Uso:**
- Gateway filtra mensagens da ECU real
- CAN3 injeta mensagens específicas em CAN2
- Teste comportamento de ECUs com mensagens controladas
- Segurança: ECU real isolada da rede de teste

#### **Cenário 4: Comparação A/B**
```
Fonte → CAN1 (Gateway OFF) → Monitor A
     → CAN2 (Gateway ON)  → Monitor B
     → CAN3 (Referência)
```

**Setup:**
1. Mesma fonte de mensagens para CAN1 e CAN2
2. CAN1: Sem Gateway (passthrough)
3. CAN2: Com Gateway e modificações
4. CAN3: Captura mensagens originais

**Teste:**
- Compare comportamento com e sem Gateway
- Valide que modificações são aplicadas corretamente
- Benchmark de performance

### Limitação Atual

**IMPORTANTE:** O Gateway atual trabalha com os **2 primeiros barramentos** configurados:
- Bus 1 = Primeiro barramento na lista
- Bus 2 = Segundo barramento na lista

**Para usar 3 barramentos:**
- Configure 3 barramentos em Settings
- Gateway usará os 2 primeiros (CAN1 e CAN2)
- O terceiro barramento (CAN3) pode ser usado para:
  - Monitoramento independente
  - Injeção de mensagens
  - Referência/comparação
  - Não participa do Gateway

**Workaround para testar diferentes pares:**
- Reordene os barramentos em Settings
- Exemplo: Para testar Gateway entre CAN2↔CAN3:
  - Coloque CAN2 como primeiro
  - Coloque CAN3 como segundo
  - CAN1 fica como terceiro (não usado pelo Gateway)

---

## 🔧 Teste com 3 Controladores CAN (Setup Ideal)

### Configuração Recomendada

**Hardware necessário:**
- 2 adaptadores CAN USB conectados ao computador
- 1 módulo/dispositivo CAN enviando mensagens
- Cabos e terminadores apropriados

### Topologia de Teste

```
┌────────────────────────────────────────────────────────────────┐
│                    Computador (CAN Analyzer)                    │
│                                                                 │
│  ┌──────────────┐                      ┌──────────────┐        │
│  │  Adaptador 1 │  ← Recebe/Envia →   │  Adaptador 2 │        │
│  │   (CAN1)     │                      │   (CAN2)     │        │
│  │  /dev/ttyUSB0│                      │  /dev/ttyUSB1│        │
│  └──────┬───────┘                      └──────┬───────┘        │
│         │                                     │                │
│         │  ┌─────────────────────────────┐   │                │
│         │  │   GATEWAY (Software)        │   │                │
│         │  │  - Forward CAN1→CAN2        │   │                │
│         │  │  - Block IDs                │   │                │
│         │  │  - Modify messages          │   │                │
│         │  └─────────────────────────────┘   │                │
│         │                                     │                │
└─────────┼─────────────────────────────────────┼────────────────┘
          │                                     │
          │ CAN-H/CAN-L                         │ CAN-H/CAN-L
          │                                     │
    ┌─────┴──────────┐                    ┌────┴─────┐
    │   CAN Bus A    │                    │ CAN Bus B│
    │   (Rede 1)     │  ← ISOLADAS! →     │ (Rede 2) │
    │   500 kbit/s   │                    │ 500 kbit/s│
    └────────┬───────┘                    └──────────┘
             │                                   │
             │                                   │
      ┌──────┴────────┐                         │
      │  Módulo CAN   │                    (vazio ou
      │  Emissor      │                     outro módulo)
      │  (Arduino/    │
      │   ECU/etc)    │
      └───────────────┘
      
      Envia mensagens:
      - 0x100: [01 02 03 04 05 06 07 08]
      - 0x200: [AA BB CC DD EE FF 00 11]
      - 0x300: [12 34 56 78 9A BC DE F0]
      - Período: 100ms cada
```

**Conexões físicas:**
- CAN-H (Adaptador 1) ↔ CAN-H (Módulo) ↔ Terminador 120Ω
- CAN-L (Adaptador 1) ↔ CAN-L (Módulo) ↔ Terminador 120Ω
- CAN-H (Adaptador 2) ↔ Terminador 120Ω
- CAN-L (Adaptador 2) ↔ Terminador 120Ω

**CRÍTICO:** Barramentos A e B devem estar **completamente isolados** (sem conexão física entre eles)!

### Passo a Passo

#### 1. Configuração Física

**Rede A (CAN Bus 1):**
- Conecte Adaptador 1 ao barramento A
- Conecte Módulo emissor ao barramento A
- Use terminadores de 120Ω nas extremidades
- Baudrate: 500k (ou o que seu módulo usa)

**Rede B (CAN Bus 2):**
- Conecte Adaptador 2 ao barramento B
- Deixe inicialmente sem outros dispositivos
- Use terminadores de 120Ω
- Baudrate: 500k (mesmo do barramento A)

**IMPORTANTE:** As duas redes devem estar **fisicamente isoladas** (não conectadas entre si)!

#### 2. Configuração no Software

```
Settings (Ctrl+,) → Multi-CAN Configuration:

CAN1:
- Name: CAN1
- Device: /dev/ttyUSB0 (ou /dev/cu.usbserial-xxx no macOS)
- Baudrate: 500000
- Listen Only: NO (para poder transmitir)
- COM Baudrate: 115200

CAN2:
- Name: CAN2
- Device: /dev/ttyUSB1 (ou /dev/cu.usbserial-yyy no macOS)
- Baudrate: 500000
- Listen Only: NO
- COM Baudrate: 115200
```

#### 3. Testes Práticos

### Teste 1: Verificar Isolamento Inicial
**Objetivo**: Confirmar que as redes estão isoladas

```
1. Conecte (Connect)
2. Ative Split-Screen (Ctrl+D)
   - Esquerda: CAN1
   - Direita: CAN2
3. Observe mensagens do módulo emissor aparecendo APENAS em CAN1
4. CAN2 deve estar vazio

✅ Resultado: Isolamento confirmado
```

### Teste 2: Gateway Básico (Passthrough)
**Objetivo**: Encaminhar mensagens do módulo para CAN2

```
1. Abra Gateway (Ctrl+W)
2. Configure:
   - Enable Gateway: ✓
   - Transmit from CAN1 to CAN2: ✓
   - Transmit from CAN2 to CAN1: ✗
3. Clique OK

Observe no Split-Screen:
- CAN1 (esquerda): Mensagens originais do módulo
- CAN2 (direita): Mesmas mensagens sendo encaminhadas

✅ Resultado: Gateway funcionando como ponte
Estatísticas: Forwarded > 0
```

### Teste 3: Bloqueio Seletivo
**Objetivo**: Bloquear IDs específicos

```
Cenário: Seu módulo envia 0x100, 0x200, 0x300

1. No Gateway, adicione bloqueio:
   - Channel: CAN1
   - ID: 0x200
   - Lock

2. Observe:
   - CAN1: Vê 0x100, 0x200, 0x300 (todas)
   - CAN2: Vê apenas 0x100 e 0x300 (0x200 bloqueado!)

✅ Resultado: Bloqueio seletivo funciona
Estatísticas: Forwarded = 2, Blocked = 1 (por ciclo)
```

### Teste 4: Modificação de Dados
**Objetivo**: Alterar bytes específicos

```
Cenário: Módulo envia 0x100 com data [01 02 03 04 05 06 07 08]

1. No Gateway, adicione modificação:
   - Channel: CAN1
   - ID: 0x100
   - Add Modify Rule
   
2. No ModifyRuleDialog:
   - Byte 0: ✓ Modify → 0xFF
   - Byte 3: ✓ Modify → Toggle bit 7 (0x04 → 0x84)
   - OK

3. Observe:
   - CAN1: [01 02 03 04 05 06 07 08] (original)
   - CAN2: [FF 02 03 84 05 06 07 08] (modificado!)

✅ Resultado: Modificação bit-a-bit funciona
Estatísticas: Modified = 1, Forwarded = 1
```

### Teste 5: Bloqueio Dinâmico
**Objetivo**: Testar cycling de IDs

```
Cenário: Módulo envia 0x100, 0x101, 0x102, 0x103 continuamente

1. No Gateway, configure dynamic block:
   - Channel: CAN1
   - ID From: 0x100
   - ID To: 0x103
   - Period: 1000 (1 segundo)
   - Start

2. Observe no Split-Screen:
   - A cada 1 segundo, um ID diferente é bloqueado
   - Padrão rotativo: 0x100 bloqueado → 0x101 bloqueado → 0x102 → 0x103 → repete

✅ Resultado: Cycling automático funciona
Use para simular falhas intermitentes!
```

### Teste 6: Gateway Bidirecional com Módulo
**Objetivo**: Comunicação nos dois sentidos

```
Setup:
- Módulo enviando em CAN1
- Gateway: CAN1↔CAN2 (ambas direções)

1. Mensagens do módulo aparecem em CAN2
2. Use Transmit para enviar em CAN2
3. Essas mensagens aparecem em CAN1
4. Módulo pode "ver" mensagens enviadas pelo computador

✅ Resultado: Ponte bidirecional completa
Útil para: Simular ECUs, testar protocolos, debugging
```

### Teste 7: Salvar/Carregar Perfis
**Objetivo**: Criar perfis reutilizáveis

```
1. Configure Gateway complexo (várias regras)
2. Salve: "profile_test_ecu_1.gwcfg"
3. Feche aplicação
4. Reabra aplicação
5. Carregue: "profile_test_ecu_1.gwcfg"
6. Todas as regras restauradas!

✅ Resultado: Perfis persistentes
Benefício: Trocar rapidamente entre cenários de teste
```

---

## 🎯 Casos de Uso Reais com 3 Controladores

### Caso 1: Teste de ECU Isolada
**Cenário**: Testar ECU sem afetar rede principal

```
Topologia:
- CAN1: Rede principal do veículo (produção)
- CAN2: Rede de teste (isolada)
- Módulo: ECU sendo testada

Configuração Gateway:
- CAN1→CAN2: ON (mensagens da rede vão para ECU)
- CAN2→CAN1: OFF (respostas da ECU NÃO vão para rede)
- Bloqueio: IDs críticos que não devem chegar na ECU

Benefício: Teste ECU com dados reais, sem risco!
```

### Caso 2: Simulação de Gateway Automotivo
**Cenário**: Simular gateway entre redes do veículo

```
Topologia:
- CAN1: Rede do motor (Engine CAN)
- CAN2: Rede da carroceria (Body CAN)
- Módulo: Simulador de sensores

Configuração Gateway:
- CAN1↔CAN2: Bidirecional
- Bloqueio: Mensagens que não devem cruzar redes
- Modificação: Tradução de IDs entre redes

Exemplo real:
- Velocidade do motor (0x100 em CAN1) → 
  Modificado para 0x300 em CAN2 (formato diferente)
```

### Caso 3: Análise de Protocolo
**Cenário**: Entender comunicação entre ECUs

```
Topologia:
- CAN1: ECU A (módulo emissor)
- CAN2: ECU B (módulo receptor - futuro)
- Computador: Gateway no meio

Configuração Gateway:
- CAN1→CAN2: ON
- Bloqueio dinâmico: Testar quais mensagens são essenciais
- Observar: Quais mensagens causam erro quando bloqueadas

Método:
1. Deixe tudo passar (baseline)
2. Bloqueie IDs um por um
3. Observe comportamento do sistema
4. Documente dependências
```

### Caso 4: Desenvolvimento de Filtros
**Cenário**: Criar filtros customizados

```
Objetivo: Permitir apenas mensagens específicas

Configuração:
- CAN1→CAN2: ON
- Bloqueio: TODOS os IDs exceto whitelist
- Whitelist: 0x100, 0x200, 0x300

Implementação:
1. Adicione bloqueio dinâmico 0x000-0x7FF
2. Remova bloqueios dos IDs permitidos
3. Resultado: Firewall CAN!
```

---

## 💡 Dicas para Teste com 3 Controladores

### Dica 1: Use Split-Screen
- Sempre ative Split-Screen (Ctrl+D)
- Visualize CAN1 e CAN2 simultaneamente
- Veja em tempo real o efeito do Gateway

### Dica 2: Monitore Estatísticas
- Mantenha Gateway dialog aberto
- Observe contadores em tempo real
- Use para validar comportamento

### Dica 3: Salve Perfis
- Crie perfis para cada cenário
- Nomeie descritivamente: `gateway_block_0x250.gwcfg`
- Troque rapidamente entre testes

### Dica 4: Log de Ambos os Canais
- Salve logs separados de CAN1 e CAN2
- Compare offline
- Valide que modificações foram aplicadas

### Dica 5: Teste Incremental
1. Primeiro: Apenas encaminhamento (sem regras)
2. Depois: Adicione 1 bloqueio
3. Depois: Adicione modificação
4. Valide cada passo antes de adicionar complexidade

---

## 🔧 Como Usar em Modo Simulação

Se você não tem hardware CAN, pode testar com simulação:

1. **Configure 2 barramentos virtuais:**
   ```
   Settings → Multi-CAN Configuration
   - CAN1: can0 (ou qualquer nome), Simulation Mode: ON
   - CAN2: can1, Simulation Mode: ON
   ```

2. **Conecte:**
   - Clique Connect
   - Ambos os barramentos entram em modo simulação

3. **Configure Gateway:**
   - Tools → Gateway (Ctrl+W)
   - Enable Gateway
   - Configure regras

4. **Teste com Transmit:**
   - Use a aba Transmit para enviar mensagens
   - Selecione o canal de origem (CAN1 ou CAN2)
   - Observe o comportamento do Gateway

5. **Use Split-Screen:**
   - View → Split-Screen Mode (Ctrl+D)
   - Selecione CAN1 à esquerda, CAN2 à direita
   - Veja o Gateway em ação visualmente!

---

## 📊 Métricas de Performance

**Latência esperada:**
- Encaminhamento: < 1ms (processamento Python)
- Bloqueio: < 0.1ms (verificação de regras)
- Modificação: < 0.5ms (cópia e alteração de dados)

**Capacidade:**
- Suporta centenas de regras de bloqueio
- Thread dedicada para dynamic blocking
- Estatísticas thread-safe

---

## 🐛 Troubleshooting

### Gateway não está encaminhando mensagens
**Checklist:**
- [ ] Gateway está habilitado? (checkbox "Enable Gateway")
- [ ] Direção de transmissão configurada? (CAN1→CAN2 ou CAN2→CAN1)
- [ ] Ambos os barramentos conectados?
- [ ] Mensagem não está sendo bloqueada por regra?
- [ ] Adaptadores configurados com baudrates corretos?
- [ ] Listen Only está DESABILITADO em ambos os adaptadores?

### Estatísticas não atualizam
**Solução:**
- Feche e reabra o dialog Gateway
- Verifique logs no terminal
- Confirme que mensagens estão chegando em CAN1

### Bloqueio dinâmico não funciona
**Checklist:**
- [ ] Dynamic block está "enabled"?
- [ ] Período configurado corretamente?
- [ ] Gateway está habilitado?

### Problemas com 3 Controladores

#### Problema: Mensagens aparecem em ambos os barramentos mesmo sem Gateway
**Causa**: Barramentos estão conectados fisicamente
**Solução**: 
- Verifique conexões físicas
- Barramentos A e B devem estar ISOLADOS
- Use multímetro para confirmar isolamento

#### Problema: Módulo não envia mensagens
**Checklist:**
- [ ] Módulo está alimentado?
- [ ] Baudrate do módulo = baudrate do adaptador?
- [ ] Terminadores de 120Ω instalados?
- [ ] Cabos CAN-H e CAN-L corretos?

#### Problema: Adaptador não detectado
**Solução:**
```bash
# macOS
ls /dev/cu.usbserial*
ls /dev/cu.usbmodem*

# Linux
ls /dev/ttyUSB*
ls /dev/ttyACM*

# Verificar permissões (Linux)
sudo chmod 666 /dev/ttyUSB0
sudo chmod 666 /dev/ttyUSB1
```

#### Problema: Gateway encaminha mas modificação não funciona
**Checklist:**
- [ ] Regra de modificação está "enabled"?
- [ ] ID e canal corretos?
- [ ] Pelo menos um byte está marcado para modificar?
- [ ] Verifique estatísticas: "Modified" deve incrementar

#### Problema: CAN2 recebe mensagens mas não consegue enviar
**Causa**: Listen Only pode estar habilitado
**Solução:**
- Settings → Multi-CAN Configuration
- CAN2 → Listen Only: ✗ (desmarcar)
- Reconnect

---

## 📝 Próximos Passos Sugeridos

### Prioridade Alta:
1. **Completar UI de Modificação de Mensagens**
   - Adicionar controles no GatewayDialog
   - Testar modificação de ID e dados

2. **Salvar/Carregar Configuração**
   - Permitir salvar setup do Gateway
   - Facilitar testes repetitivos

### Prioridade Média:
3. **Logs Detalhados**
   - Registrar ações do Gateway
   - Facilitar debugging

4. **Indicadores Visuais**
   - Mostrar status do Gateway na status bar
   - Indicador de mensagens bloqueadas/modificadas

### Prioridade Baixa:
5. **Filtros Avançados**
   - Filtros por DLC, dados, etc.

6. **Performance Monitoring**
   - Medir latência real
   - Gráficos de throughput

---

## 🎯 Conclusão

**O que funciona AGORA (100% Implementado):**
- ✅ Encaminhamento bidirecional (CAN1↔CAN2)
- ✅ Bloqueio estático de IDs
- ✅ Bloqueio dinâmico com cycling
- ✅ Modificação de mensagens com máscaras de bits
- ✅ Interface interativa para modificação (bit-level)
- ✅ Estatísticas em tempo real
- ✅ Salvar/carregar configuração do Gateway
- ✅ Validação de tipos de arquivo
- ✅ Split-Screen para visualização lado a lado

**Funcionalidades Opcionais (Futuro):**
- ⚠️ Logs detalhados de ações do Gateway
- ⚠️ Gráficos de performance
- ⚠️ Filtros avançados (DLC, conteúdo)

**Status Final:**
O Gateway está **COMPLETO E PRONTO PARA USO PROFISSIONAL** com todas as funcionalidades principais implementadas:
- Encaminhamento ✅
- Bloqueio ✅
- Modificação ✅
- Persistência ✅
- Validação ✅

**Para começar a testar:**
1. Configure 2 barramentos CAN
2. Abra Gateway (Ctrl+W)
3. Configure regras
4. Salve a configuração para reutilizar
5. Use Split-Screen (Ctrl+D) para visualizar!

**Teste de modificação de bits:**
1. Adicione regra de modificação
2. Selecione bytes específicos
3. Toggle bits individuais
4. Veja preview em tempo real
5. Aplique e observe mensagens modificadas!
