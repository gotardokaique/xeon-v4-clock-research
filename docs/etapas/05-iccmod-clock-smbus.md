# Etapa 05 — ICCMOD, arquitetura de clock, ARC e SMBus

> Fase: levantamento de requisitos e estudos. Registro derivado da [pesquisa consolidada](../xeon-e5-2680v4-h9s-pesquisa-bclk-icc.md), de 26/11/2026. Não representa novos testes em hardware.

Objetivo: mapear o alvo físico de clock e as funções candidatas do firmware SPS, incluindo armazenamento e transporte.

## 6. ICC: arquitetura de clock documentada

O datasheet Intel C610/X99 PCH (capítulo 4, especialmente 4.5 e 4.6) descreve configuração de clocks via firmware SPS 3.0/ME9, com parâmetros persistentes na região de dados da flash. A tabela 1-2 associa LPC 8D44 ao C612. C612 suporta clock integrado nativo, híbrido e gerador externo CK420BQ; não está demonstrado qual topologia física foi montada na H9S.

O modulador **MOD3** está associado a CPU BCLK (CLKOUT_DMI), DMI, PCIe, USB3, SATA/sSATA e outros clocks. O mesmo datasheet distingue recursos de overclock HEDT. A existência de MOD3 não garante que seu ajuste adaptativo seja desbloqueado no C612/SPS nem que todos os clocks se alterem na mesma proporção.

```text
SPI / dados SPS -> configuração ICC -> PLL / moduladores / divisores
                                        |-> CPU BCLK (se roteado)
                                        |-> DMI/PCIe/USB/SATA (domínios dependentes)
```

**Hipótese de trabalho:** ajustar a configuração de clock inicial do SPS original, sem depender da rotina de overclock de ratio do CPU. MOD3 é o alvo funcional; ainda não há mapeamento entre MOD3 e os endereços auxiliares privados do ICCMOD.

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

## Reconstrução do executável ICCMOD

O raw descomprimido não é um executável ELF originalmente. O ELF abaixo é uma representação de análise criada para fornecer arquitetura e VMA corretas ao disassembler.

```bash
cd ~/backup-bios/unhuffme-output/mod
arc-linux-gnu-objcopy -I binary -O elf32-littlearc -B arc \
  --rename-section .data=.text,alloc,load,readonly,code,contents \
  ICCMOD-200ef000.mod ICCMOD.elf
arc-linux-gnu-objcopy --change-section-vma .text=0x200ef000 \
  ICCMOD.elf ICCMOD-fixed.elf
arc-linux-gnu-objdump -d -M cpu=arc700 ICCMOD-fixed.elf > ICCMOD.asm
```

Para esse módulo, offset raw = endereço ARC menos 0x200EF000, dentro dos 0x4000 bytes extraídos. Exemplo: 0x200F0424 corresponde a offset 0x1424. Isso não permite converter o endereço diretamente em posição da SPI comprimida.

## Módulos de execução

| Nome | Base ARC inferida do nome | Tamanho do raw | Investigação |
|---|---|---:|---|
| ICCMOD | 0x200EF000 | 16 KiB | handlers e registradores parcialmente analisados |
| HOSTCOMM | 0x200E1000 | 28 KiB | registro de cliente e roteamento pendentes |
| POLICY | 0x2009F000 | 208 KiB | condições e políticas pendentes |
| KERNEL | 0x20041000 | não registrado aqui | serviços e primitivas de execução |
| BASEEXT | 0x2010B000 | não registrado aqui | dependências candidatas |
| NM | 0x20193000 | não registrado aqui | Node Manager, não identificado como controlador BCLK |

## Worker e hipóteses de persistência

| Evento observado | ID interno | Tamanho | Ação candidata |
|---|---|---:|---|
| bit 9 | 0x1F | 12 bytes | chamada 0x200EEAB0, depois 0x200EFDE8 |
| bit 11 | 0x3B | 8 bytes | chamada 0x200EEAB0, depois 0x200EFE10 |
| bit 12 | 0x1F | não revalidado | chamada 0x200EEAC8 |
| bit 13 | 0x3B | não revalidado | chamada 0x200EEAC8 |

Os IDs podem ser parâmetros internos ou registros de configuração. Não são offsets confirmados nem identificadores de comandos HECI. A tabela de handlers deve ser validada com análise de fluxo e tipos, levando em conta delay slots do ARC.

## Investigação de clock

| Domínio / componente | O que sabemos | O que falta |
|---|---|---|
| MOD3 | associação documentada ao domínio BCLK/CLKOUT_DMI | endereço interno, faixa e permissões no C612 |
| PLL interno | arquitetura prevista no datasheet | configuração montada na placa |
| CK420BQ | topologia externa prevista | presença física e endereço |
| SSC | IFR contém campos de configuração | efeito no BCLK real e representações |
| DMI/PEG | campo de divisor na BIOS | compatibilidade e aplicação |
| Aux 0x12301 | rotina de escrita mascarada localizada | significado físico e vínculo com MOD3 |

Não há requisito de isolamento absoluto dos barramentos; a alteração compartilhada é aceita na pesquisa. Isso não transforma uma escrita desconhecida em operação de frequência válida.

**Saída:** arquitetura e alvos de investigação identificados, sem comando de escrita BCLK validado. Próximo: [comparação de firmware](06-comparacao-firmware-ferramentas.md).
