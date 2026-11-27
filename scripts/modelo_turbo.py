"""Simula decisões de PpmInitialize para o modelo 06_4f com snapshots sintéticos."""
import argparse
import json
from pathlib import Path

LIMITS = ("0x1ad", "0x1ae", "0x1af")


def unsigned(value, bits):
    if isinstance(value, str):
        value = int(value, 0)
    if type(value) is not int or not 0 <= value < 1 << bits:
        raise ValueError(f"esperado inteiro sem sinal de {bits} bits")
    return value


def construction(snapshot, ratios):
    platform_info = unsigned(snapshot["msr_ce"], 64)
    core_count = (unsigned(snapshot["msr_35"], 64) >> 16) & 0xff
    first_selector = unsigned(snapshot["msr_1ac"], 64)
    msr_194 = unsigned(snapshot["msr_194"], 64)

    result = {"core_count": core_count, "status": "blocked", "ratio_msr_writes": {},
              "ratio_msr_attempts": [], "rejected_slot": None,
              "reaches_msr_194_update": False}
    if first_selector >> 32:
        result["gate"] = "0x240a"
    elif not platform_info & (1 << 28):
        result["gate"] = "0x244c"
    elif not (msr_194 >> 17) & 7:
        result["gate"] = "0x2454"
    elif unsigned(snapshot["msr_1ac_second"], 64) >> 63:
        result.update(status="spin_on_saved_value", gate="0x26d3")
    else:
        for index, ratio in enumerate(ratios[1:core_count], start=2):
            if ratio > ratios[0]:
                result.update(gate="0x2700", rejected_slot=index)
                return result
        if core_count > len(ratios):
            result.update(status="outside_policy_array", gate="0x26f8")
            return result

        result.update(status="write_attempt", gate=None,
                      ratio_msr_attempts=list(LIMITS),
                      reaches_msr_194_update=bool(core_count and ratios[0]))
        # In this range the RMW preserves untouched bytes and ORs the policy WORD.
        # At larger counts the binary has additional branches and irregular masks.
        if core_count <= 14:
            values = [unsigned(snapshot[name], 64) for name in LIMITS]
            for index, ratio in enumerate(ratios[:core_count]):
                if ratio:
                    bank, byte = divmod(index, 8)
                    shift = byte * 8
                    word_shift = (byte % 4) * 8
                    value = ((ratio << word_shift) & 0xffffffff) << (shift - word_shift)
                    values[bank] = (values[bank] & ~(0xff << shift)) | value
            result["ratio_msr_writes"] = dict(zip(LIMITS, values))
        return result
    return result


def selection(snapshot):
    platform_info = unsigned(snapshot["msr_ce"], 64)
    capid4 = unsigned(snapshot["capid4"], 32)
    selector = unsigned(snapshot["msr_1ac"], 64)
    gate = None
    if not platform_info & (1 << 28):
        gate = "0x2be5"
    elif not capid4 & (1 << 28):
        gate = "0x2bf5"
    return {"gate": gate, "write": None if gate else {"0x1ac": selector | (1 << 63)}}


def model(build, select, ratios):
    if len(ratios) != 24:
        raise ValueError("esperados 24 WORDs de política")
    ratios = [unsigned(ratio, 16) for ratio in ratios]
    return {"construction": construction(build, ratios), "selection": selection(select)}


def main():
    cli = argparse.ArgumentParser(description=__doc__)
    cli.add_argument("scenario", type=Path, help="JSON com build, select e ratios")
    args = cli.parse_args()
    print(json.dumps(model(**json.loads(args.scenario.read_text())), indent=2))


if __name__ == "__main__":
    main()
