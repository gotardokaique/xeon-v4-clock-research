# Etapa 16 — ClockLab, HECI funcional e limites turbo em UEFI

Data: 27/11/2026. Continuação da etapa 15. Evidências: logs de terminal e UEFI fornecidos pelo operador nesta sessão; não constituem uma nova execução remota. Plataforma permanece E5-2680 v4, CPUID 406F1, X99-H9S V1.21, C612, SPS 3.1.3.72. Nenhum overclock efetivo demonstrado.

## CPU — experimentos Linux e UEFI

- Linux: microcode padrão 0x0B000040; boot experimental sem carregador de microcode preservou 0x0B000038. A redução experimental dos limites para 28x produziu aproximadamente 2800 MHz; restaurar tabelas não recuperou imediatamente 29x, mas reboot recuperou. Não atribuir causalidade isolada ao 1AE: faltou controle após restauração.
- A elevação da tabela para 30x foi legível, mas não elevou a frequência efetiva. Solicitação de 33x via MSR 199 não equivale à frequência alcançada.
- UEFI: microcode 0x0B000038; CE=20080C3BF2811800; 194=0; 1AC=0; CAPID4=24038E61 (bit 28 limpo); CAPID5=C602FD6F. Tabela original 1AD=1D1D1D1D1E1F2121; 1AE e 1AF=1D1D1D1D1D1D1D1D. IntelSetup 24 WORDs de ratio zerados.
- v0.8: MP Services total=28 enabled=28. Escrita do bit 63 de 1AC aceita temporariamente. Primeira leitura limpa em 51.561.660 ticks (tabela original) e 238.135.588 ticks (modificada); aproximadamente 21,5 e 99,4 ms considerando TSC ~2,396 GHz. Uma observação por condição, sem inferir causalidade. Medição APERF/MPERF 23,99x confundida pela solicitação 199=1800 (24x).
- v0.9: sweep BSP, 15 condições, solicitações 29/30/31/32/33x, modos stock, tabela 30x e tabela 30x+1AC. Todas produziram ratio x100=2899, estado efetivo 29 no início/fim, SMI delta=0 e restore=1. No modo 2, 1AC passou de 8000000000000000 a zero. Não se controlou o estado dos demais núcleos, portanto não é teste single-core controlado. O Linux não é necessário para reproduzir a limitação; PCU/microcode/SMM ainda são hipóteses, não prova de fuse irreversível.
- v0.9: R após G confirmou os cinco MSRs originais no BSP. H interrompeu no primeiro cenário stock: StartupAllAPs: Success count=28; STOP: AP failure or restore mismatch. A validação esperava 27 callbacks, segundo revisão relatada na sessão; confirmar no fonte antes de corrigir. Não há resultados individuais válidos dos APs. Não inferir falha de restauração nem atribuir o bloqueio a R.
- Após reboot, rdmsr -a confirmou 1AC=0 e tabelas originais nos 28 processadores. Ubuntu iniciou normalmente. Não houve brick permanente observado.

## HECI — controle positivo e negativos

IntelSetup GUID EC87D643-EBA4-4BB5-A1E5-3F3E36B20DA9, tamanho 0x17EC, atributos 3. v0.4 alterou somente offset 12D4 de Auto(2) para Enabled(1), com verificação de leitura e zero diferenças inesperadas. Após reboot HECI1 8086:8d3a presente em 00:16.0; HECI2 ausente. EOP 12D2=1, HECI2 12D5=2, override ICC 12EB=0. Configuração HECI1 continua alterada; não confundir recuperação dos MSRs com restauração da NVRAM.

HECI protocolo UEFI cfb33810-6e87-4284-b203-a66abe07f6e8: slots +0 SendWithAck, +8 Receive, +10 Send, +38 status, +40 mode. Mode=6, status=82; FWSTS=000F0392. Não interpretar retorno Success da consulta de modo como serviço ICC operacional.

| Experimento | Método | Resultado |
|---|---|---|
| EXP61 v0.5 | ICC API 30000 opcode 06, host 0 dest 8, payload total 20 bytes | SendWithAck timeout, 0 bytes |
| EXP62 v0.6 | Separar Send e Receive | Send Success, 0 bytes de resposta |
| EXP63 | CSR após boot Linux | HOST RP/WP 10/10, SPS 5/5; sujeito a interferência do boot |
| EXP64 v0.7 | MKHI FF/02 GET_FW_VERSION, host 0 dest 7 | Send/Receive Success, 20 bytes, resultado 0 |
| v0.7 ICC instrumentado | Mesmo opcode, captura imediata | HOST RP/WP 6→12, SPS 11→11, sem resposta em ~2 s |
| v0.8 HBM | Host Start 1.0, dest 0 | HOST RP/WP 4→6, SPS 5→5, sem resposta em ~2 s; enumeração não executada |

MKHI resposta DWORDs: 000082FF 05030001 00030048 05030001 00030048. Cabeçalho confirma grupo FF, resposta ao opcode 02, result=0. Não atribuir versão exata aos campos sem validar layout SPS: a interpretação anterior como 3.1.3.72 não está demonstrada por esse payload isoladamente. O SPS consumiu os pacotes ICC/HBM no nível FIFO; não há prova de despacho ao serviço. MKHI valida comunicação bidirecional e refuta indisponibilidade global após EOP, não restrição seletiva.

## Engenharia reversa SPS

ICCMOD strings: 0x2964 IccHeci1InputQ, 0x2973 IccHeci1ConnectedBufferQ, 0x298C IccHeci1SendQ, 0x299A IccHeci1ConnectionlessBufferQ (offsets de módulo). HOSTCOMM contém HeciCmdQueue, HeciSend, HeciTxDone e HeciAccessCtrl. Identificadores candidatos reportados em ICCMOD +2944/+2954: 8c2f4425-77d6-4755-aca3-891fdbc66a58 e bf3cb4da-4045-4f9b-838d-8cbcfb21a107. Revalidar bytes e referências antes de usar como GUIDs de clientes; registro ativo/endereço não demonstrados.

Mapa OPR1 SHA SPS 04b63494d57ac598c026bff9fe7bb392e5129c5800ec5779dd247e57aec8f414: ambas as tabelas, índices 695,696,698, flags 0x40, word 0x80000000, owners ICCMOD. Serviços candidatos 200EDE64, 200EE318, 200EEAB0/AC8 encontram-se na janela intermediária de aliases, não no conteúdo extraído HOSTCOMM. A etapa 15 já documenta RAPI e a inicialização por descritor. Não repetir extração das páginas vazias. Busca textual dos offsets IntelSetup 12D2/12EB/130F em ASM retornou arquivo vazio; não prova ausência de consumidores.

## Artefatos locais e hashes

Fontes e logs permanecem em ~/backup-bios; não publicar dumps ou dados de provisionamento. Binários EFI compilados pelo operador:
- v0.5: 29f9cbd541a202c0b475ae784ed7f8ca15810ac7f3868de54cefb9758ba48442
- v0.6: 35adf89de925a136896dd07d6aa565d323a2236c364f63d4464e41dca2feb722
- v0.7: 19cfc6f73553a12c7beb0cfb48195b5e6a9e4fae6931b92850eb7bcfe6871d3b
- v0.8: 2dad446dc21a65003b77050817cdb35ee247ae56a7157385de5032a343b1a491
- v0.9: d7a53a5a47cb9c013943071daaa265c174a3559fca3c6ebf4c705aa18016135b

## Próxima entrega: ClockLab v0.11 (planejada, não implementada)

1. Corrigir MP Services: validar ABI, assinatura, estrutura, contagem retornada, identidade BSP/AP por WhoAmI e APIC ID; executar primeiro callback exclusivamente de leitura. Registrar cada resultado antes de validar, detectar duplicatas e slots ausentes; não substituir 27 por 28 cegamente.
2. Separar estado package/core/thread; não escrever MSRs de escopo compartilhado em callbacks concorrentes. Verificar restauração individual; registrar falhas específicas; bloquear operações ativas se pré-validação falhar.
3. Medir atividade real por núcleo, APERF/MPERF e solicitação/estado efetivo; comparar cenários com quantidade de núcleos controlada quando possível. Não repetir as 15 condições BSP já concluídas sem nova hipótese.
4. Investigar indicadores de limitação e persistência de 1AC com amostragem temporal; não desabilitar proteções térmicas/elétricas.
5. BCLK: resolver inicialização do cliente ICC e consumidores EOP/override/locks via análise offline; investigar serviços nativos SPS e HECI2 sem envio arbitrário. Não repetir HBM/ICC nas mesmas condições. Alteração persistente somente após validar consumidor, parâmetros e recuperação.
6. Agrupar testes em uma sessão, com logs completos, confirmação específica de operações ativas e critérios de interrupção. Preservar v0.8 e v0.9 como histórico; v0.9 não deve ser reexecutada antes da correção.

## Limites

Nenhum aumento efetivo de BCLK ou turbo acima de 29x demonstrado. Nenhuma gravação SPI experimental nesta sessão. A documentação é uma consolidação de evidências fornecidas pelo operador; fontes locais e estado git do clone não foram auditados nesta atualização remota.

## Atualização — ClockLab v0.11 e preparação da v0.12 (27/11/2026)

**v0.11:** compilação GNU-EFI concluída sem diagnósticos de erro; SHA-256 fe7b12e32b6438e125fad6c6614114bb0c3598a91bc93c1a918cae284d44ae9d. Validador sintético e 5 testes Python aprovados. Execução física: preflight J retornou "MP READ-ONLY preflight FAILED status=Success; active tests blocked". H e U não executaram intervenções; R não dispunha de baseline MP. A condição interna exata da falha não foi registrada. Não atribuir o erro a um flag específico antes de observar os descritores brutos.

**Referência temporal:** ACPI PM Timer, PMBASE=0401, ACPI_CNTL=80. Três amostras de TSC: 2394471, 2394466, 2394474 kHz. TSC/24 ~99769 kHz; ratio APERF/MPERF ~23,99x sob solicitação 24x. Estimativa indireta da referência; compatível com SSC, sem comprovar SSC ou medir fisicamente BCLK.

**OC Mailbox:** domínio 0 resposta 0x221, domínio 2 resposta 0x21B, completion=0 em ambos. Decodificação utilizada pela ferramenta reporta ratio máximo 33/27, Ratio OC=0, Voltage Override=1, Voltage Offset=0. Consultas V/F retornaram dados 0 e completion=0 em ambos. Não interpretar zero como tensão física; suporte reportado não prova aceitação de escrita. Nenhuma sobretensão aplicada. HECI1 8D3A8086 presente, HECI2 ausente; FD2=001D. MKHI FWCAPS GET_RULE regra 0, host 0 dest 7: Send Success, HOST RP/WP 4→7, SPS 5→5, sem resposta em ~2 s. Não repetir sem alteração de hipótese.

**v0.12:** compilação GNU-EFI concluída; SHA-256 4b06db7fd34efdab4887f014f1652270a572021c6aa01179da2abeb1248c53ec. Validador sintético MP12 e 9 testes Python aprovados. Execução UEFI pendente. Coleta Linux (395 linhas, 20.094 bytes) confirma 28 CPUs online, pares SMT 0/14 até 13/27; IDs físicos sysfs 0–6 e 8–14 (não contíguos). Não confundir índices lógicos com IDs físicos ou APIC. Clocksource TSC, alternativas HPET e ACPI PM. Temperatura pacote 34 °C, núcleos 30–31 °C; nenhum sensor de Vcore apareceu na coleta. A busca de candidatos por constantes em 12 módulos encontrou falsos positivos: CpuMpDxe 17C2 e PpmInitialize 17C1 são destinos de saltos; UncoreInitPeim 150/1301 aparecem em aritmética e comparação, não como consumidores de MSR/IntelSetup demonstrados. Não repetir busca por literais sem rastrear fluxo de dados e seções executáveis.

Próxima ação: v0.12 J (descritores, identidade e callbacks passivos), I/H/U apenas se as respectivas pré-condições forem satisfeitas; R entre intervenções; coletar log completo. Em paralelo, analisar desassemblagens existentes de SpsDxe, SpsPei, MeDxePolicyInit, HeciInitDxe, IccPlatform, IccOverClocking, OcInit e CpuMpDxe. Nenhuma alteração física de BCLK ou tensão validada. Fontes das versões experimentais ainda não publicadas neste repositório.

## v0.12 — reset durante preflight J

Execução física em 27/11/2026: LocateProtocol Success, total=28 enabled=28, WhoAmI BSP Success index=0 APIC=0. Interface 79186070; slots 0–6: 79187724, 79187808, 79187938, 79187BF0, 79187D8C, 79188044, 791880E0 (endereços desta sessão, não offsets de arquivo). Reset espontâneo antes da primeira linha INFO. Fonte mp11.h confirma que após WhoAmI o loop inicializa MP_INFO e chama slot 1 (GetProcessorInfo), antes de registrar INFO. Causa exata ainda não demonstrada; investigar implementação/ABI e logging imediatamente posterior, sem presumir que chegou a StartupThisAP. H/I/U não executados. dmesg do boot posterior mostrou apenas NMI watchdog enabled no filtro MCE/Hardware Error/Watchdog/ERST/BERT; não exclui exceção pré-OS. Suspender J e intervenções MP em UEFI até analisar CpuMpDxe offline. Não repetir reboot para diagnóstico genérico.

## Análise offline após reset v0.12 — 27/11/2026

Fonte: pacote ClockLab-v12-firmware-analysis.tar.gz (oito desassemblagens), fonte local ClockLab v0.12. SHA-256 CpuMpDxe.asm 78d4bd6f185078e9579298fa0b37e6dc24e45d1d0d152710e9e821a7dc07bcec; SpsDxe.asm eaa10133c4a2d74b62c28ef2b503b6a8fb865b9d4960e3b1114ced3e2eeb840a; OcInit.asm 29418f2267549c4de985d5b5c22d048ace301f9b356ace0ffdf41825f2557c59.

**MP:** a sequência inteira dos sete métodos coincide com base de carregamento 0x79185000: RVAs 2724, 2808, 2938, 2BF0, 2D8C, 3044, 30E0. GetProcessorInfo 2808–2936 recebe RDX índice, R8 buffer, verifica BSP por WhoAmI, limite e ponteiro. Escreve ID QWORD +0, flags DWORD +8, package/core/thread DWORDs +C/+10/+14. O buffer MP_INFO de 120 bytes na v0.12 comporta a saída de 24 bytes. Não há evidência de incompatibilidade da assinatura ou overflow desse buffer pelo método. Flags enabled/health/BSP são efetivamente construídos em 28D1–291E. WhoAmI consulta APIC e percorre registros de stride 0x3D8 via [CA58]+10. A ausência de INFO após WhoAmI não distingue falha dentro do método de falha posterior de logging. StartupAllAPs usa porta I/O 0x430 (2A2D–2A38, restauração no final), exclui índice BSP em 29DB–2A0B; não presumir que callback adicional da v0.9 era BSP. Próxima sonda, se autorizada: GetProcessorInfo do BSP apenas, marcadores fixos com flush antes/depois e canários; não executar StartupAllAPs/ThisAP nem escritas MSR. Testes multicore continuam suspensos.

**EOP (consumidor confirmado estaticamente):** SpsDxe 634 aloca 0x1830 bytes; 682–6BD passa buffer+0x40 a GetVariable, nome IntelSetup (3A8), GUID EC87D643-EBA4-4BB5-A1E5-3F3E36B20DA9 (280), tamanho 0x17EC. 93D e 11C3 referenciam callback 1010; 11EE usa GUID de ReadyToBoot (2A0, 7ce88fb3-4bd7-4679-87a8-a8d8dee50d2b), 1201 registra CreateEventEx. 1043 testa [contexto+1312], equivalente a IntelSetup[12D2]. Se não zero e LocateProtocol HECI bem-sucedido, 1062–1077 monta MKHI 0x00000CFF (grupo FF, cmd 0C), 4 bytes request, 8 bytes response, host 0, destino 7, SendWithAck. 10A0 testa [contexto+1313], correspondente a IntelSetup[12D3], e se não zero aplica bits 20/31 de registrador ECAM relativo F80AC. Não alterar lock. 6ED configura EOP=1 no fallback GetVariable falho. Existe segundo caminho EOP em HeciInitDxe 2798–286B, chamada 1419, com gate GetMeMode=0 em 27F6–2807, mesmo pacote 281E–2837. Ainda falta estabelecer condições de execução desse segundo caminho e provar efeito de omitir EOP sobre ICC. IntelSetup[12D2]=1 medido em v0.11; nenhuma alteração realizada.

**OC Mailbox (estático):** OcInit PEI 32-bit VMA FFDC54BA usa opcode 10, helper FFDC5E61 e extrai ratio baixo 8 bits, mode bit 20, campos de tensão [19:8] e [31:21], com conversores FFDC57BF/582E. Notar truncamento aparente a 16 bits antes de shift do campo [19:8] em FFDC5535: não assumir decodificação completa sem revisão. FFDC557A usa opcode 11 via helper de escrita FFDC5CA0; FFDC566B usa opcode 12 e lê campo baixo 12 bits e bit 31, FFDC56E5 usa opcode 13. Backend MSR 150 demonstrado em FFDC5F8D–5FD1 e helpers RDMSR/WRMSR FFDC6A4B/6A6D. A consulta 10 já executada v0.11 retornou zero; não é leitura de Vcore físico. Não escrever tensão até mapear unidades, domínio, modo e restauração e dispor de monitoramento. Nenhum BCLK modificado. 

## ClockLab v0.13 — fonte preparado, execução pendente

O CpuMpDxe em RVA 28D8 chama helper A87C, que lê cache C9E8 ou usa LocateProtocol com GUID armazenado em 3B0 (11b34006-d85b-4d0a-a290-d5a571310ef7). Em 28E2 há chamada ao slot +18 sem teste explícito de ponteiro nulo. Dependência ausente é hipótese testável, não diagnóstico confirmado. v0.13 separa J (LocateProtocol da dependência, contagem MP e WhoAmI) de M (uma chamada GetProcessorInfo BSP, guard de layout, marcadores antes/depois, canários); exclui dispatch AP e matriz ativa do executável. O usa consulta OC Mailbox opcode 12, byte de domínio zero e payload zero conforme OcInit FFDC566B/FFDC5BAB, campos low12 e bit31 brutos. Não escreve configuração de tensão.

E/T implementam experimento opcional persistente, isolado, de IntelSetup[12D2] 1→0 e restauração 0→1, com snapshot dedicado no ESP, confirmação específica, validação integral de readback e requisito de recuperação SPI verificada. C, após reboot, compara baseline e consulta MKHI versão (controle), depois ICC 06 somente se controle válido. Nenhuma alteração dos outros campos, locks ou HMRFPO planejada; EOP=0 não prova ausência de EOP na comunicação. Não inicializar OS durante a condição experimental; restaurar e reiniciar. Sem gravação SPI direta. Não executar E antes de confirmar meios de recuperação. Fonte distribuído separadamente, SHA-256 do tar.gz 4296bbd3846a74ff3ed07bdd94bd1024631e8779bbb9ce357811b7f48bdf72e6. Teste C histórico MP12 e 13 testes Python (9 históricos + 4 verificações estáticas v13) passaram no ambiente de preparação. GNU-EFI ausente (efi.h não encontrado), compilação física e execução ainda pendentes. Nenhum aumento de tensão/BCLK demonstrado.

## v0.13 — execução diagnóstica concluída

Compilação GNU-EFI sem warnings/erros reportados, SHA-256 EFI 51db70caea2aaf902b21f6f0409d6b2923b13f9d45d397a029b72c43649d215e; teste C histórico e 13 testes Python aprovados. Log físico: EOP=1. J localizou dependência 11b34006-d85b-4d0a-a290-d5a571310ef7 em 7947A320, método +18 em 7947A620, MP total=28 enabled=28, WhoAmI BSP=0. M registrou BEFORE/AFTER GetProcessorInfo, EFI_SUCCESS, canaries=1, sem dispatch AP. Três QWORDs de saída: 0, 3, 0 (ID=0, StatusFlag=3, package/core/thread=0). StatusFlag BSP+enabled, health não marcado; explica rejeição do descritor pela validação que exigia HEALTHY na v0.11. Não comprova defeito físico nem causa exata do reset da v0.12. Hipótese de dependência ausente não observada nesta sessão. O: OC request 8000001200000000, response=0, busy=0 completion=0, 12780 ticks; low12=0 bit31=0, sem interpretação como Vcore. Operador confirmou possuir gravador SPI/adaptador e capacidade de restaurar dump caso falhe POST. Próximo experimento isolado EOP E/X/A/L/C/T/X, com confirmação específica de escrita, seleção manual ClockLab após resets, sem iniciar OS sob condição EOP=0. Não houve escrita EOP nesta execução.
