# Xeon v4 Clock Research

![Status](https://img.shields.io/badge/status-research-yellow)
![Platform](https://img.shields.io/badge/platform-Intel%20Broadwell--EP-blue)
![Chipset](https://img.shields.io/badge/chipset-C612-blue)

Pesquisa independente de engenharia reversa para identificar, implementar e validar um método reproduzível de alteração de clock em processadores Intel Xeon E5 v4 (Broadwell-EP), especialmente modelos com multiplicador bloqueado.

> **Fase atual: levantamento de requisitos e estudos técnicos (R&D).** O projeto ainda não disponibiliza uma solução funcional de overclock, firmware modificado ou ferramenta de gravação.
>
> **[ETAPA ATUAL — 11: Investigação ativa de BCLK, SSC, ICC e caminhos alternativos](docs/etapas/11-etapa-atual-investigacao-bclk-icc.md).** Consulte primeiro este documento: ele reúne os 12 tópicos da análise de continuidade e o plano operacional.

## Objetivo

Investigar mecanismos de controle do Base Clock (BCLK) e de desbloqueio efetivo do multiplicador/limites turbo do próprio processador, por meio de engenharia reversa de firmware UEFI, Intel Server Platform Services (SPS), políticas CPU, PCU e microcode. Ambas as frentes permanecem ativas, buscando aumentar a frequência efetiva da CPU acima do turbo all-core original. O foco inicial é o Xeon E5-2680 v4 na QIYIDA X99-H9S V1.21. A compatibilidade com outros modelos será avaliada posteriormente, com evidências específicas de cada plataforma.

## Plataforma de referência

| Componente | Configuração |
|---|---|
| CPU | Intel Xeon E5-2680 v4 — 14 núcleos / 28 threads |
| Placa-mãe | QIYIDA X99-H9S V1.21 |
| Chipset | Intel C612 (PCI LPC `8086:8d44`) |
| Firmware | AMI UEFI / Intel SPS 03.01.03.072 (Grantley) |
| BCLK nominal | 100 MHz |
| Turbo all-core observado | ~2,90 GHz (29x) |
| Ambiente | Ubuntu / Linux |

### Metas experimentais

| BCLK | All-core teórico (29x) | Ganho nominal |
|---:|---:|---:|
| 100 MHz | 2,900 GHz | Baseline |
| 101 MHz | 2,929 GHz | +1% |
| 103 MHz | 2,987 GHz | +3% |
| 105 MHz | 3,045 GHz | +5% |
| 110 MHz | 3,190 GHz | +10% |

As frequências acima são projeções matemáticas, não resultados alcançados. Alterações nos demais domínios de clock são aceitáveis para a pesquisa; o isolamento de PCIe/DMI não é requisito obrigatório. A integridade de dados e a estabilidade devem, contudo, ser verificadas experimentalmente.

## Estado da investigação

- [x] Caracterização da plataforma e baseline de frequência.
- [x] Backup SPI consistente e identificação das partições SPS.
- [x] Extração e análise inicial de módulos UEFI e ICC.
- [x] Teste do OC Mailbox: solicitação de ratio 30x rejeitada.
- [x] Investigação HECI/MEI: dispositivo exposto, inicialização HBM malsucedida.
- [x] Comparação de versões alternativas do OcInit.
- [ ] Interpretar os dados persistentes do ICC no SPS 3.1.
- [ ] Identificar ferramenta ou método compatível de análise dos perfis.
- [ ] Confirmar topologia do clock e a atuação do MOD3 sobre o BCLK.
- [ ] Projetar um analisador offline com validação estrutural.
- [ ] Produzir e validar um candidato experimental.
- [ ] Demonstrar aumento real do BCLK, estabilidade e recuperação.
- [ ] Investigar desbloqueio efetivo de ratio e limites turbo; demonstrar pelo menos 30x all-core a BCLK nominal, se viável.

## Linhas de pesquisa

| Linha | Prioridade | Situação |
|---|---|---|
| Perfis ICC persistentes no SPS original | Principal | Estrutura binária ainda não decodificada |
| Gerador de clock e moduladores | Alta | Topologia física pendente |
| HECI e protocolo ICC | Complementar | Comunicação não validada |
| OcInit e BCLK Strap | Complementar | Restrições e pré-condições em estudo |
| Desbloqueio de multiplicador, turbo, PCU e microcode | Alta (estudos offline em paralelo) | Ratio 30x rejeitado pelo mecanismo testado; outras hipóteses permanecem abertas |

## Agentes de pesquisa (Codex)

O arquivo [AGENTS.md](AGENTS.md), na raiz, reúne as instruções permanentes para agentes: contexto obrigatório, localização dos artefatos, duas frentes de investigação, método de execução, preservação de evidências, limites de operações em hardware e critérios de validação. Abra o clone no VS Code e disponibilize o diretório de pesquisa local conforme as permissões da sessão.

## Documentação

### Pesquisa consolidada

**[Engenharia reversa do BCLK — Xeon E5-2680 v4 / QIYIDA X99-H9S](docs/xeon-e5-2680v4-h9s-pesquisa-bclk-icc.md)**

O documento principal permanece como referência da investigação de 26/11/2026. As etapas abaixo reorganizam essa base, acrescentam catálogos, fluxos, procedimentos de auditoria e requisitos para continuidade. Não representam novas execuções em hardware.

### Caderno técnico por etapas

| Etapa | Documento |
|---|---|
| 01 | [Plataforma, baseline, CPUID, MSRs e OC Mailbox](docs/etapas/01-plataforma-cpu-msr.md) |
| 02 | [Flash SPI, descriptor, FPT, offsets e recuperação](docs/etapas/02-flash-spi-sps.md) |
| 03 | [Boot, módulos PEI/DXE, IFR, NVRAM e políticas](docs/etapas/03-boot-uefi-intelsetup.md) |
| 04 | [PCI, HECI, MMIO, driver MEI e protocolo ICC](docs/etapas/04-heci-pci-mmio.md) |
| 05 | [ICCMOD, ARC, rotinas, filas, MOD3 e SMBus](docs/etapas/05-iccmod-clock-smbus.md) |
| 06 | [BIOS alternativas, ferramentas e compatibilidade](docs/etapas/06-comparacao-firmware-ferramentas.md) |
| 07 | [Requisitos, arquitetura proposta, plano e validação](docs/etapas/07-requisitos-plano-validacao.md) |
| 08 | [Manifesto de hashes, cronologia e endereçamento](docs/etapas/08-evidencias-cronologia.md) |
| 09 | [Caderno de comandos e resultados brutos](docs/etapas/09-caderno-comandos-resultados.md) |
| 10 | [Mapa de funções, estruturas e condições de boot](docs/etapas/10-mapa-funcoes-estruturas.md) |
| **11 — Atual** | [Investigação ativa: BCLK, SSC, ICC e caminhos alternativos](docs/etapas/11-etapa-atual-investigacao-bclk-icc.md) |

**Leitura recomendada:** iniciar pela etapa 11, que contém o contexto e a estratégia atuais. Consultar etapas 01 a 06 para entender as evidências, etapa 07 para executar o plano de pesquisa, etapa 08 para localizar artefatos e conferir a rastreabilidade; etapas 09 e 10 para revisar os comandos históricos, valores brutos, funções privadas e estruturas de baixo nível.

```text
xeon-v4-clock-research/
├── README.md
├── AGENTS.md
├── .gitignore
└── docs/
    ├── xeon-e5-2680v4-h9s-pesquisa-bclk-icc.md
    └── etapas/
        ├── 01-plataforma-cpu-msr.md
        ├── 02-flash-spi-sps.md
        ├── 03-boot-uefi-intelsetup.md
        ├── 04-heci-pci-mmio.md
        ├── 05-iccmod-clock-smbus.md
        ├── 06-comparacao-firmware-ferramentas.md
        ├── 07-requisitos-plano-validacao.md
        ├── 08-evidencias-cronologia.md
        ├── 09-caderno-comandos-resultados.md
        ├── 10-mapa-funcoes-estruturas.md
        └── 11-etapa-atual-investigacao-bclk-icc.md
```

## Roadmap

1. **Levantamento de requisitos e estudos — fase atual:** consolidar evidências, reunir dados persistentes do SPS, investigar a compatibilidade das ferramentas e documentar hipóteses.
2. **Engenharia reversa:** interpretar as estruturas de configuração do ICC e estabelecer o vínculo com os domínios físicos de clock.
3. **Prototipagem offline:** desenvolver um analisador reproduzível e validar formatos e diferenças binárias antes de qualquer alteração física.
4. **Validação experimental:** testar uma alteração isolada de frequência em ambiente recuperável, medir desempenho, estabilidade e integridade de dados.
5. **Documentação e expansão:** registrar o procedimento efetivamente validado e avaliar outras placas e CPUs Xeon v4.

## Critérios de validação

Uma solução não será considerada funcional apenas por exibir opções ocultas na BIOS, aceitar uma solicitação de ratio ou responder a um comando. Será necessário demonstrar frequência efetiva acima do baseline, desempenho reproduzível sob carga equivalente e ausência de erros nos testes executados. Os resultados devem identificar a revisão da placa, firmware, CPU e condições experimentais.

## Contribuições e evidências

Relatos devem distinguir resultados medidos, observações de engenharia reversa, documentação pública e hipóteses. Registre versões, hashes e logs relevantes, removendo identificadores sensíveis antes de compartilhá-los. Não inclua dumps integrais de firmware, binários proprietários, dados de configuração específicos de uma máquina ou credenciais no repositório.

## Aviso técnico

Projeto experimental, não afiliado à Intel nem à QIYIDA. Alterações no firmware e em clocks compartilhados podem impedir o POST ou corromper dados. Experimentos de escrita exigem meios de recuperação e acesso físico. Nenhuma licença de redistribuição de firmware de terceiros é presumida; uma licença para código próprio será definida quando houver implementação.
