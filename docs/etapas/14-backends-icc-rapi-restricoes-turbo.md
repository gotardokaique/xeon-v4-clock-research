# Etapa 14 — Backends ICC, RAPI e restrições de turbo

Sessão de 26/11/2026, exclusivamente offline. Continuação da [etapa 13](13-resolucao-servicos-sps-politicas-turbo.md). Os endereços de código são VMA PE/COFF para x86 e VMA ARC para SPS, salvo indicação de offset. Conferidos novamente os SHA-256 do SPI original e da região SPS.

## CPU-04 — Auditoria de PLATFORM_INFO

O valor transcrito em EXP-02, **0xa0080c3bf2811800**, tem DWORD baixo 0xf2811800 e **bits [30:28] = 111b**. O nibble alto do byte little-endian +3 (0xf2) confirma a extração. Truncar para o DWORD baixo preserva esses bits. A conversão correta entre decimal com sinal e inteiro de 64 bits também preserva os três bits. O campo [15:8] vale 0x18, coerente com o ratio nominal.

```bash
python3 -c 'v=0xA0080C3BF2811800; print(hex(v & 0xffffffff), (v>>28)&7, [(n,(v>>n)&1) for n in (28,29,30)])'
rdmsr --version
rdmsr --help
dpkg-query -W msr-tools
```

O caderno EXP-02 é a fonte disponível mais próxima da coleta. A etapa 01 registra a sintaxe de leitura com CPU 0. A busca nos logs locais e a listagem dos pacotes ICC não localizaram stdout primário, leituras independentes dos campos ou indicação da versão histórica da ferramenta. A versão **local** é msr-tools 1.3, pacote 1.3+git20220805.7d78c80-1ubuntu0.1. A ajuda confirma -p para CPU, -x/-X para hexadecimal, -d/-u para decimal e -f h:l para faixa inclusiva com o bit alto primeiro. Só a ajuda e a versão foram executadas. A aritmética resolve a contradição da transcrição. A fidelidade da transcrição e o valor durante DXE continuam sem verificação. A conclusão histórica de que 0xCE[28] estava em zero fica superada. [Intel SDM, vol. 4, tabela 2-38](https://cdrdv2-public.intel.com/874253/335592-090-sdm-vol-4.pdf#page=361).

## CPU-05 — Acessos a 0x1AC e tabela de resume

Usei GNU objdump 2.46 sobre os PE/COFF originais e a referência C612RD24. Para modelos 0x4f/0x56, ESI recebe 0x1ac em 0x2391, derivado dos índices consecutivos das tabelas. No caminho que chega a 0x26aa, ESI mantém esse valor.

| VMA H9S | Evidência |
|---|---|
| 0x23fb | Primeira leitura de 0x1ac na montagem da tabela. 0x240a sai se a metade alta inteira for diferente de zero. |
| 0x26ac | Segunda leitura de 0x1ac na montagem. O resultado é salvo em rsp+0xe8. |
| 0x2c61 | Leitura de 0x1ac na rotina separada que seleciona a tabela alternativa. |
| 0x2c8f | Escrita compartilhada. No modelo 0x4f/0x56 usa 0x1ac com bit 63 ligado. Para 0x3f usa 0x1af. O fallback usa 0x1ae. |

Em 0x26c7–0x26ce, EAX recebe a metade alta salva uma vez e é mascarado por 0x80000000. O salto em 0x26d5 volta ao TEST em 0x26d3. O laço não relê o MSR nem a memória e, se alcançado com o bit ligado, não termina pelo fluxo normal. Para chegar aqui com bit 63 ativo na segunda leitura, a primeira leitura precisa ter passado pelo gate da metade alta zero. A mesma forma aparece para modelos 0x3e e 0x3f em 0x2653 e 0x2691. A referência C612RD24 preserva o padrão em 0x26cb–0x26cd, tem segunda leitura em 0x26a4 e escrita em 0x2c87. O PpmInitialize da BIOS mod de referência H9S é idêntico ao original. A C612RD24 tem SHA-256 2e1f504fc200e853cd3b4c495be3ee9bad0e352b898b36bf0a51869a12cedaa8.

Em 0x2318, a tabela do PCD 0x29 passa pelo ramo de modelo e semáforo, por 0xCE[28] e pelo campo de bins 0x194[19:17]. 0x26f8–0x2700 sai se um ratio percorrido exceder o primeiro. A quantidade de núcleos e os campos zero condicionam a composição de bytes. As escritas principais são 0x2b23 e 0x2b3c, e 0x2b9a em 0x1af depende de modelo 0x3f/0x4f. A função separada 0x2bcc exige 0xCE[28] e o bit 28 do DWORD CSR em 0x2be5 e 0x2bf5. O call graph permite selecionar a tabela sem um retorno de sucesso da montagem. Em 0x1ec0 há outro caminho, que ajusta a solicitação em 0x199 usando campos de 0xCE e política. OcInit/PEI, por sua vez, usa outro transporte e consulta capacidades por 0x150.

**0x1d8c registra operações para replay.** A função encaminha o valor do sexto argumento ao sétimo de 0x1c68. O produtor usa PCD 0x17, inicializado em 0xc1b–0xc31, e a tabela em bloco+0x28. O descritor indexado tem 24 bytes, com contagem +0, capacidade em bytes +8 e ponteiro +0x10. A capacidade cresce em 0x1000 bytes. Cada entrada também tem 24 bytes. O tipo DWORD em +0 vale zero, o índice do MSR está em +4, bit inicial em +8 vale zero, largura em +9 vale 0x40 e valor QWORD em +0x10. O código incrementa a contagem. Não há WRMSR, despacho de AP nem readback dentro dessas funções.

Em PiSmmCpuDxeSmm, 0x18d8 lê o mesmo PCD 0x17. 0x256c–0x25e1 copia descritores e suas listas, e o caminho que verifica a assinatura SMMS3_64 seleciona um descritor pelo APIC em 0x247c–0x249b. O intérprete em 0x3194 consome o mesmo layout e faz WRMSR de largura integral em 0x3346–0x335a. Está estabelecida a finalidade de replay de configuração. A ponte de cada lista DXE até os dois snapshots no SMM e a execução de uma entrada 0x1ac durante resume desta H9S continuam pendentes.

| Evidência | Limite |
|---|---|
| Firmware | Gates, teste de ratios, laço de valor congelado e separação entre montagem e seleção são fatos estáticos. |
| Arquitetura | 0x1AC é R/O se 0xCE[28] valer zero e R/W se valer um. Elevar os limites acima da configuração de fábrica depende do processador e da plataforma. |
| Hardware histórico | Bins registrados como zero em 0x194. OC Mailbox retornou completion 5 à solicitação específica de 30x. |
| Pendente | Estado em DXE, aceitação de 0x1AC/ratios alternativos, frequência efetiva e origem física de cada capacidade. Nenhuma evidência de fusíveis foi acrescentada. |

## CPU-06 — Seletor CSR e condições de capacidade

Em CpuCsrAccess, LocateProtocol em 0x2974–0x298b fornece o ponteiro em 0x2ef8. 0x2a28–0x2a38 lê o perfil de topologia no byte +0x1676 da estrutura apontada. +0x1677 é copiado separadamente. +0x167e fornece o bitmap de sockets e +0x10a2 fornece a base de configuração em 0x2aeb. O GUID consumido é a7ced760-c71c-4e1a-acb1-89604d5216cb. A mesma referência existe em IioInit, CpuMpDxe e no módulo CSR de SMM. O encaminhamento foi localizado até essa interface, e o escritor anterior do byte +0x1676 segue pendente.

0x21f4 retorna a base combinada por OR com (bus<<20) | ((device&31)<<15) | ((function&7)<<12) | (selector&0xfff). O grupo 0x0a, índice 3, largura 4 e offset 0x94 são extraídos de 0x0a034094. Para os argumentos zero de PpmInitialize, o ramo 0x1321 produz device 30 nos perfis 0/2 e 0x1344 produz device 10 no perfil 1. A tabela de função em 0x1cd4–0x1cfa retorna 3 nos três perfis. O bus vem da tabela por socket em 0xb54. A parcela abaixo do bus é 0xf3094 nos perfis 0/2, consistente com CAPID4 do PCU no datasheet E5 v4. O BDF vivo não foi medido.

O campo CSR em contexto+0xc → +0x25 tem oito consumidores diretos do bit 28 em PpmInitialize. 0x12a7, 0x1f9b e 0x2223 afetam caminhos de potência ou bits de bloqueio. 0x2bef condiciona o semáforo de ratio. 0x3038, 0x3169, 0x3309 e 0x3456 afetam cálculos de potência. O teste separado de PLATFORM_INFO e do campo CSR impede tratá-los como a mesma variável de firmware. O datasheet local de registradores (§5.4.6) não nomeia CAPID4[28]. CAPID5, seletor 0x0a034098, aparece em 0x1ac7 e nos gates 0x1e2d/0x1e93, inclusive na referência C612RD24.

CpuMpDxe usa 0xCE em 0x5558, 0x60b4 e 0x7ef3 e 0x1ad em 0x60dd. CpuMpPei segue com APIC como únicos MSRs diretos inventariados no módulo. OcInit verifica capacidades via 0x150 antes do caminho de 0x61e. Os blocos de microcode inventariados na etapa 12 não permitem atribuir a origem de CAPID4, PLATFORM_INFO ou OC Mailbox. A diferença de revisão do PpmInitialize C612RD24 preservou os dois seletores CSR, o laço e o semáforo.

## ARC-03 — Janelas RAPI/KAPI confirmadas

Cruzei as duas LLUT com os bits [19:17] e [21:20] dos descritores $MME, seguindo a convenção documentada no me-tools local (commit b35da192377d70b0b855ac53b39b90555ebb68c7). Uma janela do manifesto tem unidades de 4 KiB, enquanto a LLUT tem unidades de 1 KiB.

| Módulo | Janelas de 4 KiB RAPI/KAPI | Bases |
|---|---|---|
| KERNEL | 1/0 | 0x20040000 |
| BUP OPR1 / FTPR | 1/0 | 0x201f8000 / 0x20300000. Entradas 0x201f9000 / 0x20301000. Dumps raw 0xf000 / 0x17000 bytes. |
| POLICY / HOSTCOMM | 1/1 | 0x2009d000 / 0x200df000 |
| ICCMOD / BASEEXT | 1/1 | 0x200ed000 / 0x20109000 |

Em ICCMOD, 0x200efde2 salta a 0x200eddf4, 0x200efe14 chama 0x200edcec e 0x200ef7f0 chama 0x200edcdc. Todos pertencem à LLUT 695, página 0x200edc00, janela RAPI. O par GET/SET 0x200eeab0/0x200eeac8 pertence à LLUT 698, página 0x200ee800, janela KAPI. Ambas as entradas têm valor 0x80000000 nas duas LLUT. Os quatro destinos candidatos estão confirmados como endereços de alias reservados pelo mapa e sem stream de OPR1. O prólogo em 0x200ef03c exige assinatura RAPI e versão WORD 5 na base. Os 14 dumps de módulos têm o mesmo imediato de assinatura em formato de instrução ARC.

No KERNEL há templates KAPI reais em 0x20041000 e 0x20044000. A desassemblagem mostra stubs com passo de 12 bytes, código que carrega seletor em r8 e salto comum em +0x10. Em 0x20044fd8–0x20044fe8, o dispatcher usa os 16 bits baixos como índice na tabela apontada por [0x2008ed14] e salta indiretamente. Outro dispatcher, em 0x20089260, separa classes pelo bit 18 e valida limites antes da resolução. Essa evidência sustenta tabelas de despacho para KAPI. No segundo dispatcher, quando o bit 18 está limpo, 0x200892f4–0x200892fc substitui a tabela global por uma constituída a partir de [r0-4]. Os dois globais do KERNEL em 0x2008ed14 e 0x20095280 estão além do intervalo de código 0x2008e000 e antes do limite de memória 0x2009c9a0 calculado pelo campo $MME +0x44. Encontrei apenas loads absolutos para eles no código desassemblado. A instalação dos templates e a correspondência entre os serviços ICC e os seletores ainda precisam ser localizadas.

0x200f11d0–0x200f120e prepara dados e associa o contexto recebido. 0x200f1294 guarda descritores de 16 bytes em uma tabela do contexto. POLICY usa 0x2009e018, em janela KAPI sem stream, para resolver a importação 0x102f destinada a 0x200deca4. POLICY termina seu código em 0x200d3000 e declara memória até 0x200decb0. A célula de importação 0x200deca4 fica nos últimos 12 bytes desse intervalo de dados, embora a LLUT não tenha stream para ela. Os templates não revelaram o exportador de 0x102f nem a implementação do slot +0x24. O próximo teste é seguir os escritores das tabelas apontadas por 0x2008ed14 e 0x20095280 e verificar como o KERNEL combina essas tabelas com os descritores de cada módulo.

## ICC-02 — Formato dos registros e operações AUX

Em 0x200ef7f0, o retorno de 0x200edcdc vira r16, e o bloco é rejeitado se nulo. A única referência literal a +0xb70 no ICCMOD é o load em 0x200ef964. A pesquisa de instruções nos 14 dumps revelou cópias dessa leitura nos dois BUP, em offsets raw +0xc212 (OPR1) e +0x12c4a (FTPR), e nenhuma escrita de offset literal. Um alias de ponteiro, cópia em bloco ou o produtor por trás de RAPI pode preencher o campo. Essa busca não cobre escritas por ponteiro calculado.

Para selector da classe 0x7f00 e subíndice 1, 0x200ef964–0x200ef980 compara old & ~allowed com requested & ~allowed. A igualdade equivale a **((old ^ requested) & ~allowed) == 0**, e a falha retorna 0x1a. 0x200ef9c4 fica dentro da instrução de quatro bytes iniciada em 0x200ef9c2. Em 0x200ef9d8–0x200ef9e0, a rotina forma AUX 0x12300+subíndice e grava o valor. O helper 0x200efde8 recebe ponteiro de saída em r0, máscara em r1 e dados em r2 e aplica **new = (old & ~mask) | (data & mask)** a AUX 0x12301. O mesmo padrão existe nos dois BUP. A máscara de autorização e a máscara de aplicação têm origens distintas no fluxo.

| Registro ICC | Layout e consumidor |
|---|---|
| 0x1f, 12 bytes | +0 DWORD dados, +4 DWORD máscara, +8 DWORD flags, bit 0 válido. 0x200f0f7c–0x200f0f84 confirma a ordem contando o delay slot. Reset envia três DWORDs zero. |
| 0x3b, 8 bytes | +0 DWORD configuração e +4 DWORD flags, bit 0 válido. 0x200efe10 desdobra o primeiro DWORD em oito descritores. Consome os dois primeiros bits de cada nibble e o terceiro em 2,6,…,30. Bits 3,7,…,31 aparecem em checagens no produtor. Os dois passes em 0x200f00aa e 0x200f0142 chamam 0x200ef7ec. Os bits superiores do DWORD de flags e a função física dos canais continuam sem atribuição conclusiva. |

O bit 2 de AUX 0x12302 é ajustado em 0x200ef2b2–0x200ef2ca quando o subíndice é 2, com leitura subsequente do mesmo AUX. AUX 0x10005[12:13] é setado no caminho de erro do prólogo RAPI. AUX 0x8011 é lido em sete pontos. As cópias em contexto+0x64, +0x68 e +0x6c em 0x200f1232, 0x200f0f24 e 0x200f10d2 sustentam amostragem de estado. A associação documentada do MOD3 a CLKOUT_DMI não resolve esses endereços AUX. Falta cruzar unidade, divisor, SSC, PLL e saída física com pelo menos um programa equivalente ou um par de perfis com diferença conhecida.

## SPS-05 — Diretório candidato MFS e leitor SCA validado

A busca por periodicidade em MFS encontrou 123 ocorrências de dc f0 entre offsets 0x14 e 0x552, com 122 diferenças consecutivas iguais a 11 bytes. MFSB repete os mesmos offsets. Os bytes +0/+1 e +8 de cada intervalo são invariantes (dc f0 e 01). O layout de 11 bytes é candidato a tabela, com semântica e integridade dos campos ainda abertas. Os acessos a [r13+0xf] em POLICY 0x200ae920/0x200ae94c pertencem a estado RAM decrementado. Eles não explicam o byte divergente do cabeçalho MFS em +0xf. O rodapé MFSB [0xff08,0xff1c) contém DWORDs LE 0, 0xa, 0xa, 0xa, 0xa. A BIOS mod de referência preserva integralmente MFS, MFSB e SCA. A referência C612RD24 não contém essas entradas SPS na FPT inspecionada. Nenhuma dessas amostras permite atribuir o rodapé ou o byte divergente.

No POLICY, 0x200be278 valida DWORD zero, comprimento do cabeçalho igual a 0x10 DWORDs, assinatura $SCA em +8 e versão 1 em +0x18. 0x200be050 caminha pelos registros usando a extensão em DWORDs no campo +4 e compara o ID DWORD em +0. 0x200be134 valida a capacidade de destino e entrega o registro. 0x200be214 conta entradas e bytes e chama a soma com complemento em 0x200bdff4. Na amostra, cabeçalho de 0x40 bytes, comprimento total 0xac4 e contagem nove incluem cabeçalho e terminador. A soma de DWORDs LE em [0,0xac4) vale 0xffffffff. O DWORD +0x3c, 0x44107319, coincide com o complemento da soma dos demais.

| Offset SCA | ID DWORD | Comprimento em bytes |
|---:|---:|---:|
| 0x40 | 0x0a534b55 | 0xc |
| 0x4c | 0x10424d43 | 0xc |
| 0x58 | 0x10455243 | 0xc |
| 0x64 | 0x10535349 | 0xc |
| 0x70 | 0x0a4f4350 | 0xa2c |
| 0xa9c | 0x104f4943 | 0x14 |
| 0xab0 | 0x0b534d54 | 0xc |
| 0xabc | 0xffffffff | 0x8 |

HOSTCOMM 0x200e671e e BASEEXT 0x20145022 contêm a mesma checagem de assinatura. As duas BUP contêm comparações equivalentes em offsets raw +0x6abe (OPR1) e +0xa3ae (FTPR). O SCA já tem, portanto, leitor estruturado e busca por ID independentes de MFS. Os IDs externos não incluem 0x1f ou 0x3b. A pesquisa de 1f 00 0c 00 e 3b 00 08 00 em MFS, MFSB e SCA não encontrou correspondência. Essa ausência elimina apenas essas codificações literais e a identificação direta com uma chave SCA externa. O KERNEL compara a chave 0x0a4f4350 em 0x20052ac8 e segue a 0x20053b2a, que exige comprimento mínimo de 0xa24 e acessa o conteúdo via r20. Isso coincide com 0xa24 bytes de payload no registro em SCA+0x70 após o cabeçalho de oito bytes. Outro ramo reconhece 0x0a534b55 em 0x200530a8. Foi encontrado um validador concreto do bloco maior. Sua relação com os IDs ICC ainda precisa ser demonstrada. Para testar a relação com ICC, é necessário seguir o consumidor de uma chave SCA até a estrutura retornada por RAPI ou mapear o despacho dos IDs KAPI.

```bash
python3 scripts/auditoria_sps.py --sca ../sps-icc-research/SCA.bin \
  --opr1-map ../sps-icc-research/mapa-opr1.json \
  0x200eddf4 0x200edcec 0x200eeab0 0x200eeac8 0x200deca4 \
  > ../sps-icc-research/auditoria-etapa14.json
python3 -m unittest discover -s tests -v
git diff --check
```

## Estado das duas frentes

- **Turbo.** PCD 0x29 → 0x1ad/0x1ae/0x1af → seleção via 0x1ac é a cadeia mais completamente rastreada. A correção da transcrição de 0xCE reabre essa via para investigação. Faltam confirmação contemporânea dos bins e CAPID4 na fase relevante, aceitação pela CPU e medição de frequência efetiva. PCD 0x25 continua ligado à apresentação do primeiro ratio. O próximo teste offline é identificar a origem PEI da topologia CSR e os produtores do estado consultado pelo PPM.
- **BCLK.** O fluxo ICCMOD → AUX 0x12301/0x12302 já tem formato observável e análogos no BUP. A ligação RAPI/KAPI e a estrutura SCA oferecem pontos para resolver o backend. O próximo teste é ligar as tabelas de despacho a um produtor de registros ou a um perfil conhecido e verificar o domínio de clock. Falta demonstração de que os AUX alteram CPU BCLK.
- **Entregas.** O analisador offline gerou auditoria-etapa14.json com metadados SCA e classificação das janelas ARC. Cinco testes sintéticos foram adicionados. Nenhuma leitura de hardware, gravação, flash, transação ou reinicialização foi feita. A combinação dos mecanismos continua dependente da validação separada.
