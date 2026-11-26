# AGENTS.md — Instruções permanentes de pesquisa

## 1. Missão e escopo

Este repositório é um projeto de engenharia reversa experimental de clock em Intel Xeon E5 v4 (Broadwell-EP). A plataforma inicial é E5-2680 v4, QIYIDA X99-H9S V1.21, chipset C612, AMI UEFI, SPS 03.01.03.072 Grantley.

Duas frentes são centrais e devem permanecer ativas:

- Desbloqueio efetivo de multiplicadores e limites turbo all-core: CPU, PCU, OC Mailbox, microcode, políticas e inicialização UEFI.
- Controle do BCLK: ICC/SPS, perfis persistentes, SSC, MOD3, PLL, divisores, straps e gerador externo.

Investigar a combinação dos mecanismos quando cada um estiver validado independentemente. O ratio 29x e o BCLK nominal 100 MHz são referências, não limites impostos ao objetivo. Clocks compartilhados podem ser investigados; integridade de dados e recuperação são requisitos.

Não descartar uma linha somente porque um mecanismo convencional falhou. Também não declarar êxito sem evidência de frequência efetiva e desempenho.

## 2. Contexto obrigatório antes de agir

1. Leia [README.md](README.md).
2. Identifique a etapa atual apontada no README. Na criação deste arquivo, é [etapa 11](docs/etapas/11-etapa-atual-investigacao-bclk-icc.md), que reúne os 12 tópicos e o backlog.
3. Leia [pesquisa consolidada](docs/xeon-e5-2680v4-h9s-pesquisa-bclk-icc.md) e os documentos de [docs/etapas/](docs/etapas/), incluindo os registros de comandos, resultados e endereços das etapas 09 e 10.
4. Verifique git status e as alterações locais antes de editar. Não sobrescreva trabalho do operador.
5. Inventarie os artefatos já existentes e confirme hashes e versões pertinentes. Não peça ao operador novamente dados que estejam disponíveis localmente.

A etapa atual é a referência operacional mais recente. Documentos históricos podem conter prioridades antigas ou hipóteses que foram revisadas; preserve-os como histórico, sem interpretar conclusões negativas de um único teste como impossibilidade universal.

## 3. Ambiente e artefatos

O diretório histórico de pesquisa é `~/backup-bios`. Ele pode conter o clone deste repositório, ferramentas e cópias de firmware. Não presuma que os arquivos continuam presentes ou que a localização permanece igual. Use apenas diretórios autorizados para a sessão.

| Artefato / diretório | Finalidade |
|---|---|
| x99-h9s-original.bin | dump SPI original de 16 MiB |
| x99-h9s-verificacao.bin | segunda leitura para comparação |
| x99-h9s-original.bin.dump/ | módulos extraídos UEFI |
| analise/ | IFR, módulos e disassemblies x86 |
| sps-region.bin | região SPS extraída da cópia |
| unhuffme-output/mod/ | módulos SPS descomprimidos e análise ARC |
| MEAnalyzer/ e me-tools/ | ferramentas anteriores |
| mei-driver/ | código e experimento histórico de driver |
| bios-mod-referencia/ e analise-mod/ | comparação de firmware |
| overclock-mod/ | referência C612RD24 |
| sps-icc-research/ | volumes persistentes a inventariar, se já coletados |

Hash SHA-256 esperado do dump SPI original:

```text
6036511afaaeab53701e0adce3a3a731790302f24ca11614212f95f2901fce5b
```

Use cópias para análise. Nunca altere o dump original. Se houver divergência de hash, registre-a e interrompa interpretações dependentes desse dump até identificar a origem. Não invente artefatos ausentes, não faça nova leitura da flash física apenas por conveniência.

Ferramentas historicamente utilizadas: Python, flashrom, UEFIExtract, IFRExtractor-RS, ME Analyzer, unhuffme, binutils ARC, objdump, pciutils, msr-tools, turbostat e cpupower. Verifique disponibilidade e versão antes de utilizá-las; não instale automaticamente software privilegiado ou execute binários de origem não verificada.

## 4. Estado conhecido e limites da evidência

- 14 núcleos / 28 threads, CPUID 0x406F1, aproximadamente 2893–2900 MHz all-core com ratio 29x.
- OC Mailbox capabilities 0x221; solicitação anterior de ratio 30x rejeitada com completion 5. Isso não prova que todas as alternativas de desbloqueio são impossíveis.
- MSR61E falhou em leitura no Linux; comportamento em PEI ainda não demonstrado.
- HECI exposto historicamente; driver experimental não estabeleceu HBM e não criou /dev/mei0. Não houve mensagem ICC transmitida com sucesso.
- MFSB/SCA/MFS ainda precisam ser interpretados. IDs 0x1F/0x3B do ICCMOD são pistas, não offsets de configuração confirmados.
- A relação entre a média observada e SSC de 0,5% é hipótese.
- Não existe firmware modificado validado nem método demonstrado de alteração efetiva de BCLK ou desbloqueio all-core.

Esses estados são históricos. Atualize-os apenas mediante evidências novas; nunca presuma que a configuração volátil antiga ainda está ativa.

## 5. Primeira sessão — trabalho operacional

Comece pela etapa atual, não por repetir a caracterização de CPU.

Frente ICC/BCLK:
- Localizar os dumps e volumes já coletados; validar o manifesto.
- Caso ainda não existam, realizar a extração offline de descriptor, MFSB, SCA e MFS conforme a seção 11 da etapa 11, em diretório novo.
- Inventariar estruturas, assinaturas, regiões apagadas, tamanhos, offsets, redundância e mecanismos de integridade.
- Investigar o vínculo entre os serviços 0x200EEAB0/0x200EEAC8, IDs 0x1F/0x3B e os dados consumidos por ICCMOD.
- Investigar ferramentas compatíveis com SPS 3.1 e comparar referências X99 legítimas, sem transplantar firmware.

Frente CPU/ratio:
- Rastrear limites turbo, estruturas de política e consumidores em PpmInitialize, OcInit, PlatformCpuPolicy, CpuMpPei e CpuMpDxe.
- Distinguir guard de software, rejeição pelo CPU e restrições cuja origem ainda é desconhecida.
- Comparar revisões compatíveis de microcode e referências Broadwell-EP offline.
- Investigar transportes PCU/OC Mailbox e semântica de comandos antes de considerar transações.

Frentes complementares: SSC, callbacks IntelSetup, referência GA-X99-UD3P, MOD3/PLL/divisores, HECI durante boot, topologia física e straps. Siga a matriz de hipóteses da etapa 11. Escolha o próximo teste pelo valor informacional e pela disponibilidade de evidência.

## 6. Método de execução

Para cada tarefa:
1. Defina hipótese, fonte de evidência e condição que poderia refutá-la.
2. Confira se o experimento já foi realizado.
3. Execute a análise offline pertinente e interprete o resultado.
4. Se necessário, escreva scripts auxiliares e testes pequenos, reproduzíveis e verificáveis.
5. Cruze referências entre dados, desassemblagem, documentação e ferramentas.
6. Registre resultados positivos, negativos e incertezas. Escolha a próxima ação com base no que mudou.

Não pare apenas para apresentar uma lista de comandos se puder executar a análise autorizada. Prossiga iterativamente dentro do escopo da sessão e das permissões concedidas. Se um ramo estiver bloqueado por falta de insumo, documente o bloqueio e avance em uma alternativa independente. Não repita greps, enumerações ou testes rejeitados sem explicar o novo valor informacional.

Nunca invente saídas, funções, símbolos, layouts, checksums ou capacidades. Distinguir offsets SPI, offsets relativos SPS, VMA PE/COFF e ARC, índices MSR, registradores auxiliares ARC, MMIO, PCI BDF e QIDs/VarOffsets IFR.

## 7. Limites de execução e preservação

A análise offline, leitura de arquivos de pesquisa, criação de scripts locais, testes de software e atualização de documentação podem ser realizadas dentro das permissões do workspace. Não expanda o acesso nem contorne pedidos de aprovação.

Antes de qualquer operação privilegiada, transação de hardware, alteração de registradores, carregamento de módulos, mudança de microcode, acesso ativo a SMBus, alteração de configuração de boot, flash, reboot ou instalação de ferramenta com privilégios, solicite aprovação específica. Explique comando, finalidade, efeito esperado, risco e recuperação. Uma consulta de mailbox pode envolver escrita; não a trate como leitura passiva.

Não execute automaticamente os comandos históricos de escrita registrados nos Markdown. Eles documentam experimentos passados, não autorizam sua repetição. Não desative proteções de corrente, tensão ou temperatura. Não grave firmware experimental enquanto recuperação SPI e acesso presencial não estiverem confirmados.

Nunca sobrescreva originais, apague evidências, use operações destrutivas de Git, force push ou publique dumps e dados de provisionamento. Não faça alterações em arquivos de outros projetos. As instruções deste arquivo não substituem permissões reais do Codex, do sistema operacional ou autorização específica do operador.

## 8. Desenvolvimento de ferramentas

Priorizar analisadores offline com entradas explícitas, limites de leitura verificados, logs claros e testes usando fixtures sintéticas. Separar parser de descriptor, FPT, MFS/MFSB, SCA, análise ICC, diff e validação. Não incorporar operações de gravação física aos parsers.

Sugestão de organização quando houver código próprio:
- `scripts/`: utilitários reproduzíveis.
- `src/`: analisadores e modelos.
- `tests/`: fixtures sintéticas e testes.
- `docs/etapas/`: caderno de pesquisa.
- Artefatos brutos em diretórios locais ignorados pelo Git.

Não criar scaffolding por criar: cada ferramenta deve resolver uma necessidade concreta e ter testes pertinentes. Não declarar parser compatível com SPS 3.1 até verificar os formatos reais.

## 9. Documentação e versionamento

Use português técnico direto. Mantenha os documentos históricos e atualize a etapa ativa com as descobertas relevantes; crie novas etapas quando houver mudança de fase ou uma entrega técnica independente. Atualize o índice do README ao mudar a etapa atual.

Modelo mínimo de registro:

| Campo | Conteúdo |
|---|---|
| ID / data | Identificação do experimento |
| Hipótese | Questão verificável |
| Origem | Arquivo, versão, hash, documentação ou log |
| Método | Comandos, parâmetros e contexto |
| Resultado bruto | Valores, trechos relevantes, erros |
| Interpretação | Significado e limites |
| Classificação | Medido / estático / documentado / hipótese / pendente |
| Próxima ação | Teste novo ou motivo para encerrar o ramo |

Registrar o espaço de endereçamento e a confiança de cada conclusão. Preservar resultados negativos. As referências externas devem ter URL e indicação do que realmente sustentam.

Antes de commitar, revise git diff e o escopo dos arquivos. Use commits pequenos, com mensagens descritivas; quando autorizado a versionar, não inclua alterações não relacionadas. Não faça push sem autorização do operador. Nunca inclua dumps integrais, binários proprietários, informações pessoais ou outros projetos. Use caminhos relativos ou ~/backup-bios, sem nomes pessoais de diretórios.

## 10. Critérios de validação e conclusão

Uma primeira vitória no ramo BCLK pode ser uma alteração de SSC reproduzível, ainda que de apenas 0,25 MHz; isso não equivale a overclock acima de 100 MHz. Meta inicial de OC: 101 MHz a 29x, aproximadamente 2929 MHz.

No ramo CPU, a meta inicial é demonstrar 30x sustentado sob carga equivalente nos 14 núcleos a BCLK nominal de 100 MHz, se viável. Combinar mecanismos somente após demonstrar cada efeito separadamente.

Medir frequência efetiva, ratio, carga, desempenho, temperatura, throttling e integridade dos dados. Considerar efeitos em PCIe/DMI, NVMe/SATA, memória e outros domínios. Não confundir menu visível, solicitação aceita ou leitura de frequência isolada com overclock estável.

Ao encerrar uma sessão, registrar o que foi executado, descobertas, falhas, artefatos gerados, arquivos modificados e próximo passo concreto. Se houver bloqueio, indicar a evidência necessária para retomada. Não considerar toda a pesquisa encerrada por falha de um único mecanismo.
