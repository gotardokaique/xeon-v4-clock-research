# Etapa 07 — Requisitos, arquitetura proposta e validação experimental

> Fase: levantamento de requisitos e estudos. Registro derivado da [pesquisa consolidada](../xeon-e5-2680v4-h9s-pesquisa-bclk-icc.md), de 26/11/2026. Não representa novos testes em hardware.

Objetivo: converter os resultados anteriores em requisitos verificáveis, entregáveis e critérios de conclusão.



## Requisitos de pesquisa

| ID | Requisito | Critério verificável | Estado |
|---|---|---|---|
| RF-01 | Interpretar descriptor SPI | regiões, offsets e limites corretamente reportados | mapa manual disponível |
| RF-02 | Interpretar FPT SPS | inventário coerente com dump e ME Analyzer | mapa manual disponível |
| RF-03 | Identificar configuração persistente ICC | registro, tipo, tamanho, offset e referência cruzada | pendente |
| RF-04 | Decodificar representação de frequência | alteração diferencial de um único parâmetro | pendente |
| RF-05 | Relacionar configuração com MOD3 / CPU BCLK | evidência de documentação, código e teste | pendente |
| RF-06 | Exportar relatório e diferenças | JSON/Markdown, hashes, offsets e confiança | proposto |
| RF-07 | Demonstrar 101 MHz e ganho efetivo | frequência, carga equivalente e desempenho | pendente |
| RNF-01 | Preservar firmware de referência | original não alterado e hash conferido | satisfeito no histórico |
| RNF-02 | Análise inicial sem escrita em hardware | ferramenta offline, entradas locais | proposto |
| RNF-03 | Reprodutibilidade | versões, hashes, comandos e resultados | parcial |
| RNF-04 | Recuperação | restauração presencial e backup externo verificados | pendente |
| RNF-05 | Privacidade e distribuição | não publicar dumps, chaves ou binários proprietários | política definida |

O proprietário aceita investigar clocks compartilhados; isolamento PCIe/DMI não é requisito obrigatório. A estabilidade e a integridade dos dados continuam critérios de validação.

## Interfaces de software propostas (ainda não implementadas)

| Componente | Responsabilidade | Entrada | Saída |
|---|---|---|---|
| DescriptorParser | interpretar mapa SPI | bytes da imagem | regiões e permissões |
| PartitionTableParser | interpretar FPT | bytes SPS | lista de partições |
| MfsParser | identificar registros e redundância | MFS/MFSB | registros e metadados |
| ScaParser | interpretar SCA | bytes SCA | registros candidatos |
| IccProfileAnalyzer | correlacionar campos ICC | registros e referências | perfil candidato |
| BinaryDiff | comparar amostras | duas imagens ou partições | intervalos alterados |
| Validator | checar limites e invariantes | imagem, metadados | relatório de validação |

Os nomes acima são **classes conceituais** para futura implementação Python, não símbolos existentes na BIOS ou no SPS. Assinaturas e modelo de domínio serão definidos depois de validar o formato.

## Modelo de registro de evidência

```json
{
  "source": "MFS",
  "offset_relative": null,
  "offset_spi": null,
  "length": null,
  "field": "unknown",
  "encoding": "unknown",
  "reference": null,
  "confidence": "hypothesis",
  "hardware_validated": false
}
```

Não preencher posições ou formatos desconhecidos com valores inventados. Separar tipos de endereçamento e evidência estática de resultado experimental.

## 16. Matriz de decisão

| Ramo | Evidência atual | Ganho potencial | Decisão |
|---|---|---|---|
| MSR/ratio 30x | rejeição real | improvável por este método | suspender |
| Patch PpmInitialize | guard de software conhecido, CPU rejeita ratio | incerto | suspender como via de ratio |
| Remover guard OcInit | caminho PLL alcançável, MSR61E falha em runtime | incerto | só após análise de pré-condições |
| C612RD24 OcInit | guarda e layout incompatível | não comprovado | não transplantar isoladamente |
| Driver MEI normal/quirk bypass | HBM não inicializa | nenhum ganho direto | não repetir |
| HECI connectionless | transporte e filas localizados | consulta em runtime, eventual ajuste | secundário, protocolo pendente |
| Configuração persistente ICC | arquitetura Intel documentada | alvo real do BCLK se suportado | **prioridade 1** |
| PLL externo | opção CK420, sem identificação física | depende da placa | prioridade 2 quando identificável |
| Trocar SPS por M1/ME desktop | incompatibilidades, pacote não obtido | incerto | último recurso, nunca primeiro teste |
| Downgrade de microcode | nenhuma prova v4 | incerto | não priorizar |

## 17. Plano de ação operacional

### Fase 0 — Preservação e baseline

- [x] Dois dumps SPI idênticos; original protegido.
- [x] Turbo all-core aproximado e bloqueio de ratio registrados.
- [ ] Copiar backups para outro computador/armazenamento e validar recuperação presencial.
- [ ] Capturar baseline reproduzível de CPU, memória, armazenamento e AER/MCE.
- [ ] Confirmar governor e limites de frequência atuais; verificar alteração parcial de CPU0.

### Fase 1 — Coletar os dados persistentes do SPS (próxima ação concreta)

Extrair descriptor, MFSB, SCA e MFS da cópia original. Não precisamos ler novamente a flash física nem enviar o dump completo. O bloco abaixo é somente leitura do arquivo original; cria arquivos separados para análise.

```bash
cd ~/backup-bios
mkdir -p sps-icc-research
python3 - <<'PY'
from pathlib import Path
import hashlib

src = Path('x99-h9s-original.bin')
rom = src.read_bytes()
expected = '6036511afaaeab53701e0adce3a3a731790302f24ca11614212f95f2901fce5b'
actual = hashlib.sha256(rom).hexdigest()
assert len(rom) == 16 * 1024 * 1024, 'Tamanho incorreto'
assert actual == expected, 'Hash diferente do dump de referência'
regions = {
    'descriptor': (0x000000, 0x1000),
    'MFSB': (0x002000, 0x10000),
    'SCA':  (0x012000, 0x10000),
    'MFS':  (0x042000, 0x40000),
}
folder = Path('sps-icc-research')
manifest = [f'original {actual}']
for name, (offset, size) in regions.items():
    data = rom[offset:offset+size]
    assert len(data) == size
    (folder / f'{name}.bin').write_bytes(data)
    line = f'{name} offset=0x{offset:06x} size=0x{size:x} sha256={hashlib.sha256(data).hexdigest()}'
    print(line)
    manifest.append(line)
(folder / 'manifest.txt').write_text('\n'.join(manifest)+'\n')
PY
```

Somente se o Python terminar sem erros:

```bash
tar -czf sps-icc-research.tar.gz sps-icc-research
tar -tzf sps-icc-research.tar.gz
xdg-open "$PWD"
```

Enviar `sps-icc-research.tar.gz` de forma privada. **Ainda não foi recebido na data deste documento.** Os volumes podem conter configuração específica da plataforma.

### Fase 2 — Implementar analisador offline, não editor

Projeto proposto `sps-icc-analyzer` em Python, sem acesso direto a `/dev/mem`, flashrom, MSRs ou SMBus.

```text
sps-icc-analyzer/
├── README.md
├── firmware/                 # local, ignorado pelo Git
├── src/
│   ├── descriptor.py
│   ├── partition_table.py
│   ├── mfs_parser.py
│   ├── sca_parser.py
│   ├── icc_parser.py
│   ├── binary_diff.py
│   └── validator.py
├── profiles/                 # esquemas decodificados, sem dados privados
├── tests/                    # fixtures sintéticas e testes unitários
└── main.py
```

Entregas:

1. Parser do descriptor e FPT, com limites, intervalos, versão de header, offsets relativos/absolutos e hashes.
2. Identificação de blocos apagados, assinaturas, páginas, sequências de registros e possíveis checksums em MFSB/SCA/MFS.
3. Testar meimagetool/parseMFS em cópias e validar se reconhecem corretamente a geração. Saída de parser moderno não é evidência suficiente; comparar offsets, tamanho, magic e conteúdo bruto.
4. Correlacionar as chamadas internas do ICCMOD (IDs 0x1F/0x3B, tamanhos 12/8) com configuração persistente; completar análise de HOSTCOMM e POLICY. Procurar relações entre estruturas, não apenas ocorrências de `100`, `101`, `100000000` ou `MOD3`.
5. Exportar inventário e resultados em JSON/Markdown, incluindo offset, tamanho, origem, interpretação, confiança e campos desconhecidos.

**Critério de saída:** identificar pelo menos um registro plausível de configuração ICC com referência cruzada do código ou de uma ferramenta compatível. Nenhuma escrita em firmware nessa fase.

### Fase 3 — Obter referência oficial ou diferencial

- Procurar spsFITc e seus dados de plataforma para Grantley 3.1. Verificar versão, origem e compatibilidade antes de executar. Ambiente isolado, sem acesso ao hardware real.
- Testar abertura de uma cópia do dump e exportação de configuração. Se falhar, registrar a mensagem; não forçar outra plataforma.
- Se houver campos ICC utilizáveis, gerar dois arquivos offline com uma única alteração conhecida, mantendo os demais parâmetros iguais. Comparar regiões e analisar impacto de normalização/rebuild.
- Se não houver ferramenta compatível, comparar dumps da mesma versão SPS e plataforma com parâmetros de clock conhecidos. A diferença pode incluir dados de provisionamento e NVRAM, portanto não é automaticamente o perfil ICC.
- Identificar representação de frequência, faixa, spread, divisores e política. Confirmar MOD3 e distinguir frequência nominal de ajustes de modulação.

**Critério de saída:** relação causal reproduzível entre um parâmetro de clock identificado e sua representação binária, com validação independente (ferramenta, fluxo de código ou múltiplos pares de amostras controladas). Caso contrário, manter hipótese aberta.

### Fase 4 — Candidato de imagem experimental offline

Somente após a fase 3: preparar uma imagem derivada que altere o mínimo de dados necessário para uma configuração nominal de 101 MHz, se suportada. Preservar dados de placa, descriptor, executáveis SPS e BIOS. Entender e preservar checksums, redundância, estado de arquivos e eventuais mecanismos de assinatura/autenticação; não tratar bypass de integridade como solução genérica. Validar tamanho, regiões e diferenças; documentar manifestos e possibilidade de restauração. Primeiro gerar e validar um rebuild sem alteração funcional para detectar mudanças inesperadas da ferramenta.

Não há, neste documento, offset confirmado nem patch pronto para 101 MHz. Não se deve fabricar uma imagem por substituição de uma sequência binária semelhante a 100 MHz. A validação offline é necessária, mas não suficiente para provar boot e estabilidade.

### Fase 5 — Teste físico e validação de frequência

**Pré-requisitos:** acesso físico e recuperação SPI disponível; backup de arquivos críticos em outro dispositivo; armazenamento de teste descartável ou cópia recuperável; console local. O proprietário aceita clocks acoplados, portanto não é necessário abandonar o experimento apenas por afetar PCIe/DMI. Porém, não testar primeiro em um disco com dados insubstituíveis.

Sequência de metas: baseline 100 → 101 → 102 → 103 → 104 → 105 MHz. Só avançar após validar a etapa anterior. Passos adicionais (107, 110 ou straps) exigem nova avaliação e não são garantidos. Não alterar tensão, limites de potência ou spread simultaneamente ao primeiro teste de frequência. Se a plataforma exigir um reset global/cold boot, confirmar isso na documentação da ferramenta e assegurar acesso local.

Medições de referência (se ferramentas estiverem instaladas):

```bash
lscpu
cpupower frequency-info
sudo turbostat --quiet --interval 2 --num_iterations 10
sudo journalctl -k -b --no-pager | grep -iE 'mce|machine check|hardware error|aer|pcie|nvme|ata|i/o error|edac'
lsblk -o NAME,SIZE,FSTYPE,MOUNTPOINTS,MODEL
```

Executar `turbostat` durante a mesma carga utilizada no baseline; registrar temperatura, Busy%, Bzy_MHz, throttling e potência. Usar benchmark de CPU com carga definida e tempo externo/independente quando possível: uma referência derivada do TSC pode ser influenciada pelo clock, então não aceitar apenas uma leitura de frequência ou valor DMI como prova. Confirmar também desempenho real, ratios e ausência de regressões.

Testes mínimos por etapa:

- Inicialização normal e estabilidade em idle/carga CPU sustentada.
- Teste de memória; comparar resultados de compilação/benchmark e hashes determinísticos.
- PCIe/GPU, NVMe, SATA, USB e rede: erros de link, resets, retries, falhas de checksum e corrupção. Validar leitura e escrita em arquivos descartáveis com hashes antes/depois; não realizar testes destrutivos sobre discos de produção.
- Comparar eventos AER/MCE/EDAC e saúde do armazenamento antes/depois; monitorar temperatura e throttling.
- Reiniciar e conferir persistência, quando houver acesso presencial e recuperação.

**Critério de sucesso inicial:** aumento verificável do BCLK ou de frequência efetiva acima do baseline, mantendo 29x sob carga equivalente, acompanhado de ganho mensurável e sem erros nos testes realizados. A ausência de erros durante um teste curto não prova estabilidade de longo prazo.

**Critério de interrupção/rollback:** ausência de POST, desconexões, erros de I/O ou de memória, AER/MCE, perda de desempenho, throttling anormal ou divergência de hashes. Restaurar configuração/dump original pelo método de recuperação previamente validado.

### Fase 6 — Ramo paralelo, caso os dados ICC não sejam editáveis

- Determinar a topologia física de clock e identificar eventual PLL externo.
- Completar a análise de protocolo HECI, HOSTCOMM e POLICY para verificar se existe consulta autorizada após o POST. Só implementar um cliente de teste quando o comando e a compatibilidade forem conhecidos. Não desabilitar End Of POST ou outras proteções cegamente.
- Investigar por que MSR61E não está acessível em runtime e se as rotinas de strap têm pré-condições adicionais no PEI. Um patch de guard só deve ser avaliado depois que a execução subsequente estiver compreendida.
- Se todos os caminhos forem incompatíveis, registrar conclusão negativa específica desta placa/firmware. Não inferir impossibilidade universal do Xeon v4 nem prometer ganho sem mecanismo verificável.

## 18. Handoff: como retomar sem repetir a investigação

**Estado mais recente:** 2,9 GHz all-core, HECI exposto mas sem HBM e sem cliente ICC testado. OC Mailbox rejeita ratio 30x. Firmware executável ICC disponível e parcialmente analisado. Mod C612RD24 não fornece solução demonstrada e tem layout incompatível. SPS persistente permanece original. Não houve flash modificada nem aumento comprovado de BCLK.

**Próxima entrega necessária:** `sps-icc-research.tar.gz`, conforme fase 1. Ao recebê-lo, começar por validar o manifesto e interpretar MFSB/SCA/MFS; não pedir novamente lspci, rdmsr de ratio, IFR de clock ou descompactação dos módulos já disponíveis.

**Perguntas técnicas ainda abertas:**

1. Onde está a configuração ICC inicial nesta versão de SPS? MFS, MFSB, SCA ou outro armazenamento?
2. IDs internos 0x1F/0x3B representam registros de configuração de clock ou outra função?
3. Qual ferramenta/versão interpreta esses volumes sem substituir o SPS original?
4. Existe ajuste de frequência de MOD3 autorizado para a configuração do C612 da H9S?
5. O CLKOUT_DMI alimenta efetivamente o CPU nesta revisão física? Existe PLL externo?
6. Quais domínios e divisores mudam juntos? Que representação de frequência é usada?
7. O firmware aceita o protocolo ICC da BIOS após EOP, ou somente em determinada fase/cliente?
8. É possível medir 101 MHz e 2,929 GHz all-core de forma independente e reproduzível?

**Regra para a continuação:** distinguir endereço localizado de função compreendida; função compreendida de comando suportado; comando suportado de alteração física; alteração física de overclock estável. O objetivo é o último, não apenas mostrar menus ou obter respostas de registradores.

**Saída:** plano operacional e critérios definidos; nenhuma ferramenta de alteração funcional foi implementada. Próximo: [manifesto e rastreabilidade](08-evidencias-cronologia.md).
