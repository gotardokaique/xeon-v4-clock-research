# Etapa 15 — Produtores de configuração e parâmetros de turbo e ICC

Sessão offline de 26/11/2026. Continuação da [etapa 14](14-backends-icc-rapi-restricoes-turbo.md). Os endereços x86 e ARC são VMA das respectivas desassemblagens. Os intervalos de arquivos usam offsets locais com fim exclusivo. As conclusões abaixo são estáticas, salvo leituras históricas explicitamente identificadas.

## CPU-07 — Montagem, seleção e limites efetivos

A hipótese de que a seleção em `0x2bcc` exige sucesso prévio de `0x2318` foi refutada no caminho DXE do PpmInitialize original. O GUID de notificação `a25f2fcd-c168-4e77-ad3e-a488acb725ab` aparece em PpmInitialize e no Bds. Em Bds `0xe041–0xe053`, a referência é passada como argumento de instalação de protocolo. O callback em `0x1128` testa a existência do protocolo com LocateProtocol em `0x1141`.

```text
PpmInitialize 0xa90 → 0xc44 → 0x1874 (estrutura CSR e PCD)
  0xcfa → 0x14d8
  0xd2e → MP Services.StartupAllAPs(0x1158, SingleThread=1, contexto=0x3638)
  0xd34 → 0x1158 no BSP → 0x1315 → 0x2318
  0xd61 / 0xd67 → 0x1ec0 nos APs / BSP
  0xd90 CreateEvent → 0xdab RegisterProtocolNotify → 0xdbd SignalEvent
Bds 0xe053 → instala protocolo de notificação
PpmInitialize 0x1128 → LocateProtocol → 0x114c → 0xe00
  0xe3b → MP Services.StartupAllAPs(0x2bcc, SingleThread=1, contexto=0x3638)
  0xe41 → 0x2bcc no BSP
```

StartupAllAPs recebe evento de conclusão nulo e timeout zero nos dois despachos. A chamada local ocorre no BSP. Em `0x1158`, WhoAmI no slot MP `+0x30` identifica o processador lógico para o estado de replay. A distinção física é entre o processador lógico que executa e registra a instrução, os núcleos ativos que indexam a tabela, e o pacote dono dos limites de turbo. Os callbacks alcançam APs habilitados e o BSP e podem tentar programar o mesmo pacote mais de uma vez. A política CSR compartilhada foi lida para socket/controlador zero. O código observado não constrói uma política CSR independente para cada socket. O caminho de `0x2318` tem uma chamada direta em `0x1315`. `0x2bcc` é referenciado como callback em `0xe1b` e tem a chamada direta `0xe41`.

| Condição | Montagem 06_4f em `0x2318` | Seleção 06_4f em `0x2bcc` |
|---|---|---|
| `0x1ac[63:32]` na primeira leitura | Qualquer bit ativo sai por `0x240a` | Lê e preserva o valor, acrescentando bit 63 |
| `0xce[28]` | Exige 1 em `0x244c` | Exige 1 em `0x2be5` |
| `0x194[19:17]` | Exige valor diferente de zero em `0x2454` | Sem teste no caminho de seleção |
| `0x1ac[63]` na segunda leitura da montagem | Bit ativo entra no laço `0x26d3` sobre o DWORD salvo, sem nova leitura | Sem espera correspondente |
| CAPID4[28] | Sem teste direto neste construtor | Exige 1 em `0x2bf5` |
| Núcleos | `BL = (MSR 0x35 >> 16) & 0xff`. O laço percorre a contagem sem saturar a 24 | Sem teste |
| 24 WORDs de política | `0x26f8–0x270f` compara cada WORD dos slots 2 até a contagem ao primeiro. Um aumento local entre slots é aceito se ambos forem menores ou iguais ao primeiro | Sem teste |
| Zero e merge | Cada slot válido na trajetória de 14 núcleos substitui o byte correspondente somente se seu WORD for diferente de zero. Com todos zero, os três WRMSR de ratio podem ser emitidos com os valores relidos | Preserva os bytes de `0x1ad–0x1af` |

O código lê `0xce` e `0x194` antes dos testes em ambos os valores na montagem. Em `0x245a`, a comparação com 1 usa o resultado já mascarado por `0x10000000`. Depois que o teste de zero deixou passar, esse resultado só pode ser `0x10000000`. O ramo `0x2464–0x260e` que tentaria limitar WORDs ao ratio nominal mais os bins fica inalcançável pelo fluxo observado. A checagem de ordenação ainda vale. Em contagem superior a 24 o laço pode ultrapassar a matriz se as comparações anteriores passarem. Para contagens maiores que a da H9S, o empacotamento também exige análise própria. Em `0x29fb–0x2b01` há testes de um WORD seguidos do uso do anterior e deslocamentos de oito bits com máscaras que limpam outros bytes.

**Fonte de valores.** `IntelSetup+0x16e7` inicia a sequência de WORDs, publicada por PlatformCpuPolicy no PCD `0x29` e consumida em `[contexto+0x14]+0x65`. IFR descreve limites de 0 a 255 e defaults zero. Os bins preservados vêm das leituras `0x236c`, `0x2384` e `0x23e8` de `0x1ad`, `0x1ae` e `0x1af`, respectivamente. Em 14 núcleos os campos afetáveis são os oito bytes de `0x1ad` e os seis primeiros de `0x1ae`. `0x1af` mantém seu valor lido e ainda recebe uma tentativa de escrita. Quando o primeiro WORD e a contagem são diferentes de zero, há também o ramo `0x2730–0x27bb` com leitura de `0x194`, limpeza condicional do bit 20 e merge do DWORD de política `+0x61`. Esse efeito é separado do empacotamento dos ratios.

**Semântica arquitetural.** A tabela 2-38 descreve a configuração de fábrica com `0x1ac[63]=0` e a alternativa com bit 63 ativo. A disponibilidade de escrita de `0x1ac` depende de `0xce[28]`. O aumento acima do limite de fábrica depende da CPU e da plataforma. A configuração esperada sem seleção alternativa é a de fábrica do SKU. A referência local não fornece uma imagem de reset com os QWORDs deste exemplar. O caderno [EXP-02](01-plataforma-cpu-msr.md) tem apenas leituras pós-boot. `0x1ad=0x1d1d1d1d1e1f2121` e `0x1ae=0x1af=0x1d1d1d1d1d1d1d1d`. O ratio solicitado em `0x199` era 33x e o observado em `0x198` sob carga era 29x. O valor histórico de `0xce` tem bit 28 ativo pela reanálise na etapa 14, enquanto `0x194[19:17]` foi transcrito como zero. O primeiro gate não implica que o segundo passou. [Intel SDM, vol. 4, tabela 2-38, referência da etapa 13](https://cdrdv2-public.intel.com/874253/335592-090-sdm-vol-4.pdf#page=361).

**Consequência estática.** Se a montagem sair e a seleção passar, o firmware tenta selecionar os bins já presentes. Se os bancos ainda contiverem seus valores de fábrica, a seleção por si só não produz um novo ratio. Uma escrita prevista pela desassemblagem, o valor que a CPU preserva depois da escrita, e a frequência efetiva sob carga são três observações independentes.

## CPU-08 — Produtor PEI da topologia e CAPIDs

Hipótese verificada seguindo referências RIP, o campo de comprimento `0x16b4` e a remontagem do GUID a partir de imediatos. A busca contígua pelo GUID DXE encontrava consumidores. A busca pelo uso do argumento RDX de InstallMultipleProtocolInterfaces revelou **PlatformType `0x1e5c–0x1e7f`** como instalador. O GUID DXE aponta para um wrapper cujo primeiro QWORD aponta para a cópia do HOB.

```text
UncoreInitPeim 0xffe074b5 → CPUID folha 1 via 0xffe0e417 → estado PEI
  0xffe77570 / 0xffe778c2–0xffe778f2 → payload de 0x16b4 em [EBP-0x1714]
  0xffe77a69 → 0xffe073ef → 0xffe073ba → HOB tipo 4, payload +0x18
  HOB 7ff396a1-ee7d-431e-ba53-8fca127c44c0
PlatformType 0x136d → 0x1f90 (localiza lista de HOBs)
  0x15da–0x1627 forma GUID em imediatos, 0x1dba–0x1df7 caminha a lista
  0x1e00–0x1e2a aloca e copia 0x16b4 bytes
  0x1e40–0x1e7f instala a7ced760-c71c-4e1a-acb1-89604d5216cb
CpuCsrAccess 0x298b → desreferência em 0x29ae → leitura dos campos
```

| Offset no payload | Produtor UncoreInitPeim | Uso em CpuCsrAccess |
|---|---|---|
| `+0x1676` | `0xffe778bc/0xffe778c2` copia `[estado+0x220d4]`. `0xffe07502–0xffe07541` compara `CPUID.1:EAX >> 4`: `0x306f → 0`, `0x406f/0x5066 → 2`, demais → 1 | `0x2a32` guarda perfil. Para CPUID 0x406f1, segue o perfil 2 e o ramo de device 30 |
| `+0x1677` | `0xffe778c8/0xffe778ce` copia `[estado+0x220d5]`. `0xffe07749–0xffe077b5` usa um discriminante lido anteriormente, atribuindo 0/1 nos ramos observados | `0x2a48` guarda o discriminante secundário |
| `+0x167e` | `0xffe778ec/0xffe778f2` copia `[estado+0x220fc]`. Em `0xffe075a1–0xffe075ec` a máscara inicial é `1 << socket`, com socket formado dos bits [1:0] e 3 do DWORD lido via CF8/CFC. `0xffe3e794` também pode atualizar a máscara | `0x2a5e` e `0xb67` consultam presença por socket |
| `+0x10a2` | `0xffe77570` copia `[esi+0x81]`, preenchido em `0xffe773e3` pelo helper `0xffe0c17b(…,0)`. Para 06_4f lê a seleção CF8 `0x80002890` e mascara CFC com `0xfc000000` | `0x2ae5` lê o DWORD da base MMCONFIG. CpuMpDxe `0x2424` soma o QWORD iniciado no mesmo offset |

Para grupo `0x0a`, CpuCsrAccess `0xb54 → 0xc34` usa `payload+0xfdf+0x16×socket`. UncoreInitPeim `0xffe77626–0xffe7762c` copia para esse offset `estado+0x2275f+socket`. O byte recebe o bus derivado de `MSR 0x300[15:8]` em `0xffe07571–0xffe07616` para o socket inicial. O ramo `0xffe3e7aa–0xffe3e7f2` lê o seletor `0x0802404c` e calcula outro candidato de bus como `32 × (1 + ((DWORD >> (3 × índice)) & 7)) - 1`. Há ainda escritas de `0x3f` em outros ramos. O histórico de `MSR 0x300=0x8000ff00` e a enumeração de funções vizinhas em bus `ff` sustentam **`ff:1e.3`** como candidato para a H9S. Faltam os bytes do HOB da inicialização observada e uma identificação de `ff:1e.3` com CAPID4/5 no mesmo estado.

`0x0a034094` e `0x0a034098` são seletores literais no PpmInitialize, com unidade `0x0a`, índice 3, acesso de 4 bytes e offsets de configuração `0x94` e `0x98`. A mesma codificação aparece no PEI para os seletores vizinhos `0x0a034084/88` em `0xffe0762a/0xffe0763a`. CAPID4 vai inteiro para `[contexto+0xc]+0x25`. CAPID5 fornece o campo baixo de 24 bits em `0x1abf–0x1acc`. Seus bits 26 e 25 têm gates separados em `0x1e2d/0x1e93`. O bit 26 desvia um RMW de `0xe2`. As referências a CAPID5 em `0x139c` e `0x140d` são releituras do mesmo CSR. Os campos adjacentes fazem parte da mesma família de registradores de capacidade do PCU. [Intel Xeon E5 v4 Datasheet, vol. 2, §5.4.6–5.4.7](https://www.intel.com/content/www/us/en/content-details/333810/intel-xeon-processor-e5-v4-family-volume-2-of-2-registers-datasheet.html).

| Consumidor CAPID4[28] | Efeito observado em PpmInitialize |
|---|---|
| `0x12a7` | Controla o merge do DWORD da política `+0x1a` no QWORD de `MSR 0x601`. Limpo, permite desse campo apenas o bit 31 nesse OR. Ativo, usa o DWORD todo. A lógica posterior de bits 12:0 também depende de outra flag. Escrita em `0x12ed`. |
| `0x1f9b` | Se limpo, força bit 31 antes de escrever no CSR `0x0a0040ec` via slot `+0x10` em `0x1fb5`. |
| `0x2223` | Se limpo, força bit 31 de `MSR 0x601` antes de `0x223f` e registra o QWORD para S3. |
| `0x2bef` | Gate de seleção alternativa descrito em CPU-07. |
| `0x3038` | Ativo, recalcula o produto WORD combinado ao campo de potência baixo de `MSR 0x610`, escrito em `0x31cf`. |
| `0x3169` | Ativo e operando `SI > R14W`, recalcula o produto usado no DWORD alto do mesmo MSR. |
| `0x3309` | Ativo, refaz o produto usando `[contexto+0xc]+0x21` como escala para o CSR `0x0a0040e8`, escrito em `0x34d3`. |
| `0x3456` | Ativo e operando `R10W > R14W`, usa a escala `+0x21` no produto levado ao CSR `0x0a0040ec`, escrito em `0x34e6`. |

Os caminhos de potência eliminam a interpretação do bit como seletor exclusivo de OC. O nome do bit e a origem física do valor permanecem abertos.

## CPU-09 — Replay S3 e microcode

CpuMpDxe `0x1f0b–0x1f2d` cria duas áreas de `N×0x20` bytes a partir da contagem de processadores e guarda os ponteiros em `0x12ee8` e `0x12ee0`. Cada vetor utiliza descritores de 24 bytes. Parte da área adicional de `0x12ee8` guarda índices de CPU em `0x12ef0`. CpuMpDxe publica `&0x12ec0` no PCD `0x17` em `0x1f7e`. Seu layout dá acesso a `0x12ee0` em `+0x20` e a `0x12ee8` em `+0x28`. A função `0x7314` de CpuMpDxe escolhe o vetor pelo argumento CL e indexa o descritor por CPU. O PpmInitialize usa o vetor `+0x28` para anexar as entradas de tipo 0, largura 64, pela cadeia `0x1d8c → 0x1c68`. `0x21ab–0x21b6` copia o APIC para `descritor+0xc` no vetor `0x12ee0`.

O bloco de intercâmbio de S3 é produzido em CpuMpDxe `0x2618`, que aloca `0x78` bytes, guarda o ponteiro em `0x12e98` e publica-o no PCD `0x1c` em `0x2712–0x271c`. Seus campos `+0x38` e `+0x40` recebem `0x12ee0` e `0x12ee8`, nessa ordem. PiSmmCpuDxeSmm lê `0x1c` em `0x2758` e usa `0x256c` para copiar descritores e cada lista de operações para `0xa538` e `0xa540`, a partir de `0x2817–0x2855`. Os dois snapshots representam vetores preenchidos em DXE com listas distintas.

O interpretador `0x3194` percorre as entradas do descritor em ordem. O caminho com assinatura `SMMS3_64` usa primeiro o vetor `0xa538` por `0x3528 → 0x3572` para o BSP. Há despacho do mesmo vetor para APs via `0x343c`. Após passos de preparação, `0x2461–0x249b` seleciona o vetor `0xa540` no BSP e `0x24c0` instala o callback AP `0x349c`. Esse segundo callback ajusta `0x350[16]` e `0x360[16]` antes do replay. O índice lógico é reobtido comparando o APIC atual com `descritor+0xc`. Se o APIC não for encontrado ou a lista estiver vazia, o respectivo conjunto de entradas é omitido.

Quando as quatro operações de turbo foram registradas para o mesmo APIC, o vetor do PPM em `0xa540` solicita `0x1ad → 0x1ae → 0x1af → 0x1ac`. Os pontos de registro são `0x2b51`, `0x2b6c`, `0x2bb2` e `0x2ca2`. Há uma diferença de atribuição. `0x1158` atualiza `contexto+0x1c` por WhoAmI em `0x1188`. `0x2bcc` usa esse campo em `0x2c94` sem atualizá-lo. Pelo fluxo compartilhado e sequencial, a seleção despachada a APs pode registrar no descritor deixado pelo último callback `0x1158`, normalmente o BSP em `0xd34`. O callback `0xdc8` atualiza novamente o índice por CPU, porém só é despachado depois da seleção, em `0xe6e/0xe74`. O replay pode conter apenas o seletor se a montagem tiver saído antes. `0x3346–0x335a` reproduz valores de 64 bits e não recalcula os gates do PPM. A execução concreta de S3 e a aceitação pelo hardware da H9S permanecem sem observação nesta etapa.

| Fonte | Revisão / data | Assinatura / máscara | Dados / bloco | Checksum do header |
|---|---|---|---|---|
| SPI original `+0xeac180`, mesma revisão nas referências da etapa 12 | `0x0b000038`, 18/06/2019 | `0x406f1 / 0xef` | `0x77d0 / 0x7800` | `0xe705e458` |
| `/lib/firmware/intel-ucode/06-4f-01.initramfs` | `0x0b000040`, 19/05/2021 | `0x406f1 / 0xef` | `0x8bd0 / 0x8c00` | `0xe5babfdb` |

A leitura dos 12 DWORDs mostrou versão de cabeçalho e loader 1, três DWORDs reservados zerados, ausência de uma tabela de assinaturas estendidas após os dados declarados e soma modular zero em cada bloco. O aumento dos dados foi `0x1400` bytes. A estrutura externa, o checksum e a assinatura estabeleceram a compatibilidade de identificação. O conteúdo opaco dos dados não sustentou associação a um comando turbo, a CAPID4 ou ao PCU.

## SPS-06 — MFS, MFSB e SCA

A hipótese de diretório foi testada com um layout LE de 11 bytes e uma comparação por chave, comprimento e conteúdo. As 123 entradas começam em MFS e MFSB `+0x14`. O limite calculado é `+0x55d` em ambos. MFSB tem nesse ponto o marcador `01 03 02 04 00 00 3a a3` e MFS tem preenchimento até `+0x4000`, conforme a expansão da etapa 13.

| Offset | Largura | Resultado na amostra |
|---|---|---|
| `+0` | WORD | `0xf0dc` em 123/123. Marcador de registro candidato |
| `+2` | DWORD | 123 chaves únicas. Duas correspondências com SCA por chave e tamanho verificados em conteúdo |
| `+6` | WORD | Comprimento confirmado nas duas correspondências. Valores não nulos totalizam 12.424 bytes, máximo `0xa24` |
| `+8` | byte | 1 em todas. Função pendente |
| `+9` | byte | 31 grupos em ordem crescente, com lacunas. Mínimo 0, máximo 36 |
| `+10` | byte | Índice interno candidato 0–8. Histograma de 0 a 8: `8,30,25,20,18,12,6,3,1`. Todos os pares `(+9,+10)` são únicos |

A chave `0x0a534b55`, índice 0 e grupo/slot 0/0, tem quatro bytes de payload SCA a partir de `+0x48`, iguais à única ocorrência em MFS `+0x40d2`. A chave `0x0a4f4350`, índice 9 e grupo/slot 6/1, tem `0xa24` bytes de payload a partir de SCA `+0x78`. A busca contígua retorna zero. Uma comparação diferencial encontrou a seguinte reconstrução exata.

| Trecho relativo ao payload SCA | Offset MFS |
|---|---|
| `[0,0xca)` | `[0x4635,0x46ff)` |
| `[0xca,0x9c6)` | `[0x4704,0x5000)` |
| `[0x9c6,0xa24)` | `[0x5002,0x5060)` |

Os bytes interpostos são `00 b0 09 01 08` na primeira quebra e `80 60` na segunda. Na segunda, `0x60` coincide com a soma de dois bytes interpostos e `0x5e` bytes restantes. Essa relação é candidata a comprimento de fragmento. A primeira quebra precisa de outra regra. O grupo 6 começa em uma zona `0x46xx`, porém as entradas seguintes têm grupos 8 e 10 enquanto o payload 6/1 atravessa `0x4800–0x5000`. Isso invalida usar diretamente o byte de grupo como endereço de página exclusivo de cada registro. A comparação comprova uma representação comum para os dois conteúdos. Origem, direção da cópia, recuperação de slots e função dos bytes interpostos requerem um leitor correspondente. Nenhuma chave de diretório é 0x1f ou 0x3b. Uma tradução ou namespace intermediário continua possível.

A auditoria de `ADD +11` no POLICY encontrou `0x200bc516/0x200bc874`, que passa `registro+11` como ponteiro enquanto lê bytes `+7/+8` e `+9/+10`. `0x200bcf70` lê bytes depois de `+11`. Esses acessos não demonstram um cursor com passo 11, nem a verificação de `0xf0dc` seguida dos campos identificados. As rotinas de página do POLICY da etapa 13 continuam sendo a ligação observada com endereçamento dos volumes. O decodificador lógico completo permanece pendente.

MFS tem duas páginas de 16 KiB com corpo ocupado em `+0` e `+0x4000`, com 1.364 e 12.503 bytes diferentes de FF. As 14 restantes conservam apenas cinco bytes diferentes de FF em cada cabeçalho `ff 78 ff ff 00 00 00 00`, com o corpo apagado. As duas primeiras começam com `00 78 fe ff` e `01 78 fe ff`. Isso é compatível com diferença de estado e ordenação. O DWORD `+4` vale zero nas 16 páginas, portanto não distingue as ocupadas. A diferença em `MFS+0xf` permanece `0x72` frente a `0x35` em MFSB, mesmo com os primeiros 15 bytes iguais. O rodapé MFSB `[0xff08,0xff1c)` mantém os DWORDs `0,0xa,0xa,0xa,0xa`. A sessão não encontrou instrução associando-o a tamanho, contagem ou checksum. Sem um intervalo candidato sustentado por leitura, o teste de checksum fica restrito ao mecanismo documentado em SCA pela etapa 14.

### Validador do registro 0x0a4f4350

KERNEL `0x2005b078` chama `0x20051438` com `r3=2`, descritor em r0, buffer em r1 e um argumento não nulo exigido em r2. O segundo ponto em `0x2005b0f4` usa `r3=3` e r2 zero. A função guarda o descritor em r19 e o payload em r20. Antes do despacho, chama os slots `+0x40` e `+0x18` do objeto de serviço com o ID e campos do descritor. `[r19+8]` fornece o comprimento em bytes. O braço `0x20052ac8 → 0x20053b2a` exige pelo menos `0xa24`; comprimento insuficiente leva ao estado 3 em `0x20055bb2`.

O mapa gerado registra **649 leituras DWORD** dos offsets `0,4,…,0xa20`, entre `0x20053b38` e `0x20055456`. Inclui `ld`, `ld_s` e `ld.as`. `r1 = r20 + 0x7fc` em `0x20054540–0x20054542` permite alcançá-los com deslocamentos sinalizados e escalados. Cada DWORD é comparado sem sinal com `0xffffffff`. Por construção esse máximo não rejeita um DWORD. Checado o último campo, o braço entra em `0x20057768` com status zero. Essa junção pode anexar o **ID** a um vetor em r24 e chamar o slot `+0x44` com o descritor. O braço PCO não grava campos do payload. O contraste com outros braços que aplicam limites a campos menores explica por que este validador isolado não revela subestruturas, versão, contagens, máscaras ou destinos físicos. O backend dos slots é a próxima ligação necessária para encontrar consumidores semânticos em RAM.

| Offset SCA | ID | Comparação e braço KERNEL |
|---|---|---|
| `0x40` | `0x0a534b55` | `0x200530a8 → 0x200538a2` |
| `0x4c` | `0x10424d43` | `0x20053568 → 0x20053a6e` |
| `0x58` | `0x10455243` | `0x2005360c → 0x20057766` (saída de status) |
| `0x64` | `0x10535349` | `0x2005371e → 0x20053b0a` |
| `0x70` | `0x0a4f4350` | `0x20052ac8 → 0x20053b2a` |
| `0xa9c` | `0x104f4943` | `0x200536f2 → 0x2005551e` |
| `0xab0` | `0x0b534d54` | `0x20053112 → 0x2005558c`. O braço exige pelo menos cinco bytes, mas o registro externo tem quatro. Falta verificar se o objeto interno acrescenta bytes ou registra falha. |
| `0xabc` | `0xffffffff` | Terminador do volume SCA |

O payload PCO de `0xa24` bytes também é curto para conter diretamente o DWORD `+0xb70` da estrutura RAPI. Uma cópia parcial, uma transformação ou uma tabela agregada ainda poderia ligá-los. Nenhuma dessas operações foi identificada neste caminho.

## SPS-07 — KAPI, RAPI e importação do POLICY

O teste de passo 12 cruzou o cabeçalho KAPI, o body bruto, o opcode de carregamento em r8 e o destino de branch em cada template. O offset-base dos stubs é `+0x18`. Os alvos do ICCMOD correspondem a slots 226 e 228, com alternância de classe no slot 227. Os limites declarados em `+8` são `0x20041fd8` e `0x20044fd8`.

| Alias observado | LLUT | Offset na janela | Stub candidato no primeiro template | Segundo template | Seletor nas duas variantes |
|---|---:|---|---|---|---|
| `0x200eeab0` | 698 | `0xab0` | `0x20041ab0` | `0x20044ab0` | `0x601c4 / 0x701c4` |
| `0x200eeabc` | 698 | `0xabc` | `0x20041abc` | `0x20044abc` | `0x401c4 / 0x501c4` |
| `0x200eeac8` | 698 | `0xac8` | `0x20041ac8` | `0x20044ac8` | `0x601c8 / 0x701c8` |
| `0x2009e018` | 376 | `0x18` | `0x20041018` | `0x20044018` | `0x60000 / 0x70000` |
| `0x200ee018` | 696 | `0x18` | `0x20041018` | `0x20044018` | `0x60000 / 0x70000` |
| `0x200edcdc` | 695 | `0xcdc` | janela RAPI | janela RAPI | outra família de stubs |

Nos quatro offsets da tabela, a primeira variante segue pelo salto em `0x20041010 → 0x20089260` e a segunda por `0x20044010 → 0x20044fd8`. Os seletores candidatos `0x60000/1c4/1c8` entram na classe com bit 18 ativo, usam o limite baixo `0x29c` e a tabela global de `[0x2008ed14]` em `0x200892e4–0x20089304`. A classe intercalada com bit 18 limpo passa pela checagem do objeto `[r0]` em `0x200892a4–0x200892cc`, com limite `0x1c8` e validação contra a tabela de `[0x20095280]`. O ponteiro de tabela final nesse ramo vem de `[r0-4]+4` em `0x200892f4–0x20089304`. O segundo dispatcher usa diretamente `[[0x2008ed14]+(r8 & 0xffff)]`. O passo, a classe e os offsets `0/0x1c4/0x1c8` ficam demonstrados **nos templates**. O slot adjacente é uma referência para comparação, sem chamador ICCMOD demonstrado.

O seletor de template está em KERNEL `0x2004d8c4–0x2004d8f2`. O código combina os bytes do descritor `r13+0x52/+0x53` e testa bit 0. Seleciona `0x20044000` se ativo ou `0x20041000` se limpo, lê base e limite do cabeçalho, guarda a base via `[0x200404f0]` e o tamanho limite menos base via `[0x200404f4]`. A rotina é alcançada por `0x2004ce16/0x2004cf9c/0x2004dba2`. Logo após a seleção, `0x2004d8fe` chama o serviço `0x20040070`. A materialização dos aliases e o valor efetivo do bit nos descritores dos módulos ainda dependem de resolver esse serviço ou os objetos em RAM.

No código desassemblado de KERNEL/BUP/POLICY, as referências absolutas a `0x2008ed14` são as duas leituras de dispatcher e a de `0x20095280` é a leitura de validação. O mapa classifica ambas as células como estado de execução do KERNEL, nas LLUT 315 e 340, sem streams. A origem das tabelas e os endereços finais dos stubs GET/SET continuam pendentes. A busca absoluta em LE e na ordem dos imediatos ARC não cobre inicialização por bloco ou endereçamento derivado. O POLICY entrega seu descritor ao slot zero em `0x200c9200 → 0x2009e018`. O ICCMOD usa o slot zero do seu alias em `0x200f1224 → 0x200ee018`, também com dois endereços de estrutura como argumentos em r0 e r1. O desenho é compatível com serviços comuns entre módulos. Ainda falta demonstrar que o GET/SET por ID compartilha backend persistente.

A busca de pares de DWORDs LE `ID → ponteiro` em todos os módulos ARC extraídos distinguiu células de importação em RAM de tabelas com ponteiros de código na imagem. Para `0x102f`, a importação `0x200cc0a0 → &0x200deca4` e a exportação `0x200ca014 → 0x200c9fd0` estão no próprio POLICY. O slot `+0x24` da exportação resolve para `0x200bb9b8`. Recebe o nome em r1 e o destino em r2. `0x200bb93c` procura o DWORD do nome em `descritor+8` na lista de `0x200d8504`, com iteração por `0x200abcac/0x200abcf4`. `0x200bb9b8` devolve `[saída+4] = [descritor+0x14]` e `[saída+0x30] = [descritor+0x10] + 0x400000`. A rotina confirma que a segunda saída é um endereço ajustado por uma base de firmware. A primeira já é usada em comparações de comprimento pelos consumidores da etapa 13. A lista de descritores é estado de execução. A relação numérica exata entre seus offsets e os offsets SPI da FPT precisa de um produtor ou captura dessa lista.

Em `0x200b3b54–0x200b3b62` e `0x200b3b8e–0x200b3ba0`, o POLICY usa `0x200deca4` e o slot `+4 → 0x200bbb3c` para ler fora do cache de 256 bytes. O callee verifica o offset mais o tamanho contra `[descritor+0x14]` e soma o offset à base `[descritor+0x28]`. O helper `0x200bbb98` chama `[[0x200d7bdc]+0x10]`, com mais um ajuste de base em `0x200bbbae`. `0x200ca024` identifica `0x1033 → &0x200d7bdc` como outra importação do mesmo descritor POLICY. O par de exportação `0x200ca088 → 0x200ca04c` leva o slot `+0x10` a `0x200c58dc`. A função empacota uma operação de tipo 0 com endereço, comprimento e ponteiro de destino no descritor de 16 bytes passado a `0x200c53dc`. O backend de leitura de partição passa por dois serviços resolvidos dentro do POLICY. A associação a um cursor de entradas de 11 bytes continua aberta.

## ICC-06 — Contexto compartilhado, descritores e destino das operações

O helper equivalente em cada BUP chama RAPI no mesmo offset de janela `+0xcdc`, em ICCMOD `0x200ef7f0 → 0x200edcdc`, BUP OPR1 `0x2020409c → 0x201f7cdc` e BUP FTPR `0x20312ad4 → 0x202ffcdc`. As âncoras `0x200ef964 / 0x20204212 / 0x20312c4a` têm 29 bytes contíguos idênticos centrados na leitura `r16+0xb70`. Isso reforça uma interface e layout compartilhados. O tamanho mínimo do contexto acessado nesse caminho é `0xb74`. O produtor do ponteiro RAPI e o escritor da máscara continuam sem resolução. A comparação cobre a janela local de leitura.

Outro caminho de inicialização em ICCMOD `0x200f11b8` recebe um descritor em r2. Em `0x200f11fa–0x200f1210` deriva um ponteiro com `+0x44` a partir de `[r2+4]` e lê um DWORD no offset `+0xa24` desse ponteiro. Os resultados vão ao estado local `0x200f3000+0x58/0x5c/0x60`. O valor `0xa24` coincide com o comprimento PCO, porém aqui é deslocamento de leitura após a base derivada. Para estabelecer uma ligação é necessário identificar o produtor do descritor e o intervalo de origem. O mesmo prólogo usa três ponteiros diferentes e o fato de compartilhar esse imediato não identifica o registro.

O consumidor de 0x3b em `0x200efe10` usa outro getter RAPI, `0x200edcec`, e transforma os dois primeiros DWORDs relevantes no fluxo da etapa 14. No empacotamento observado, cada descritor usa um par de bits para estado e um terceiro bit para omitir aplicação. Os grupos variam de 2 a 9 e o subíndice é 3. O seletor usa grupo nos bits [14:8] e subíndice nos bits [7:2], com bit 15 limpo e bits [1:0] preservados. O índice do comando derivado em `0x200efa18–0x200efa24` é `(grupo<<8)+4×subíndice`.

| Descritor | Grupo | Seletor com bits [1:0] zero | Entrada de autorização no contexto |
|---:|---:|---|---|
| 0 | 2 | `0x020c` | `+0xa4c` |
| 1 | 3 | `0x030c` | `+0xa54` |
| 2 | 4 | `0x040c` | `+0xa5c` |
| 3 | 5 | `0x050c` | `+0xa64` |
| 4 | 6 | `0x060c` | `+0xa6c` |
| 5 | 7 | `0x070c` | `+0xa74` |
| 6 | 8 | `0x080c` | `+0xa7c` |
| 7 | 9 | `0x090c` | `+0xa84` |

Em `0x200f0048–0x200f00ba`, a primeira passagem ignora descritores com bit 3 ou 0 ativo e encaminha o estado dos bits [2:1] com operação 4. A segunda passagem em `0x200f00c4–0x200f0154` ignora bit 3 ativo, lê estado em `0x200ef260`, combina os bits de estado e envia a operação 7. Ambos os laços terminam na primeira falha. `0x200ef7ec` exige contexto não nulo, operação 0–7 e validação do seletor com `0x200ef0d4` e a tabela em contexto `+0xa8c`. Para grupos 2–9 e subíndice 3, `0x200ef910–0x200ef94a` passa o DWORD de dados e a entrada de oito bytes a `0x200ef398`. Ali, o bit 26 da entrada decide se o valor baixo é comparado ao estado lido ou autorizado por flags 29/28/27 para os estados 0/1/2. O erro de autorização usa `0x100e+grupo`.

O despacho de operação 7 também ativa o caminho `0x200efa0c → 0x200ef6fc` para esses grupos/subíndice. Essa função combina o estado com bit 3 e usa `0x200f1004`. A operação 4, depois dos gates, pode chegar a `0x200f1004` por `0x200efa24`. O helper monta pedido com `0xed` e índice do grupo/subíndice e chama a interface de `[0x200f304c]`, slot `+0xc`, em `0x200f102c`. O par em `0x200f0eac–0x200f0ed4` usa o slot `+8` do mesmo objeto. `0x200f304c` é célula de importação no descritor ICCMOD `0x200f2000`, com par `0x1057 → &0x200f304c` em `0x200f202c/0x200f2030`. O prólogo `0x200ef020–0x200ef028` passa o descritor e a base do estado local `0x200f3000` a RAPI `0x200ede64` após inicializar a faixa de dados em `0x200f11d0–0x200f11dc`.

O KERNEL exporta `0x1057 → 0x200659a0` em `0x200659c4`. A tabela tem código local nos slots `+8 → 0x2004c3b8` e `+0xc → 0x2004c548`. Ambos transformam os argumentos e passam `0xed` como byte inicial a `0x2004c244`. O argumento `r2=6` do ICCMOD vira a modalidade em r1 dessa validação, associada ao bit 5 no teste de máscara. A largura `4` participa da validação de intervalo. A lista bruta a partir de `0x20065994+0x40` inclui `0xed` como um dos seletores. Os dois caminhos passam adiante por `[0x2008eff0+0x1c]` e `[0x2008eff0+0x20]` em `0x2004c43e–0x2004c44e` e `0x2004c5c8–0x2004c5d8`. Os slots ficam em estado de execução do KERNEL, LLUT 316, sem stream. Os oito descritores seguem esse encaminhamento de serviço. O acesso direto de AUX em `0x200ef9d8` é reservado aos grupos 126/127.

A entrada do KERNEL em `0x20042000 → 0x200420c4` preserva o terceiro argumento em r15. `0x200421ac–0x200421b8` entrega `0x2008eff0` como destino, r15 como fonte e `0x1458` como ambos os limites ao RAPI `0x20040e64`, cujo padrão de uso é cópia com limites. A análise diferencial encontrou blocos do mesmo tamanho no BUP OPR1 `0x2020a000` e FTPR `0x2031d6cc`. O OPR1 copia para o seu bloco em `0x201fccc2` ou o inicializa em `0x201fcd16`. O FTPR inicializa seu bloco em `0x203063b6` e o passa para `0x2030805c` em `0x20306614`. O comprimento comum fornece um alvo para reconstruir a transferência de boot. O produtor de `r15+0x1c/+0x20` na chamada efetiva ao KERNEL ainda precisa ser identificado.

O ramo direto preserva a equação de autorização `((old XOR requested) & ~allowed) == 0` para grupo 127, subíndice 1 e AUX `0x12301`. AUX `0x12300+subíndice` é destino em `0x200ef9e0` para esse grupo e para 126. Em `0x200ef2b2–0x200ef2ca` existe manipulação de AUX `0x12302[2]`. AUX `0x8011` continua sendo fonte de amostras de estado e `0x10005[13:12]` aparece no tratamento de erro do prólogo. Não foi encontrada evidência local ligando o índice `0xed` ou os endereços AUX a unidades de frequência, MOD3, SSC, PLL, divisor ou saída física CPU BCLK. O leitor de `+0xb70` pode retirar permissões dentro do ramo direto, mas falta estabelecer qual saída seria afetada.

## Reprodução e limites das entregas

Foram usados os dumps e os módulos PE/COFF existentes em `~/backup-bios`. GNU objdump e binutils ARC 2.46 foram usados para gerar e conferir desassemblagens. A análise x86 partiu das referências RIP aos GUIDs e dos VMA de funções nas etapas anteriores. O GUID do HOB foi reconstruído dos imediatos em PlatformType e conferido nos imediatos de UncoreInitPeim.

```bash
work=$(mktemp -d -t xeon-etapa15.XXXXXXXX)
mod=../unhuffme-output/mod
vol=../sps-icc-research
arc-linux-gnu-objcopy -I binary -O elf32-littlearc -B ARC700 \
  --rename-section .data=.text,alloc,load,readonly,code,contents \
  --change-addresses=0x20041000 "$mod/KERNEL-20041000.mod" "$work/kernel.elf"
arc-linux-gnu-objdump -d "$work/kernel.elf" > "$work/kernel.asm"
python3 scripts/mapa_parametros_sps.py \
  --mfs "$vol/MFS.bin" --mfsb "$vol/MFSB.bin" --sca "$vol/SCA.bin" \
  --opr1-map "$vol/mapa-opr1.json" --kernel "$mod/KERNEL-20041000.mod" \
  --policy "$mod/POLICY-2009f000.mod" \
  --kernel-asm "$work/kernel.asm" --iccmod "$mod/ICCMOD-200ef000.mod" \
  --bup-recovery "$mod/BUP-201f8000.mod" --bup-operational "$mod/BUP-20300000.mod" \
  > "$work/mapa-etapa15.json"
python3 -m unittest discover -s tests -v
git diff --check
sha256sum ../x99-h9s-original.bin ../x99-h9s-verificacao.bin ../sps-region.bin
```

`scripts/modelo_turbo.py` recebe um JSON com `build`, `select` e `ratios`. `build` usa `msr_ce`, `msr_35`, `msr_194`, `msr_1ac`, `msr_1ac_second` e os QWORDs iniciais `0x1ad/0x1ae/0x1af`. `select` tem `msr_ce`, `capid4` e `msr_1ac`. Os snapshots independentes permitem testar os dois corpos. A simulação do seletor indica o resultado caso ele execute. Um laço na fase de montagem pode impedir que o firmware chegue ao callback posterior. O modelo calcula o merge dos MSRs de ratio no intervalo de zero a 14 núcleos e reporta as decisões para contagens superiores até 24. Os testes sintéticos cobrem as independências nos dois sentidos, zero, política fora de ordem, validação de limites ARC e igualdade de conteúdo fragmentado. O arquivo local `~/backup-bios/sps-icc-research/mapa-etapa15.json` contém o mapa integral dos registros e acessos, os stubs comparados e os slots de exportação, sem dados de payload.

SHA-256 do SPI original e verificação `6036511afaaeab53701e0adce3a3a731790302f24ca11614212f95f2901fce5b`. SHA-256 da região SPS `04b63494d57ac598c026bff9fe7bb392e5129c5800ec5779dd247e57aec8f414`. Nenhuma imagem experimental foi gerada. A sessão preservou os originais e executou análises de arquivos e testes locais.

## Evidências necessárias para a próxima fase

- **CPU.** Resolver o estado prévio no pacote antes de cada callback, incluindo os bins de `0x194`, `0x1ac` e CAPID4/5. Os quatro elementos podem divergir entre fases. A origem PEI já define onde buscar o HOB e distingue política de permissão e de eficácia. A mesma configuração histórica precisa de confirmação da projeção dos ratios solicitados sobre a atividade dos 14 núcleos.
- **BCLK.** Resolver os slots KAPI `0/0x1c4/0x1c8` e os implementadores a jusante de `0x1057` nos slots de `0x2008eff0` a partir de um caminho produtor ou uma segunda imagem compatível. Em paralelo, identificar os campos usados pelo leitor MFS para remontar as quebras do PCO e validar a geometria com outros registros. Um par de perfis com diferença conhecida ou uma referência física de clock seria evidência para mapear o comando ao domínio CPU.
- **Primeira imagem offline.** Faltam um parâmetro cuja alteração tenha consequência causal demonstrável, a representação íntegra no caminho escolhido e um comparador que verifique as dependências atingidas no artefato. Combinar turbo e BCLK depende de validar cada efeito separadamente.
