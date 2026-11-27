# Validação Linux — gs_usb / SocketCAN / CAN FD

Handoff para validar o branch `feature/gs-usb-can-fd` (PR #12) em uma máquina
Linux real com o adaptador CAN FD de dois canais.

**Não é um teste de `vcan`.** O objetivo é validar o caminho real:

```
adaptador gs_usb → driver gs_usb do kernel → can0/can1 → python-can socketcan(fd=True) → app
```

---

## 1. Branch e PR

- Repositório: <https://github.com/phnahes/can-bus-analyzer>
- Branch: `feature/gs-usb-can-fd`
- PR (draft): <https://github.com/phnahes/can-bus-analyzer/pull/12>
- Commit de referência: `4c5c116`
- Documentação de hardware: `docs/reports/2026-11-26-gs_usb-can-fd.md`

Clone ou atualize:

```bash
git clone --branch feature/gs-usb-can-fd https://github.com/phnahes/can-bus-analyzer.git
cd can-bus-analyzer
git log --oneline -1
```

---

## 2. Hardware e fiação

- Adaptador: can-module USBCANFD DUAL (CANable 2.5 / gs_usb), `1d50:606f`
- Dois canais ligados entre si em loopback:
  - CAN-H do canal 0 ↔ CAN-H do canal 1
  - CAN-L do canal 0 ↔ CAN-L do canal 1
  - GND do canal 0 ↔ GND do canal 1 (lado CAN; recomendado em adaptador isolado)
  - Terminação: ~60 Ω total entre CAN-H e CAN-L (120 Ω em cada ponta, se possível)
- **Os dois canais devem estar em modo Normal** (Listen Only desligado) para o
  loopback. Listen Only não dá ACK e o transmissor entra em bus-off.

Não comece pelo data bitrate de 2 Mbit/s. No firmware CANable 2.5 FW 38.3.4 ele
produziu error frames e reiniciou o adaptador; 1/4/5/8 Mbit/s foram validados no
macOS.

---

## 3. Pré-requisitos

- Linux com suporte a CAN FD (kernel moderno; ideal 5.13+).
- Driver `gs_usb` disponível:

```bash
uname -a
lsusb -d 1d50:606f
sudo modprobe gs_usb
lsmod | grep -E 'gs_usb|can'
dmesg | grep -iE 'gs_usb|can[0-9]' | tail -30
```

Se `gs_usb` não existir, instale os módulos extras da sua distribuição
(ex.: `linux-modules-extra-$(uname -r)` no Ubuntu).

- `can-utils` e `ip`:

```bash
sudo apt update && sudo apt install -y can-utils iproute2
ip -V
```

- Python 3.9–3.11, Qt e dependências:

```bash
python3 -m venv .venv
.venv/bin/pip install --upgrade pip
.venv/bin/pip install -r requirements-dev.txt
```

Em máquina sem display, instale as libs de Qt usadas no CI:

```bash
sudo apt install -y libegl1 libxkbcommon0 libgl1
```

---

## 4. Testes automatizados (sem hardware)

```bash
QT_QPA_PLATFORM=offscreen .venv/bin/python -m pytest
```

Esperado: **166 passed** (ou o total atual do branch).

Isso cobre Qt offscreen, parsing do `ip`, comandos de bring-up, candle (mock),
FD/BRS, logs, playback e diff. Não substitui o hardware.

---

## 5. Interfaces no Linux

Conecte o adaptador e confirme:

```bash
ip -d -j link show type can
ip -d link show can0
ip -d link show can1
```

Configure os dois canais em FD (exemplo 1 Mbit/s nominal / 5 Mbit/s data):

```bash
sudo ip link set dev can0 down
sudo ip link set dev can0 up type can bitrate 1000000 dbitrate 5000000 fd on

sudo ip link set dev can1 down
sudo ip link set dev can1 up type can bitrate 1000000 dbitrate 5000000 fd on

ip -d -j link show type can
```

Confira no JSON: `bitrate: 1000000`, `data_bittiming.bitrate: 5000000` e
`ctrlmode` com `fd`.

Teste rápido com can-utils:

```bash
# terminal 1
candump -x can1

# terminal 2 — frame FD de 64 bytes com BRS
DATA=$(python3 -c "print('AA'*64)")
cansend can0 123##1$DATA
```

Se o `cansend`/sintaxe FD da sua versão do can-utils for diferente, use o
script da seção 6; ele exercita a mesma pilha do app.

---

## 6. Loopback FD pela pilha do app

Salve como `linux_loopback.py` na raiz do repositório e rode com o venv:

```python
import struct
import time

from src.can_bus_manager import CANBusConfig, CANBusManager
from src.models import CANMessage

N = 20000
PAYLOAD = 64
TX, RX = "can0", "can1"  # ajuste se os nomes forem outros

received = []


def on_message(bus_name, msg):
    received.append((bus_name, msg))


def main():
    mgr = CANBusManager(message_callback=on_message)
    for channel, name in ((TX, "CAN1"), (RX, "CAN2")):
        mgr.add_bus(CANBusConfig(
            name=name,
            channel=channel,
            baudrate=1_000_000,
            interface="socketcan",
            listen_only=False,
            receive_own_messages=False,
            fd=True,
            dbitrate=5_000_000,
        ))

    results = mgr.connect_all(simulation=False)
    print("connect:", results)
    if not all(results.values()):
        for name, err in mgr.connect_errors.items():
            print(f"  {name}: {err}")
        return 1

    time.sleep(0.3)
    t0 = time.perf_counter()
    sent = 0
    for i in range(N):
        payload = struct.pack("<I", i) + bytes([i & 0xFF]) * (PAYLOAD - 4)
        msg = CANMessage(timestamp=time.time(), can_id=0x100, dlc=PAYLOAD,
                         data=payload, is_fd=True, bitrate_switch=True)
        if not mgr.send_to("CAN1", msg):
            print("send failed at", i)
            break
        sent += 1
    tx_time = time.perf_counter() - t0

    deadline = time.time() + 3.0
    while time.time() < deadline and len(received) < sent:
        time.sleep(0.02)

    seqs = set()
    bad = 0
    wrong_bus = 0
    for bus_name, msg in received:
        if bus_name != "CAN2":
            wrong_bus += 1
            continue
        if not msg.is_fd or not msg.bitrate_switch or len(msg.data) != PAYLOAD:
            bad += 1
            continue
        seq = struct.unpack("<I", msg.data[:4])[0]
        if seq in seqs:
            bad += 1
        else:
            seqs.add(seq)

    print(f"sent={sent} tx_time={tx_time:.2f}s ({sent / tx_time:.0f} fps)")
    print(f"rx={len(received)} unique={len(seqs)} lost={sent - len(seqs)} "
          f"bad={bad} wrong_bus={wrong_bus}")
    mgr.disconnect_all()
    return 0 if bad == 0 and wrong_bus == 0 and len(seqs) == sent else 1


if __name__ == "__main__":
    raise SystemExit(main())
```

Esperado:

```
connect: {'CAN1': True, 'CAN2': True}
sent=20000 tx_time=...s (... fps)
rx=20000 unique=20000 lost=0 bad=0 wrong_bus=0
```

Repita com data bitrate 8 Mbit/s (se a fiação/adaptação permitir) e, opcionalmente,
com frames clássicos de 8 bytes (`fd=False`).

---

## 7. Teste da interface gráfica

Rode o app no Linux:

```bash
./run.sh
```

1. **Settings (Ctrl+,) → CAN bus**
   - **Scan Devices** deve listar `can0` e `can1`.
   - Selecione `can0`, marque **CAN FD**, escolha **Data bitrate 5 Mbit/s**.
   - O label deve mudar para **Nominal bitrate**.
   - COM Baudrate/RTS HS devem estar cinza; “Bring interface up…” só ativo
     para SocketCAN.
2. **Connect**. Se a interface já estiver up/FD (seção 5), ele conecta direto.
   Se estiver down, o app mostra o comando `ip link ...` ou executa via
   `pkexec` quando a opção estiver marcada.
3. **Monitor/Tracer**: confirme as colunas **FD** e **BRS** com ✓ e o payload
   completo no tooltip da coluna Data.
4. **Transmit panel (Ctrl+Shift+P)**:
   - marque **FD**, preencha 64 bytes, marque **BRS**, envie;
   - `candump -x can1` deve mostrar o frame com `fd`/BRS.
5. **Listen Only**: marque Listen Only no CAN1 e tente transmitir; o app deve
   recusar e avisar, sem dizer que enviou.
6. Salve um log JSON e confirme que ele tem uma mensagem por linha e os campos
   `is_fd`/`bitrate_switch`.

---

## 8. Critérios de aceite

- `pytest` headless: tudo passando.
- `can0`/`can1` em FD, com `dbitrate` configurado.
- 20.000 frames FD de 64 B com BRS, 0 perdidos, 0 corrompidos, 0 bus errors.
- App conecta, mostra FD/BRS e envia FD de 64 B.
- Clássico de 8 B continua funcionando no mesmo barramento FD.
- Listen Only recusa TX e não mente sobre envio.
- Sem bus-off com os dois canais em modo Normal.
- Evidência de `ip -d -j link show type can`, `dmesg`, `candump`, saída do
  script e screenshot/log do app.

---

## 9. Cuidados / problemas conhecidos

- **2 Mbit/s**: não é o primeiro teste. No FW 38.3.4 ele deu bit errors e
  reiniciou o adaptador. Se testar, registre e depois reconecte/replugue.
- **Listen Only não dá ACK**: em loopback os dois canais precisam estar em
  Normal. Listen Only é para escutar um barramento com outros nós.
- **candle no Linux**: não é o caminho deste teste. O driver `gs_usb` do kernel
  precisa estar carregado; o candle via libusb não abre o dispositivo enquanto
  o kernel o “claima”.
- **Não altere código** durante a validação. Se encontrar um bug reproduzível,
  pare, colete a evidência e reporte no PR #12.
- **Não faça merge** do PR: ele está em draft até a validação Linux.

---

## 10. Prompt para o agente no Linux

Copie o texto abaixo para a sessão do agente na máquina Linux:

```text
You are continuing the Linux validation of the CAN Analyzer gs_usb/CAN FD
feature.

Repository: https://github.com/phnahes/can-bus-analyzer
Branch: feature/gs-usb-can-fd
PR: #12 (draft; do not merge)
Handoff: docs/TESTING_LINUX.md

Steps:
1. Clone/update the branch and read docs/TESTING_LINUX.md.
2. Run the headless test suite: QT_QPA_PLATFORM=offscreen .venv/bin/python -m pytest.
3. Validate real hardware with SocketCAN: check gs_usb/can0/can1, configure FD
   links, and run the loopback stress script from the handoff (20k FD frames,
   64 bytes, BRS, 1M/5M and optionally 1M/8M).
4. Validate the GUI: Scan Devices, FD/BRS columns, FD TX, Listen Only refusal,
   and one-line JSON log.
5. Collect evidence: uname, lsusb, dmesg, ip -d -j link show type can, pytest
   summary, stress output, candump snippet, app logs/screenshots.
6. Report results as a PR comment. Do not change code or merge the PR without
   being asked. If something fails, report the exact command/output and stop.

Important: both channels must be Normal (Listen Only off) for loopback. Do not
start with a 2 Mbit/s data phase; it is a known firmware issue on this adapter.
```
