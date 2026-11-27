# Etapa 13 — Serviços SPS, reconstrução de MFS e políticas de turbo

> **Auditoria posterior.** O valor bruto transcrito para MSR 0xCE implica bits 28–30 iguais a 1. As anotações históricas de zero foram revistas na [etapa 14](14-backends-icc-rapi-restricoes-turbo.md). A saída original da leitura ainda precisa ser recuperada.

Sessão offline de 26/11/2026. Continuação da [etapa 12](12-inventario-offline-sps-turbo.md) e da matriz da [etapa 11](11-etapa-atual-investigacao-bclk-icc.md). As evidências desta sessão são estáticas, exceto quando identificadas como medições históricas. Conferidos novamente os SHA-256 do dump SPI e da região SPS com o manifesto anterior. Os mapas JSON ficam em `~/backup-bios/sps-icc-research/`, junto às entradas locais.

## SPS-03 — Reconstrução diferencial de MFSB e MFS

**Hipótese e teste.** Em vez de procurar mais coincidências isoladas, interpretar `01 03 02 04` seguido de DWORD big-endian como marcador que representa uma sequência de `ff`. A hipótese seria refutada nesta amostra se algum marcador produzisse lacuna com dados, se os trechos literais subsequentes perdessem sincronismo ou se a expansão invadisse os limites do volume. O marcador também aparece no POLICY e o leitor foi localizado independentemente.

| Intervalo MFSB | Intervalo MFS | Observação |
|---|---|---|
| `[0x0b07, 0x1520)` | `[0x464d, 0x5066)` | Igualdade literal, deslocamento `+0x3b46` |
| `[0x1520, 0x1528)` | `[0x5066, 0x5070)` | `01 03 02 04 00 00 00 0a` representa dez bytes `ff` |
| `[0x1528, 0x1c3c)` | `[0x5070, 0x5784)` | Igualdade literal, deslocamento `+0x3b48` |

A expansão de 8 para 10 bytes explica a diferença de dois no deslocamento. O mesmo marcador em `MFSB+0x55d` carrega comprimento `0x3aa3` e avança até `MFS+0x4000`. Os trechos com deslocamento recorrente `0x4000` no MFS correspondem às páginas candidatas da etapa 12. A parte literal do cabeçalho inicial contém `MFS\0` em `+0x8` em ambas as imagens.

**Resultado reproduzido.** O prefixo MFSB `[0, 0x3ad8)` contém 94 marcadores de oito bytes e 95 intervalos literais. A expansão produz 231.456 bytes de lacunas verificadas, 14.312 bytes literais e uma cauda apagada de 16.376 bytes. O resultado de 256 KiB coincide com o MFS em todos os bytes, exceto `MFS+0xf`, que é `0x72` na partição MFS e `0x35` na cópia codificada. Os primeiros 15 bytes são idênticos, portanto um cálculo determinístico limitado a `[0, 0xf)` não explica sozinho essa divergência. O significado de `+0xf` e dos DWORDs do rodapé `MFSB+0xff08–0xff1b` segue em aberto. O corte em `0x3ad8` corresponde ao fim dos últimos bytes úteis observados antes do preenchimento dessa região e do rodapé. O script recebe esse corte explicitamente.

O mapa enumera todos os intervalos da reconstrução, incluindo a posição de cada marcador, a extensão da lacuna, o deslocamento acumulado, os cabeçalhos a cada 16 KiB, a posição da única divergência e a cauda do backup. As fronteiras entre literais e lacunas são do formato de compactação e podem cortar registros lógicos. A igualdade quase integral sustenta uma cópia recuperável dos dados da amostra, sem estabelecer a ordem temporal das operações nem o algoritmo de seleção usado em boot.

```bash
python3 scripts/mapas_sps.py volumes ../sps-icc-research/MFSB.bin \
  ../sps-icc-research/MFS.bin --payload-end 0x3ad8 > ../sps-icc-research/mapa-mfs.json
```

## SPS-04 — POLICY, interface de partição e leitores

**Origem do objeto.** O descritor de interface do POLICY, em VMA `0x200cc080`, lista a publicação de `0x102d → 0x200cc024` e a importação de `0x102f → &0x200deca4`, ao lado de `0x1016 → &0x200deca8` e `0x1050 → &0x200decac`. Em `0x200c9200`, o código entrega esse descritor e o contexto `0x200deca0` a `0x2009e018`. A importação é sustentada pelo contraste entre ponteiros para tabelas de código presentes e ponteiros para células que o código consome por desreferência. A célula `0x200deca4` não tem bytes inicializados nas LLUT locais. O corpo do resolvedor, o exportador de `0x102f` e o endereço final do slot `+0x24` ainda precisam de evidência.

**Identidade funcional do slot.** Em `0x200b2ffe/0x200b3000` o POLICY seleciona os nomes `MFSB` ou `MFS\0`, chama `[[0x200deca4]+0x24]` e retorna os campos do buffer `+0x30` e `+4` pelos ponteiros originalmente em r1 e r2. O terceiro, originalmente em r3, recebe `0x4000` quando o bit 2 do byte global `[0x200de9ac]` está ativo ou `0x10000` quando está limpo. Esse terceiro valor vem de um seletor do POLICY. A entrada `0x200c91ac`, listada na tabela exportada, encaminha os três ponteiros para `0x200b2fd0`.

| Campo | Consumidor encontrado | Interpretação |
|---|---|---|
| Buffer `+0x30` | Outro chamador do mesmo slot, `0x200b396e–0x200b3974`, grava em `0x200dea6c+0x20`. `0x200b39c8` repassa a `0x200ab6a4`, que soma a posição percorrida e lê o marcador em `0x200ab6ee). | Base endereçável do fluxo. O valor bruto em execução e a conversão para offset SPI ou SPS permanecem desconhecidos. |
| Buffer `+4` | `0x200b395e–0x200b3964` compara o campo de MFSB ao de MFS. `0x200b3984–0x200b3986` guarda o valor de MFSB e `0x200ab714–0x200ab71a` o usa como limite da varredura. | Comprimento em bytes para essa operação. A ordem observada na FPT, MFS 0x40000 > MFSB 0x10000, é coerente com o ramo que prepara a leitura da cópia compactada. A igualdade numérica em execução com o tamanho FPT continua pendente. |
| Buffer `+0x18`, `+0x1a`, `+0x1c` | `0x200b3d88–0x200b3dbe` e `0x200af078–0x200af08e` leem campos adicionais. | Há mais metadados na estrutura. A semântica deles permanece aberta. |

**Caminho do armazenamento.**

- `0x200b3900 → 0x200b39ce → 0x200ab6a4` percorre a base até o limite e monta uma tabela de checkpoints de oito bytes. `0x200ac18c` compara quatro bytes com o literal em `0x200cc018` (`01 03 02 04)). `0x200bbe30` lê os quatro bytes seguintes como inteiro big-endian. O laço avança a posição física em oito bytes na ocorrência do marcador e acumula o comprimento lógico. Isso sustenta a expansão observada no mapa.
- `0x200ae738` lê 16 bytes via `0x200b3aac`, exige byte `+1 = 0x78` e byte `+3 = 0xff`, e usa o DWORD `+4` com limite `0xfffff`. Os cabeçalhos de MFS e MFSB satisfazem as duas checagens de byte. `0x200ae93e` chama esse leitor. `0x200b38a8–0x200b38b2` distingue o caso `0x4000`. A estrutura final dos registros e a função do byte `+0xf` seguem sem nome.
- `0x200ae6c2–0x200ae6e4` combina componentes de offsets, limita cada iteração a 256 bytes e chama `0x200b3be0`. Em `0x200b3aac` a leitura pode seguir a tabela usada para a cópia compactada ou o slot `+4` da mesma interface. A busca chegou ao leitor de cabeçalhos e ao caminho de acesso a registros. A tabela exporta o wrapper, mas os consumidores externos que recebem os três DWORDs ficam atrás da ligação em runtime.

## ARC-02 — OPR1, lacunas de memória e serviços ICC

O mapa reproduzível contém os 13 descritores `$MME`, intervalos declarados, campos de entrada, segmentos presentes/vazios, extensão raw de BUP e todas as 1.760 páginas de cada LLUT. A partição OPR1 começa em `SPS+0x81000`. As LLUT estão em `OPR1+0x840` e `+0x2400`. O stream começa em `OPR1+0x3fc0`, com comprimento declarado `0xe0569`. A base virtual é `0x20040000` com páginas de `0x400`. As tabelas concordam em flags e VMA. Para os 1.288 itens presentes, o endereço codificado da segunda tabela é o da primeira mais `0x200000`. Os 472 itens restantes têm DWORD `0x80000000`, flag `0x40`, sem endereço de stream. As páginas presentes de cada módulo Huffman formam um intervalo contíguo. Os 13 dumps, incluindo BUP raw, conferem com os SHA-256 do manifesto após interpretar o campo de digest em ordem de bytes invertida.

```bash
python3 scripts/mapas_sps.py opr1 ../sps-region.bin > ../sps-icc-research/mapa-opr1.json
```

| Endereço ARC | Página | Índice LLUT | Resultado |
|---|---|---:|---|
| `0x2009d000` | `0x2009d000` | 372 | Vazia. Cabeçalho RAPI esperado pelo prolog do POLICY. |
| `0x2009e018` | `0x2009e000` | 376 | Vazia. Alvo do resolvedor chamado pelo POLICY. |
| `0x200deca4` | `0x200dec00` | 635 | Vazia. Célula de ponteiro declarada pelo consumidor. |
| `0x200ed000` | `0x200ed000` | 692 | Vazia. Cabeçalho RAPI esperado pelo prolog do ICCMOD. |
| `0x200eeab0`, `0x200eeac8` | `0x200ee800` | 698 | Vazia nas duas tabelas. Alvos separados por 24 bytes. |

A ausência em OPR1 explica por que a extração por módulo não recupera os alvos. Tanto `ICCMOD:0x200ef03c` como `POLICY:0x2009f03c` testam o DWORD ASCII `RAPI` e exigem WORD `+0xc == 5` na base declarada de cada módulo. O padrão favorece uma área preenchida durante a ligação, com stubs ou wrappers curtos como hipótese para os dois alvos. A separação de 24 bytes é compatível com stubs de tamanho fixo, sem provar tamanho ou conteúdo. Não encontrei ponteiros literais para os dois alvos em ordem little-endian ou ARC middle-endian nos dumps examinados. A BIOS mod de referência contém OPR1 idêntica à original. A referência C612RD24 tem layout distinto nesse offset SPI e não foi usada como substituta do mapa.

**Chamadores confirmados.** Desmontei os 14 dumps ARC locais (13 da OPR1 e o BUP adicional de FTPR), com o binutils ARC 2.46 e as bases dos arquivos. A procura por destinos revelou 11 chamadas diretas confirmadas, todas no ICCMOD. O candidato isolado em `POLICY+0x2fab2` é `bnv.d`, em dados desassemblados como instrução. A enumeração cobre chamadas diretas visíveis nos dumps. Ligações indiretas e páginas construídas em execução permanecem fora dessa cobertura.

| Chamada | Serviço | ID / tamanho | Fluxo de resultado ou buffer |
|---|---|---|---|
| `0x200f0934` | `0x200eeab0` | `0x203` / 2 | Requer retorno zero e bit 0 do WORD lido. |
| `0x200f0950` | `0x200eeab0` | `0x200` / 8 | Requer zero e compara os dois DWORDs com valores da requisição. |
| `0x200f09a2`, `0x200f0a22` | `0x200eeac8` | `0x1f` / 12 | Envia dados mais bit 0 do terceiro DWORD; o caminho segue sem testar o retorno. |
| `0x200f0af2` | `0x200eeac8` | `0x3b` / 8 | Envia valor aceito por `0x200efe10`, seguido de DWORD com bit 0 ativo; retorno não testado. |
| `0x200f0d68` | `0x200eeab0` | `0x5a` / 12 | Requer zero e usa o terceiro DWORD em checagem de comprimento. |
| `0x200f0e8a` | `0x200eeac8` | `0x36` / 12 | Envia buffer construído no stack; segue para método de outra interface. |
| `0x200f0f6c`, `0x200f0f94` | `0x200eeab0` | `0x1f` / 12, `0x3b` / 8 | Testa retorno zero e bit de validade, depois chama os respectivos consumidores. |
| `0x200f0fbc`, `0x200f0fd0` | `0x200eeac8` | `0x1f` / 12, `0x3b` / 8 | Envia buffers zerados no worker; retorno não testado. |

As assinaturas observadas são compatíveis com `get(id, buffer, tamanho)` e `set(id, tamanho, buffer)`. A leitura e gravação dos mesmos IDs, com bit de validade ligado no caminho de atualização e zerado no caminho de reset, consolidam a hipótese de uma interface comum de registros. A persistência de `0x1f` e `0x3b` e seu backend em MFS, MFSB, SCA ou RAM seguem em aberto. O próximo teste é rastrear no KERNEL/BUP ou em uma segunda imagem Grantley com OPR1 diferente a população dos cabeçalhos RAPI e a resolução das importações `0x102f` e dos serviços do ICCMOD.

## CPU-03 — Cadeias de política, PCD e MSR

**Semântica documentada.** Para DisplayFamily_DisplayModel `06_4f`, `MSR 0x1AC` é `MSR_TURBO_RATIO_LIMIT3`. Bit 63 seleciona a tabela alternativa de `0x1ad/0x1ae/0x1af`; zero seleciona a de fábrica. A escrita está documentada como disponível somente quando `MSR_PLATFORM_INFO[28]` vale 1. A nota da tabela torna o aumento acima do limite de fábrica dependente dos recursos do processador e da plataforma. [Intel SDM vol. 4, tabela 2-38](https://cdrdv2-public.intel.com/874253/335592-090-sdm-vol-4.pdf#page=361).

### Caminho que altera o valor apresentado por CpuMpDxe

1. `PlatformCpuPolicy:0x6d5–0x708` lê `IntelSetup` no buffer `rsp+0x80`, tamanho `0x17ec`. Em `0x10e0–0x1114` exige Turbo Mode em `IntelSetup+0xb4` e Extreme Edition em `+0x13fc` para trocar o valor inicial zero pelo WORD do primeiro ratio em `+0x16e7`. Os três nomes e offsets conferem no IFR. Publica o DWORD no token `0x25`, slot `+0x88` da interface PCD.
2. `CpuMpDxe:0xa87c` localiza o mesmo protocolo `11b34006-d85b-4d0a-a290-d5a571310ef7`, publicado por `PcdDxe:0x583`. A chamada `CpuMpDxe:0x1fe1–0x1ff5` lê o token via slot `+0x18` e grava o resultado no global `0xf340`.
3. `CpuMpDxe:0x60d8–0x6105` inicializa o campo de saída `+0x80` a partir do byte baixo de `0x1ad`. Se o PCD for não nulo, usa o byte baixo dele. O bloco observado só escreve na estrutura em memória. Confirma-se uma via para alterar o valor de ratio apresentado separadamente da programação de turbo.

### Caminho de PpmInitialize e ordem relativa

- `PpmInitialize:0xa90 → 0xc44 → 0x1874` prepara os dados antes de executar o caminho de programação em `0xd34 → 0x1158`. No construtor `0x1874`, aloca e zera um bloco de `0x3f` bytes em `[0x36c8]`; em `0x1b37` grava o ponteiro em `[0x3644]`, que corresponde a `contexto 0x3638 + 0xc`. Em `0x1aad–0x1ab3`, lê DWORD via protocolo CSR `0067835f-9a50-433a-8cbb-852078197814`, seletor `0x0a034094`, e em `0x1b68` grava o retorno integral em `bloco+0x25`. O fluxo de dados independe do token PCD `0x25`. Em `CpuCsrAccess:0x29cd`, o slot `+8` é ligado a `0x22ec`. Essa rotina lê um DWORD por MMCONFIG. O decodificador `0x21f4` separa grupo `0x0a`, índice `3`, largura `4` e offset `0x94`. Para esse grupo e argumentos de socket/controlador zero, `0x1321` seleciona device 30 nos perfis 0 e 2. Para o perfil 1, `0x1344` seleciona device 10. A tabela de função lida em `0x1cd4–0x1cfa` retorna 3 nos três perfis. O bus é resolvido em `0xb54` a partir da topologia no HOB. Device 30, função 3, offset `0x94` corresponde a CAPID4 do PCU na referência E5 v4. O datasheet não atribui nome ao bit 28 nessa tabela. O valor do DWORD no DXE da H9S permanece desconhecido. [Intel Xeon E5 v4 Datasheet, vol. 2, §5.4.6](https://www.intel.com/content/www/us/en/content-details/333810/intel-xeon-processor-e5-v4-family-volume-2-of-2-registers-datasheet.html).
- `PlatformCpuPolicy:0x68a` carrega `ebp=0xa3`; `0x6b8` calcula `0xa3-0x7a=0x29` e `0x6be → 0x14c8` publica o endereço do bloco pelo setter PCD de 64 bits (slot `+0x90`, implementação `PcdDxe:0x7d0`). `0x10b9` grava os 24 WORDs de ratio a partir de `bloco+0x65` (`0x60+5`), lendo `IntelSetup+0x16e7` em sequência. `PpmInitialize:0x1b17–0x1b2b` lê o **mesmo token 0x29** via slot `+0x20` (`PcdDxe:0x638`, leitura de 64 bits) e guarda o endereço em `contexto+0x14`. `0x2318` usa esse ponteiro, lê os mesmos 24 WORDs a partir de `+0x65` e constrói as tabelas. A base PCD independente confirma a distinção. Pela indexação de `PcdDxe:0x16b8/0xe90`, com oito tokens PEI nesta imagem, `0x29` tem descritor `0x08000231`, enquanto `0x25` tem `0x04000259`.
- O primeiro caminho de PPM chama `0x2318` em `0x1315`. Para modelo `0x4f`, `RDMSR` em `0x23fb` usa `ECX = 0x1ac`, calculado a partir dos índices anteriores. A rotina testa a metade alta inteira em `0x2408–0x240a`. Se zero, os gates de `0x244c` e `0x2454` ainda exigem PLATFORM_INFO[28] e bins de OC em `0x194[19:17]`. Só então é alcançável a construção e escrita das tabelas.
- O caminho diferido registra `0x1128` em `0xd90` e checa o protocolo `a25f2fcd-c168-4e77-ad3e-a488acb725ab` antes de `0xe00`. Em seguida usa `0x2bcc` como callback e também o chama diretamente em `0xe41`. Em `0x2be1–0x2bf5` testa tanto `MSR 0xce[28]` como o bit 28 do DWORD CSR armazenado na política. No modelo `0x4f`, lê `0x1ac` em `0x2c61`, seta o bit 63 e escreve em `0x2c8f`. O call graph estabelece a ordem dentro de cada caminho e o registro da fase diferida depois da chamada direta de `0x1158`. A ordem de execução entre processadores e eventos não foi medida.

### Cobertura e limites do teste

Verifiquei 274 seções PE/TE extraídas do dump original para candidatos com literal imediato de 32 bits `0x1ac` e bytes de `RDMSR/WRMSR` no mesmo módulo. A desassemblagem selecionou quatro ocorrências imediatas. `PpmInitialize:0x2c5c` é a única com acesso confirmado. `UncoreInitPeim:0xffe3fd2b` passa 0x1ac como comprimento a uma rotina com `rep stosb`. `RtkUndiDxe:0xdf75` e `Shell_Full:0xaa1d9` são argumentos de rotinas sem instrução MSR no ponto candidato. A outra leitura de PpmInitialize, em `0x23fb`, usa índice calculado e foi rastreada separadamente. A busca por literal pode omitir índices calculados em outros módulos ou funções genéricas chamadas indiretamente.

O desvio do firmware e a permissão arquitetural são evidências diferentes. Para a unidade estudada, a leitura histórica mostrou `0xce[28]=0` e `0x194[19:17]=0`, e o OC Mailbox recusou uma solicitação de 30x por outro caminho. Junto ao SDM, isso sustenta a restrição da via documentada de `0x1ac` sob as condições históricas. A sessão não mediu o estado desses registradores em DXE e não determinou a origem física da restrição. A cadeia de política explica onde os valores passam a ser apresentados e onde a tentativa de aplicá-los depende da CPU. O próximo teste offline é seguir a origem da variante de topologia escolhida por CpuCsrAccess e buscar diferenças nos gates em outras revisões compatíveis de PpmInitialize.

## Entregas e estado

O [script de mapas](../../scripts/mapas_sps.py) gerou `mapa-mfs.json` e `mapa-opr1.json` fora do repositório. Cinco testes sintéticos novos cobrem expansão, divergência literal, limites, lacuna não apagada e interpretação da LLUT. Os nove testes do repositório passaram com `python3 -m unittest discover -s tests -v`. Os dumps originais foram preservados. A sessão avançou no formato persistente e na distinção entre publicação de ratio e programação de turbo. O parâmetro ICC de BCLK, a alteração efetiva de ratio e a combinação dos dois continuam pendentes de evidência independente.
