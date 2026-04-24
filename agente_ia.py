from facturacion import crear_cliente, crear_proveedor
import re

from facturacion import registrar_factura_compra, registrar_factura_venta
from tesoreria import pagar_factura_compra, cobrar_factura_venta
import sqlite3

conexion = sqlite3.connect("database/contabilidad.db")
cursor = conexion.cursor()

def buscar_o_crear_tercero(nombre, tipo):

    cursor.execute("SELECT id FROM clientes WHERE nombre = ?", (nombre,))
    cliente = cursor.fetchone()

    cursor.execute("SELECT id FROM proveedores WHERE nombre = ?", (nombre,))
    proveedor = cursor.fetchone()

    if tipo == "venta":
        if cliente:
            return cliente[0]

        crear_cliente(nombre, "", "")
        cursor.execute("SELECT id FROM clientes WHERE nombre = ?", (nombre,))
        return cursor.fetchone()[0]

    if tipo == "compra":
        if proveedor:
            return proveedor[0]

        crear_proveedor(nombre, "", "")
        cursor.execute("SELECT id FROM proveedores WHERE nombre = ?", (nombre,))
        return cursor.fetchone()[0]


def interpretar_factura_texto(texto):
    texto_original = texto
    texto = texto.lower()

    tipo = None
    if "compra" in texto or "proveedor" in texto or "recibida" in texto:
        tipo = "compra"
    elif "venta" in texto or "cliente" in texto or "emitida" in texto:
        tipo = "venta"

    estado = "pendiente"
    if "pagada" in texto or "pagado" in texto:
        estado = "pagada"
    elif "cobrada" in texto or "cobrado" in texto:
        estado = "cobrada"

    base = None
    igic = None

    numeros = re.findall(r"\d+(?:[.,]\d+)?", texto)

    valores = []
    for n in numeros:
        n = n.replace(",", ".")
        try:
            valores.append(float(n))
        except:
            pass

    if len(valores) >= 2:
        base = valores[0]
        igic = valores[1]

    concepto = texto_original

    return {
        "tipo": tipo,
        "base": base,
        "igic_porcentaje": igic,
        "estado": estado,
        "concepto": concepto
    }


def mostrar_interpretacion(texto):
    resultado = interpretar_factura_texto(texto)

    print("\nINTERPRETACIÓN DE FACTURA\n")
    print("Tipo detectado:", resultado["tipo"])
    print("Base detectada:", resultado["base"])
    print("IGIC detectado:", resultado["igic_porcentaje"])
    print("Estado detectado:", resultado["estado"])
    print("Concepto:", resultado["concepto"])


def obtener_ultima_factura_id():
    cursor.execute("SELECT MAX(id) FROM facturas")
    resultado = cursor.fetchone()[0]
    return resultado


def registrar_desde_texto(texto, fecha, nombre_tercero):

    resultado = interpretar_factura_texto(texto)

    tipo = resultado["tipo"]
    base = resultado["base"]
    igic = resultado["igic_porcentaje"]
    estado = resultado["estado"]
    concepto = resultado["concepto"]

    if tipo is None or base is None or igic is None:
        print("No se pudo interpretar correctamente la factura")
        return

    tercero_id = buscar_o_crear_tercero(nombre_tercero, tipo)

    if tipo == "compra":

        registrar_factura_compra(fecha, tercero_id, nombre_tercero, base, igic, concepto)
        factura_id = obtener_ultima_factura_id()

        if estado == "pagada":
            pagar_factura_compra(factura_id, fecha)

    elif tipo == "venta":

        registrar_factura_venta(fecha, tercero_id, nombre_tercero, base, igic, concepto)
        factura_id = obtener_ultima_factura_id()

        if estado == "cobrada":
            cobrar_factura_venta(factura_id, fecha)

    else:
        print("Tipo de operación no reconocido")