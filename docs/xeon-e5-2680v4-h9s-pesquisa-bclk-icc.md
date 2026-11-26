# Engenharia reversa do BCLK — Xeon E5-2680 v4 / QIYIDA X99-H9S

**Data de consolidação:** 26/11/2026  
**Estado:** pesquisa experimental; overclock acima de 2,9 GHz all-core ainda não demonstrado.  
**Escopo:** firmware original, ICC/SPS, OC Mailbox, HECI, straps, configuração persistente e plano de ação reproduzível.

## 1. Objetivo e decisão estratégica

Aumentar efetivamente o BCLK do Xeon E5-2680 v4, mantendo o multiplicador turbo all-core de 29x, em vez de apenas solicitar ratios superiores que a CPU não executa. O primeiro marco é **101 MHz**, depois 102–103 MHz e, se validado, 105 MHz ou mais. Não há teto estável comprovado para esta placa.

O proprietário aceita investigar alterações que também afetem outros domínios de clock. Assim, a separação de BCLK e PCIe/DMI não é um requisito absoluto para a pesquisa. Isso não elimina risco de corrupção silenciosa, falhas de armazenamento, perda de conexão remota ou impossibilidade de POST. Esses riscos são diferentes da simples instabilidade da CPU e devem ser medidos separadamente.

**Prioridade:** editar dados persistentes do ICC no SPS original; preservar descriptor, firmware executável e BIOS sempre que possível. A investigação de gerador externo e transporte HECI continua como alternativa. Remover apenas a checagem `RatioOcSupported` não constitui um desbloqueio físico do multiplicador.

### Legenda de evidência

- **Confirmado (teste):** saída efetivamente obtida no computador do proprietário.
- **Confirmado (estático):** campo/instrução identificado no dump, IFR, desassemblagem ou arquivo fornecido.
- **Documentado:** informação da documentação pública; não prova a implementação específica da placa.
- **Hipótese:** interpretação plausível que ainda precisa de validação.
- **Pendente:** não há prova experimental suficiente.

Este arquivo consolida o histórico da investigação, não é uma nova execução de todos os testes. Os três arquivos compactados foram reabertos e seus hashes recalculados nesta consolidação. O dump SPI integral e os volumes persistentes ainda não foram enviados; os dados sobre eles provêm dos logs e da análise anterior. Alguns nomes de funções e registradores privados são rótulos descritivos, não símbolos originais da Intel.

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

## 4. Flash SPI e recuperação

Dois dumps independentes de 16 MiB foram obtidos por flashrom 1.6.0 com hardware sequencing. O JEDEC retornado foi `A1 28 18`, não reconhecido pelo modo software; hipótese de chip Fudan FM25W, identificação física pendente. O modo hardware detectou flash opaca de 16 MiB. O chipset Wellsburg foi marcado como não testado pelo flashrom.

| Arquivo no computador | SHA-256 |
|---|---|
| `~/backup-bios/x99-h9s-original.bin` | `6036511afaaeab53701e0adce3a3a731790302f24ca11614212f95f2901fce5b` |
| `~/backup-bios/x99-h9s-verificacao.bin` | mesmo hash, `cmp` idêntico |

Backups originais foram protegidos com chmod 444. Isso valida consistência de leitura, **não** uma restauração real. Nenhuma imagem modificada foi gravada. Antes de experimentar uma imagem persistente: acesso presencial, gravador SPI externo e tensão/pinagem confirmadas, cópias fora do PC e procedimento de recuperação verificado.

### Mapa do descriptor

| Região | Intervalo absoluto (inclusive) | Tamanho |
|---|---|---|
| Descriptor FREG0 | `0x000000–0x000FFF` | 4 KiB |
| SPS FREG2 | `0x001000–0x7FFFFF` | 8 MiB menos 4 KiB |
| BIOS FREG1 | `0x800000–0xFFFFFF` | 8 MiB |

Permissões observadas R/W nas três regiões. Permissão de acesso não significa que seja apropriado escrever.

`FLMAP1=0x15100306`; FPSBA=0x10 → tabela PCHSTRP em `0x100`. PCHSTRP17 em `0x144` = `0x00000002`. Bits 7=0, 1=1, 0=0. O datasheet associa esses bits ao modo nativo/híbrido, seleção de straps e clock interno/externo; **a polaridade não foi confirmada**. Não modificar straps com base nesse valor isolado.

## 5. Estrutura do SPS 3.1 Grantley

ME Analyzer v1.312.0 r378 identificou SPS 03.01.03.072, Production, Extracted, SKU GR, data 2019-02-12 e tamanho reportado 0x285000. A região bruta foi extraída para `~/backup-bios/sps-region.bin` (offset SPI 0x1000, 2047 blocos de 4096 bytes).

FPT: assinatura `$FPT` no offset relativo 0x10; cabeçalho com comprimento 0x30. Atenção: os offsets FPT são relativos ao início da região SPS, não ao início da assinatura FPT.

| Partição | Offset relativo SPS | Offset SPI absoluto | Tamanho | Foco |
|---|---:|---:|---:|---|
| MFSB | 0x001000 | 0x002000 | 0x10000 | dados/configuração, analisar |
| SCA | 0x011000 | 0x012000 | 0x10000 | dados/configuração, analisar |
| FTPR | 0x021000 | 0x022000 | 0x20000 | código de recuperação/boot |
| MFS | 0x041000 | 0x042000 | 0x40000 | dados/configuração, analisar |
| OPR1 | 0x081000 | 0x082000 | 0x200000 | módulos operacionais |
| ASAP | 0x281000 | 0x282000 | 0x4000 | aparentemente vazio no dump |

Não há partição explicitamente denominada ICC. Isso não prova ausência de parâmetros ICC. O local exato dos dados persistentes, a interpretação de MFSB/SCA e seus mecanismos de integridade continuam pendentes.

`$MMEICCMOD` em offset relativo SPS 0x81410 (SPI 0x82410), descritor de 96 bytes em OPR1+0x410. Campos observados: +0x34=0x200ed000, +0x38=0x840, +0x3C=0x6000, +0x44/+0x48=0x7b98, +0x4C=0x200ef000. Não atribuir semântica definitiva a todos os campos.

## 6. ICC: arquitetura de clock documentada

O datasheet Intel C610/X99 PCH (capítulo 4, especialmente 4.5 e 4.6) descreve configuração de clocks via firmware SPS 3.0/ME9, com parâmetros persistentes na região de dados da flash. A tabela 1-2 associa LPC 8D44 ao C612. C612 suporta clock integrado nativo, híbrido e gerador externo CK420BQ; não está demonstrado qual topologia física foi montada na H9S.

O modulador **MOD3** está associado a CPU BCLK (CLKOUT_DMI), DMI, PCIe, USB3, SATA/sSATA e outros clocks. O mesmo datasheet distingue recursos de overclock HEDT. A existência de MOD3 não garante que seu ajuste adaptativo seja desbloqueado no C612/SPS nem que todos os clocks se alterem na mesma proporção.

```text
SPI / dados SPS -> configuração ICC -> PLL / moduladores / divisores
                                        |-> CPU BCLK (se roteado)
                                        |-> DMI/PCIe/USB/SATA (domínios dependentes)
```

**Hipótese de trabalho:** ajustar a configuração de clock inicial do SPS original, sem depender da rotina de overclock de ratio do CPU. MOD3 é o alvo funcional; ainda não há mapeamento entre MOD3 e os endereços auxiliares privados do ICCMOD.

## 7. IntelSetup / IFR / NVRAM

UEFIExtract e IFRExtractor-RS foram usados para extrair `Platform.bin`, `Setup.bin`, `IccPlatform.bin`, `IccOverClocking.bin`. O formset IntelRCSetup tem GUID `EC87D643-EBA4-4BB5-A1E5-3F3E36B20DA9`; VarStore 1 `IntelSetup` tamanho 0x17EC (6124 bytes). VarStore 2 `AmiSetupSupportedFeatures` tamanho 4, mesmo GUID. VarStore 3 `SystemAccess`, GUID `E770BB69-BCB4-4D04-9E97-23FF9456FEAC`, tamanho 1.

### Campos relevantes (offsets relativos ao payload IntelSetup, não offsets SPI)

| Campo | Offset | Tamanho | Observações |
|---|---:|---:|---|
| OC visibility QID 13FC | 0x163D | 1 | zero nas cópias NVRAM |
| Overclocking Feature QID E3F | 0x163F | 1 | default 0 |
| Extreme Edition QID D8F | 0x13FC | 1 | default 1; distinto do QID 13FC |
| Overclocking Lock QID D90 | 0x13FD | 1 | opções 0/1; efeito real no MSR não provado |
| Filter PLL | 0x163E | 1 | GPIO8, default 0 |
| Adjust PLL | 0x17C1 | 1 | ajuste para combinação de BCLK elevado, default 0 |
| PLL Trim | 0x17C2 | 4 | magnitude 0–15, não MHz |
| PLL Trim Prefix | 0x17C6 | 1 | sinal +/− |
| TJMax offset | 0x17C7 | 1 | não alterar neste projeto |
| CLR minimum ratio | 0x17C8 | 1 | ajuste de cache |
| AVX2 offset | 0x17D7 | 1 | ajuste de ratio AVX |
| SfrTrim | 0x17D8 | 1 | workaround HSX |
| CPU core ratios | 0x16E7 em diante | 24 WORDs | 14º em 0x1701 |
| CPU Flex Ratio Override | 0xA4 | 1 | escondido; não-turbo |
| CPU Core Ratio | 0xA3 | 1 | default 23; não-turbo |
| FIVR faults | 0x16B1 | 1 | default 1: manter proteções OVP/OCP |
| FIVR efficiency | 0x16B2 | 1 | default 1; não alvo atual |
| ICC override clock enables | 0x12EB | 1 | default 0 |
| ICC/OC watchdog | 0x12EC | 1 | default 0 |
| ICC unused clocks | 0x12ED | 1 | default 1 |
| ICC Profile | 0x12EF | 1 | default 0, dependente do OEM |
| ICC Profile editable | 0x12F0 | 1 | flag dinâmica |
| DMI frequency | 0x12F9 | 2 | default 0; unidade desconhecida |
| PCI frequency | 0x12FB | 2 | default 0; unidade desconhecida |
| DMI spread | 0x12FE | 1 | 0,01% por passo conforme IFR |
| PCI spread | 0x12FF | 1 | 0,01% por passo conforme IFR |
| DMI/PEG ratio | 0x1301 | 1 | 5:5, 5:4, 5:3, 5:2 |
| DMI visible / PCI visible | 0x1304 / 0x1305 | 1 cada | flags dinâmicas |
| DMI editable / PCI editable | 0x1307 / 0x1308 | 1 cada | flags dinâmicas |
| ICC Locks after EOP | 0x130F | 1 | default 0; não alterar cegamente |
| ICC editable | 0x1311 | 1 | flag dinâmica |
| SSC override | 0x132B | 1 | 1 override / 2 auto |
| SSC0–SSC7 mode | 0x132C–0x1333 | 1 cada | down/center/disable/no change/auto |
| External SSC CK420 | 0xF5 | 1 | somente spread spectrum externo, não prova chip presente |
| ME FW Image Re-Flash QID D12 | 0x1334 | 1 | 0 auto, 1 disabled, 2 enabled; não é SKU |
| HMRFPO lock / enable | 0x12D0 / 0x12D1 | 1 cada | defaults 1/0 |
| End of POST / Global reset lock | 0x12D2 / 0x12D3 | 1 cada | defaults 1/1 |
| HECI1/2, IDER, KT | 0x12D4–0x12D7 | 1 cada | auto=2 |
| ME State | 0x171C | 1 | valor 1 nos registros observados |

Os menus DMI/PCI aparecem com frequência de exemplo 100,00 MHz, downspread 0,50%, limites `uninitialized`. Mudanças são descritas como aplicadas após salvar e resetar. Os campos são condicionados por flags e callbacks. Não está provado se a frequência é codificada em MHz, centésimos ou outra representação, nem se esses campos são o CPU BCLK. Não gravar `101` ou `10100` neles por dedução.

### NVRAM encontrada no dump

Dois volumes de 256 KiB, FFSv2, arquivo NVAR GUID `CEF5B9A3-476D-497F-9FDC-E98143E0422C`. Estados de arquivo no dump:

| Região | Base do arquivo | Estado | Último registro IntelSetup | Payload absoluto |
|---|---:|---|---|---:|
| 0 | 0x800048 | F0, invertido 0F, bit alto 08: marked for update | 586 | 0x828E38 |
| 1 | 0x840048 | F8, invertido 07, bit alto 04: data valid | 352 | 0x85F4A1 |

Região 0: OC_ENABLE=1, OC_LOCK=1, EXTREME=1, primeiros dez ratios 33, restantes 0. Região 1: OC_ENABLE=0, OC_LOCK=0, EXTREME=1, ratios zero. Ambas: OC_VISIBLE=0; ICC_LOCK, ICC_PROFILE, DMI/PCI_CLOCK, flags ICC editáveis =0; HECI1/2/IDER/KT=2; EXTERNAL_SSC=0. Região 1 provavelmente ativa, mas não verificada por leitura de variável no firmware.

`IntelSetup` não apareceu em efivars runtime; variável pode ser acessível apenas em boot services. Não confundir histórico de registro NVAR com configuração efetiva da CPU. A presença dos menus e valores não prova que a placa implemente overclock.

## 8. Engenharia reversa do código UEFI

### 8.1 PpmInitialize

- Rotina original em torno de 0x2318 copia 24 WORDs de ratios da política.
- Lê `MSR 0x35`, `0x1AD`, `0x1AE`, `0x1AF`, `0x1AC`.
- 0x2410 lê PLATFORM_INFO, 0x241B lê MSR194, 0x243E extrai OC bins.
- 0x2445/0x244C testa bit 28 de PLATFORM_INFO e desvia se zero; 0x2452/0x2454 testa OC bins e desvia se zero. Ambos são zero na CPU testada.
- Caminho de escrita em torno de 0x2770/0x27A3 manipula MSR194 e política de ratios.

Os guards são de software, mas o teste de mailbox rejeitado demonstra uma restrição adicional. CpuMpDxe solicita ratio pelo MSR199 e usa limites de turbo; não foi localizado um mecanismo comprovado de desbloqueio nele.

### 8.2 OcInit original (endereços relativos ao código original)

- Entrada 0x4A84, buffer local 0x1894, tabela de straps 100/125/166/250 em 0x4AAD.
- Busca IntelSetup com tamanho 0x17EC em 0x4B2A; OC_ENABLE=0 causa saída.
- 0x5724 consulta OC Mailbox command 1; extrai ratio max e bits de capacidades.
- Guard de ratio em 0x4B8C/0x4B90 impede avanço se `RatioOcSupported=0`.
- 0x4B96/0x4B9B tenta ler MSR61E. No Linux essa leitura falhou; não sabemos o comportamento no PEI.
- CPUID 306f/406f diferencia rotinas de ajuste de PLL.
- 0x647E usa dados de HECI/PCI e sincroniza strap; não é prova de que configura a frequência física independentemente.

Trecho do diff, com endereço PEI mapeado:

```asm
ffdc4b84: call 0xffdc5724
ffdc4b89: add esp,0x10
ffdc4b8c: cmp BYTE PTR [ebp-0x17],0x0
ffdc4b90: je 0xffdc4ea5
ffdc4b96: mov ecx,0x61e
ffdc4b9b: rdmsr
```

A condição pode ser modificada em software, mas fazê-lo isoladamente pode levar à execução de RDMSR não suportado e impedir POST. **Não é uma imagem pronta para gravação.** É necessário compreender os guards de capacidade e a rotina de falha antes de desenvolver uma alternativa.

### 8.3 Transportes e ajustes privados

OcInit possui transportes de mailbox em 0x5E61 e polling em 0x602D: transporte 2 usa MSR150, transporte 1 usa janela MMIO via helper/PEI protocol, offsets 0x5DA0 (data) e 0x5DA4 (interface), bit 31 busy. O formato de resposta do caminho MMIO precisa ser revisado (possível cópia da interface em vez de data).

Encoder de comando 0x11 (0x5A3F–0x5BAB): ratio bits 7:0, alvo de tensão bits 19:8, modo bit 20, offset bits 31:21. Domínio 2 também interage com MSR620. Isso não representa BCLK em MHz.

PCU mailbox em 0x677A: usa bus de MSR300, janelas PCI f8040/f8044 (interface/data). Fluxos de PLL observados:

- HSX 306f: SfrTrim usa sequência de operações privadas (não demonstradas em execução).
- BDW 406f: PLLTrim assinado (−15…+15), não incremento em MHz.
- Adjust PLL: condiciona execução a strap existente 125/166 MHz, não estabelece por si só um novo strap.
- CLR min/max: rotinas de cache; não confundí-las com CPU BCLK.

Mapa PCI uncore e valores históricos (somente observação, não instruções de escrita):

| Dispositivo | Identificação | Registradores observados |
|---|---|---|
| ff:1f.0 | PCU 8086:6f88 | 40.L=0x90, 44.L=0 |
| ff:1e.1 | PCU 8086:6f99 | 8C.L=0x00c20002, 90.L=0 |
| ff:10.7 | Ubox 8086:6f1f | 5C=0x20, 60=0x230, 64=0, 68=1, 6C=0 |

Em `OcInit` 0x647E, offsets b0000/b0040/b0048/b0060/b0064/b0068/b006c correspondem a HECI1 em ECAM, não a um PLL independente. A rotina confronta strap observado com MSR61E e tem handshake privado. Não enviar `0x60000001` ao PCI 4C sem semântica validada.

## 9. HECI / MEI: tentativas em runtime

### 9.1 Descoberta e exposição PCI

Inicialmente HECI1/2 não apareciam em lspci. DSDT/SSDT continham dispositivos HECI, HEC2, IDER, MEKT e SpsNm, mas tabelas ACPI genéricas não comprovavam interface ativa.

RCBA obtida em PCI 00:1f.0 F0.L = 0xfed1c001; base 0xFED1C000. FD2 em 0xFED1F428, inicial 0x1F. A análise de SpsPei/SpsDxe/HeciInitDxe associou bits 1–4 a HECI1/2, IDER, KT. Em teste anterior, FD2 passou a 0x1D (limpeza do bit HECI1). O dispositivo surgiu no barramento com `8086:8d3a`, rev05, subsystem 8086:7270. O rescan PCI enumerou o dispositivo; BAR0 foi realocado de f831a000 para b4000000. Isso foi alteração volátil já realizada, não alteração do dump SPI.

### 9.2 Driver experimental

`mei_me` padrão recusou o dispositivo com `Device doesn't have valid ME Interface`. HFS1 PCI 40.L=`0x000f0392` contém bits 19:16=f, condição que faz o driver reconhecer SPS no caminho `MEI_ME_PCH8_SPS_4_CFG`.

Foi compilado módulo experimental a partir do kernel 7.0.0, em `~/backup-bios/mei-driver/mei-experimental`, alterando apenas a associação `MEI_LPT_W, MEI_ME_PCH8_SPS_4_CFG` para `MEI_LPT_W, MEI_ME_PCH8_CFG`. Módulo `mei-me.ko` de aproximadamente 1,3 MB, vermagic compatível. Carregamento de módulo sem assinatura contaminou (taint) o kernel. O bypass de reconhecimento não resolveu o protocolo:

```text
mei mei0: waiting for mei start failed
mei mei0: HBM haven't started
mei mei0: link layer initialization failed.
mei_me 0000:00:16.0: init hw failure.
mei_me 0000:00:16.0: initialization failed.
```

Nenhum `/dev/mei0`, nenhum driver vinculado. HBM HOST_START_REQ=1/response=0x81 (referência de protocolo Linux, não resposta recebida do SPS). Não há prova de que o problema seja apenas IRQ. Não repetir a mesma modificação de driver.

### 9.3 Último estado MMIO observado

PCI COMMAND=0x0002 (Mem+; BusMaster-). BAR0=0xB4000000–0xB400000F, 16 bytes. IRQ pin A roteado a 16, MSI desabilitado, D0, grupo IOMMU 53. HFS1=0x000f0392; HFS2/PCI48 variou (último 0x90406006, outros 0x90408006/0x90402006/0x9040c006). PCI4C=0x1300ffff, 60/64/68/6C=0 em observação.

| MMIO | Papel |
|---|---|
| BAR+0x0 | buffer de escrita do host |
| BAR+0x4 | host CSR |
| BAR+0x8 | buffer de leitura do ME/SPS |
| BAR+0xC | ME CSR |

Ambos CSRs retornaram `0x80020209`: profundidade 128 DWORDs, read/write pointers=2, ready=1, reset=0. Isso mostra buffers aparentemente vazios/prontos no instante observado, não prova entrega ou processamento de mensagens. A leitura do buffer de dados pode consumir informação; não confundir com leitura de CSR.

HECI connectionless/fixed-address é hipótese para contornar a dependência de enumeração HBM. Nenhuma mensagem ICC foi efetivamente transmitida/testada. Antes de desenvolver transporte experimental, confirmar cliente e protocolo, impedir disputa com driver e verificar existência de recuperação local. Se for restaurar o software normal, usar módulo padrão do kernel; não alterar FD2 enquanto o PCI estiver enumerado. O estado posterior não foi verificado.

## 10. Protocolo ICC no firmware UEFI

### 10.1 IccPlatform

Função 0x96C distingue modos via HFS1 PCI b0040: nibble 19:16=f leva a retorno 1; outros casos podem retornar 2. Chamadores 0x430 e 0xAA8 exigem 2 para disponibilizar determinada interface. No SPS original o valor observado é compatível com retorno 1. Não implica que **todo** ICC do SPS esteja desabilitado.

Função 0x9A8 localiza protocolo HECI (`CFB33810-6E87-4284-B203-A66ABE07F6E8`), testa modo 0 e status low nibble zero. Constrói comando 0x03, versão 0x00030000, header 20 bytes, payload 12 bytes (dois argumentos de 32 bits e constante 1). Chamada por interface +0x10. Não foi identificada a finalidade exata; não tratar como GET de frequência.

### 10.2 IccOverClocking

PE32 x86-64, base 0x10000000, `.text` VMA 0x10000280, `.rdata` 0x10009420, `.data` 0x100098e0. Função 0x100003C0 usa protocolo HECI via ponteiro global 0x1000A5A0; verifica modo retornado pela função +0x40 e chama slot 0. Argumentos compatíveis com HeciSendwAck: mensagem, tamanho de envio, ponteiro de tamanho de resposta, host 0x00, destino ME 0x08. O endereço e o fluxo estão identificados; entrega ao SPS Grantley não foi provada.

| Rotina | Papel inferido |
|---|---|
| 0x10007500 | wrapper de transporte |
| 0x10007560 | chamada padrão de biblioteca |
| 0x100078A0 | construtor de header |
| 0x10007970 | seleciona command 0x06 |
| 0x100079A0 | interpreta estrutura de resposta |
| 0x10008700 | construtor parcial de header |
| 0x10008770 | preparação/dispatch de mensagem |
| 0x1000889F, 0x10008A3E, 0x10008BD5, 0x10008D84, 0x10008F6C, 0x100090F8 | pontos de chamada de envio |

Header de 20 bytes (DWORDs little-endian): +0x0 versão, +0x4 comando, +0x8 status, +0xC tamanho dos dados, +0x10 campo adicional geralmente zero. Semântica completa do último campo não estabelecida.

O payload `icc-request-06.bin` foi gerado offline (20 bytes, versão 0x30000, command 0x06, três DWORDs zero). Não transmitido. A rotina de resposta espera estrutura de 32 bytes em um caminho de sucesso e interpreta +0x14 (dois WORDs), +0x18 (bits 1:0), +0x1C (DWORD). **Não está comprovado que 0x06 leia frequência, nem que sua API seja suportada no SPS 3.1.** O formato na biblioteca BIOS não deve ser assumido como universal.

## 11. ICCMOD: módulos SPS extraídos e análise ARC

`unhuffme` v2.4.2 foi compilado localmente para descomprimir a família SPS 3.x; download foi feito ignorando certificado TLS expirado, então a origem do executável merece revisão independente. Pequena adaptação `sha256.c`: inicialização de `W[64]`. Extração reportou MATCH para 12 módulos Huffman. Ferramenta `me_unpack.py` do projeto me-tools é Python 2 e não foi executada. ME Analyzer não extraiu os módulos com `-unp86` naquele teste.

Módulos em `~/backup-bios/unhuffme-output/mod/`: ICCMOD, HOSTCOMM, POLICY, KERNEL, BASEEXT, NM e outros. O ICCMOD é ARC Compact/ARC700, não x86. Disassembly foi obtido convertendo o raw para ELF `elf32-littlearc`, seção `.text`, VMA 0x200ef000 e usando `arc-linux-gnu-objdump -d -M cpu=arc700`. A desassemblagem linear pode interpretar dados/literal pools como instruções; validar fluxo e alinhamento antes de conclusões.

Strings do ICCMOD confirmam `IccEventFlagsGroup`, `IccWorkerThread`, `IccHeci1InputQ`, `IccHeci1ConnectedBufferQ`, `IccHeci1SendQ`, `IccHeci1ConnectionlessBufferQ`. Isso evidencia implementação de filas, não que todas estejam habilitadas na placa.

| Endereço ARC | Achado estático / hipótese |
|---|---|
| 0x200EF0D4 | validação de grupo/índice de registro; status 0x1018/0x1019 |
| 0x200EF260 | leitura de registro auxiliar, decodificação grupo/índice; caso 0x7f especial |
| 0x200EF7EC–0x200EF9E0 | validação e escrita auxiliar `sr` |
| 0x200EFDE8 | escrita mascarada em aux 0x12301; `new=(old & ~mask) | (data & mask)` |
| 0x200EFE10 | rotina candidata a configuração; semântica pendente |
| 0x200F0424 | tratamento de estrutura de mensagem e dispatch; compara 0x03/0x0C/0x0D/0x0E/0x0F |
| 0x200F07B0 | handler de evento; rastrear |
| 0x200F0908, 0x200F09C4, 0x200F0A44, 0x200F0C28, 0x200F0D14 | candidatos a handlers associados a tabela de descritores |
| 0x200F09C4 | comparação de máscara solicitada com permitida, possível status 0x1A; revisar contexto e tipos |
| 0x200F0EF0 | entry point candidato de IccWorkerThread, loop de eventos |
| 0x200F1848 | descritor da thread; nome em 0x200F1868, entry 0x200F0EF0 |
| 0x200F18A8 / 0x200F1914–0x200F1938 | descritores candidatos de handlers com tamanhos packed |

Registradores auxiliares ARC observados: `0x10005`, `0x12301`, `0x12302`, `0x8011`. Eles não são MSRs do CPU nem endereços MMIO x86 diretamente. Não há associação validada com MOD3/BCLK. A rotina 0x200EF260 pode modificar um bit de 0x12302 em um caso especial de leitura, portanto nem toda operação chamada de leitura é necessariamente isenta de efeitos colaterais.

No worker loop, bits de evento 9 e 11 chamam função comum 0x200EEAB0 com identificadores 0x1F (12 bytes) e 0x3B (8 bytes); caminhos posteriores chamam 0x200EFDE8/0x200EFE10. Bits 12/13 chamam 0x200EEAC8 com os mesmos IDs. Hipótese: leitura/escrita de configuração interna; ainda não identificada a API nem o local persistente correspondente. Esses IDs são candidatos para correlação com volumes MFS/SCA, não offsets de patch.

HOSTCOMM e POLICY foram extraídos e seus hashes verificados. Ainda falta completar grafo de chamadas e interpretar como o cliente ICC é registrado e quais políticas controlam clocks. Não alegar que esses dois módulos já foram inteiramente decodificados.

## 12. Gerador de clock externo e SMBus

O Linux enumerou i2c-0 (Intel I801, 00:1f.3) e i2c-1…4 da NVIDIA. Não havia clientes I2C registrados que identificassem um PLL externo. Isso não prova que não exista um chip físico, nem que o chip esteja acessível por esse barramento. Nenhuma varredura ativa ou escrita SMBus foi realizada.

SMBus I801 PCI 8086:8d22 rev05, subsystem 8086:7270, BAR0 `0xf8315000–0xf83150ff`, BAR4 I/O `0x0580–0x059f`, IRQ18. Os dois BARs pertencem ao mesmo controlador. `i2cdetect -F 0` indicou suporte às operações SMBus, não I2C raw. Evitar varreduras que possam atingir SPD, VRM ou dispositivos sensíveis.

Busca por referências externas à CK420 no firmware retornou principalmente a opção `External SSC Enable - CK420`. Protocolo EFI SMBUS HC GUID correto `E49D33ED-513D-4634-B698-6F55AA751C1B` encontrado em IioInit, PlatformType, MtrrS3SaveRestoreSmm e PchSmbusDxe. A busca inicial usou um GUID incorreto e foi corrigida. Não foi confirmado comando de programação de PLL externo em PlatformType; ocorrências de constantes isoladas podem ser dados e não instruções.

**Próximo passo desse ramo:** fotografia nítida da placa ou documentação elétrica para identificar marcação de um eventual gerador externo, trilhas/topologia e datasheet do componente. Até lá, não supor endereço SMBus nem aplicar receitas SetFSB de outras placas.

## 13. Comparação de BIOS e módulos alternativos

### 13.1 Mod conhecido da própria H9S

Repositório `jwagnervaz/QIYIDA-X99-H9S`, variantes de 16 MiB BOOTSECURE-TPM-MOD:

| Arquivo | SHA-256 histórico |
|---|---|
| BOOTSECURE-TPM-151-H9SC612SPSJWAGNERVAZ.ROM | `a61b34a7b2f5f5dac2c2981defbd31dde66c6b6eebdfda7b4b226b0cd76be12d` |
| variante LEGACYGPU | `ab61b48770981e74c1f3ec39ff455f5a7e4855703920c8cc0dbacec707b8d705` |

A comparação anterior encontrou região SPS idêntica à original (SHA-256 `04b63494d57ac598c026bff9fe7bb392e5129c5800ec5779dd247e57aec8f414`), mesmos microcodes e mesmos executáveis PpmInitialize, OcInit, UncoreInitPeim, IccPlatform, IccOverClocking e PlatformCpuPolicy. Platform e Setup diferem. Os defaults IntelSetup mudam 13 bytes, incluindo 0x13FD (0→1), sem mudanças de OC enable/visibility/profile. Outras diferenças: LAN, NUMA, PCIe IOU, rótulo XMP, S3/ventoinha. Não há evidência de ganho BCLK nesse mod. Normalização de QIDs no diff de IFR ajuda a filtrar renumerações, mas pode esconder alterações de referências; não é prova de equivalência semântica.

### 13.2 Pacote D1_M1_B1 de Win-Raid

Guia de BIOS de overclock para placas X99 chinesas; candidatos históricos D1 (descriptor Machinist X99-B9), M1 (firmware Machinist X99-K9), B1 (BIOS Huananzhi X99-BD4 modificada). O histórico da pesquisa encontrou relato de H9S com M1 e E5-1650 v3, não E5-2680 v4. Pacote MEGA indisponível; arquivo completo não obtido. Não há teste do conjunto no computador investigado. Não é correto descrever o pacote como solução comprovada para v4 bloqueado.

### 13.3 OcInit da C612RD24

BIOS de referência localizada em Mi899, arquivo `machinist-x99z-c612rd24.rom.zip`. Extração feita no computador do proprietário; o pacote `ocinit-comparacao.tar.gz` contém binário alternativo, disassembly e diff contra o original.

| Propriedade | H9S original | C612RD24 alternativo |
|---|---|---|
| IntelSetup | 0x17EC = 6124 bytes | 0x17CB = 6091 bytes |
| OC Mailbox MSR150 | sim | sim |
| Guard RatioOcSupported | sim | sim |
| MSR61E / lógica de strap do original | presente | não localizada no módulo alternativo |

Trecho alternativo confirmado no diff:

```asm
ffdc32c3: call 0xffdc3aea
ffdc32cd: cmp BYTE PTR [esp+0xd],bl
ffdc32d1: je 0xffdc32ef
```

A função de capacidades usa OC Mailbox. O módulo alternativo tem layout de variável diferente (33 bytes), portanto não deve ser simplesmente transplantado. O arquivo alternativo possui 6112 bytes. A comparação confirma diferenças e restrições, não que o BCLK esteja fisicamente bloqueado.

## 14. Ferramentas e referências de pesquisa

| Ferramenta | Estado | Uso |
|---|---|---|
| flashrom hardware sequencing | utilizado | dump SPI, leitura; recuperação ainda não validada |
| UEFITool / UEFIExtract | utilizado | inspeção FFS, GUIDs e módulos |
| IFRExtractor-RS | utilizado | extração de forms e variáveis |
| ME Analyzer | utilizado | identificação SPS, FPT, validações |
| unhuffme | utilizado | extração de módulos Huffman ARC |
| binutils-arc-linux-gnu | utilizado | análise ARC700 |
| msr-tools, turbostat, cpupower, pciutils | utilizado | medição e testes históricos |
| me-tools | clonado | análise de formatos anteriores; Python 2 |
| Intel FITC ME 9.1 | localizado no GitHub | candidato apenas para comparação; não validado para SPS |
| Intel CCT ME 9.1 | localizado no GitHub | operações de clock em plataformas compatíveis; não executado |
| spsFITc para Grantley SPS 3.x | pendente | prioridade para edição oficial dos dados |
| meimagetool / parseMFS | candidatos | analisar formato de MFS offline, compatibilidade incerta |

O repositório `avkila-tech/ALL-X99-BIOS-TOOLS` foi consultado pelo conector GitHub. A árvore contém FITC ME 9.1 r7 (`fitc.exe`, 2.785.240 bytes), CCT EFI64 (`cct.efi`, 396.288), WIN32 (`cctWin.exe`, 190.424, `cctDll_LPT.dll`, 81.920) e DOS (`cct.exe`, 442.910). Os binários não foram executados nem autenticados como distribuição oficial. Não usar ferramentas de procedência duvidosa no sistema de produção.

Operações CCT citadas na investigação: `gcc` (clock capabilities), `gc` (get clock), `sc` (set clock), `gp` (get profile), `gr` (get register), `sr` (set register). Sintaxe e disponibilidade variam por versão; não são comandos testados. FITC desktop pode expor parâmetros ICC/Spread Spectrum, mas suporte à geração C610/X99 não implica suporte ao SKU SPS Grantley.

Pacote de ferramentas SPS mencionado na comunidade: `SPS_E5_03.00.05.402.0_PV-G_WBG_REL`. Não foi obtido; compatibilidade com SPS 03.01.03.072 não demonstrada. Buscar **spsFITc + dados/XML/templates específicos para Grantley/SPS 3.1**, não somente um executável com nome parecido. Não converter SPS para ME desktop como primeiro experimento.

### Referências públicas e locais

1. Intel C610/X99 PCH Datasheet, tabela 1-2 e capítulo 4 (especialmente 4.5, 4.6 e tabela de moduladores): <https://www.intel.com.tw/content/dam/www/public/us/en/documents/datasheets/x99-chipset-pch-datasheet.pdf>. Cópia local no PC `~/backup-bios/x99-pch.pdf` e `.txt`. Texto do PDF reconsultado nesta consolidação; a tentativa de abrir imagens das páginas retornou cache miss.
2. Intel Xeon E5 v4 datasheet, vol. 2 (Registers): <https://www.intel.com/content/www/us/en/content-details/333810/intel-xeon-processor-e5-v4-family-volume-2-of-2-registers-datasheet.html>; cópia local `~/backup-bios/xeon-v4-registers.pdf`.
3. Intel Xeon E5 v4 datasheet, vol. 1 (Electrical): <https://www.intel.com/content/www/us/en/content-details/333809/intel-xeon-processor-e5-v4-family-volume-1-of-2-electrical-datasheet.html>.
4. Linux MEI driver: <https://github.com/torvalds/linux/tree/v7.0/drivers/misc/mei> (especialmente `pci-me.c`, `hw-me.c`, `hw-me-regs.h`, `hw-me.h`).
5. <https://github.com/platomav/MEAnalyzer>.
6. <https://github.com/LongSoft/UEFITool> e <https://github.com/LongSoft/IFRExtractor-RS>.
7. <https://github.com/skochinsky/me-tools>.
8. <https://github.com/peterbjornx/meimagetool> e <https://github.com/ptresearch/parseMFS> — candidatos; não validados para SPS 3.1.
9. <https://github.com/coreboot/coreboot> — referências de protocolos HECI/ICC, comparar versões.
10. <https://github.com/avkila-tech/ALL-X99-BIOS-TOOLS/tree/main/TOOLS>.
11. <https://github.com/jwagnervaz/QIYIDA-X99-H9S>.
12. <https://github.com/miyconst/Mi899> — BIOS de referência C612RD24.
13. <https://winraid.level1techs.com/t/guide-overclock-bios-mods-for-chinese-x99-mbs/104683> e publicações `/61`, `/134` — histórico D1/M1/B1; links de download podem estar indisponíveis.
14. <https://winraid.level1techs.com/t/sps-3-tools/37875/8> — referência ao pacote SPS 3 tools.
15. <https://github.com/Koshak1013/HuananzhiX99_BIOS_mods> — comparação de firmware, não receita validada para a H9S.

Os links de comunidade e repositórios acima são referências da investigação acumulada; nem todos foram reabertos nesta consolidação. Dados privados, dumps integrais e identificadores de máquina não devem ser publicados junto com o código de pesquisa.

## 15. Manifesto de evidências e arquivos

### Pacotes enviados e reabertos na consolidação

| Pacote | Arquivo | Bytes | SHA-256 recalculado |
|---|---|---:|---|
| icc-analysis.tar.gz | ICCMOD-200ef000.mod | 16384 | `e6a3782d4b62d269f086597849a768426d215198015ab37b2e1ff0537e8b97d6` |
| idem | ICCMOD-fixed.elf | 16836 | `6595569716fc3f12043dacf629860543da7dd6161318fdf01c00e9c1ffa2c722` |
| idem | ICCMOD.asm | 224238 | `2bc2f813f5d11bee8c2726442636f65ddfca3539ee076970c3b34b158cc2bc68` |
| idem | HOSTCOMM-200e1000.mod | 28672 | `6bd4fcb81262bac2b5f23a03425a9426b5834637fe86127d11b338068b23833e` |
| idem | POLICY-2009f000.mod | 212992 | `00c3fd04827b0336d793d15576758ff943f9bb0ebeb76d9650c3525a8356da4e` |
| icc-bios-protocol.tar.gz | IccOverClocking.bin | 43840 | `e0d5df1664ddaea2b2f98a3dda625c30fe177f930f372bac563682cdfe2af14e` |
| idem | IccOverClocking.asm | 549340 | `752105bb10403fcf6dd6db631345b26da19bd850708b9d73f32a49545e486c29` |
| idem | IccPlatform.bin | 3424 | `113d798639ce43756a4a32bd4b6a0157e7b93b0e2c926ade84147738392e0243` |
| idem | IccPlatform.asm | 32471 | `d1b154b7cb5b986a7a76839ff29645a80f1aa364014392700f3fafdf26ecd21e` |
| ocinit-comparacao.tar.gz | OcInit-mod.bin | 6112 | `a8ebc035afb83b245f818994c1ebd4979399ad8312a337b0bbb93d9ec06e64a5` |
| idem | OcInit-mod.asm | 100101 | `5b4cdc3c17480ef8df4020cb0ccc59dd3c510d0dc3ab2c2d176a5b311c585c87` |
| idem | OcInit-diff.txt | 267116 | `67e44bf3060d376e26cf17a008f26ec84e99bd07ae7deb8531844324e9867b42` |

### Arquivos e diretórios mantidos no computador

```text
~/backup-bios/
├── x99-h9s-original.bin
├── x99-h9s-verificacao.bin
├── x99-h9s-original.bin.dump/
├── x99-h9s-original.bin.guids.csv
├── x99-h9s-original.bin.report.txt
├── analise/                 # módulos originais, IFR, disassembly
│   ├── Platform.bin.0.0.en-US.uefi.ifr.txt
│   ├── IccOverClocking.bin / .asm
│   ├── IccPlatform.bin / .asm
│   ├── OcInit.bin / .asm
│   └── PpmInitialize.bin / .asm
├── analise-mod/
├── bios-mod-referencia/
├── bios-mod-referencia.rom
├── MEAnalyzer/
├── mei-driver/              # inclui driver experimental
├── me-tools/
├── sps-region.bin
├── unhuffme-output/mod/      # módulos SPS descomprimidos
├── overclock-mod/           # C612RD24 + comparação OcInit
├── icc-analysis.tar.gz
├── icc-bios-protocol.tar.gz
├── icc-request-06.bin       # offline, nunca transmitido
├── bclk-options.txt
├── x99-pch.pdf / .txt
└── xeon-v4-registers.pdf
```

Logs de terminal anexados à conversa documentam os passos de extração, MSRs, FPT, HECI, IFR e comparação. Para prosseguir em outro ambiente, anexar este Markdown e os três pacotes acima; o Markdown não substitui os binários para desassemblagem.

## 16. Matriz de decisão

| Ramo | Evidência atual | Ganho potencial | Decisão |
|---|---|---|---|
| MSR/ratio 30x | rejeição real | improvável por este método | suspender |
| Patch PpmInitialize | guard de software conhecido, CPU rejeita ratio | incerto | suspender como via de ratio |
| Remover guard OcInit | caminho PLL alcançável, MSR61E falha em runtime | incerto | só após análise de pré-condições |
| C612RD24 OcInit | guarda e layout incompatível | não comprovado | não transplantar isoladamente |
| Driver MEI normal/quirk bypass | HBM não inicializa | nenhum ganho direto | não repetir |
| HECI connectionless | transporte e filas localizados | consulta em runtime, eventual ajuste | secundário, protocolo pendente |
| Configuração persistente ICC | arquitetura Intel documentada | alvo real do BCLK se suportado | **prioridade 1** |
| PLL externo | opção CK420, sem identificação física | depende da placa | prioridade 2 quando identificável |
| Trocar SPS por M1/ME desktop | incompatibilidades, pacote não obtido | incerto | último recurso, nunca primeiro teste |
| Downgrade de microcode | nenhuma prova v4 | incerto | não priorizar |

## 17. Plano de ação operacional

### Fase 0 — Preservação e baseline

- [x] Dois dumps SPI idênticos; original protegido.
- [x] Turbo all-core aproximado e bloqueio de ratio registrados.
- [ ] Copiar backups para outro computador/armazenamento e validar recuperação presencial.
- [ ] Capturar baseline reproduzível de CPU, memória, armazenamento e AER/MCE.
- [ ] Confirmar governor e limites de frequência atuais; verificar alteração parcial de CPU0.

### Fase 1 — Coletar os dados persistentes do SPS (próxima ação concreta)

Extrair descriptor, MFSB, SCA e MFS da cópia original. Não precisamos ler novamente a flash física nem enviar o dump completo. O bloco abaixo é somente leitura do arquivo original; cria arquivos separados para análise.

```bash
cd ~/backup-bios
mkdir -p sps-icc-research
python3 - <<'PY'
from pathlib import Path
import hashlib

src = Path('x99-h9s-original.bin')
rom = src.read_bytes()
expected = '6036511afaaeab53701e0adce3a3a731790302f24ca11614212f95f2901fce5b'
actual = hashlib.sha256(rom).hexdigest()
assert len(rom) == 16 * 1024 * 1024, 'Tamanho incorreto'
assert actual == expected, 'Hash diferente do dump de referência'
regions = {
    'descriptor': (0x000000, 0x1000),
    'MFSB': (0x002000, 0x10000),
    'SCA':  (0x012000, 0x10000),
    'MFS':  (0x042000, 0x40000),
}
folder = Path('sps-icc-research')
manifest = [f'original {actual}']
for name, (offset, size) in regions.items():
    data = rom[offset:offset+size]
    assert len(data) == size
    (folder / f'{name}.bin').write_bytes(data)
    line = f'{name} offset=0x{offset:06x} size=0x{size:x} sha256={hashlib.sha256(data).hexdigest()}'
    print(line)
    manifest.append(line)
(folder / 'manifest.txt').write_text('\n'.join(manifest)+'\n')
PY
```

Somente se o Python terminar sem erros:

```bash
tar -czf sps-icc-research.tar.gz sps-icc-research
tar -tzf sps-icc-research.tar.gz
xdg-open "$PWD"
```

Enviar `sps-icc-research.tar.gz` de forma privada. **Ainda não foi recebido na data deste documento.** Os volumes podem conter configuração específica da plataforma.

### Fase 2 — Implementar analisador offline, não editor

Projeto proposto `sps-icc-analyzer` em Python, sem acesso direto a `/dev/mem`, flashrom, MSRs ou SMBus.

```text
sps-icc-analyzer/
├── README.md
├── firmware/                 # local, ignorado pelo Git
├── src/
│   ├── descriptor.py
│   ├── partition_table.py
│   ├── mfs_parser.py
│   ├── sca_parser.py
│   ├── icc_parser.py
│   ├── binary_diff.py
│   └── validator.py
├── profiles/                 # esquemas decodificados, sem dados privados
├── tests/                    # fixtures sintéticas e testes unitários
└── main.py
```

Entregas:

1. Parser do descriptor e FPT, com limites, intervalos, versão de header, offsets relativos/absolutos e hashes.
2. Identificação de blocos apagados, assinaturas, páginas, sequências de registros e possíveis checksums em MFSB/SCA/MFS.
3. Testar meimagetool/parseMFS em cópias e validar se reconhecem corretamente a geração. Saída de parser moderno não é evidência suficiente; comparar offsets, tamanho, magic e conteúdo bruto.
4. Correlacionar as chamadas internas do ICCMOD (IDs 0x1F/0x3B, tamanhos 12/8) com configuração persistente; completar análise de HOSTCOMM e POLICY. Procurar relações entre estruturas, não apenas ocorrências de `100`, `101`, `100000000` ou `MOD3`.
5. Exportar inventário e resultados em JSON/Markdown, incluindo offset, tamanho, origem, interpretação, confiança e campos desconhecidos.

**Critério de saída:** identificar pelo menos um registro plausível de configuração ICC com referência cruzada do código ou de uma ferramenta compatível. Nenhuma escrita em firmware nessa fase.

### Fase 3 — Obter referência oficial ou diferencial

- Procurar spsFITc e seus dados de plataforma para Grantley 3.1. Verificar versão, origem e compatibilidade antes de executar. Ambiente isolado, sem acesso ao hardware real.
- Testar abertura de uma cópia do dump e exportação de configuração. Se falhar, registrar a mensagem; não forçar outra plataforma.
- Se houver campos ICC utilizáveis, gerar dois arquivos offline com uma única alteração conhecida, mantendo os demais parâmetros iguais. Comparar regiões e analisar impacto de normalização/rebuild.
- Se não houver ferramenta compatível, comparar dumps da mesma versão SPS e plataforma com parâmetros de clock conhecidos. A diferença pode incluir dados de provisionamento e NVRAM, portanto não é automaticamente o perfil ICC.
- Identificar representação de frequência, faixa, spread, divisores e política. Confirmar MOD3 e distinguir frequência nominal de ajustes de modulação.

**Critério de saída:** relação causal reproduzível entre um parâmetro de clock identificado e sua representação binária, com validação independente (ferramenta, fluxo de código ou múltiplos pares de amostras controladas). Caso contrário, manter hipótese aberta.

### Fase 4 — Candidato de imagem experimental offline

Somente após a fase 3: preparar uma imagem derivada que altere o mínimo de dados necessário para uma configuração nominal de 101 MHz, se suportada. Preservar dados de placa, descriptor, executáveis SPS e BIOS. Entender e preservar checksums, redundância, estado de arquivos e eventuais mecanismos de assinatura/autenticação; não tratar bypass de integridade como solução genérica. Validar tamanho, regiões e diferenças; documentar manifestos e possibilidade de restauração. Primeiro gerar e validar um rebuild sem alteração funcional para detectar mudanças inesperadas da ferramenta.

Não há, neste documento, offset confirmado nem patch pronto para 101 MHz. Não se deve fabricar uma imagem por substituição de uma sequência binária semelhante a 100 MHz. A validação offline é necessária, mas não suficiente para provar boot e estabilidade.

### Fase 5 — Teste físico e validação de frequência

**Pré-requisitos:** acesso físico e recuperação SPI disponível; backup de arquivos críticos em outro dispositivo; armazenamento de teste descartável ou cópia recuperável; console local. O proprietário aceita clocks acoplados, portanto não é necessário abandonar o experimento apenas por afetar PCIe/DMI. Porém, não testar primeiro em um disco com dados insubstituíveis.

Sequência de metas: baseline 100 → 101 → 102 → 103 → 104 → 105 MHz. Só avançar após validar a etapa anterior. Passos adicionais (107, 110 ou straps) exigem nova avaliação e não são garantidos. Não alterar tensão, limites de potência ou spread simultaneamente ao primeiro teste de frequência. Se a plataforma exigir um reset global/cold boot, confirmar isso na documentação da ferramenta e assegurar acesso local.

Medições de referência (se ferramentas estiverem instaladas):

```bash
lscpu
cpupower frequency-info
sudo turbostat --quiet --interval 2 --num_iterations 10
sudo journalctl -k -b --no-pager | grep -iE 'mce|machine check|hardware error|aer|pcie|nvme|ata|i/o error|edac'
lsblk -o NAME,SIZE,FSTYPE,MOUNTPOINTS,MODEL
```

Executar `turbostat` durante a mesma carga utilizada no baseline; registrar temperatura, Busy%, Bzy_MHz, throttling e potência. Usar benchmark de CPU com carga definida e tempo externo/independente quando possível: uma referência derivada do TSC pode ser influenciada pelo clock, então não aceitar apenas uma leitura de frequência ou valor DMI como prova. Confirmar também desempenho real, ratios e ausência de regressões.

Testes mínimos por etapa:

- Inicialização normal e estabilidade em idle/carga CPU sustentada.
- Teste de memória; comparar resultados de compilação/benchmark e hashes determinísticos.
- PCIe/GPU, NVMe, SATA, USB e rede: erros de link, resets, retries, falhas de checksum e corrupção. Validar leitura e escrita em arquivos descartáveis com hashes antes/depois; não realizar testes destrutivos sobre discos de produção.
- Comparar eventos AER/MCE/EDAC e saúde do armazenamento antes/depois; monitorar temperatura e throttling.
- Reiniciar e conferir persistência, quando houver acesso presencial e recuperação.

**Critério de sucesso inicial:** aumento verificável do BCLK ou de frequência efetiva acima do baseline, mantendo 29x sob carga equivalente, acompanhado de ganho mensurável e sem erros nos testes realizados. A ausência de erros durante um teste curto não prova estabilidade de longo prazo.

**Critério de interrupção/rollback:** ausência de POST, desconexões, erros de I/O ou de memória, AER/MCE, perda de desempenho, throttling anormal ou divergência de hashes. Restaurar configuração/dump original pelo método de recuperação previamente validado.

### Fase 6 — Ramo paralelo, caso os dados ICC não sejam editáveis

- Determinar a topologia física de clock e identificar eventual PLL externo.
- Completar a análise de protocolo HECI, HOSTCOMM e POLICY para verificar se existe consulta autorizada após o POST. Só implementar um cliente de teste quando o comando e a compatibilidade forem conhecidos. Não desabilitar End Of POST ou outras proteções cegamente.
- Investigar por que MSR61E não está acessível em runtime e se as rotinas de strap têm pré-condições adicionais no PEI. Um patch de guard só deve ser avaliado depois que a execução subsequente estiver compreendida.
- Se todos os caminhos forem incompatíveis, registrar conclusão negativa específica desta placa/firmware. Não inferir impossibilidade universal do Xeon v4 nem prometer ganho sem mecanismo verificável.

## 18. Handoff: como retomar sem repetir a investigação

**Estado mais recente:** 2,9 GHz all-core, HECI exposto mas sem HBM e sem cliente ICC testado. OC Mailbox rejeita ratio 30x. Firmware executável ICC disponível e parcialmente analisado. Mod C612RD24 não fornece solução demonstrada e tem layout incompatível. SPS persistente permanece original. Não houve flash modificada nem aumento comprovado de BCLK.

**Próxima entrega necessária:** `sps-icc-research.tar.gz`, conforme fase 1. Ao recebê-lo, começar por validar o manifesto e interpretar MFSB/SCA/MFS; não pedir novamente lspci, rdmsr de ratio, IFR de clock ou descompactação dos módulos já disponíveis.

**Perguntas técnicas ainda abertas:**

1. Onde está a configuração ICC inicial nesta versão de SPS? MFS, MFSB, SCA ou outro armazenamento?
2. IDs internos 0x1F/0x3B representam registros de configuração de clock ou outra função?
3. Qual ferramenta/versão interpreta esses volumes sem substituir o SPS original?
4. Existe ajuste de frequência de MOD3 autorizado para a configuração do C612 da H9S?
5. O CLKOUT_DMI alimenta efetivamente o CPU nesta revisão física? Existe PLL externo?
6. Quais domínios e divisores mudam juntos? Que representação de frequência é usada?
7. O firmware aceita o protocolo ICC da BIOS após EOP, ou somente em determinada fase/cliente?
8. É possível medir 101 MHz e 2,929 GHz all-core de forma independente e reproduzível?

**Regra para a continuação:** distinguir endereço localizado de função compreendida; função compreendida de comando suportado; comando suportado de alteração física; alteração física de overclock estável. O objetivo é o último, não apenas mostrar menus ou obter respostas de registradores.
