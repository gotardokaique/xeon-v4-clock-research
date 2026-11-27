import struct
import unittest

from scripts.mapa_parametros_sps import (DIRECTORY_END, PCO_SPANS, TEMPLATES, arc_instructions,
                                         cross_volume, directory, interface_slots, kapi_references,
                                         matching_window, sca_payload_accesses)


class SpsParametersTests(unittest.TestCase):
    def directory_fixture(self):
        image = bytearray(0x5100)
        for i in range(123):
            key, size = (0x0a4f4350, 0xa24) if i == 9 else (i + 1, 4)
            struct.pack_into("<HIHBBB", image, 0x14 + i * 11, 0xf0dc, key, size, 1, i // 8, i % 8)
        return image

    def test_directory_bounds_and_unique_pairs(self):
        image = self.directory_fixture()
        self.assertEqual(directory(image)[-1]["offset"], DIRECTORY_END - 11)
        with self.assertRaises(ValueError):
            directory(image[:DIRECTORY_END - 1])
        image[0x14 + 11 + 10] = 0
        with self.assertRaisesRegex(ValueError, "par grupo/slot"):
            directory(image)

    def test_fragmented_sca_match_requires_content_equality(self):
        image = self.directory_fixture()
        sca = bytearray(0xa74)
        struct.pack_into("<7I", sca, 0, 0, 0x10, 0x41435324, 0, len(sca), 3, 1)
        struct.pack_into("<II", sca, 0x40, 0x0a4f4350, 0x28b)
        struct.pack_into("<II", sca, len(sca) - 8, 0xffffffff, 2)
        start = 0x48
        for index, (left, right) in enumerate(PCO_SPANS, start=1):
            size = right - left
            sca[start:start + size] = image[left:right] = bytes([index]) * size
            start += size
        match = cross_volume(image, image, sca)["sca_matches"][0]
        self.assertTrue(match["reconstructed"])
        self.assertEqual(match["contiguous_occurrences"], 0)
        image[PCO_SPANS[0][0]] ^= 1
        self.assertFalse(cross_volume(image, image, sca)["sca_matches"][0]["reconstructed"])

    def test_arc_scaled_compact_and_signed_displacements(self):
        # Sintético, com o mesmo número de leituras do braço observado.
        lines = ["20053b38:\t1400 2000\tld\tr0,[r20]",
                 "20053b3c:\t70\tcmp_s\tr0,r4",
                 "20053b40:\t14\tld_s\tr2,[r20,0x4]",
                 "20053b42:\t70\tcmp_s\tr2,r4",
                 "20053b44:\t14\tmov_s\tr1,r20",
                 "20053b46:\t14\tadd\tr1,r1,12",
                 "20053b4a:\t14\tld.as\tr2,[r1,-1]",
                 "20053b4e:\t70\tcmp_s\tr2,r4"]
        for i in range((0xa24 - 12) // 4):
            address = 0x20053b50 + 8 * i
            lines.extend((f"{address:x}:\t14\tld\tr2,[r1,{4 * i}]",
                          f"{address + 4:x}:\t70\tcmp_s\tr2,r4"))
        accesses = sca_payload_accesses(arc_instructions("\n".join(lines)))
        self.assertEqual(len(accesses), 649)
        self.assertEqual(accesses[-1]["offset"], 0xa20)
        with self.assertRaises(ValueError):
            sca_payload_accesses(arc_instructions("\n".join(lines[:-1])))

    def test_kapi_lanes_require_both_bytes_and_valid_jump(self):
        image = bytearray(0x4000)
        instructions = []
        for index, base in enumerate(TEMPLATES):
            offset = base - TEMPLATES[0]
            struct.pack_into("<4sII", image, offset, b"KAPI", base, base + 0xfd8)
            image[offset + 0x18:offset + 0x20] = b"\x0a\x20\x80\x1f" + struct.pack(
                "<HH", 6 + index, 0x1c4)
            instructions.append((base + 0x20, "b", "", base + 0x10))
        report = {"tables": [{}, {"addrbase_field": 0x10080000, "page_size": 1024, "pages": []}],
                  "modules": [{"start": 0x20080000, "end": 0x20082000, "name": "test",
                               "flags": 1 << 20}]}
        refs = kapi_references(image, instructions, report, (0x20080018, 0x20080019, 0x20081018))
        self.assertEqual([m["selector"] for m in refs[0]["template_matches"]], [0x601c4, 0x701c4])
        self.assertEqual([r["slot_candidate"] for r in refs], [0, None, None])

    def test_matching_window_stops_at_both_bounds(self):
        self.assertEqual(matching_window(b"aXYZ", 2, b"XYZ!", 1),
                         {"offset_before_anchor": 1, "offset_from_anchor": 2, "length": 3})
        with self.assertRaises(ValueError):
            matching_window(b"x", 1, b"x", 0)

    def test_interface_slots_follow_the_export_and_check_target_bounds(self):
        image = bytearray(0x90)
        struct.pack_into("<II", image, 0x20, 0x1057, 0x1050)
        struct.pack_into("<I", image, 0x5c, 0x1080)
        self.assertEqual(interface_slots(image, 0x1000, 0x1020, 0x1057, (0xc,))["slots"],
                         {"0xc": 0x1080})
        with self.assertRaises(ValueError):
            interface_slots(image[:0x80], 0x1000, 0x1020, 0x1057, (0xc,))
