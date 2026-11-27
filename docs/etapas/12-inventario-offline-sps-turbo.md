# Etapa 12 — Inventário offline dos volumes SPS e caminhos de turbo

Sessão de 26/11/2026. A [etapa 11](11-etapa-atual-investigacao-bclk-icc.md) permanece como referência operacional para as hipóteses H01–H12. Esta entrega registra evidências novas para H02, H08–H11 e os limites de cada inferência.

## SPS-01 — Coleta e geometria dos volumes

**Hipótese.** O descriptor e a FPT apontam para os mesmos volumes da etapa 11. Assinatura inválida, intervalos divergentes ou diferença em relação à cópia SPS refutariam a correspondência.

Os dois dumps SPI de 16 MiB têm SHA-256 `6036511afaaeab53701e0adce3a3a731790302f24ca11614212f95f2901fce5b`. O intervalo SPI `[0x1000, 0x800000)` é idêntico a `sps-region.bin` (SHA-256 `04b63494d57ac598c026bff9fe7bb392e5129c5800ec5779dd247e57aec8f414`). Na cópia original, FRBA é `0x40` e FLREG2 é `0x07ff0001`. A FPT tem tag no offset SPS `0x10`, versão de header `0x20`, seis entradas de `0x20` bytes a partir de `0x30`. A soma modular de 8 bits de SPS `[0,0x30)` é zero, enquanto a de `[0x10,0x30)` é `0xeb`. A soma observada só caracteriza o cabeçalho desta imagem.

| Volume | Offset SPI | Offset SPS | Tamanho | SHA-256 |
|---|---:|---:|---:|---|
| descriptor | 0x000000 | — | 0x1000 | `9ee9d284bfec565e49bf5934e1d3800f8d57351844d7460bd09d281d44af9d4d` |
| MFSB | 0x002000 | 0x1000 | 0x10000 | `6a2de998bcbbc71585db8a5ba656ba94479e9845624cb085098459a8bb0761c3` |
| SCA | 0x012000 | 0x11000 | 0x10000 | `7e3ebba8d81881e71eea9a3d946b9c193c648b36dbbb01b7bb5ed0087f19677d` |
| MFS | 0x042000 | 0x41000 | 0x40000 | `c77c1f1c7abc3f17cb0149ed36f4087f8dbcb7c7e64359a31c175a074d6c2c28` |

Coleta executada em `~/backup-bios/sps-icc-research/`, com `manifest.json` e os quatro binários locais. Para reproduzir a partir da raiz do repositório, use um diretório de saída novo.

```bash
python3 scripts/inventario_sps.py ../x99-h9s-original.bin ../sps-icc-research-replay \
  --sha256 6036511afaaeab53701e0adce3a3a731790302f24ca11614212f95f2901fce5b
python3 -m unittest discover -s tests -v
```

**Classificação.** Evidência estática, validada com Python 3.14.4. O script valida o hash informado, limites e sobreposições e inventaria blocos de 4 KiB. A cobertura do parser está restrita à variante FPT observada. Quatro testes sintéticos cobrem offsets, truncamento, sobreposição e duplicidade.

## SPS-02 — Páginas candidatas e redundância parcial

**Hipótese.** MFS tem unidades de 16 KiB distinguíveis pelo cabeçalho e MFSB contém conteúdo compartilhado. Refutação proposta: outro dump Grantley compatível ou o leitor no firmware atribuir os padrões a uma estrutura de granularidade diferente.

| Volume | Observação estática em offset relativo ao volume |
|---|---|
| MFS | Nos 16 limites de 0x4000, os primeiros oito bytes são `0078feff00000000` em 0 e `0178feff00000000` em 0x4000. Os 14 limites de 0x8000 a 0x3c000 começam com `ff78ffff00000000` e o restante de cada unidade é 0xff. |
| MFSB | Mesmo cabeçalho inicial de MFS. Dados em 0–0x3fff e 20 bytes diferentes de 0xff no último bloco de 4 KiB, com último byte em 0xff1b. |
| SCA | Primeiro DWORD zero, segundo DWORD 0x10, sequência ASCII SCA em 0x9. Último byte diferente de 0xff em 0xac3. |

Entropia de Shannon por unidade de 0x4000 bytes, incluindo preenchimento: MFS 0x0 = 0,828, MFS 0x4000 = 2,337, MFS 0x8000 = 0,004, MFSB 0x0 = 2,854, SCA 0x0 = 0,899 bit/byte. O preenchimento domina parte dessas medidas.

O cruzamento usou âncoras de 32 bytes alinhadas em MFSB com pelo menos 12 valores de byte distintos, buscou a primeira ocorrência em MFS e estendeu cada igualdade nos dois sentidos. Os três maiores trechos encontrados foram conferidos pelos intervalos abaixo. O método procura evidência de sobreposição e pode omitir outras ocorrências.

| Início MFSB | Início MFS | Comprimento |
|---:|---:|---:|
| 0x0b07 | 0x464d | 0x0a19 |
| 0x1528 | 0x5070 | 0x0714 |
| 0x0010 | 0x0010 | 0x054d |

**Interpretação.** Os deslocamentos distintos sustentam conteúdo compartilhado com organização diferente. A seleção de cópia ativa, a função do rodapé MFSB e a integridade dos registros seguem pendentes. Nenhum dos três volumes contém a assinatura de página `87 78 55 aa`, e MFSB não começa com a tag ASCII exigida pelos caminhos de backup R0/R1 do MEAnalyzer local (commit `d27ccdba0aadbad490f47b5b631c369b682a7ef5`). Esse é um teste de pré-condição por inspeção da fonte, sem executar o parser. O layout de páginas de 8 KiB publicado para MFS do Intel ME não explica a amostra Grantley. [Pesquisa primária sobre o MFS de ME](https://blackhat.com/docs/eu-17/materials/eu-17-Sklyarov-Intel-ME-Flash-File-System-Explained-wp.pdf).

**Referência cruzada.** Após encapsular o POLICY raw como ELF ARC700, a rotina em VMA `0x200b2fee–0x200b3028` seleciona MFSB para seletor 0 ou MFS para 1 e chama uma função indireta no slot `+0x24` do objeto obtido via `[0x200deca4]`, usando o nome de quatro bytes em r1 e um buffer local em r2. Copia DWORDs do buffer em `[sp+0x30]` e `[sp+4]` para destinos do chamador. Os loads PC-relativos em `0x200af05c`, `0x200b3928`, `0x200b3d74` e `0x200c90a2` também referenciam o literal MFSB. A função indireta é candidata a consulta de metadados de partição. A origem do objeto e os campos retornados ainda precisam ser confirmados.

```bash
arc-linux-gnu-objcopy -I binary -O elf32-littlearc -B arc:ARC700 \
  --rename-section .data=.text,alloc,load,readonly,code,contents \
  --change-addresses 0x2009f000 \
  ../unhuffme-output/mod/POLICY-2009f000.mod /tmp/policy-sps-research.elf
arc-linux-gnu-objdump -d --start-address=0x200b2fee --stop-address=0x200b3030 \
  /tmp/policy-sps-research.elf
```

**Próximo teste.** Resolver o slot `+0x24` e seguir os consumidores dos dois DWORDs para testar se representam offset e tamanho. Cruzar as referências do POLICY com o leitor de páginas para testar a granularidade de 16 KiB e o papel do rodapé MFSB.

## ICC-01 — Direção dos buffers no worker

**Hipótese.** Os dois serviços usam registros tipados. A hipótese de persistência requer encontrar o backend de armazenamento ou localizar o mesmo registro em um volume com estrutura validada.

Com GNU binutils ARC 2.46, a desassemblagem de `ICCMOD-fixed.elf` em `0x200f0f5c–0x200f0fd6` confirma a ordem dos argumentos considerando os delay slots. A referência original é o módulo raw com SHA-256 `e6a3782d4b62d269f086597849a768426d215198015ab37b2e1ff0537e8b97d6`.

| Evento | VMA da chamada | Argumentos na ordem r0/r1/r2 | Consumidor |
|---|---:|---|---|
| bit 9 | 0x200f0f6c | serviço 0x200eeab0, ID 0x1f, buffer, 12 | retorno zero e bit 0 do terceiro DWORD habilitam chamada a 0x200efde8 com os dois primeiros DWORDs |
| bit 11 | 0x200f0f94 | serviço 0x200eeab0, ID 0x3b, buffer, 8 | retorno zero e bit 0 do segundo DWORD habilitam chamada a 0x200efe10 com o primeiro DWORD |
| bits 12/13 | 0x200f0fbc / 0x200f0fd0 | serviço 0x200eeac8, ID 0x1f/0x3b, 12/8, buffer zerado | o worker prossegue sem testar o retorno nesses eventos |

**Limite e próxima ação.** O primeiro serviço fornece dados ao chamador no caminho de sucesso. O segundo recebe buffers zerados, compatível com solicitação de reset de estado do registro. Persistência e efeito físico continuam hipóteses. Ambos os alvos estão fora dos intervalos exportados pelo unhuffme. HOSTCOMM termina em `0x200e8000` exclusivo, e o intervalo ICCMOD exportado começa em `0x200ef000`. O manifesto de extração indica início declarado em `0x200ed000` para ICCMOD, ainda acima dos serviços. Para localizar os corpos é preciso mapear a lacuna em OPR1 pelos metadados de páginas e relocação, ou obter outra extração que cubra esse intervalo.

## CPU-01 — Gates independentes e pontos de leitura

**Hipótese.** Alterar uma política de turbo produz efeito apenas se a rotina consumidora alcançar a escrita e a plataforma aceitar o novo limite. Uma escrita observada com rejeição ou frequência idêntica em carga refutaria a eficácia para aquela configuração.

Desassemblagem local x86 com GNU objdump 2.46. Os endereços abaixo são VMA PE/COFF. O relatório UEFIExtract classifica PpmInitialize, PlatformCpuPolicy e CpuMpDxe como DXE, e CpuMpPei e OcInit como PEI. Isso corrige a classificação de fase de PpmInitialize na tabela de endereçamento da etapa 10, cuja redação histórica foi preservada.

- **PpmInitialize.** A chamada em 0x1315 chega a 0x2318. Para modelo 0x4f, 0x23e6–0x240a lê 0x1af e 0x1ac. A metade alta de 0x1ac diferente de zero desvia para a saída antes de 0x2410. O valor de 0x1ac no momento do DXE é desconhecido. Se avançar, a rotina sai em 0x244c com PLATFORM_INFO[28] limpo ou em 0x2454 com zero em MSR 0x194[19:17]. As escritas para 0x1ad, 0x1ae e, nos modelos 0x3f/0x4f, 0x1af ficam em 0x2b23, 0x2b3c e 0x2b9a.
- **Construção dos limites.** Em 0x245a, a comparação com 1 usa o resultado da máscara literal 0x10000000 aplicada em 0x2445. Pela entrada sequencial, só 0x10000000 alcança a comparação. O salto para 0x2610 é tomado nesse fluxo, deixando de fora o caminho de clamp em 0x2464–0x260e. Este resultado é sobre o fluxo estático local e não altera os gates anteriores.
- **Rotina separada de bit 63.** A chamada em 0x0e41 chega a 0x2bcc. O código testa MSR 0xCE[28] e bit 28 do DWORD em `[[contexto+0xc]+0x25]`. Sob ambos os gates, para modelos 0x4f/0x56 lê 0x1ac e prepara escrita com bit 63 setado em 0x2c8f. A origem exata do DWORD de política continua pendente.
- **CpuMpDxe.** Em 0x60d8–0x6105 lê o byte baixo de 0x1ad como valor para uma estrutura, com substituição pelo byte baixo do resultado não nulo armazenado em 0xf340. O produtor em 0x1fe1–0x1ff5 chama uma interface indireta com seletor 0x25. Este trecho evidencia construção de dados de CPU. A semântica do seletor requer identificação da interface.
- **CpuMpPei e OcInit.** As instruções MSR do corpo de CpuMpPei inventariado referenciam 0x1b, 0x802 e 0x830 (APIC). Em OcInit, `0xffdc5724` divide os bits 8–10 da resposta da consulta em três flags, após sucesso. A flag do bit 8 é a testada em `0xffdc4b8c` antes de ler MSR 0x61e. A resposta histórica 0x221 tem bit 8 limpo, compatível com o branch de saída se a mesma resposta ocorrer no PEI. A resposta em PEI permanece desconhecida.

**Limite.** Evidência estática do código, correlacionada com leituras históricas. A rejeição anterior de ratio 30x no OC Mailbox continua sendo evidência da transação realizada, distinta das condições do DXE. Próximo teste offline: cruzar GUIDs e o layout produzido por PlatformCpuPolicy com `contexto+0xc`, identificar a interface do seletor 0x25 e mapear o domínio exato da consulta PEI. O seletor de transporte 2 em 0xffdc5760 chega ao caminho de MSR 0x150 em 0xffdc5f8d–0xffdc5fd1.

## CPU-02 — Comparação de microcode 0x406F1

A hipótese de que as duas BIOS de referência trazem revisão ou payload diferente para 0x406F1 foi testada por assinatura primária do cabeçalho Intel, offsets alinhados a 16 bytes, comprimento delimitado, soma DWORD módulo 2³² igual a zero e SHA-256 do bloco completo.

| Origem | Offset na entrada | Revisão | Máscara de plataformas | Tamanho |
|---|---:|---:|---:|---:|
| SPI H9S original e BIOS mod de referência | 0xeac180 | 0x0b000038 | 0xef | 0x7800 |
| SPI C612RD24 | 0xe77f90 | 0x0b000038 | 0xef | 0x7800 |
| `/lib/firmware/intel-ucode/06-4f-01.initramfs` | 0 | 0x0b000040 | 0xef | 0x8c00 |

As três cópias SPI têm bloco idêntico, com SHA-256 `e3e4d916ffde5337c7d34b8bff227ea6623c2dfe288beab7f8381d2328a4144d`. O bloco local para initramfs tem SHA-256 `e3242ce8ec36a416af379475c04bf4d10178905c3bec5643d2690bd136aa18fa`. A presença desse arquivo demonstra disponibilidade local da revisão, enquanto a revisão carregada durante a sessão não foi consultada. O resultado negativo circunscreve as duas BIOS comparadas e não mede diferenças comportamentais entre revisões.

## Estado experimental

A sessão usou exclusivamente arquivos locais e análise estática. Os binários originais foram lidos e todos os volumes extraídos ficaram fora do repositório. H02 avançou com a geometria e os trechos compartilhados. H08–H11 avançaram com a separação dos gates, a flag de OcInit e a identidade do microcode das referências. Ainda faltam vínculo do ICCMOD com um registro persistente, cadeia completa de política de turbo e medições independentes de alteração efetiva. A combinação fica condicionada à validação isolada de cada mecanismo.
