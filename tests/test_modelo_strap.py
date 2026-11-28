import unittest
from scripts.modelo_strap import decisao


class StrapTests(unittest.TestCase):
    def test_igual_nao_escreve(self):
        self.assertFalse(decisao(2, 2)['escrita_e_handshake'])

    def test_or_nao_limpa_bits(self):
        resultado = decisao(2, 1)
        self.assertEqual(resultado['operando_wrmsr'], 11)
        self.assertEqual(resultado['low2_operando'], 3)

    def test_bit2_da_origem_pode_ser_setado(self):
        self.assertEqual(decisao(0, 4)['operando_wrmsr'], 12)

    def test_alto_preservado(self):
        self.assertEqual(decisao(1 << 63, 1)['operando_wrmsr'], (1 << 63) | 9)

    def test_mei_ausente_bloqueia_escrita(self):
        self.assertFalse(decisao(0, 1, False)['escrita_e_handshake'])

    def test_rejeita_valores_invalidos(self):
        for msr, gmes2 in [(-1, 0), (1 << 64, 0), (0, -1), (0, 1 << 32)]:
            with self.subTest(msr=msr, gmes2=gmes2), self.assertRaises(ValueError):
                decisao(msr, gmes2)


if __name__ == '__main__':
    unittest.main()
