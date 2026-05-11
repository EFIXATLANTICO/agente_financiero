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


class FakeCursorImportador:
    def __init__(self):
        self.next_id = 1
        self.fetchone_value = None
        self.importaciones = []
        self.asientos_importacion = []
        self.terceros = {"clientes": {}, "proveedores": {}}
        self.facturas = []
        self.asientos = []
        self.lineas = []
        self.vencimientos = []
        self.incidencias = []

    def execute(self, query, params=None):
        sql = " ".join(str(query).lower().split())
        params = params or ()

        if sql.startswith("savepoint") or sql.startswith("release savepoint") or sql.startswith("rollback to savepoint"):
            self.fetchone_value = None
            return
        if sql.startswith("alter table"):
            self.fetchone_value = None
            return

        if sql.startswith("select id from importaciones"):
            hash_archivo = params[0]
            encontrados = [i for i in self.importaciones if i["hash_archivo"] == hash_archivo]
            self.fetchone_value = (encontrados[-1]["id"],) if encontrados else None
            return

        if sql.startswith("select count(*) from asientos_importacion"):
            importacion_id = params[0]
            total = sum(1 for a in self.asientos_importacion if a["importacion_id"] == importacion_id)
            self.fetchone_value = (total,)
            return

        if sql.startswith("delete from importaciones"):
            importacion_id = params[0]
            self.importaciones = [i for i in self.importaciones if i["id"] != importacion_id]
            self.fetchone_value = None
            return

        if sql.startswith("insert into importaciones"):
            item = {"id": self._id(), "tipo": params[0], "nombre_archivo": params[1], "hash_archivo": params[2]}
            self.importaciones.append(item)
            self.fetchone_value = (item["id"],)
            return

        if sql.startswith("select id from clientes") or sql.startswith("select id from proveedores"):
            tabla = "clientes" if "from clientes" in sql else "proveedores"
            nombre = str(params[0]).strip().upper()
            tercero_id = self.terceros[tabla].get(nombre)
            self.fetchone_value = (tercero_id,) if tercero_id else None
            return

        if sql.startswith("insert into clientes") or sql.startswith("insert into proveedores"):
            tabla = "clientes" if sql.startswith("insert into clientes") else "proveedores"
            tercero_id = self._id()
            self.terceros[tabla][str(params[0]).strip().upper()] = tercero_id
            self.fetchone_value = (tercero_id,)
            return

        if sql.startswith("select id from facturas"):
            empresa_id, tipo, numero_factura, nombre_tercero = params[:4]
            encontrada = None
            for factura in self.facturas:
                if (
                    factura["empresa_id"] == empresa_id
                    and factura["tipo"] == tipo
                    and factura["numero_factura"] == numero_factura
                    and factura["nombre_tercero"].strip().upper() == str(nombre_tercero).strip().upper()
                ):
                    encontrada = factura
                    break
            self.fetchone_value = (encontrada["id"],) if encontrada else None
            return

        if sql.startswith("insert into facturas"):
            factura = {
                "id": self._id(),
                "empresa_id": params[0],
                "tipo": params[1],
                "numero_factura": params[3],
                "nombre_tercero": params[5],
                "total": params[14],
                "estado": params[15],
            }
            self.facturas.append(factura)
            self.fetchone_value = (factura["id"],)
            return

        if sql.startswith("insert into asientos ("):
            asiento = {"id": self._id(), "fecha": params[0], "concepto": params[1], "tipo_operacion": params[2]}
            self.asientos.append(asiento)
            self.fetchone_value = (asiento["id"],)
            return

        if sql.startswith("insert into asientos_importacion"):
            self.asientos_importacion.append({"importacion_id": params[0], "asiento_id": params[1]})
            self.fetchone_value = None
            return

        if sql.startswith("insert into lineas_asiento"):
            self.lineas.append({"asiento_id": params[0], "cuenta": params[1], "movimiento": params[2], "importe": params[3]})
            self.fetchone_value = None
            return

        if sql.startswith("insert into vencimientos"):
            self.vencimientos.append(params)
            self.fetchone_value = None
            return

        if sql.startswith("select id from incidencias_importacion"):
            self.fetchone_value = None
            return

        if sql.startswith("insert into incidencias_importacion"):
            self.incidencias.append(params)
            self.fetchone_value = None
            return

        self.fetchone_value = None

    def fetchone(self):
        return self.fetchone_value

    def _id(self):
        valor = self.next_id
        self.next_id += 1
        return valor


class FakeConnectionImportador:
    def __init__(self):
        self.cursor_obj = FakeCursorImportador()
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


class FakeCursorTesoreria:
    def __init__(self):
        self.next_id = 10
        self.fetchone_value = None
        self.vencimientos = {
            1: {"id": 1, "factura_id": 7, "tipo": "cobro", "estado": "pendiente", "importe": 107.0, "importe_pendiente": 107.0},
        }
        self.facturas = {7: {"id": 7, "tipo": "venta", "estado": "pendiente", "forma_pago": ""}}
        self.asientos = []
        self.lineas = []

    def execute(self, query, params=None):
        sql = " ".join(str(query).lower().split())
        params = params or ()

        if sql.startswith("select id, factura_id, tipo, estado"):
            venc = self.vencimientos.get(int(params[0]))
            self.fetchone_value = (
                venc["id"], venc["factura_id"], venc["tipo"], venc["estado"], venc["importe"], venc["importe_pendiente"]
            ) if venc else None
            return

        if sql.startswith("insert into asientos"):
            asiento_id = self.next_id
            self.next_id += 1
            self.asientos.append({"id": asiento_id, "fecha": params[0], "concepto": params[1], "tipo_operacion": params[2]})
            self.fetchone_value = (asiento_id,)
            return

        if sql.startswith("insert into lineas_asiento"):
            self.lineas.append({"asiento_id": params[0], "cuenta": params[1], "movimiento": params[2], "importe": params[3]})
            self.fetchone_value = None
            return

        if sql.startswith("update vencimientos"):
            venc = self.vencimientos[int(params[3])]
            venc["estado"] = params[0]
            venc["importe_pendiente"] = params[1]
            venc["forma_pago"] = params[2]
            self.fetchone_value = None
            return

        if sql.startswith("select id, tipo from facturas"):
            fac = self.facturas.get(int(params[0]))
            self.fetchone_value = (fac["id"], fac["tipo"]) if fac else None
            return

        if sql.startswith("select coalesce(sum"):
            factura_id = int(params[0])
            total = sum(
                float(v["importe_pendiente"] or 0)
                for v in self.vencimientos.values()
                if v["factura_id"] == factura_id and v["estado"] in ["pendiente", "vencido", "cobro_parcial", "pago_parcial"]
            )
            self.fetchone_value = (total,)
            return

        if sql.startswith("update facturas"):
            factura_id = int(params[3])
            self.facturas[factura_id]["estado"] = params[0]
            self.facturas[factura_id]["forma_pago"] = params[1]
            self.fetchone_value = None
            return

        self.fetchone_value = None

    def fetchone(self):
        return self.fetchone_value


class FakeConnectionTesoreria:
    def __init__(self):
        self.cursor_obj = FakeCursorTesoreria()
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

    def test_importar_pago_proveedor_valido(self):
        import pandas as pd
        import importador_excel

        df = pd.DataFrame([{
            "factura/venc": "FP-1",
            "identificador": "1",
            "proveedor": "P001",
            "razon": "Proveedor Test SL",
            "importe": "107,00",
            "fec fact": "01/05/2026",
            "fec vcto": "15/05/2026",
            "forma de pago": "transferencia",
            "estado": "pagado",
        }])
        fake_conn = FakeConnectionImportador()
        with patch.object(importador_excel, "get_connection", return_value=fake_conn), \
             patch("db_context.obtener_empresa_id_activa", return_value=1):
            resultado = importador_excel.importar_pagos_proveedor_desde_excel(df, "pagos.xlsx", b"pagos-ok")

        self.assertTrue(resultado["ok"])
        self.assertEqual(resultado["importadas"], 1)
        self.assertEqual([a["tipo_operacion"] for a in fake_conn.cursor_obj.asientos], ["factura_importada_excel", "pago_factura"])
        self.assertEqual(fake_conn.cursor_obj.facturas[0]["estado"], "pagada")

    def test_importar_cobro_cliente_valido(self):
        import pandas as pd
        import importador_excel

        df = pd.DataFrame([{
            "factura/venc": "FV-1",
            "identificador": "1",
            "cliente": "C001",
            "razon": "Cliente Test SL",
            "importe": "214,00",
            "fec fact": "01/05/2026",
            "fec vcto": "15/05/2026",
            "forma de pago": "transferencia",
            "estado": "cobrado",
        }])
        fake_conn = FakeConnectionImportador()
        with patch.object(importador_excel, "get_connection", return_value=fake_conn), \
             patch("db_context.obtener_empresa_id_activa", return_value=1):
            resultado = importador_excel.importar_cobros_cliente_desde_excel(df, "cobros.xlsx", b"cobros-ok")

        self.assertTrue(resultado["ok"])
        self.assertEqual(resultado["importadas"], 1)
        self.assertEqual([a["tipo_operacion"] for a in fake_conn.cursor_obj.asientos], ["factura_importada_excel", "cobro_factura"])
        self.assertEqual(fake_conn.cursor_obj.facturas[0]["tipo"], "venta")
        self.assertEqual(fake_conn.cursor_obj.facturas[0]["estado"], "cobrada")

    def test_importacion_cartera_detecta_archivo_duplicado(self):
        import pandas as pd
        import importador_excel

        df = pd.DataFrame([{
            "factura/venc": "FP-2",
            "razon": "Proveedor Test SL",
            "importe": "107,00",
            "fec fact": "01/05/2026",
            "estado": "pagado",
        }])
        fake_conn = FakeConnectionImportador()
        with patch.object(importador_excel, "get_connection", return_value=fake_conn), \
             patch("db_context.obtener_empresa_id_activa", return_value=1):
            primero = importador_excel.importar_pagos_proveedor_desde_excel(df, "pagos.xlsx", b"duplicado")
            segundo = importador_excel.importar_pagos_proveedor_desde_excel(df, "pagos.xlsx", b"duplicado")

        self.assertTrue(primero["ok"])
        self.assertEqual(segundo["estado"], "duplicado")

    def test_importacion_cartera_columnas_faltantes(self):
        import pandas as pd
        import importador_excel

        df = pd.DataFrame([{"factura/venc": "FP-3", "importe": "107,00"}])
        fake_conn = FakeConnectionImportador()
        with patch.object(importador_excel, "get_connection", return_value=fake_conn), \
             patch("db_context.obtener_empresa_id_activa", return_value=1):
            resultado = importador_excel.importar_pagos_proveedor_desde_excel(df, "mal.xlsx", b"mal")

        self.assertFalse(resultado["ok"])
        self.assertEqual(resultado["estado"], "error_columnas")
        self.assertIn("proveedor", resultado["detalle"])

    def test_vencimientos_filtro_pendientes_vencidos_y_proximos(self):
        import datetime
        import tesoreria

        hoy = datetime.date(2026, 5, 11)
        filas = [
            {"id": 1, "estado": "pendiente", "fecha_vencimiento": "2026-05-10", "nombre_tercero": "A"},
            {"id": 2, "estado": "pendiente", "fecha_vencimiento": "2026-05-15", "nombre_tercero": "B"},
            {"id": 3, "estado": "pagado", "fecha_vencimiento": "2026-05-09", "nombre_tercero": "C"},
        ]

        self.assertEqual([r["id"] for r in tesoreria._filtrar_vencimientos(filas, "pendientes", hoy=hoy)], [1, 2])
        self.assertEqual([r["id"] for r in tesoreria._filtrar_vencimientos(filas, "vencidos", hoy=hoy)], [1])
        self.assertEqual([r["id"] for r in tesoreria._filtrar_vencimientos(filas, "proximos", hoy=hoy)], [2])

    def test_registrar_desde_vencimiento_actualiza_vencimiento_factura_y_asiento(self):
        import tesoreria

        fake_conn = FakeConnectionTesoreria()
        with patch.object(tesoreria, "get_connection", return_value=fake_conn), \
             patch.object(tesoreria, "registrar_movimiento_banco", return_value=None):
            resultado = tesoreria.registrar_desde_vencimiento(
                vencimiento_id=1,
                fecha="2026-05-11",
                forma_pago="transferencia",
                importe=107.0,
                observaciones="test",
            )

        self.assertTrue(resultado["ok"])
        self.assertEqual(fake_conn.cursor_obj.vencimientos[1]["estado"], "cobrado")
        self.assertEqual(fake_conn.cursor_obj.vencimientos[1]["importe_pendiente"], 0.0)
        self.assertEqual(fake_conn.cursor_obj.facturas[7]["estado"], "cobrada")
        self.assertEqual([a["tipo_operacion"] for a in fake_conn.cursor_obj.asientos], ["cobro"])
        self.assertEqual(fake_conn.commits, 1)


if __name__ == "__main__":
    unittest.main()
