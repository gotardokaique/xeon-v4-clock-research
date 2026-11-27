import struct
import unittest

from scripts.mapas_sps import MARKER, opr1_map, volume_map


class VolumeMapTest(unittest.TestCase):
    def test_padding_expansion_displacement_and_literal_difference(self):
        backup = b"AX" + MARKER + bytes.fromhex("0000000a") + b"BCfooter"
        active = b"AY" + b"\xff" * 10 + b"BC" + b"\xff"
        report = volume_map(backup, active, 12)
        self.assertEqual(report["differences"], [
            {"mfsb": 1, "mfs": 1, "expected": ord("X"), "actual": ord("Y")},
        ])
        self.assertEqual(report["intervals"][2]["delta"], 2)
        self.assertEqual(report["intervals"][3]["kind"], "erased_tail")

    def test_rejects_expansion_past_active_volume(self):
        with self.assertRaisesRegex(ValueError, "fora da imagem"):
            volume_map(MARKER + b"\xff" * 4, b"\xff", 8)

    def test_rejects_non_erased_gap(self):
        with self.assertRaisesRegex(ValueError, "lacuna MFS divergente"):
            volume_map(MARKER + b"\0\0\0\1", b"\0", 8)


class Opr1MapTest(unittest.TestCase):
    def setUp(self):
        self.sps = bytearray(0x2000)
        struct.pack_into("<4sIBBB", self.sps, 0x10, b"$FPT", 1, 0x20, 0x10, 0x30)
        struct.pack_into("<4s4xII", self.sps, 0x30, b"OPR1", 0x1000, 0x1000)
        self.sps[0x101c:0x1020] = b"$MN2"
        struct.pack_into("<I", self.sps, 0x1004, 0x40 // 4)
        struct.pack_into("<I", self.sps, 0x1020, 1)
        struct.pack_into("<4s16s32x8I", self.sps, 0x104c, b"$MME", b"POLICY",
                         0x20000000, 0x100, 0x800, 0, 0, 0, 0x20000400, 0x10)
        for offset in (0x1100, 0x1148):
            struct.pack_into("<6I", self.sps, offset, 0x54554c4c, 2, 0x10000000, 0, 0x20, 0x1000)
            struct.pack_into("<I", self.sps, offset + 0x30, 0x400)
            struct.pack_into("<2I", self.sps, offset + 0x40, 0x80000000, 0x40001000)

    def test_empty_page_and_mapped_sps_offset(self):
        report = opr1_map(self.sps)
        first, second = report["tables"][1]["pages"]
        self.assertEqual(first["flags"], 0x40)
        self.assertNotIn("stream_sps_offset", first)
        self.assertEqual(second["stream_sps_offset"], 0x1190)
        self.assertEqual([s["state"] for s in report["modules"][0]["llut_segments"]],
                         ["empty", "mapped"])

    def test_rejects_truncated_partition(self):
        with self.assertRaisesRegex(ValueError, "fora da imagem"):
            opr1_map(self.sps[:-1])
