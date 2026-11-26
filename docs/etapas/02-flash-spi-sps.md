# Etapa 02 — Flash SPI, descriptor, partições e memória persistente

> Fase: levantamento de requisitos e estudos. Registro derivado da [pesquisa consolidada](../xeon-e5-2680v4-h9s-pesquisa-bclk-icc.md), de 26/11/2026. Não representa novos testes em hardware.

Objetivo: estabelecer a origem dos bytes, a geometria da imagem e os limites de cada região.

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

## Mapa de endereçamento

```text
SPI [0x000000, 0x1000000)
  descriptor [0x000000, 0x001000)
  SPS        [0x001000, 0x800000)
    MFSB     [0x002000, 0x012000)
    SCA      [0x012000, 0x022000)
    FTPR     [0x022000, 0x042000)
    MFS      [0x042000, 0x082000)
    OPR1     [0x082000, 0x282000)
    ASAP     [0x282000, 0x286000)
    restante da região: não atribuir função sem analisar bytes
  BIOS       [0x800000, 0x1000000)
```

Intervalos acima são semiabertos. A conversão de offset SPS para SPI soma 0x1000. Exemplo: OPR1 relativo 0x81000 -> SPI 0x82000. O endereço ARC de carregamento 0x200EF000 não é um offset SPI. Não confundir capacidade da flash, tamanho da região SPS e tamanho útil reportado pelo ME Analyzer.

## Etapas históricas e reprodução offline

1. Detecção com flashrom no modo interno; JEDEC desconhecido no software sequencing.
2. Detecção com hardware sequencing; flash opaca de 16 MiB.
3. Duas leituras independentes, comparação byte a byte, SHA-256 e proteção do original.
4. Extração UEFI, identificação do FPT e análise dos metadados de módulos.
5. Separação de regiões e volumes de dados para investigar ICC. A coleta MFSB/SCA/MFS ainda é pendente.

```bash
cd ~/backup-bios
sha256sum x99-h9s-original.bin x99-h9s-verificacao.bin
cmp x99-h9s-original.bin x99-h9s-verificacao.bin
stat -c '%n %s bytes' x99-h9s-original.bin
uefiextract x99-h9s-original.bin all
```

O último comando gera arquivos locais; não grava a SPI. Usar pasta de trabalho separada se a extração já existir.

## Camadas de integridade

| Camada | Validação necessária | Estado |
|---|---|---|
| Dump | tamanho e hash | confirmado |
| Descriptor | limites, acesso, straps | mapa identificado |
| FPT | assinatura, offsets, tamanhos e integridade | mapa identificado; parser próprio pendente |
| MFS/SCA | registros, redundância e checksums | formato pendente |
| Executáveis SPS | manifestos e hashes | módulos extraídos com MATCH |
| BIOS UEFI | FV/FFS, estados e checksums | inspeção inicial |
| Recuperação SPI | gravação/restauração externa verificada | pendente |

Não há alteração persistente aplicada. A permissão RW da flash não comprova que uma imagem alterada seja inicializável. Os dumps brutos ficam fora do Git.

**Saída:** mapa de memória persistente estabelecido. Próximo: [boot, UEFI e IntelSetup](03-boot-uefi-intelsetup.md).
