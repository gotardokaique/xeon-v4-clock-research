import struct
import unittest
from scripts.compara_fpt import inspect


def fixture():
    data=bytearray(b'\xff'*512)
    data[0x10:0x14]=b'$FPT'
    struct.pack_into('<I', data, 0x14, 2)
    data[0x18:0x1b]=bytes([0x20,0x10,0x30])
    struct.pack_into('<4s4sII',data,0x30,b'TEST',b'OSID',0x100,16)
    struct.pack_into('<4s4sII',data,0x50,b'NVCL',b'\xff'*4,0xffffffff,100)
    return data

class FptTests(unittest.TestCase):
    def test_valid_and_virtual(self):
        entries=inspect(fixture())['entries']
        self.assertEqual(entries[0]['non_ff'],0)
        self.assertIn('não é partição física',entries[1]['status'])
    def test_reject_truncation(self):
        data=fixture(); struct.pack_into('<I',data,0x38,510)
        with self.assertRaises(ValueError): inspect(data)
    def test_reject_unknown_header(self):
        data=fixture(); data[0x1a]=0x20
        with self.assertRaises(ValueError): inspect(data)
    def test_reject_large_count(self):
        data=fixture(); struct.pack_into('<I',data,0x14,257)
        with self.assertRaises(ValueError): inspect(data)
    def test_reject_wrong_origin(self):
        with self.assertRaises(ValueError): inspect(bytes(512))

if __name__ == '__main__': unittest.main()
