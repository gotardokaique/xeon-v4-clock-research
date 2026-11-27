import struct
import unittest

from scripts.auditoria_sps import inspect_sca, locate_arc


class ScaTest(unittest.TestCase):
    def setUp(self):
        self.sca = bytearray(0x60)
        struct.pack_into("<7I", self.sca, 0, 0, 0x10, 0x41435324, 1, 0x54, 3, 1)
        struct.pack_into("<5I", self.sca, 0x40, 1, 3, 0, 0xFFFFFFFF, 2)
        total = sum(word for (word,) in struct.iter_unpack("<I", self.sca))
        struct.pack_into("<I", self.sca, 0x3C, ~total & 0xFFFFFFFF)

    def test_record_intervals_and_checksum(self):
        report = inspect_sca(self.sca)
        self.assertTrue(report["checksum_matches"])
        self.assertEqual([(r["offset"], r["size"]) for r in report["records"]],
                         [(0x40, 12), (0x4C, 8)])

    def test_reports_checksum_divergence(self):
        self.sca[0x48] = 1
        self.assertFalse(inspect_sca(self.sca)["checksum_matches"])

    def test_rejects_invalid_record_length(self):
        self.sca[0x44] = 1
        with self.assertRaisesRegex(ValueError, "comprimento de registro"):
            inspect_sca(self.sca)


class ArcTest(unittest.TestCase):
    def test_distinguishes_rapi_and_kapi_with_empty_pages(self):
        report = {"tables": [{}, {"addrbase_field": 0x10000000, "page_size": 0x400,
                                  "pages": [{"flags": 0x40}] * 8}],
                  "modules": [{"name": "ICC", "start": 0x20000000, "end": 0x20003000,
                               "flags": (1 << 17) | (1 << 20)}]}
        for address, window in ((0x20000DFC, "RAPI"), (0x20001AB0, "KAPI")):
            item = locate_arc(report, address)
            self.assertEqual((item["window"], item["page"]["flags"]), (window, 0x40))

    def test_finds_runtime_data_beyond_code_interval(self):
        report = {"tables": [{}, {"addrbase_field": 0x10000000, "page_size": 0x400,
                                  "pages": [{"flags": 0x40}] * 20}],
                  "modules": [{"name": "POLICY", "start": 0x20000000, "end": 0x20003000,
                               "field_44": 0x4000, "flags": 0}]}
        item = locate_arc(report, 0x20003FFC)
        self.assertEqual((item["module"], item["window"]), ("POLICY", "runtime_data"))
        self.assertIsNone(locate_arc(report, 0x20004000)["module"])
