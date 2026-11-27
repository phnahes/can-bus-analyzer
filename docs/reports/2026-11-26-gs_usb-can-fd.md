# Relatório — validação de CAN FD com adaptador gs_usb

**Data:** 2026-11-26  
**Adaptador:** can-module USBCANFD DUAL (STM32G473)  
**Objetivo:** validar o suporte gs_usb/candleLight e CAN FD no CAN Analyzer no macOS,
incluindo loopback de 64 bytes com BRS, throughput e estabilidade.

---

## 1. Resumo executivo

O suporte a gs_usb no macOS funciona sem driver de kernel, usando o backend
`candle` (`python-can-candle`). CAN FD de 64 bytes com BRS foi validado em
loopback nos data bitrates de **1, 4, 5 e 8 Mbit/s**, com **20.000 frames por
configuração e zero perda/corrupção**.

A pilha do aplicativo (dois `CANBusInstance` no mesmo adaptador, UI real,
monitor e tracer) também passou no estresse, sem drops.

O único problema relevante foi o **data bitrate de 2 Mbit/s**: gerou error
frames e, numa segunda tentativa já com os GNDs ligados, **reiniciou o
adaptador**. O firmware voltou sozinho, com o mesmo serial, e as demais taxas
permaneceram estáveis. A opção 2 Mbit/s foi retirada dos padrões da UI.

---

## 2. Ambiente e hardware

| Item | Valor |
|---|---|
| Host | macOS 26.6.2, arm64 |
| Python | 3.9 (venv do projeto) |
| python-can | 4.6.1 |
| python-can-candle | 1.2.4 |
| candle-api | 0.0.12 |
| Adaptador | CANable 2.5 Candlelight |
| Fabricante USB | ElmueSoft (netcult.ch/elmue) |
| VID:PID | `1d50:606f` |
| Serial | `2088339B413250013` |
| Firmware | 38.3.4 |
| Hardware | 2.0 |
| Canais | 2 |
| USB | Full-speed (12 Mbit/s) |

O firmware é gs_usb/candleLight; **não** aparece como `/dev/cu.*`. No macOS os
canais são enumerados como `2088339B413250013:0` e `2088339B413250013:1`.

**Fiação do loopback:** CAN-H do canal 0 ↔ CAN-H do canal 1, CAN-L ↔ CAN-L,
GND ↔ GND (ligado depois dos primeiros testes), com terminação.

---

## 3. Implementação validada

- Descoberta de adaptadores/channels via `candle_api.list_device()` e
  `python-can` (`Scan Devices`).
- Backend `candle` no `CANBusManager`, com `bitrate`, `listen_only`, `fd` e
  `data_bitrate`.
- **Sessão compartilhada por adaptador**: o `python-can-candle` abre o USB
  inteiro, então os dois canais são multiplexados numa única `CandleBus`
  (`src/candle_session.py`), com dispatch por canal e filtro de echo de TX.
- TX FD no painel: checkbox **FD**, campo de payload hex de até 64 bytes,
  **BRS**, DLC sincronizado e padding para comprimentos válidos de CAN FD.
- Flags `is_fd`/`bitrate_switch` no `CANMessage`, preservadas em logs JSON/CSV,
  playback, gateway e save/load da lista de transmissão.
- Colunas **FD** e **BRS** no Monitor e no Tracer, com o payload completo no
  tooltip da coluna Data.
- Settings mostra o driver detectado e, em CAN FD, renomeia o campo clássico
  para **Nominal bitrate** (arbitragem), separando-o do **Data bitrate**.
- 166 testes automatizados passando.

---

## 4. Testes de loopback unitário (1 frame)

Antes do estresse, um frame FD de 64 bytes foi enviado no canal 0 e verificado
no canal 1. O echo de TX (`is_rx=False`) foi descartado.

| Nominal | Data | BRS | Recebido no canal 1 | Observação |
|---:|---:|:---:|:---:|---|
| 500k | 500k | não | 1/1 | FD sem BRS OK |
| 500k | 1M | sim | 1/1 | OK |
| 500k | **2M** | sim | **0/1** | 3 error frames |
| 500k | 5M | sim | 1/1 | OK |
| 500k | 8M | sim | 1/1 | OK |
| 1M | 1M | sim | 1/1 | OK |
| 1M | **2M** | sim | **0/1** | 3 error frames |
| 1M | 5M | sim | 1/1 | OK |
| 1M | 8M | sim | 1/1 | OK |

Clássico (8 bytes, 500 kbit/s) também passou: o canal 1 recebeu o frame
íntegro, confirmando fiação, terminação e ACK.

---

## 5. Estresse de hardware (20.000 frames FD, 64 B, BRS)

Um único `CandleBus` com `channel=[0,1]`; envio sequencial pelo canal 0 e
verificação de sequência/payload no canal 1.

| Nominal | Data | Enviados | Recebidos | Perdidos | Corrompidos | Erros de barramento | TX fps | Payload |
|---:|---:|---:|---:|---:|---:|---:|---:|---:|
| 1M | 1M | 20.000 | 20.000 | 0 | 0 | 0 | 1.610 | 0,82 Mbit/s |
| 1M | 4M | 20.000 | 20.000 | 0 | 0 | 0 | 2.930 | 1,50 Mbit/s |
| 1M | 5M | 20.000 | 20.000 | 0 | 0 | 0 | 2.949 | 1,51 Mbit/s |
| 1M | 8M | 20.000 | 20.000 | 0 | 0 | 0 | 2.865 | 1,47 Mbit/s |

Após o reboot causado pelo teste de 2 Mbit/s, foram repetidos testes de
sanidade: 1M (20.000 frames), 4M (20.000), 5M (1.000) e 8M (1.000), todos sem
perda.

**Clássico:** 2.000 frames de 8 bytes a 1 Mbit/s, 0 perda, ~5.560 fps
(0,36 Mbit/s de payload).

### Limite de throughput

As taxas de 5 e 8 Mbit/s ficaram no mesmo patamar (~2.900 fps). O gargalo não é
o barramento nem o data phase: é o envio síncrono via USB do
`python-can-candle`, que custa ~0,34 ms por frame. Para passar disso seria
preciso pipelining/batching no backend ou usar SocketCAN no Linux.

---

## 6. Estresse pela pilha do aplicativo

Dois `CANBusInstance` no mesmo adaptador: CAN1 → canal 0, CAN2 → canal 1,
ambos FD, 1M/8M.

| Teste | Resultado |
|---|---|
| Envio de 20.000 frames FD pelo `CANBusManager` | 20.000/20.000 recebidos, 0 perdidos, 0 corrompidos, 0 no barramento errado |
| Throughput pelo manager | 2.965 fps (6,75 s para 20.000) |
| Echo de TX exibido como RX | 0 |
| Ciclos connect/disconnect (2 canais) | 5/5 ciclos OK |
| Payload FD de 9 bytes | Padding para 12 bytes, recebido `AA...AA 00 00 00` |
| Clássico de 8 bytes no mesmo barramento FD | Recebido íntegro, sem BRS |

---

## 7. Estresse da UI real

Janela real do aplicativo em modo offscreen, conectada ao hardware, com o loop
de eventos rodando.

| Cenário | Enviados | UI contou | Drops | Filas | Linhas |
|---|---:|---:|---:|---:|---:|
| Monitor, 20.000 FD 1M/8M | 20.000 | 20.000 | 0 | 0 | 1 (agrupado por ID) |
| Tracer + gravação, 5.000 FD 1M/8M | 5.000 | 5.000 gravados | 0 | 0 | 5.000 |

O envio no teste de monitor levou 8,19 s (~2.440 fps ponta a ponta, incluindo
UI). O tracer precisou de gravação ativa — comportamento existente do app.

**Bench sintético do pipeline (10 s a 3.000 fps):**

| Modo | Frames | Drops | p50 | p95 | p99 | Máx |
|---|---:|---:|---:|---:|---:|---:|
| Monitor | 30.000 | 0 | 6,5 ms | 9,4 ms | 11,6 ms | 20,1 ms |
| Tracer (ring 5.000) | 30.000 | 0 | 4,8 ms | 7,3 ms | 12,4 ms | 19,5 ms |

---

## 8. Problemas encontrados

### 8.1 Data bitrate de 2 Mbit/s (crítico)

- Em 500k/2M e 1M/2M o canal 1 recebeu **error frames** em vez do frame FD.
- Numa execução de 1.000 frames a 1M/2M, **já com os GNDs ligados**, o
  adaptador **reiniciou** e reenumerou com o mesmo serial.
- O timing calculado para 2 Mbit/s com f_clock de 160 MHz é `brp=5`,
  `tseg1=27`, `tseg2=2` (sample point 87,5%). É o único data rate testado que
  falhou de forma consistente, então a hipótese principal é firmware/timing, não
  fiação.
- 1, 4, 5 e 8 Mbit/s funcionaram antes e depois do reboot.

**Mitigação aplicada:** 2 Mbit/s saiu das opções padrão de data bitrate
(agora 1/4/5/8 Mbit/s); configs antigos que já tenham 2 Mbit/s continuam
abrindo, com tooltip de aviso. README e CHANGELOG documentam o caso.

### 8.2 Abertura exclusiva do dispositivo

`python-can-candle` abre o USB inteiro: duas `Bus` separadas para os canais 0
e 1 falham com `Cannot open device`. Resolvido com a sessão compartilhada e
proxies por canal.

### 8.3 Echo de TX

O adaptador entrega o frame transmitido de volta como `is_rx=False`. Sem
filtro, ele apareceria como RX e seria reencaminhado pelo gateway. Filtrado no
reader da sessão.

### 8.4 Reabertura após bus-off

Depois dos erros de 2 Mbit/s, reabrir o dispositivo imediatamente falhou
algumas vezes; após alguns segundos (ou power cycle) voltou ao normal. Não
ocorre no fluxo normal de connect/disconnect — 5 ciclos seguidos passaram.

### 8.5 Observação: Tracer exige gravação

No modo Tracer o app só exibe frames com a gravação ativa. Não é regressão
deste trabalho, mas vale revisar a UX: o nome "Tracer" sugere visualização
contínua, não apenas reprodução do que foi gravado.

---

## 9. Conclusões

1. gs_usb no macOS está funcional: descoberta, conexão, clássico e CAN FD,
   com dois canais simultâneos.
2. CAN FD de 64 bytes com BRS está validado em **1, 4, 5 e 8 Mbit/s**, com zero
   perda em 20.000 frames por taxa.
3. O data bitrate de **2 Mbit/s é inseguro nesse firmware (38.3.4)**: error
   frames e reboot. Evitar até que a Elmue/can-module publique uma correção.
4. O limite de ~2.900 fps é do envio síncrono USB, não do CAN FD. Para
   throughput maior, o caminho é SocketCAN no Linux ou batching no backend.
5. A UI aguenta a taxa de linha do adaptador sem drops (monitor e tracer).

## 10. Próximos passos sugeridos

- Reportar o caso 2 Mbit/s + reboot ao fabricante e na issue #9, com firmware,
  VID/PID, taxa e comportamento.
- Verificar atualização de firmware da Elmue (CANable 2.5).
- Repetir a validação no Linux via SocketCAN (`can0`, `dbitrate`, `fd on`) para
  comparar o caminho do kernel com o backend USB direto.
- Testar em barramento real com ECU/tráfego, não só loopback.
- Empacotar `candle`/`candle_api` no .app (py2app) e validar assinatura/
  notarização.

---

## 11. Reprodução

```bash
# Loopback FD 64 B, BRS, 1M nominal / 5M data, 20k frames
python tools/general/stress_candle.py --frames 20000 --data-bitrate 5000000

# 8M data
python tools/general/stress_candle.py --frames 20000 --data-bitrate 8000000

# Clássico 1M, 8 bytes
python tools/general/stress_candle.py --classic --nominal-bitrate 1000000

# Testes automatizados
QT_QPA_PLATFORM=offscreen pytest
```

O script exige os dois canais do mesmo adaptador ligados entre si e terminados.
