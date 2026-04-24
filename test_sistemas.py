from datetime import datetime

# =========================
# IMPORTS
# =========================

from db_context import set_active_db_path, get_connection
from crear_empresa import crear_empresa
from init_db import inicializar_bd_empresa

from contabilidad import (
    crear_asiento,
    agregar_linea_asiento,
    obtener_libro_diario
)

from facturacion import (
    crear_cliente,
    crear_proveedor,
    registrar_factura_venta,
    registrar_factura_compra,
    obtener_facturas
)

from tesoreria import (
    cobrar_factura_venta,
    pagar_factura_compra,
    obtener_facturas_pendientes
)

from operaciones_inteligentes import procesar_operacion_texto


# =========================
# SETUP EMPRESA TEST
# =========================

print("\n--- CREANDO EMPRESA TEST ---")

empresa_id, db_path = crear_empresa(
    nombre="Empresa Test QA",
    nif="TEST123",
    email="test@test.com"
)

set_active_db_path(db_path)
inicializar_bd_empresa()

print("Empresa creada y BD inicializada")


# =========================
# TEST CONTABILIDAD
# =========================

print("\n--- TEST CONTABILIDAD ---")

asiento_id = crear_asiento("2026-03-24", "Test manual", "manual")
agregar_linea_asiento(asiento_id, "600 Compras", "debe", 100)
agregar_linea_asiento(asiento_id, "400 Proveedores", "haber", 100)

diario = obtener_libro_diario()

print("Libro diario OK:", len(diario) > 0)


# =========================
# TEST FACTURACIÓN
# =========================

print("\n--- TEST FACTURACIÓN ---")

cliente = crear_cliente("Cliente Test")
proveedor = crear_proveedor("Proveedor Test")

factura_v = registrar_factura_venta(
    fecha="2026-03-24",
    cliente_id=cliente["id"],
    nombre_cliente="Cliente Test",
    base=100,
    igic_porcentaje=7,
    concepto="Venta test"
)

factura_c = registrar_factura_compra(
    fecha="2026-03-24",
    proveedor_id=proveedor["id"],
    nombre_proveedor="Proveedor Test",
    base=200,
    igic_porcentaje=7,
    concepto="Compra test"
)

facturas = obtener_facturas()

print("Facturación OK:", len(facturas) >= 2)


# =========================
# TEST TESORERÍA
# =========================

print("\n--- TEST TESORERÍA ---")

pendientes = obtener_facturas_pendientes()
print("Pendientes iniciales:", len(pendientes))

cobro = cobrar_factura_venta(factura_v["factura_id"], "2026-03-25")
pago = pagar_factura_compra(factura_c["factura_id"], "2026-03-25")

print("Cobro OK:", cobro["ok"])
print("Pago OK:", pago["ok"])

pendientes = obtener_facturas_pendientes()
print("Pendientes tras cobro/pago:", len(pendientes))


# =========================
# TEST OPERACIONES INTELIGENTES
# =========================

print("\n--- TEST OPERACIONES INTELIGENTES ---")

tests = [
    "Compra de mercadería a Proveedor IA por 100 con igic 7 al contado",
    "Venta de servicio a Cliente IA por 500 con igic 7 por transferencia",
    "Aportación de socios por 10000",
    "Comisión bancaria de 15"
]

for t in tests:
    res = procesar_operacion_texto(t, "2026-03-24", 7)
    print(f"Test: {t}")
    print("OK:", res.get("ok"), "| Tipo:", res.get("tipo"))
    print("---")


# =========================
# TEST BASE DE DATOS
# =========================

print("\n--- TEST BASE DE DATOS ---")

conn = get_connection()
cursor = conn.cursor()

cursor.execute("SELECT COUNT(*) FROM asientos")
print("Asientos:", cursor.fetchone()[0])

cursor.execute("SELECT COUNT(*) FROM lineas_asiento")
print("Líneas:", cursor.fetchone()[0])

cursor.execute("SELECT COUNT(*) FROM facturas")
print("Facturas:", cursor.fetchone()[0])

cursor.execute("SELECT COUNT(*) FROM operaciones")
print("Operaciones:", cursor.fetchone()[0])

conn.close()


print("\n--- TEST COMPLETO FINALIZADO ---")