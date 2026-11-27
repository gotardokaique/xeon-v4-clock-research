import struct
import unittest

from scripts.icc_descriptor import DescriptorError, parse_image


def make_spi(ril: int, records: list[tuple[int, int]] = ()) -> bytes:
    image = bytearray(b"\xff" * 0x1000)
    image[0x10:0x14] = bytes.fromhex("5aa5f00f")
    flmap2 = (ril << 24) | (0x21 << 16) | 0x0120
    struct.pack_into("<I", image, 0x1C, flmap2)
    for index, (selector, value) in enumerate(records):
        struct.pack_into("<II", image, 0x210 + index * 8, selector, value)
    return bytes(image)


class IccDescriptorTests(unittest.TestCase):
    def test_decodes_declared_register_init_pairs(self):
        result = parse_image(
            make_spi(2, [(0x008340EB, 0x000805A6), (0x00C100EB, 0x0F0B5F89)]),
            "fixture",
        )
        self.assertEqual(result["flmap2"], 0x02210120)
        self.assertEqual(result["icc_table_offset"], 0x210)
        self.assertEqual(result["icc_table_end_exclusive"], 0x220)
        self.assertEqual(
            [(entry["selector"], entry["value"]) for entry in result["entries"]],
            [(0x008340EB, 0x000805A6), (0x00C100EB, 0x0F0B5F89)],
        )
        self.assertEqual(result["entries"][0]["candidate_slices"]["byte_7_0"], 0xEB)

    def test_zero_length_reports_empty_table_without_parsing_erased_bytes(self):
        result = parse_image(make_spi(0), "empty")
        self.assertEqual(result["ril"], 0)
        self.assertEqual(result["icc_table_size"], 0)
        self.assertEqual(result["entries"], [])
        self.assertTrue(result["table_erased_when_ril_zero"])

    def test_rejects_missing_descriptor(self):
        with self.assertRaises(DescriptorError):
            parse_image(b"\xff" * 0x1000)

    def test_rejects_list_beyond_image(self):
        image = bytearray(make_spi(0))
        struct.pack_into("<I", image, 0x1C, (0xFF << 24) | (0xF0 << 16))
        with self.assertRaises(DescriptorError):
            parse_image(bytes(image))


if __name__ == "__main__":
    unittest.main()
