# Etapa 01 — Plataforma, identificação da CPU e OC Mailbox

> Fase: levantamento de requisitos e estudos. Registro derivado da [pesquisa consolidada](../xeon-e5-2680v4-h9s-pesquisa-bclk-icc.md), de 26/11/2026. Não representa novos testes em hardware.

Objetivo: estabelecer o limite real de frequência antes de investigar o gerador de clock.

## 2. Plataforma e baseline

| Componente | Informação |
|---|---|
| Placa | QIYIDA X99-H9S V1.21 (DMI genérico INTEL) |
| BIOS | AMI 5.11, 26/11/2024; DMI anuncia região BIOS de 8 MiB |
| CPU | E5-2680 v4, Broadwell-EP, 14C/28T, CPUID 0x406F1 |
| Frequência base/turbo máximo nominal | 2,4 / 3,3 GHz |
| Turbo all-core observado | aproximadamente 2,9 GHz |
| Host bridge | 8086:6f00 |
| LPC | 8086:8d44, Wellsburg; C612 conforme tabela 1-2 do datasheet |
| SMBus | 8086:8d22, rev. 05, Intel I801 |
| RAM / GPU | 32 GB DDR4 / RTX 5060 |
| Sistema | Ubuntu 26.04.1, kernel 7.0.0-44-generic |
| Armazenamento | NVMe 512 GB ext4; SATA 512 GB NTFS; swap 8 GiB |
| Firmware de gerenciamento | SPS 03.01.03.072, Production, SKU GR (Grantley), 12/02/2019 |
| Microcode | BIOS 0x0b000038, Linux 0x0b000040 |
| Acesso | Remoto; recuperação física indisponível durante os testes anteriores |

### Frequências teóricas

| BCLK (MHz) | All-core 29x (MHz) | Turbo 33x (MHz) | Variação |
|---:|---:|---:|---:|
| 100 | 2900 | 3300 | baseline |
| 101 | 2929 | 3333 | +1% |
| 102 | 2958 | 3366 | +2% |
| 103 | 2987 | 3399 | +3% |
| 105 | 3045 | 3465 | +5% |
| 107 | 3103 | 3531 | +7% |
| 110 | 3190 | 3630 | +10% |
| 125 | 3625 | 4125 | +25% (strap teórico, não validado) |

São projeções aritméticas, não resultados de benchmark. O ganho real depende dos limites térmicos, de potência, memória e estabilidade do conjunto.

## 3. CPU: testes de multiplicador e potência

### 3.1 Frequências solicitadas versus executadas

`intel_cpufreq` em modo passivo, faixa 1,2–3,3 GHz; governor original `schedutil`, posteriormente `performance`. Em carga, `turbostat` mostrou cerca de 2900 MHz e os 28 threads ficaram próximos de 2893 MHz. Turbo habilitado (`no_turbo=0`, max_perf_pct=100).

Uma tentativa de fixar mínimo 2,9 GHz com `cpupower` falhou no CPU1, deixando potencialmente apenas CPU0 com mínimo 2,9 GHz. A restauração foi sugerida, mas não confirmada. Não é método de overclock.

| MSR | Valor lido / interpretação |
|---|---|
| `0xCE` PLATFORM_INFO | `0xa0080c3bf2811800`; bits 28, 29, 30 = 0 |
| `0x194` | `0x0`; bit 20 de lock = 0; bits 19:17 de OC bins = 0 |
| `0x1AD` TURBO_RATIO_LIMIT | `0x1d1d1d1d1e1f2121`; 1–2 cores: 33x; 3:31x; 4:30x; 5–8:29x |
| `0x1AE`, `0x1AF` | `0x1d1d1d1d1d1d1d1d` |
| `0x199` bits 15:8 | ratio solicitado 33x nos threads |
| `0x198` bits 15:8 | ratio efetivo 29x em carga |
| `0x61E` | leitura falhou no Linux |
| `0x620` | `0xc1b`, ring max 27x / min 12x |
| `0x621` | leitura observada 15x |
| `0x300` | `0x8000ff00`, barramento uncore 0xff |

RAPL observado: PL1 120 W / 1 s, PL2 144 W / aproximadamente 7,8 ms; PL4 142 W bloqueado. Limites reportados: PL1 max 120 W, PL2 max 240 W. Temperatura alvo 100 °C, observação cerca de 51 °C. Leituras de 14–15 W em carga quase total foram implausíveis; **não** servem para provar folga de potência. Não desabilitar OVP/OCP ou proteções térmicas como parte da pesquisa.

### 3.2 OC Mailbox — resultado conclusivo para o ratio testado

Transporte MSR `0x150`: interface/comando nos 32 bits superiores, dados nos 32 inferiores; bit 63 de busy/run, status no byte inferior da interface após término. O OcInit contém também transporte MMIO (seção 8).

Teste realizado de capacidades (comando 1, domínio 0): retorno `0x221`, busy=0, completion=0.

- bits 7:0: 33x;
- bit 8: `RatioOcSupported=0`;
- bit 9: `VoltageOverrideSupported=1`;
- bit 10: `VoltageOffsetSupported=0`.

| Domínio | Retorno bruto | Interpretação |
|---|---|---|
| 0 | `0x221` | core, max 33x, sem ratio OC |
| 1 | `0x10500000000` | completion 5, payload zero |
| 2 | `0x2000000021b` | provável ring/cache, max 27x, sem ratio OC |
| 3 | `0x30000000000` | payload zero, sem capacidade demonstrada |
| 4 | `0x40000000000` | payload zero, sem capacidade demonstrada |

Consultas de comandos `0x10`, `0x14`, `0x12` nos domínios 0 e 2 e leitura AVX `0x1A` retornaram dados zero. Não significa que todos os comandos de escrita funcionem.

**Teste de escrita já executado:** comando `0x11` com ratio 30x no domínio 0, retorno `0x500000000`, completion 5. Limites turbo permaneceram inalterados. O código 5 é consistente com rejeição de OC; o nome simbólico exato deve ser confirmado em documentação da geração. Não repetir esta escrita como estratégia principal.

A conclusão é limitada ao mecanismo testado: o processador rejeita a alteração convencional de ratio. Não prova que BCLK seja impossível.

### 3.3 Microcode

Microcode carregado cedo pelo Linux: 0x0b000040, data 19/05/2021, tamanho 35.840 bytes, sig 0x406f1, máscara de plataforma 0xef. Arquivo `/lib/firmware/intel-ucode/06-4f-01.initramfs`. Pacote observado `intel-microcode 3.20260210.1ubuntu2`.

BIOS iniciou com 0x0b000038. Não foi realizado downgrade. Não há evidência de microcode alternativo que desbloqueie E5-2680 v4; métodos de turbo unlock de Haswell-EP v3 não devem ser transplantados automaticamente.

## Procedimento reproduzível de diagnóstico

| Passo | Comando ou fonte | Resultado histórico | Decisão |
|---|---|---|---|
| 1 | `lscpu`, `dmidecode -t 2 -t 4`, `lspci -nn` | Identificação da plataforma | Fixar revisão e IDs |
| 2 | `cpupower frequency-info` | intel_cpufreq passivo | Não confundir governor com OC |
| 3 | `turbostat` durante carga | ~2900 MHz | Baseline all-core |
| 4 | `rdmsr -p 0 0x1ad`, `0x1ae`, `0x1af` | Tabela de ratios | Limite por núcleos ativos |
| 5 | `rdmsr -a -f 15:8 -d 0x199` e `0x198` | 33 solicitado / 29 efetivo | Confirmar diferença |
| 6 | Consulta de capacidade do mailbox | 0x221 | Ratio OC ausente |
| 7 | Pedido histórico de ratio 30x | completion 5 | Não repetir como solução |
| 8 | Consulta de MSR61E | Falha de leitura em runtime | Pré-condição de PEI não resolvida |

### Comandos de leitura para auditoria futura

```bash
lscpu
lspci -nn
cpupower frequency-info
sudo rdmsr -p 0 0xce
sudo rdmsr -p 0 0x194
sudo rdmsr -p 0 0x1ad
sudo rdmsr -p 0 0x1ae
sudo rdmsr -p 0 0x1af
sudo rdmsr -a -f 15:8 -d 0x198
sudo rdmsr -a -f 15:8 -d 0x199
sudo turbostat --quiet --interval 2 --num_iterations 10
```

Executar somente se for necessário reestabelecer o baseline; não constitui pendência imediata. `rdmsr` requer suporte e módulo msr; uma falha não autoriza escrita arbitrária. Consultas de mailbox são transações, não simples leituras de MSR.

## Identificadores e unidades

CPUID identifica família/modelo/stepping do processador; PCI VID:DID identifica fornecedor/dispositivo; BDF identifica a instância no barramento; PID identifica processo Linux e não é um identificador estável de firmware. Nenhum PID de processo foi registrado como parte causal do overclock. Ratio é adimensional; BCLK é frequência; os valores de configuração privados não devem ser tratados como MHz sem decodificação.

**Saída:** bloqueio convencional de ratio demonstrado; gerador de clock permanece hipótese independente. Próximo: [flash e SPS](02-flash-spi-sps.md).
