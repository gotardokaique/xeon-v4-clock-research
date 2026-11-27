import unittest

from scripts.modelo_turbo import model


class TurboModelTests(unittest.TestCase):
    def setUp(self):
        self.build = dict(msr_ce=1 << 28, msr_35=14 << 16, msr_194=1 << 17,
                          msr_1ac=0, msr_1ac_second=0,
                          **{"0x1ad": 0x1d1d1d1d1d1d2121,
                             "0x1ae": 0x1d1d1d1d1d1d1d1d,
                             "0x1af": 0x1d1d1d1d1d1d1d1d})
        self.select = dict(msr_ce=1 << 28, capid4=1 << 28, msr_1ac=0)
        self.ratios = [33] + [30] * 13 + [0] * 10

    def test_14_cores_preserve_unused_slots(self):
        result = model(self.build, self.select, self.ratios)
        expected = {"0x1ad": 0x1e1e1e1e1e1e1e21, "0x1ae": 0x1d1d1e1e1e1e1e1e,
                    "0x1af": self.build["0x1af"]}
        self.assertEqual(result["construction"]["ratio_msr_writes"], expected)
        self.assertTrue(result["construction"]["reaches_msr_194_update"])
        self.assertEqual(result["selection"]["write"], {"0x1ac": 1 << 63})

    def test_build_gates_do_not_gate_selection(self):
        for field, value, gate in (("msr_1ac", 1 << 32, "0x240a"),
                                   ("msr_ce", 0, "0x244c"),
                                   ("msr_194", 0, "0x2454"),
                                   ("msr_1ac_second", 1 << 63, "0x26d3")):
            with self.subTest(field=field):
                result = model(self.build | {field: value}, self.select, self.ratios)
                self.assertEqual(result["construction"]["gate"], gate)
                self.assertEqual(result["construction"]["ratio_msr_attempts"], [])
                self.assertIsNotNone(result["selection"]["write"])

    def test_selection_gates_do_not_gate_build(self):
        for field, gate in (("msr_ce", "0x2be5"), ("capid4", "0x2bf5")):
            result = model(self.build, self.select | {field: 0}, self.ratios)
            self.assertEqual(result["construction"]["status"], "write_attempt")
            self.assertEqual(result["selection"], {"gate": gate, "write": None})

    def test_only_first_slot_is_upper_bound_and_zeros_keep_baseline(self):
        ratios = [33, 0, 32, 31] + [0] * 20
        result = model(self.build, self.select, ratios)["construction"]
        self.assertEqual(result["ratio_msr_writes"]["0x1ad"] & 0xffffffff, 0x1f202121)
        ratios[2] = 34
        result = model(self.build, self.select, ratios)["construction"]
        self.assertEqual((result["gate"], result["rejected_slot"]), ("0x2700", 3))

    def test_word_overlaps_neighbor_and_count_above_array_is_explicit(self):
        ratios = [0x121, 0] + [0] * 22
        build = self.build | {"0x1ad": 0, "msr_35": 1 << 16}
        self.assertEqual(model(build, self.select, ratios)["construction"]["ratio_msr_writes"]["0x1ad"],
                         0x121)
        build["msr_35"] = 25 << 16
        self.assertEqual(model(build, self.select, ratios)["construction"]["status"],
                         "outside_policy_array")
        with self.assertRaises(ValueError):
            model(build, self.select, [0] * 23)
