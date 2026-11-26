# Etapa 09 — Caderno de comandos, resultados brutos e decisões

> Fase: levantamento de requisitos e estudos. Suplemento à [pesquisa consolidada](../xeon-e5-2680v4-h9s-pesquisa-bclk-icc.md) e às etapas 01–08. Data da auditoria: 26/11/2026. Reconstrução dos registros históricos da investigação; não é uma nova sessão de testes. Blocos de escrita são identificados como históricos e não devem ser executados como receita.

## 1. Protocolo de registro

Cada experimento deve conservar: identificador, ambiente, comando, resultado bruto, interpretação, classificação da evidência e efeito colateral. Os valores abaixo foram recuperados do histórico técnico; quando o log completo não está preservado neste repositório, o registro não deve ser apresentado como transcrição integral de terminal.

- **Leitura:** observação de um estado, sem intenção de modificá-lo.
- **Transação:** operação que envia um comando a uma interface, mesmo quando a finalidade é consultar dados.
- **Escrita volátil:** alteração de estado em execução; não modifica necessariamente a SPI.
- **Offline:** processamento de arquivos.
- **Escrita persistente:** nenhuma realizada no projeto até a consolidação.

## 2. Frequência e limites CPU

| Experimento | Operação registrada | Resultado histórico |
|---|---|---|
| EXP-01 | CPUID | 0x406F1 |
| EXP-02 | governor schedutil → performance | frequência all-core permaneceu aproximadamente 2893–2900 MHz |
| EXP-02 | `cpupower frequency-set -d 2.9GHz -u 3.3GHz` | falhou no CPU1; CPU0 possivelmente ficou com mínimo 2,9 GHz |
| EXP-02 | MSR 0x199 bits 15:8 | 33 solicitado |
| EXP-02 | MSR 0x198 bits 15:8 | 29 executado sob carga |
| EXP-02 | MSR 0xCE | 0xa0080c3bf2811800 |
| EXP-02 | MSR 0x194 | 0x0 |
| EXP-02 | MSR 0x1AD | 0x1d1d1d1d1e1f2121 |
| EXP-02 | MSR 0x1AE, 0x1AF | 0x1d1d1d1d1d1d1d1d |
| EXP-02 | MSR 0x61E | leitura não suportada no contexto Linux observado |
| EXP-02 | MSR 0x620, 0x621 | 0xc1b; ratio observado 15x |
| EXP-02 | MSR 0x300 | 0x8000ff00, bus uncore 0xff |

O retorno ao mínimo anterior de CPU0 não foi confirmado. As leituras de RAPL anormalmente baixas não comprovam margem de potência. Os limites e condições térmicas estão descritos na [etapa 01](01-plataforma-cpu-msr.md).

### OC Mailbox — transações realizadas, não repetir

| Campo | Valor |
|---|---|
| MSR | 0x150 |
| Valor inicial observado | 0x1f00000000 |
| Consulta de capacidades: valor enviado | 0x8000000100000000 |
| Retorno | 0x221 |
| Busy / completion | 0 / 0 |
| Pedido histórico de ratio 30x: valor enviado | 0x800000110000001E |
| Retorno | 0x500000000 |
| Busy / completion | 0 / 5 |
| Efeito no limite turbo | nenhum observado |

A consulta utilizou `wrmsr` seguido de `rdmsr`; não foi uma leitura passiva. A escrita de ratio foi rejeitada, não constituindo um método de desbloqueio. O significado simbólico exato de completion 5 não foi confirmado em uma especificação da geração.

| Domínio | Retorno do comando 1 |
|---:|---|
| 0 | 0x221 |
| 1 | 0x10500000000 |
| 2 | 0x2000000021b |
| 3 | 0x30000000000 |
| 4 | 0x40000000000 |

Consultas 0x10, 0x14 e 0x12 em domínios 0 e 2 e consulta 0x1A retornaram payload zero. Não interpretar como autorização para alterar tensão ou PLL.

### Microcode

```bash
iucode-tool -l /lib/firmware/intel-ucode/06-4f-01.initramfs
```

Resultado histórico: sig 0x000406f1, pf_mask 0xef, 2021-05-19, rev 0x0b000040, 35840 bytes. BIOS iniciou com 0x0b000038; Linux carregou 0x0b000040. O pacote de microcode e o changelog foram examinados, sem encontrar evidência de desbloqueio. Não houve downgrade.

## 3. SPI — sequência de detecção, leitura e extração

| Passo | Comando ou método | Resultado |
|---|---|---|
| EXP-03a | `flashrom -p internal` | Wellsburg não testado; software sequencing não reconheceu JEDEC |
| EXP-03b | `flashrom -p internal:ich_spi_mode=hwseq` | flash opaca de 16 MiB |
| EXP-03c | duas leituras independentes | mesmo SHA-256, cmp idêntico |
| EXP-03d | chmod 444 | cópias de referência protegidas contra edição acidental |
| EXP-04 | `uefiextract x99-h9s-original.bin all` | árvore FV/FFS, relatório e CSV de GUIDs |
| EXP-04 | IFRExtractor-RS 1.6.1 | formulários IntelSetup extraídos |
| EXP-11 | ME Analyzer 1.312.0 r378 | SPS 03.01.03.072 GR |
| EXP-11 | extração SPS do dump original | região iniciando em SPI 0x1000, 2047 blocos de 4096 |

JEDEC histórico em bytes A1 28 18 (também representado como 0xA12818). Identificação física do chip continua pendente.

Abaixo, reprodução somente em cópia local do dump, sem acesso à flash física:

```bash
cd ~/backup-bios
sha256sum x99-h9s-original.bin x99-h9s-verificacao.bin
cmp x99-h9s-original.bin x99-h9s-verificacao.bin
dd if=x99-h9s-original.bin of=sps-region.bin bs=4096 skip=1 count=2047 status=none
```

Executar a extração em diretório separado para não sobrescrever artefatos já catalogados. O original esperado possui 16 MiB e SHA-256 `6036511afaaeab53701e0adce3a3a731790302f24ca11614212f95f2901fce5b`.

## 4. HECI — exposição PCI e tentativa de driver

### Registros históricos, sem repetir escritas

| Ordem | Observação ou transação | Valor / efeito |
|---|---|---|
| 1 | PCI 00:1f.0 F0.L | 0xfed1c001 |
| 2 | RCBA | 0xFED1C000 |
| 3 | FD2, endereço físico 0xFED1F428 | 0x1F |
| 4 | escrita volátil realizada em FD2 | 0x1D; HECI1 apareceu |
| 5 | consulta PCI direta, função 00:16.0 | 8086:8d3a rev05 |
| 6 | rescan PCI do Linux | dispositivo enumerado |
| 7 | BAR0 antes e depois | 0xF831A000 → 0xB4000000 |
| 8 | driver mei_me padrão | rejeição de interface SPS |
| 9 | driver experimental | HBM timeout; inicialização falhou |
| 10 | PCI COMMAND | 0x0002 |
| 11 | PCI 40.L | 0x000f0392 |
| 12 | PCI 48.L | 0x90406006 (última observação documentada) |
| 13 | host CSR e SPS CSR | 0x80020209 ambos |
| 14 | /dev/mei0 | inexistente |

Outros valores históricos em PCI48: 0x90402006, 0x90408006, 0x9040c006. PCI4C observado 0x1300ffff. Não inferir o significado desses estados sem documentação. O BAR é endereço físico atribuído pelo PCI, não endereço permanente de firmware.

### Alteração de software realizada

Foi obtido o código-fonte correspondente ao kernel 7.0.0-44 e criada uma cópia local de drivers/misc/mei. A mudança experimental foi restrita à associação do identificador:

```diff
- MEI_LPT_W, MEI_ME_PCH8_SPS_4_CFG
+ MEI_LPT_W, MEI_ME_PCH8_CFG
```

Kbuild utilizado na compilação da variante:

```makefile
obj-m := mei-me.o
mei-me-y := pci-me.o hw-me.o
```

A compilação resultou em módulo compatível com o kernel observado, porém sem assinatura. O carregamento causou taint do kernel e falha de HBM. Não houve comunicação ICC nem comprovação de que o timeout fosse causado por IRQ. Não há motivo para repetir a compilação da mesma variante.

### Último log registrado

```text
mei_me 0000:00:16.0: Device doesn't have valid ME Interface
mei_me: module verification failed: signature and/or required key missing - tainting kernel
mei mei0: waiting for mei start failed
mei mei0: HBM haven't started
mei mei0: link layer initialization failed.
mei_me 0000:00:16.0: init hw failure.
mei_me 0000:00:16.0: initialization failed.
```

A ausência de /dev/mei0 deve ser diferenciada de ausência do dispositivo PCI. O estado após eventual reboot ou restauração do driver padrão não foi verificado.

## 5. SPS e ICC — cadeia de ferramentas

| Operação | Artefato | Resultado |
|---|---|---|
| ME Analyzer `-unp86` | SPS | não produziu os módulos desejados |
| me-tools | me_unpack.py | Python 2; não executado |
| unhuffme v2.4.2 | mod/*.mod | 12 módulos Huffman com MATCH |
| adaptação histórica do código unhuffme | sha256.c | W[64] inicializado; recompilado |
| objdump raw ARC | ICCMOD-200ef000.mod | saída insuficiente, muitas .word |
| objcopy ELF + ajuste VMA | ICCMOD-fixed.elf | disassembly ARC Compact utilizável |
| grep de referências ICC | ICCMOD e demais módulos | nomes de filas/thread; sem nomes úteis de PLL/BCLK |
| geração de requisição 0x06 | icc-request-06.bin | 20 bytes, offline, não enviada |

O arquivo de requisição contém:
```text
00 00 03 00 06 00 00 00 00 00 00 00 00 00 00 00 00 00 00 00
```

A semântica e compatibilidade de 0x06 continuam pendentes. Não é um comando de clock validado.

## 6. Estado final desta cadeia

Nenhum dos passos de escrita volátil, ajuste de governor ou análise de módulos demonstrou alteração de BCLK. Nenhuma imagem SPI modificada foi gravada. A coleta e interpretação de MFSB, SCA e MFS continuam sendo o próximo passo do ramo principal.

Para os endereços de funções e dependências internas, consultar [etapa 10](10-mapa-funcoes-estruturas.md). Para o plano de coleta, consultar [etapa 07](07-requisitos-plano-validacao.md).
