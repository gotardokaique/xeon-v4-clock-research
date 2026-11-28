import hashlib
import struct
import unittest

from scripts.verifica_candidato_me import validate


def sha(data):
    return hashlib.sha256(data).hexdigest()


def fixture():
    original = bytearray(0x4000)
    struct.pack_into('<II', original, 0x10, 0x0ff0a55a, 0x00040000)
    struct.pack_into('<II', original, 0x44, 0x00030003, 0x00020001)
    region = bytes([0x5a]) * 0x2000
    candidate = original[:0x1000] + region + original[0x3000:]
    return bytes(original), region, bytes(candidate)


class ValidateTest(unittest.TestCase):
    def setUp(self):
        self.original, self.region, self.candidate = fixture()

    def run_case(self, original=None, region=None, candidate=None, original_sha=None, region_sha=None):
        return validate(original if original is not None else self.original,
                        region if region is not None else self.region,
                        candidate if candidate is not None else self.candidate,
                        original_sha or sha(self.original), region_sha or sha(self.region))

    def test_valid(self):
        result = self.run_case()
        self.assertEqual((result['me_start_spi'], result['me_end_spi_exclusive']), (0x1000, 0x3000))

    def test_reject_original_hash(self):
        with self.assertRaises(ValueError): self.run_case(original_sha='0' * 64)

    def test_reject_region_hash(self):
        with self.assertRaises(ValueError): self.run_case(region_sha='0' * 64)

    def test_reject_descriptor_change(self):
        changed = bytearray(self.candidate); changed[0x20] ^= 1
        with self.assertRaises(ValueError): self.run_case(candidate=changed)

    def test_reject_bios_change(self):
        changed = bytearray(self.candidate); changed[0x3000] ^= 1
        with self.assertRaises(ValueError): self.run_case(candidate=changed)

    def test_reject_region_corruption(self):
        changed = bytearray(self.candidate); changed[0x1001] ^= 1
        with self.assertRaises(ValueError): self.run_case(candidate=changed)

    def test_reject_bad_region_size(self):
        region = self.region[:-1]
        with self.assertRaises(ValueError): self.run_case(region=region, region_sha=sha(region))

    def test_reject_me_bios_overlap(self):
        original = bytearray(self.original); struct.pack_into('<I', original, 0x44, 0x00030002)
        with self.assertRaises(ValueError): self.run_case(original=original, original_sha=sha(original))

    def test_reject_me_outside_flash(self):
        original = bytearray(self.original); struct.pack_into('<I', original, 0x48, 0x00050001)
        with self.assertRaises(ValueError): self.run_case(original=original, original_sha=sha(original))

if __name__ == '__main__': unittest.main()
