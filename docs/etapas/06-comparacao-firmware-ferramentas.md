# Etapa 06 — Comparação de BIOS, ferramentas e hipóteses descartadas

> Fase: levantamento de requisitos e estudos. Registro derivado da [pesquisa consolidada](../xeon-e5-2680v4-h9s-pesquisa-bclk-icc.md), de 26/11/2026. Não representa novos testes em hardware.

Objetivo: preservar o histórico das alternativas testadas para evitar retrabalho ou confundir compatibilidade de placa com desbloqueio de CPU.

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

## Método de comparação

1. Registrar a procedência, nome, tamanho e hash da imagem candidata.
2. Verificar layout de descriptor, região BIOS e SPS.
3. Comparar hashes por região, módulo e microcode, não apenas o hash da imagem inteira.
4. Extrair módulos homólogos e IFR; conservar os resultados brutos.
5. Comparar versões, offsets de variáveis, tamanho de políticas e guards.
6. Identificar diferenças semânticas e registrar quais caminhos permanecem iguais.
7. Classificar a candidata como evidência, referência ou solução validada. Nenhuma das candidatas atuais é uma solução de BCLK validada.

## Resultado diferencial resumido

| Candidato | Achado útil | Por que não é solução pronta |
|---|---|---|
| H9S BOOTSECURE-TPM | SPS e executáveis OC idênticos; defaults modificados | não demonstra alteração de clock |
| D1/M1/B1 | relato comunitário de H9S | pacote indisponível; teste de CPU v3 desbloqueada |
| C612RD24 OcInit | implementação alternativa de mailbox | guarda de ratio presente, IntelSetup incompatível |
| FITC ME 9.1 | ferramentas disponíveis | parser SPS 3.1 não comprovado |
| spsFITc SPS 3.x | família de ferramentas candidata | versão compatível e pacote pendentes |
| meimagetool / parseMFS | alternativa de parser | compatibilidade com os volumes SPS desconhecida |

A pesquisa não inclui distribuição de binários proprietários; links são referências, não endosso de procedência. Não instalar BIOS de outra revisão apenas porque o nome comercial coincide.

**Saída:** preservação do SPS original é a estratégia principal. Próximo: [plano de engenharia](07-requisitos-plano-validacao.md).
