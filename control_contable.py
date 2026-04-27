import pandas as pd
from db_context import get_connection
from pgc import obtener_cuenta_pgc, normalizar_cuenta


# =========================
# REVISIÓN CONTABLE
# =========================

def revisar_asientos():
    """
    Analiza los asientos contables y devuelve incidencias en DataFrame.
    """

    conn = get_connection()
    cursor = conn.cursor()

    cursor.execute("""
    SELECT id, fecha, concepto, tipo_operacion
    FROM asientos
    ORDER BY id DESC
    """)

    asientos = cursor.fetchall()
    incidencias = []

    for asiento_id, fecha, concepto, tipo_operacion in asientos:

        cursor.execute("""
        SELECT cuenta, movimiento, importe
        FROM lineas_asiento
        WHERE asiento_id = %s
        """, (asiento_id,))

        lineas = cursor.fetchall()

        total_debe = 0.0
        total_haber = 0.0

        # ------------------------
        # VALIDACIÓN ESTRUCTURA
        # ------------------------
        if len(lineas) < 2:
            incidencias.append([
                asiento_id, fecha, concepto, tipo_operacion,
                "Menos de 2 líneas"
            ])

        for cuenta, movimiento, importe in lineas:

            # Cuenta vacía
            if not cuenta or str(cuenta).strip() == "":
                incidencias.append([
                    asiento_id, fecha, concepto, tipo_operacion,
                    "Cuenta vacía"
                ])

            # Importe inválido
            if importe is None:
                incidencias.append([
                    asiento_id, fecha, concepto, tipo_operacion,
                    "Importe vacío"
                ])
                continue

            try:
                importe = float(importe)
            except Exception:
                incidencias.append([
                    asiento_id, fecha, concepto, tipo_operacion,
                    "Importe no numérico"
                ])
                continue

            if importe < 0:
                incidencias.append([
                    asiento_id, fecha, concepto, tipo_operacion,
                    "Importe negativo"
                ])

            # Movimiento
            if movimiento == "debe":
                total_debe += importe
            elif movimiento == "haber":
                total_haber += importe
            else:
                incidencias.append([
                    asiento_id, fecha, concepto, tipo_operacion,
                    "Movimiento no válido"
                ])

        # ------------------------
        # CUADRE CONTABLE
        # ------------------------
        if round(total_debe, 2) != round(total_haber, 2):
            incidencias.append([
                asiento_id,
                fecha,
                concepto,
                tipo_operacion,
                f"Descuadre: debe {round(total_debe, 2)} / haber {round(total_haber, 2)}"
            ])

    conn.close()

    df = pd.DataFrame(
        incidencias,
        columns=["Asiento", "Fecha", "Concepto", "Tipo", "Incidencia"]
    )

    return df

def validar_sistema_completo():
    import pandas as pd
    from db_context import get_connection

    conn = get_connection()
    cursor = conn.cursor()

    incidencias = []

    try:
        # =====================================================
        # 1) ASIENTOS SIN LÍNEAS
        # =====================================================
        cursor.execute("""
            SELECT a.id, a.fecha, a.concepto, a.tipo_operacion
            FROM asientos a
            LEFT JOIN lineas_asiento l ON a.id = l.asiento_id
            WHERE l.id IS NULL
            ORDER BY a.id
        """)
        for asiento_id, fecha, concepto, tipo_operacion in cursor.fetchall():
            incidencias.append({
                "tipo": "asiento_sin_lineas",
                "asiento_id": asiento_id,
                "fecha": str(fecha),
                "concepto": str(concepto or ""),
                "detalle": "El asiento no tiene líneas contables",
                "gravedad": "alta"
            })

        # =====================================================
        # 2) ASIENTOS DESCUADRADOS
        # =====================================================
        cursor.execute("""
            SELECT
                a.id,
                a.fecha,
                a.concepto,
                a.tipo_operacion,
                ROUND(COALESCE(SUM(CASE WHEN l.movimiento = 'debe' THEN l.importe::numeric ELSE 0 END), 0), 2) AS total_debe,
                ROUND(COALESCE(SUM(CASE WHEN l.movimiento = 'haber' THEN l.importe::numeric ELSE 0 END), 0), 2) AS total_haber
            FROM asientos a
            JOIN lineas_asiento l ON a.id = l.asiento_id
            GROUP BY a.id, a.fecha, a.concepto, a.tipo_operacion
            HAVING ROUND((COALESCE(SUM(CASE WHEN l.movimiento = 'debe' THEN l.importe::numeric ELSE 0 END), 0) - COALESCE(SUM(CASE WHEN l.movimiento = 'haber' THEN l.importe::numeric ELSE 0 END), 0)), 2) != 0
            ORDER BY a.id
        """)
        for asiento_id, fecha, concepto, tipo_operacion, total_debe, total_haber in cursor.fetchall():
            incidencias.append({
                "tipo": "asiento_descuadrado",
                "asiento_id": asiento_id,
                "fecha": str(fecha),
                "concepto": str(concepto or ""),
                "detalle": f"Asiento descuadrado | Debe={total_debe:.2f} | Haber={total_haber:.2f}",
                "gravedad": "alta"
            })

        # =====================================================
        # 3) IMPORTES ABSURDOS EN LÍNEAS
        # =====================================================
        cursor.execute("""
            SELECT
                l.asiento_id,
                a.fecha,
                a.concepto,
                l.cuenta,
                l.movimiento,
                l.importe
            FROM lineas_asiento l
            JOIN asientos a ON a.id = l.asiento_id
            WHERE ABS(COALESCE(l.importe, 0)) >= 100000
            ORDER BY l.asiento_id
        """)
        for asiento_id, fecha, concepto, cuenta, movimiento, importe in cursor.fetchall():
            incidencias.append({
                "tipo": "importe_absurdo",
                "asiento_id": asiento_id,
                "fecha": str(fecha),
                "concepto": str(concepto or ""),
                "detalle": f"Importe muy alto en línea | Cuenta={cuenta} | Movimiento={movimiento} | Importe={float(importe):.2f}",
                "gravedad": "alta"
            })

        # =====================================================
        # 4) SALDO DE CLIENTES (43) ACREEDOR
        # =====================================================
        cursor.execute("""
            SELECT
                SUBSTR(TRIM(cuenta), 1, 3) AS cuenta_base,
                ROUND(SUM(CASE
                    WHEN movimiento = 'debe' THEN importe::numeric
                    WHEN movimiento = 'haber' THEN -importe::numeric
                    ELSE 0
                END)::numeric, 2) AS saldo
            FROM lineas_asiento
            WHERE TRIM(cuenta) LIKE '43%'
            GROUP BY cuenta_base
        """)
        for cuenta_base, saldo in cursor.fetchall():
            if float(saldo or 0) < 0:
                incidencias.append({
                    "tipo": "cliente_saldo_acreedor",
                    "asiento_id": None,
                    "fecha": "",
                    "concepto": cuenta_base,
                    "detalle": f"La cuenta de clientes presenta saldo acreedor: {float(saldo):.2f}",
                    "gravedad": "media"
                })

        # =====================================================
        # 5) SALDO DE PROVEEDORES (40) DEUDOR
        # =====================================================
        cursor.execute("""
            SELECT
                SUBSTR(TRIM(cuenta), 1, 3) AS cuenta_base,
                ROUND(SUM(CASE
                    WHEN movimiento = 'haber' THEN importe::numeric
                    WHEN movimiento = 'debe' THEN -importe::numeric
                    ELSE 0
                END)::numeric, 2) AS saldo
            FROM lineas_asiento
            WHERE TRIM(cuenta) LIKE '40%'
            GROUP BY cuenta_base
        """)
        for cuenta_base, saldo in cursor.fetchall():
            if float(saldo or 0) < 0:
                incidencias.append({
                    "tipo": "proveedor_saldo_deudor",
                    "asiento_id": None,
                    "fecha": "",
                    "concepto": cuenta_base,
                    "detalle": f"La cuenta de proveedores presenta saldo deudor: {float(saldo):.2f}",
                    "gravedad": "media"
                })

        # =====================================================
        # 6) CAJA NEGATIVA (570)
        # =====================================================
        cursor.execute("""
            SELECT ROUND(SUM(CASE
                WHEN movimiento = 'debe' THEN importe::numeric
                WHEN movimiento = 'haber' THEN -importe::numeric
                ELSE 0
            END)::numeric, 2)
            FROM lineas_asiento
            WHERE TRIM(cuenta) LIKE '570%'
        """)
        saldo_caja = float(cursor.fetchone()[0] or 0)
        if saldo_caja < 0:
            incidencias.append({
                "tipo": "caja_negativa",
                "asiento_id": None,
                "fecha": "",
                "concepto": "570",
                "detalle": f"La caja presenta saldo negativo: {saldo_caja:.2f}",
                "gravedad": "alta"
            })

        # =====================================================
        # 7) BANCOS NEGATIVOS (572)
        # =====================================================
        cursor.execute("""
            SELECT ROUND(SUM(CASE
                WHEN movimiento = 'debe' THEN importe::numeric
                WHEN movimiento = 'haber' THEN -importe::numeric
                ELSE 0
            END)::numeric, 2)
            FROM lineas_asiento
            WHERE TRIM(cuenta) LIKE '572%'
        """)
        saldo_bancos = float(cursor.fetchone()[0] or 0)
        if saldo_bancos < 0:
            incidencias.append({
                "tipo": "bancos_negativos",
                "asiento_id": None,
                "fecha": "",
                "concepto": "572",
                "detalle": f"Los bancos presentan saldo negativo: {saldo_bancos:.2f}",
                "gravedad": "media"
            })

        # =====================================================
        # 8) DEVOLUCIONES DE FIANZA SIN FIANZA PREVIA
        # =====================================================
        cursor.execute("""
            SELECT id, fecha, concepto
            FROM asientos
            WHERE tipo_operacion = 'fianza_devuelta'
            ORDER BY id
        """)
        devoluciones = cursor.fetchall()

        for asiento_id, fecha, concepto in devoluciones:
            concepto_txt = str(concepto or "")
            concepto_referencia = concepto_txt.replace(
                "Devolución de fianza asociada a asiento",
                "Fianza asociada a asiento"
            )

            cursor.execute("""
                SELECT id
                FROM asientos
                WHERE tipo_operacion = 'fianza_recibida'
                  AND concepto = %s
                LIMIT 1
            """, (concepto_referencia,))
            previa = cursor.fetchone()

            if not previa:
                incidencias.append({
                    "tipo": "devolucion_sin_fianza_previa",
                    "asiento_id": asiento_id,
                    "fecha": str(fecha),
                    "concepto": concepto_txt,
                    "detalle": "Existe una devolución de fianza sin asiento previo de fianza recibida",
                    "gravedad": "alta"
                })

    finally:
        conn.close()

    if not incidencias:
        return pd.DataFrame(columns=["tipo", "asiento_id", "fecha", "concepto", "detalle", "gravedad"])

    df = pd.DataFrame(incidencias)

    orden_gravedad = {"alta": 1, "media": 2, "baja": 3}
    df["orden_gravedad"] = df["gravedad"].map(orden_gravedad).fillna(99)
    df = df.sort_values(by=["orden_gravedad", "tipo", "asiento_id"], na_position="last").reset_index(drop=True)
    df = df.drop(columns=["orden_gravedad"])

    return df


# =========================
# RESET CONTABLE
# =========================

def reset_contabilidad():
    """
    Borra toda la contabilidad de la empresa activa.
    """

    conn = get_connection()
    cursor = conn.cursor()

    tablas = [
        "lineas_asiento",
        "asientos_importacion",
        "importaciones",
        "facturas",
        "operaciones_asientos",
        "operaciones",
        "vencimientos",
        "validaciones_contables",
        "movimientos_bancarios",
        "movimientos_banco",
        "conciliaciones",
        "inmovilizado",
        "amortizaciones",
        "asientos"
    ]

    try:
        for tabla in tablas:
            try:
                cursor.execute(f"DELETE FROM {tabla}")
            except Exception:
                pass

        conn.commit()
        return "ok"

    except Exception as e:
        print("ERROR RESET:", e)
        return "error"


        # =====================================================
        # 8) DEVOLUCIONES DE FIANZA SIN FIANZA PREVIA
        # =====================================================
        cursor.execute("""
            SELECT id, fecha, concepto
            FROM asientos
            WHERE tipo_operacion = 'fianza_devuelta'
            ORDER BY id
        """)
        devoluciones = cursor.fetchall()

        for asiento_id, fecha, concepto in devoluciones:
            concepto_txt = str(concepto or "")
            concepto_referencia = concepto_txt.replace("Devolución de fianza asociada a asiento", "Fianza asociada a asiento")

            cursor.execute("""
                SELECT id
                FROM asientos
                WHERE tipo_operacion = 'fianza_recibida'
                  AND concepto = %s
                LIMIT 1
            """, (concepto_referencia,))
            previa = cursor.fetchone()

            if not previa:
                incidencias.append({
                    "tipo": "devolucion_sin_fianza_previa",
                    "asiento_id": asiento_id,
                    "fecha": str(fecha),
                    "concepto": concepto_txt,
                    "detalle": "Existe una devolución de fianza sin asiento previo de fianza recibida",
                    "gravedad": "alta"
                })

    finally:
        conn.close()

    if not incidencias:
        return pd.DataFrame(columns=["tipo", "asiento_id", "fecha", "concepto", "detalle", "gravedad"])

    df = pd.DataFrame(incidencias)

    orden_gravedad = {"alta": 1, "media": 2, "baja": 3}
    df["orden_gravedad"] = df["gravedad"].map(orden_gravedad).fillna(99)
    df = df.sort_values(by=["orden_gravedad", "tipo", "asiento_id"], na_position="last").reset_index(drop=True)
    df = df.drop(columns=["orden_gravedad"])

    return df
