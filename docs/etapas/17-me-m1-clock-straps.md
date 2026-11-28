# Etapa 17 — M1, BIOS B1 e caminhos de clock

Data: 27/11/2026. Pesquisa exclusivamente offline. Estado físico: nenhum novo teste, escrita, alteração NVRAM ou flash; EOP restaurado conforme etapa 16. Hipótese principal: a M1, uma família de firmware distinta, pode oferecer comportamento de inicialização ICC diferente do SPS original. Seria refutada para um experimento específico por inicialização igual e ausência de efeito mensurável, mas falha de POST por si só não refuta todos os mecanismos de BCLK.

## 17.1 Fontes e preservação

[Publicação original e pacote 260614](https://winraid.level1techs.com/t/guide-overclock-bios-mods-for-chinese-x99-mbs/104683/134): autor recomenda B1 para v4, associa M1 a X99Z V102, XD4 e H9S e pede conferir IIO 0; essa associação de H9S remete a [relato de terceiro](https://winraid.level1techs.com/t/guide-overclock-bios-mods-for-chinese-x99-mbs/104683/187), sem validação independente de revisão, estabilidade ou CPU v4. O [CPU-Z hlp6cj](https://valid.x86.fr/hlp6cj) informa H9S/C612, E5-2680 v4 e 31 × 126,2 MHz, com microcode B000038; é uma captura, não prova de BCLK físico, carga sustentada, integridade, uso de M1 ou configuração comparável.

Arquivo original do link atualizado 260614 obtido de MEGA por API, decifrado localmente, `7z t`: todos os arquivos íntegros segundo o teste do arquivo; isso não autentica o autor. Dados guardados em `~/backup-bios/referencia-winraid-260614/`, fora do Git; extração seletiva. Nenhum executável baixado foi executado. Não confundir integridade local com assinatura de fabricante.

| Artefato | Tamanho bytes | SHA-256 |
|---|---:|---|
| `pacote-260614.bin` (260614_HNZ_BD4_mods.7z) | 6189014 | `05ba4df1a34a02dd167b34ceb1b88fe5f89e51f0316254aadb9de26b93f969b9` |
| `M1.rgn` | 8384512 | `5126dfb7712b42131fe2fd27b64b8932285f19ee72ec3aed3b508da76a5a337a` |
| `D1_Mx_B1_260614.bin` | 16777216 | `29646a594119e3b5514e4304cf78cd928acb7bff980b072d54e1b7f80be76c3a` |
| original e verificação H9S, cada | 16777216 | `6036511afaaeab53701e0adce3a3a731790302f24ca11614212f95f2901fce5b` |
| `sps-region.bin` | 8384512 | `04b63494d57ac598c026bff9fe7bb392e5129c5800ec5779dd247e57aec8f414` |
| `machinist-x99z-c612rd24.rom` | 16777216 | `e7b0c67bbfc83d852c51f56cc604481c432858c8ba90ba34483ff55ff3a17c66` |

Inventário: `analise/` possui PE e ASM originais e IFR Platform; `overclock-mod/` contém ROM C612RD24, extração, OcInit, disassembly e diff; `sps-icc-research/` contém manifesto, descriptor, MFSB, SCA, MFS e mapas. Os quatro arquivos de região do manifesto foram conferidos por SHA-256, todos coincidentes. O hash dos dois dumps originais também coincide. A região M1 **não inclui** flash descriptor: não inferir straps ou tabela ICC de M1 a partir dos primeiros bytes dela.

## 17.2 Comparação ME/SPS e descriptor

**Estático, ferramenta ME Analyzer v1.312.0 r378:** original é SPS 03.01.03.072 Production, SKU GR, Grantley, data 2019-02-12; M1 é ME 9.1.40.1000 Production, SKU 1.5MB, LPT/WPT, data 2017-02-13, FIT 9.1.10.1000. MEA identifica padding em ambas. Suporte LPT/WPT não estabelece suporte efetivo da M1 ao C612/H9S; o relato H9S é evidência de comunidade para uma combinação, não prova desta revisão ou da BIOS original. O pacote B1 inicial foi baseado na Huananzhi BD4; o changelog documenta módulos de flash/NVRAM/PlatformType de outra placa e parâmetros IIO, além de OcInit proveniente de C612RD24. Isso não prova que firmware B1 e M1 isolada sejam intercambiáveis com a BIOS H9S.

FPT: origem dos offsets abaixo é o **início de cada região ME**, não SPI. Ambas assinaturas em +0x10, layout de cabeçalho 0x20/0x10/0x30. SPS: MFSB +0x1000/0x10000, SCA +0x11000/0x10000, FTPR +0x21000/0x20000, MFS +0x41000/0x40000, OPR1 +0x81000/0x200000, ASAP +0x281000/0x4000. M1: PSVN +0xbc0/0x40, FOVD +0xc00/0x400, MDES +0x1000/0x1000, FCRS +0x2000/0x1000, EFFS +0x3000/0x40000, GLUT +0x43000/0x4000, FTPR +0x47000/0x88000, NFTP +0xcf000/0x77000, MDMV +0x146000/0x37000; outras 11 entradas declaram offset FFFFFFFF, não tratadas como intervalos físicos. EFFS é candidato de persistência, sem decodificação de arquivos, ICC ou integridade neste trabalho. Não há correspondência demonstrada entre dados MFS/SCA e EFFS, nem associação de byte a frequência. Relatório de hashes e intervalos: `~/backup-bios/referencia-winraid-260614/fpt-comparacao.json` (pode incluir hashes sensíveis, manter local).

Descriptors das três imagens: FLREG2=07FF0001, intervalo SPI `[0x001000,0x800000)`, 0x7ff000 bytes; BIOS `[0x800000,0x1000000)`. Encaixe dimensional não comprova compatibilidade ou segurança. SHA descriptor H9S `9ee9d284bfec565e49bf5934e1d3800f8d57351844d7460bd09d281d44af9d4d`; B1 `eb656911ee73a1c2fe947517b178e687bee60430f97cc08b66f7947fd3b83477`; C612RD24 `6907d3129b4db9ba1351f1f692f76241c250d555c60efe7bb5093e818af2c403`. FLMAP2 declara RIL=27, ICCRIBA=0x21 na H9S e RIL=0, ICCRIBA=0x21 em B1 e C612RD24. Diferença de lista ICC **do descriptor**, não prova sobre o conteúdo de M1, nem instrução para substituir descriptor. Straps físicos/soft straps, valores reais e dependências de leitura ainda não comparados semanticamente.

A região ME embutida na B1 não é idêntica a M1: SHA-256 `bb7bf87470a0d2810875732684730930fce34580c628350b5e111dc33be03069`, 776313 bytes diferentes. Região C612RD24 SHA `975e2b391d6287d77bfe43efc24f0cd388a3a93afa01074edbbe3dc2d4c8c50d`, 707541 bytes diferentes de M1. Isso exclui presumir que o rótulo Mx da B1 já contenha M1. SPS e M1 diferem em 1434604 bytes de 8384512; não supor equivalência de partições ou de dados provisionados.

## 17.3 OcInit e campos de clock

OcInit GUID `6540F933-425F-464B-B4AD-B93A6ED0A8F5`; referência extraída da ROM C612RD24, não reextraída da B1 nesta sessão. Changelog B1 alega substituir OcInit pela C612RD24, mas identidade binária em B1 ainda não verificada. PE32 i386: H9S 9824 bytes SHA `fe142b302812a60830c3e059933547641c534c8ca27113a2a8637e77862c7dde`, image base FFDC47B4; C612RD24 6112 SHA `a8ebc035afb83b245f818994c1ebd4979399ad8312a337b0bbb93d9ec06e64a5`, base FFDC2F78. Bases e endereços seguintes são VMA PE, não offsets SPI. Layouts IntelSetup têm tamanhos 0x17EC e 0x17CB, respectivamente; troca isolada do módulo sem adaptação de layout não é candidata segura.

Na H9S FFDC4B5E testa IntelSetup[163F], e FFDC4B8C–90 testa capacidade antes da leitura MSR61E em FFDC4B96. Em FFDC4E9A há chamada a FFDC647E, que lê 61E, lê registro ECAM relativo B0060, compara campos, e no ramo de divergência escreve 61E em FFDC658B e acessa ECAM relativo F80A0; ver a sequência completa em `analise/OcInit.asm`. É sincronização condicionada, não comprovação de pedido de strap arbitrário. A referência C612RD24 também possui guard de capacidade em FFDC32C3–32D1 e transporte OC Mailbox, mas acesso a 61E não foi localizado no seu OcInit. O resultado negativo de busca se limita ao módulo e às representações analisadas.

| Opção IFR H9S / QID | VarOffset IntelSetup | Estado da ligação com hardware |
|---|---:|---|
| ICC Profile / 10B0 | 12EF | seletor 0–15, default 0; consumidor não resolvido |
| DMI Clock Frequency / 10B1 | 12F9, 16 bits | texto IFR 100 MHz/0,5% é placeholder; unidade, produtor e programação efetiva não resolvidos |
| DMI/PEG Ratio / 10B5 | 1301 | opções 5:5, 5:4, 5:3, 5:2; consumidor ainda não demonstrado |
| Filter PLL / E40 | 163E | PEI e gates HOB/GPIO detalhados na etapa 16; identidade H9S 07 é candidata, não 13 exigido |
| Adjust PLL / E41 | 17C1 | ajuda menciona mailbox; consumidor, comando e domínio não demonstrados |
| PLL Trim / E42 | 17C2 | campo IFR 32 bits; não se infere comando ou valor físico |
| Overclocking Feature | 163F | consumidor PEI também afeta caminho MSR620 de uncore; não prova turbo dos cores |

O nome CPU Strap e os pontos de programação de BCLK, perfil ICC, divisor e Adjust PLL não foram resolvidos nesta sessão. A presença de formulários, o envio HECI e o relato de outra CPU não comprovam qualquer efeito. Gates de modo/status ICC H9S e limitações de ratio estão na etapa 16; nenhuma repetição de EOP, MSR runtime ou ICC foi realizada.

## 17.4 Próximo experimento e condições para prosseguir

**Candidato conceitual, ainda não imagem aprovada:** comparar baseline original com imagem offline que mantenha descriptor e BIOS H9S byte a byte e substitua apenas região ME por M1; reversão com dump original verificado. Hipótese específica: com BIOS H9S e seu descriptor, M1 inicializa e expõe caminho de clock distinto. Este teste altera 0x7ff000 bytes e troca SPS por ME; não é uma alteração pequena em bytes, nem está demonstrado ser compatível. H9S+M1 difere do conjunto B1+M1 recomendado no fórum; resultado negativo pode decorrer da combinação, não do M1 ou C612 isoladamente. Nenhuma imagem foi construída: faltam análise das dependências BIOS SPS/ME, dados persistentes e provisionamento, efeito dos 27 pares ICC, verificação de descritores/straps e plano de validação pré-boot. A alternativa B1+M1 muda BIOS e descriptor e adiciona fatores; é controle posterior, não primeiro teste isolado. Não transplante FPT, EFFS, OcInit ou campos individuais.

Próximo passo executável offline: extrair e identificar módulos B1/C612RD24 ligados a ME/ICC e OcInit com ferramenta UEFI já verificada, comparar dependências PEI/DXE e strings/protocolos contra H9S; inspecionar EFFS com ferramenta que documente ME 9.1, sem assumir que seja MFS. Depois, se a compatibilidade e os limites forem compreendidos, produzir imagem em arquivo novo, hash e comparação com máscara exata da região ME, sem gravar. Qualquer flash, reboot ou mudança de NVRAM requer autorização específica; a confirmação de gravador/backups é relevante, mas não equivale a autorização de gravação. Preservar limites térmicos, elétricos e de corrente. Em eventual ensaio autorizado: baseline, recuperação SPI, inicialização e identificação de firmware, depois frequência efetiva com referência independente, carga e desempenho equivalentes, temperatura, throttling, PCIe/armazenamento e integridade em dados descartáveis. Interromper diante de falha POST, corrupção ou erros, restaurando backup conforme plano.

## 17.5 Reprodutibilidade e validação

- `python3 scripts/compara_fpt.py ../sps-region.bin '../referencia-winraid-260614/extraido/Step 2, choose ME/M1.rgn'` — relatório JSON de regiões explicitamente fornecidas, hashes e limites; reconhece somente layout legado observado, sem validar assinatura criptográfica, checksum FPT, sobreposições ou semântica de persistência. Offset FFFFFFFF tratado como não mapeado; não extrai nem escreve firmware.
- `python3 scripts/icc_descriptor.py --image h9s=../x99-h9s-original.bin --image b1='../referencia-winraid-260614/extraido/Step 1, B1 or B2 BIOS/D1_Mx_B1_260614.bin' --image c612rd24=../overclock-mod/machinist-x99z-c612rd24.rom` — lista de pares brutos; não interpreta seletores.
- `python3 -m unittest discover -s tests`: 34 testes passaram, incluindo fixtures sintéticas de FPT válido, entrada sem offset, limites, cabeçalho desconhecido e contagem excessiva.
- ME Analyzer exigiu terminal interativo no ambiente local; execução não interativa falhou em colorama e não foi usada como resultado. Python 3.14.4; objdump GNU 2.46; 7-Zip 26.00. Originais preservados.
