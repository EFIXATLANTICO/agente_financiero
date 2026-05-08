import unittest


class SmokeTests(unittest.TestCase):
    def test_imports_principales(self):
        import app  # noqa: F401
        import auth_empresas  # noqa: F401
        import db_context  # noqa: F401
        import facturacion  # noqa: F401
        import tesoreria  # noqa: F401
        import importador_excel  # noqa: F401
        import conciliacion_bancaria  # noqa: F401

    def test_totales_factura_venta(self):
        from facturacion import calcular_totales_factura_venta

        totales = calcular_totales_factura_venta(100, 7)

        self.assertEqual(totales["base_imponible"], 100)
        self.assertEqual(totales["cuota_impuesto"], 7)
        self.assertEqual(totales["total"], 107)

    def test_numero_factura_no_requiere_imports_obsoletos(self):
        from facturacion import cobrar_factura_venta, pagar_factura_compra

        self.assertTrue(callable(cobrar_factura_venta))
        self.assertTrue(callable(pagar_factura_compra))


if __name__ == "__main__":
    unittest.main()
