import struct
import unittest

from scripts.inventario_sps import describe, regions


class InventarioSpsTest(unittest.TestCase):
    def setUp(self):
        self.rom = bytearray(b"\xff" * 0x6000)
        struct.pack_into("<II", self.rom, 0x10, 0x0FF0A55A, 4 << 16)
        struct.pack_into("<I", self.rom, 0x48, (5 << 16) | 1)
        struct.pack_into("<4sIBBB", self.rom, 0x1010, b"$FPT", 3, 0x20, 0x10, 0x30)
        for index, name in enumerate((b"MFSB", b"SCA\0", b"MFS\0")):
            struct.pack_into("<4s4sII", self.rom, 0x1030 + index * 0x20,
                             name, b"OSID", (index + 1) * 0x1000, 0x1000)

    def test_offsets_and_block_inventory(self):
        self.rom[0x4000] = 0
        spi, sps, data = regions(self.rom)["MFS"]
        self.assertEqual((spi, sps), (0x4000, 0x3000))
        self.assertEqual(describe(data)["blocks_4k"], [{"offset": 0, "non_ff": 1}])

    def test_truncated_image(self):
        with self.assertRaisesRegex(ValueError, "fora da imagem"):
            regions(self.rom[:-1])

    def test_overlapping_entries(self):
        struct.pack_into("<I", self.rom, 0x1058, 0x1000)
        with self.assertRaisesRegex(ValueError, "sobrepostos"):
            regions(self.rom)

    def test_duplicate_volume(self):
        self.rom[0x1050:0x1054] = b"MFSB"
        with self.assertRaisesRegex(ValueError, "duplicada"):
            regions(self.rom)
