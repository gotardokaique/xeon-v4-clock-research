import struct
import unittest
from scripts.compare_pe_reloc import normalize


def fixture(base):
    d = bytearray(0x600)
    d[:2] = b'MZ'
    struct.pack_into('<I', d, 0x3c, 0x80)
    d[0x80:0x84] = b'PE\0\0'
    struct.pack_into('<H', d, 0x86, 1)
    struct.pack_into('<H', d, 0x94, 0xe0)
    o = 0x98
    struct.pack_into('<H', d, o, 0x10b)
    struct.pack_into('<I', d, o+28, base)
    struct.pack_into('<I', d, o+92, 16)
    struct.pack_into('<II', d, o+136, 0x1200, 12)
    s = o+0xe0
    struct.pack_into('<III', d, s+12, 0x1000, 0x400, 0x200)
    struct.pack_into('<I', d, 0x220, base+0x123)
    struct.pack_into('<IIHH', d, 0x400, 0x1000, 12, 0x3020, 0)
    return d


class NormalizeTests(unittest.TestCase):
    def test_rebased_equal(self):
        a, info = normalize(fixture(0x100000))
        b, _ = normalize(fixture(0x200000))
        self.assertEqual(a, b)
        self.assertEqual(info['relocations'], 1)
    def test_code_difference_remains(self):
        a = fixture(0x100000); b = fixture(0x200000); b[0x230] = 1
        self.assertNotEqual(normalize(a)[0], normalize(b)[0])
    def test_bad_relocation(self):
        d = fixture(0x100000); struct.pack_into('<H', d, 0x408, 0xa020)
        with self.assertRaises(ValueError): normalize(d)
    def test_truncated(self):
        with self.assertRaises(ValueError): normalize(fixture(0x100000)[:0x410])
    def test_duplicate(self):
        d = fixture(0x100000); struct.pack_into('<H', d, 0x40a, 0x3020)
        with self.assertRaises(ValueError): normalize(d)

if __name__ == '__main__': unittest.main()
