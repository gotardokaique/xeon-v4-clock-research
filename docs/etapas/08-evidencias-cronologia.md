# Etapa 08 — Evidências, cronologia e rastreabilidade

> Fase: levantamento de requisitos e estudos. Registro derivado da [pesquisa consolidada](../xeon-e5-2680v4-h9s-pesquisa-bclk-icc.md), de 26/11/2026. Não representa novos testes em hardware.

Objetivo: permitir que outro pesquisador retome a investigação a partir dos artefatos existentes, sem repetir etapas já concluídas.

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

## Linha do tempo técnica

A ordem abaixo é de investigação, não uma cronologia com horários absolutos auditados. As saídas de terminal históricas estão consolidadas na pesquisa principal.

| ID | Passo | Evidência principal | Resultado |
|---|---|---|---|
| EXP-01 | Caracterizar CPU e plataforma | CPUID, PCI, DMI | E5-2680 v4 / C612 |
| EXP-02 | Medir turbo e ratios | cpupower, turbostat, MSRs | 29x all-core |
| EXP-03 | Ler flash duas vezes | SHA-256 e cmp | backups consistentes |
| EXP-04 | Extrair BIOS e IFR | UEFIExtract, IFRExtractor | IntelSetup e menus |
| EXP-05 | Comparar NVAR | dois volumes, estados FFS | configurações distintas; ativa não provada |
| EXP-06 | Desassemblar módulos CPU | PpmInitialize, OcInit | guards de OC e strap |
| EXP-07 | Consultar OC Mailbox | retorno 0x221 | sem RatioOcSupported |
| EXP-08 | Solicitar ratio 30x | completion 5 | rejeitado |
| EXP-09 | Investigar HECI | PCI, ACPI, FD2 | dispositivo exposto |
| EXP-10 | Testar MEI modificado | logs HBM | timeout, sem /dev/mei0 |
| EXP-11 | Analisar SPS | ME Analyzer, FPT | SPS 03.01.03.072 |
| EXP-12 | Descomprimir módulos | unhuffme, MATCH | ICCMOD/HOSTCOMM/POLICY extraídos |
| EXP-13 | Desassemblar ARC | ELF de análise | rotinas auxiliares e worker |
| EXP-14 | Rastrear protocolo BIOS | IccOverClocking/IccPlatform | cabeçalho de 20 bytes; sem GET validado |
| EXP-15 | Comparar H9S modificada | hashes de regiões e módulos | SPS/OC executável idênticos |
| EXP-16 | Comparar C612RD24 | OcInit diff | layout e guard incompatíveis |
| EXP-17 | Pesquisar arquitetura de clock e ferramentas | datasheet C610/X99, FITC/CCT | hipótese de perfil persistente ICC |
| EXP-18 | Coletar MFSB/SCA/MFS | pacote sps-icc-research.tar.gz | pendente |

Algumas atividades foram realizadas em paralelo ou revisitadas; os IDs não implicam que cada operação ocorreu exatamente nessa sequência.

## Matriz de origem das evidências

| Tipo | Exemplo | Como conferir |
|---|---|---|
| Resultado de runtime | MSR150 retornou 0x221 | log de terminal histórico |
| Identificação PCI | 8086:8d44 | log lspci / tabela Intel |
| Achado estático | guard OcInit em 0xFFDC4B90 | assembly e binário original |
| Inferência | IDs 0x1F/0x3B podem indicar configuração | referência cruzada em ICCMOD e volumes |
| Documentação | MOD3 associado ao domínio CLKOUT_DMI | datasheet C610/X99 |
| Pendente | posição do perfil ICC e codificação de MHz | análise de dados persistentes |

## Registro de espaços de memória

| Espaço | Exemplo | Acesso ou origem |
|---|---|---|
| Flash SPI | 0x042000 | arquivo bruto; MFS |
| SPS relativo | 0x041000 | FPT |
| Memória ARC | 0x200EF000 | VMA ICCMOD |
| Registrador auxiliar ARC | 0x12301 | instruções lr/sr |
| MMIO físico x86 | 0xB4000004 | host CSR HECI no teste |
| Config PCI | BDF 00:16.0, offset 0x40 | HFS1 |
| MSR x86 | 0x150 | OC Mailbox |
| Variável UEFI | IntelSetup + 0x12F9 | DMI frequency |
| Endereço de instrução | 0x100003C0 | transporte IccOverClocking |

## Política para novas evidências

Registrar data, versão do firmware, revisão da placa, comando exato, saída, classificação da evidência e conclusão. Preservar falhas de testes; não substituir valores observados por hipóteses. Não publicar números de série, dumps ou dados de provisionamento. Os hashes nesta etapa são transcritos do manifesto consolidado, não recalculados nesta reorganização.

**Próxima ação:** analisar os volumes persistentes depois de receber o pacote privado; consultar [etapa 07](07-requisitos-plano-validacao.md) para o procedimento de coleta.
