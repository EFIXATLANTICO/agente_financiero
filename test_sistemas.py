import unittest
from unittest.mock import patch


class FakeCursorFacturacion:
    def __init__(self):
        self.next_id = 1
        self.fetchone_value = None
        self.facturas = {}
        self.asientos = []
        self.commits = 0
        self.rollbacks = 0

    def execute(self, query, params=None):
        sql = " ".join(str(query).lower().split())
        params = params or ()

        if sql.startswith("select id from clientes"):
            self.fetchone_value = None
            return

        if sql.startswith("insert into clientes"):
            self.fetchone_value = (self._id(),)
            return

        if sql.startswith("insert into facturas"):
            factura_id = self._id()
            self.facturas[factura_id] = {
                "id": factura_id,
                "tipo": params[0],
                "numero_factura": params[2],
                "nombre_tercero": params[4],
                "total": params[14],
                "estado": params[16],
            }
            self.fetchone_value = (factura_id,)
            return

        if sql.startswith("insert into asientos"):
            asiento_id = self._id()
            self.asientos.append({"id": asiento_id, "tipo": params[2]})
            self.fetchone_value = (asiento_id,)
            return

        if sql.startswith("select id, tipo, numero_factura"):
            factura = self.facturas[int(params[0])]
            self.fetchone_value = (
                factura["id"],
                factura["tipo"],
                factura["numero_factura"],
                factura["nombre_tercero"],
                factura["total"],
                factura["estado"],
            )
            return

        if sql.startswith("update facturas set estado"):
            factura_id = int(params[2])
            self.facturas[factura_id]["estado"] = params[0]
            self.fetchone_value = None
            return

        self.fetchone_value = None

    def fetchone(self):
        return self.fetchone_value

    def _id(self):
        valor = self.next_id
        self.next_id += 1
        return valor


class FakeConnectionFacturacion:
    def __init__(self):
        self.cursor_obj = FakeCursorFacturacion()
        self.commits = 0
        self.rollbacks = 0

    def cursor(self):
        return self.cursor_obj

    def commit(self):
        self.commits += 1

    def rollback(self):
        self.rollbacks += 1

    def close(self):
        pass


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

    def test_guardar_factura_crea_un_solo_asiento_factura(self):
        import facturacion

        fake_conn = FakeConnectionFacturacion()
        with patch.object(facturacion, "get_connection", return_value=fake_conn):
            resultado = facturacion.registrar_factura(
                tipo="venta",
                nombre_tercero="Cliente Test",
                nif_tercero="",
                fecha_emision="2026-05-11",
                fecha_operacion="2026-05-11",
                concepto="Venta test",
                base_imponible=100,
                impuesto_pct=7,
                numero_factura="FV-TEST-0001",
                serie="FV",
            )

        self.assertTrue(resultado["ok"])
        self.assertEqual(fake_conn.commits, 1)
        self.assertEqual(fake_conn.rollbacks, 0)
        self.assertEqual([a["tipo"] for a in fake_conn.cursor_obj.asientos], ["factura_venta"])
        factura = fake_conn.cursor_obj.facturas[resultado["factura_id"]]
        self.assertEqual(factura["estado"], "pendiente")

    def test_guardar_y_cobrar_crea_factura_y_asiento_cobro_atomico(self):
        import facturacion

        fake_conn = FakeConnectionFacturacion()
        with patch.object(facturacion, "get_connection", return_value=fake_conn):
            resultado = facturacion.registrar_factura_y_cobro(
                tipo="venta",
                nombre_tercero="Cliente Test",
                nif_tercero="",
                fecha_emision="2026-05-11",
                fecha_operacion="2026-05-11",
                concepto="Venta test",
                base_imponible=100,
                impuesto_pct=7,
                numero_factura="FV-TEST-0002",
                serie="FV",
                forma_pago="transferencia",
            )

        self.assertTrue(resultado["ok"])
        self.assertEqual(fake_conn.commits, 1)
        self.assertEqual(fake_conn.rollbacks, 0)
        self.assertEqual([a["tipo"] for a in fake_conn.cursor_obj.asientos], ["factura_venta", "cobro_factura"])
        factura = fake_conn.cursor_obj.facturas[resultado["factura_id"]]
        self.assertEqual(factura["estado"], "cobrada")
        self.assertIn("asiento_factura_id", resultado)
        self.assertIn("asiento_cobro_id", resultado)

    def test_formato_moneda_usa_eur(self):
        import app_visual

        self.assertEqual(app_visual.formatear_moneda(1234.5), "1.234,50 EUR")
        self.assertEqual(app_visual.formatear_moneda(None), "0,00 EUR")

    def test_parseo_importes_acepta_eur_y_sufijo_antiguo(self):
        import importador_excel

        self.assertEqual(importador_excel._parsear_importe("1.234,56 EUR"), 1234.56)
        self.assertEqual(importador_excel._parsear_importe("1.234,56 a"), 1234.56)
        self.assertEqual(importador_excel._parsear_importe_excel("1.234,56 EUR"), 1234.56)
        self.assertEqual(importador_excel._parsear_importe_excel("1.234,56 a"), 1234.56)


if __name__ == "__main__":
    unittest.main()
