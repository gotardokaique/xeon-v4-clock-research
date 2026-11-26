# Etapa 10 — Mapa de funções, estruturas, endereços e condições de boot

> Fase: levantamento de requisitos e estudos. Suplemento de engenharia reversa reconstruído do histórico técnico de 26/11/2026. Não é uma nova desassemblagem completa. Endereços privados e nomes descritivos devem ser conferidos no binário correspondente antes de qualquer implementação.

## 1. Convenções

| Espaço | Exemplos | Interpretação |
|---|---|---|
| PEI OcInit / PpmInitialize | 0x4B84, 0x2410 | endereços curtos usados na análise original; conferir VMA e seção |
| PEI OcInit mapeado | 0xFFDC4B84 | endereço exibido no diff |
| DXE IccPlatform | 0x9A8 | endereço mostrado pelo objdump daquele módulo |
| DXE IccOverClocking | 0x100003C0 | endereço virtual PE/COFF |
| ARC SPS | 0x200EF000 | VMA atribuída ao módulo raw descomprimido |
| ARC auxiliary register | 0x12301 | índice de registrador auxiliar, não memória x86 |
| SPI | 0x082410 | offset absoluto no dump |
| IFR QID | 0x13FC | identificador de pergunta, não offset |
| IntelSetup VarOffset | 0x163D | offset relativo ao payload da variável |

Não existem símbolos de depuração suficientes para afirmar os nomes originais das funções privadas. Rótulos abaixo são nomes analíticos, não classes ou métodos exportados conhecidos.

## 2. Inicialização CPU e políticas — PpmInitialize

| Endereço curto | Observação estática |
|---|---|
| 0x2318 | copia 24 WORDs de ratios a partir da política; consulta MSRs 0x35 e 0x1AD/0x1AE/0x1AF/0x1AC |
| 0x2410 | lê MSR 0xCE |
| 0x241B | lê MSR 0x194 |
| 0x243E | extrai OC bins (bits 19:17) |
| 0x2445–0x244C | testa PLATFORM_INFO bit 28; desvia quando zero |
| 0x2452–0x2454 | testa OC bins; desvia quando zero |
| 0x2770 | manipulação de MSR 0x194, incluindo bit 20 |
| 0x27A3 | caminho de escrita de política de ratio |

Ambos os guards observados têm condição falsa para habilitação de OC na CPU testada. O teste direto de ratio pelo mailbox também foi rejeitado; portanto, alterar um branch não prova desbloqueio físico.

## 3. OcInit — mapa detalhado de chamadas

| Endereço curto | Papel observado ou inferido |
|---|---|
| 0x4A84 | entrada analisada; buffer local 0x1894 |
| 0x4AAD | tabela de valores 100/125/166/250 |
| 0x4B2A | acesso à variável IntelSetup, tamanho 0x17EC |
| 0x4B5E | teste de OC_ENABLE em offset 0x163F |
| 0x4B84 | chamada à função 0x5724 |
| 0x4B8C–0x4B90 | guard RatioOcSupported |
| 0x4B96–0x4B9B | leitura MSR 0x61E |
| 0x5724 | consulta de capacidades; chama 0x69D2/0x5919 e transporte |
| 0x5A3F–0x5BAB | encoder de comando 0x11 |
| 0x5E61 | dispatch dos transportes MMIO/MSR |
| 0x602D | polling; limite observado de 1000 iterações |
| 0x6165, 0x6207, 0x6387 | caminhos auxiliares de ajuste a investigar |
| 0x647E | leitura/sincronização de estado de strap via PCI |
| 0x658B | WRMSR 0x61E no caminho de sincronização |
| 0x6665 | rotina candidata de ajuste mínimo do ring/cache; usa PCU e MSR 0x620 |
| 0x677A | PCU mailbox por endereços PCI derivados do bus de MSR 0x300 |
| 0x6898 | caminho de offset TJMax; fora do escopo de ajuste de clock |
| 0x693F | caminho de ajuste AVX |
| 0x6A4B / 0x6A6D | wrappers de leitura/escrita |
| 0x6AEB | localização de interface PEI; GUID 06E81C58-4AD7-44BC-8390-F10265F72480 |
| 0x6B0F / 0x6B17 / 0x6B1A | acesso indireto a interface de memória |
| 0x6B1D | resolve base/ponteiro em cache |
| 0x6B43 / 0x6B4F | leitura/escrita a partir de base e offset |

O GUID em 0x6AEB está localizado, mas o tipo completo da interface ainda não foi identificado. Os caminhos privados de PCU/PLL foram encontrados estaticamente; não foram executados em teste de alteração de frequência.

### Dependências da rotina de strap

A sequência 0x647E usa a janela PCI correspondente a HECI1 (offsets b0000, b0040, b0048, b0060, b0064, b0068, b006c). A função compara bits do estado observado em b0060 com bits do MSR 0x61E e pode sincronizá-los. Também contém acesso a f80a0 e handshake privado associado a PCI4C.

A existência de valores 100/125/166/250 no código não significa que o firmware possa selecionar arbitrariamente esses valores. O ajuste PLL para 125/166 depende de um strap previamente estabelecido. A leitura de MSR 0x61E falhou em Linux; comportamento durante PEI desconhecido. Não há razão para tratar NOP de um único salto como solução pronta.

### Transportes privados

| Transporte | Interface | Dados | Controle |
|---|---|---|---|
| OC mailbox CPU | MSR 0x150 | DWORD inferior | DWORD superior / busy bit 63 |
| OC mailbox MMIO | base obtida por interface PEI | +0x5DA0 | +0x5DA4 / busy bit 31 |
| PCU mailbox | ECAM bus uncore | f8044 | f8040 / busy bit 31 |
| Ring/cache | PCI ff:1e.1 | 0x8C | 0x90 |
| HECI | PCI 00:16.0 BAR0 | +0x00/+0x08 | +0x04/+0x0C |

Os caminhos de ajuste SfrTrim em CPUID 306f e PLLTrim em CPUID 406f não são equivalentes. A magnitude assinada de PLLTrim vai de -15 a +15, sem unidade física confirmada. Não interpretar como MHz.

## 4. IFR — condições e campos que faltavam no índice principal

| QID | VarOffset | Papel |
|---|---:|---|
| 0x13FC | 0x163D | visibilidade do formulário OC |
| 0x13FB | 0x0000 em SystemAccess | condição de acesso; outro VarStore |
| 0xD8F | 0x13FC | Extreme Edition, não confundir com QID 0x13FC |
| 0xD90 | 0x13FD | Overclocking Lock |
| 0xE3F | 0x163F | OverClocking Feature |
| 0x10B0 | 0x12EF | perfil ICC |
| 0x10B1 | 0x12F9 | frequência DMI |
| 0x10B2 | 0x12FB | frequência PCI |
| 0x10B5 | 0x1301 | DMI/PEG Ratio |
| 0x13EA | 0x1308 | flag dinâmica de edição de frequência PCI |
| 0x13EB | 0x1305 | flag de visibilidade PCI |
| 0x13EC | 0x1311 | flag de edição ICC |
| 0x13EF | 0x1307 | flag dinâmica de edição de frequência DMI |
| 0x13F0 | 0x1304 | flag de visibilidade DMI |
| 0x13F1 | 0x12F0 | flag de edição do perfil |
| 0xD12 | 0x1334 | ME FW Image Re-Flash; não identifica o SKU |

O formulário OC tem FormId 0x3F0. O guard de visibilidade usa QID 0x13FC, enquanto o guard de acesso usa QID 0x13FB. Valores de frequência exibidos como placeholders, faixas uninitialized e flags zero impedem inferir suporte físico a partir do IFR.

## 5. HECI, ACPI e DXE

| Fonte | Achado histórico | Limite |
|---|---|---|
| DSDT | HECI, HEC2, IDER, MEKT | objetos ACPI podem existir sem PCI ativo |
| SSDT SpsNm | MFS1 PCI40; MECS bits 3:0; OPMD bits 19:16 | interpretação de estado depende do firmware |
| HEC2 | NMFS bit 31; NMEN; H2RP 0x60; HIDM 0xA0 | campos de ACPI, não prova de operação |
| H2CS | SystemMemory 0xF8319000, comprimento 0x10 | região não apareceu alocada em iomem na observação |
| SpsPei | manipula bit 1 de FD2 | comportamento inicial de exposição |
| HeciInitDxe | rotina 0x2045–0x20BB, máscaras por índice | associação dos dispositivos HECI |
| SpsDxe | rotina em torno de 0xD00, reconstrução de bits 1–4 | offsets de política 0x1314–0x1317; correspondência a IntelSetup não validada |

A presença de endereços de ACPI não autoriza usar essas janelas diretamente. O endereço MMIO efetivamente observado para HECI1 durante o teste foi realocado, como registra a etapa 09.

### IccPlatform

| Endereço | Achado |
|---|---|
| 0x430 | chamador que exige tipo 2 |
| 0x96C | classifica modo via HFS1; nibble f retorna 1 |
| 0x9A8 | localiza HECI e constrói mensagem |
| 0xA42–0xA71 | preenche 32 bytes: versão 0x30000, comando 3, comprimento 12, parâmetros |
| 0xA72 | chamada via slot +0x10 |
| 0xAA8 | exige classificação 2 |
| 0xAF4 | consulta flag de configuração da interface |

Na H9S, HFS1 0x000f0392 é compatível com tipo 1. Isso restringe o caminho observado, não demonstra que todo ICC esteja desabilitado.

### IccOverClocking

| Endereço virtual | Achado |
|---|---|
| 0x10000280 | entrada do módulo PE32+ analisado |
| 0x10009958 | endereço do GUID passado a LocateProtocol |
| 0x1000A2B0 | ponteiro global compatível com Boot Services |
| 0x1000A5A0 | ponteiro global para interface localizada |
| 0x100003C0 | wrapper de transporte |
| 0x10000420 | chamada 0x100091C0 para obter buffer |
| 0x10000450 / 0x100004DC | chamada 0x10009260 para cópia de dados |
| 0x10000461 | consulta de modo via interface +0x40 |
| 0x1000047F–0x100004A2 | host 0, ME 8, chamada via slot 0 |
| 0x10007500 / 0x10007560 | wrappers de envio |
| 0x100078A0 / 0x10007970 | construção de cabeçalho e comando candidato 0x06 |
| 0x100079A0 | interpretação de resposta candidata de 32 bytes |
| 0x10008700 / 0x10008770 | preparação de cabeçalho e mensagens |

O fluxo padrão de mensagem foi reconstruído, mas a semântica de consulta e aceitação no SPS Grantley não foram demonstradas. O payload offline não foi transmitido.

## 6. ICCMOD — estruturas candidatas de thread e handlers

O módulo ICCMOD descomprimido começa no endereço analítico 0x200EF000 e tem 0x4000 bytes. A estrutura identificada em torno de 0x200F1848 tem DWORDs candidatos:

| Endereço | Valor observado no histórico | Interpretação |
|---|---|---|
| 0x200F1848 | 0x2 | tipo/flags desconhecidos |
| 0x200F184C | 0x200F1868 | ponteiro para nome IccWorkerThread |
| 0x200F1850 | 0x200F0EF0 | entry candidato |
| 0x200F1854 | 0 | desconhecido |
| 0x200F1858 | 0x200F3280 | ponteiro candidato |
| 0x200F185C | 0x400 | tamanho/atributo desconhecido |
| 0x200F1860 | 0x400 | tamanho/atributo desconhecido |
| 0x200F1864 | 1 | flag/atributo desconhecido |

Não há prova de que os valores 0x400 correspondam a tamanho de stack ou que o ponteiro seja um stack buffer.

### Tabela candidata de descritores de handlers

| Posição da tabela | Ponteiro | DWORD de tamanhos candidato | Campo seguinte |
|---|---|---|---|
| 0x200F18A8 | 0x200F09C4 | 0x00200020 | 1 |
| 0x200F1914 | 0x200F0A44 | 0x001C001C | 1 |
| 0x200F1920 | 0x200F0908 | 0x00280028 | 5 |
| 0x200F192C | 0x200F0C28 | 0x00180018 | 1 |
| 0x200F1938 | 0x200F0D14 | 0x043E001D | 1 |

Não atribuir significado definitivo aos tamanhos ou à tabela sem rastrear quem consome essa memória. Valores transcritos da análise anterior; revalidar diretamente nos bytes do raw quando necessário.

### Rotinas auxiliares

| Endereço | Observação estática |
|---|---|
| 0x200EF0D4 | validação de grupo/índice; códigos 0x1018/0x1019 |
| 0x200EF260 | leitura de registro auxiliar; grupo 0x7F especial |
| 0x200EF7EC–0x200EF9E0 | validação e escrita auxiliar |
| 0x200EFDE8 | operação mascarada sobre aux 0x12301 |
| 0x200EFE10 | rotina candidata relacionada a configuração |
| 0x200F0424 | tratamento de evento/mensagem e comparações 3, 0xC, 0xD, 0xE, 0xF |
| 0x200F07B0 | handler de evento |
| 0x200F0E5C | chamada candidata do loop de eventos sob condições |
| 0x200F0EF0 | loop de IccWorkerThread |
| 0x200EEAB0 / 0x200EEAC8 | serviços comuns chamados com IDs 0x1F e 0x3B |

O loop observa eventos associados aos IDs internos 0x1F/0x3B e tamanhos 12/8. Ainda não sabemos se são IDs de registros persistentes, mensagens internas ou outro serviço. A operação sobre aux 0x12301 não foi associada ao MOD3. A leitura do caso especial 0x12302 pode ter efeitos colaterais; não tratar toda rotina de consulta como passiva.

## 7. Próximas referências cruzadas

1. Confirmar tipos e offsets de políticas carregadas pelo PEI/DXE.
2. Identificar a interface PEI associada ao GUID de 0x6AEB.
3. Revalidar descritores e limites de função ARC, inclusive delay slots e literal pools.
4. Reconstruir registro do cliente ICC em HOSTCOMM e condicionais em POLICY.
5. Comparar IDs 0x1F/0x3B com estruturas MFSB/SCA/MFS.
6. Identificar onde a configuração inicial referencia modulador, divisor e frequência; não presumir que o aux 0x12301 seja MOD3.

**Conclusão:** temos um mapa de investigação de baixo nível, não uma especificação completa nem um procedimento de escrita BCLK. A próxima etapa continua dependente dos volumes persistentes e de validação de suas estruturas.
