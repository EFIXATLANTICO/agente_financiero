import re
import unicodedata


def normalizar_texto(texto):
    texto = texto or ""
    texto = texto.strip().lower()
    texto = unicodedata.normalize("NFD", texto)
    texto = "".join(c for c in texto if unicodedata.category(c) != "Mn")
    texto = re.sub(r"[^\w\s]", " ", texto)
    texto = re.sub(r"\s+", " ", texto).strip()
    return texto


def contiene_alguna(texto, palabras):
    t = normalizar_texto(texto)
    return any(normalizar_texto(p) in t for p in palabras)


def contiene_todas(texto, palabras):
    t = normalizar_texto(texto)
    return all(normalizar_texto(p) in t for p in palabras)


FAMILIAS_OPERACION = {
    # =========================================================
    # COMPRAS DE EXISTENCIAS / MERCADERIAS
    # =========================================================
    "compra_mercaderias": {
        "aliases": [
            "compra de mercaderias",
            "compra mercaderias",
            "adquisicion de mercaderias",
            "compra de existencias",
            "compra de genero",
            "compra de stock",
            "reposicion de mercaderias",
            "factura de proveedor por mercaderias",
            "factura de proveedor por genero",
            "compra de productos para la venta",
        ],
        "keywords_any": [
            "mercaderias", "mercancia", "mercancias", "existencias",
            "genero", "stock", "productos para la venta"
        ],
        "keywords_all": [
            ["compra", "mercaderias"],
            ["compra", "existencias"],
            ["adquisicion", "mercaderias"],
        ],
        "reglas": {
            "tipo": "compra",
            "subtipo": "mercaderias",
            "cuenta_base": "cuenta_compra_mercaderia",
        },
        "plantilla": {
            "lineas": [
                {"cuenta": "cuenta_compra_mercaderia", "lado": "debe", "formula": "base"},
                {"cuenta": "cuenta_igic_soportado", "lado": "debe", "formula": "impuesto"},
                {"cuenta": "cuenta_proveedores_o_bancos", "lado": "haber", "formula": "total"},
            ]
        },
    },
    "anticipo_a_proveedor": {
        "aliases": [
            "anticipo a proveedor",
            "pago anticipado a proveedor",
            "entrega a cuenta a proveedor",
            "anticipo de compra",
        ],
        "keywords_any": [
            "anticipo", "pago anticipado", "entrega a cuenta", "proveedor"
        ],
        "keywords_all": [
            ["anticipo", "proveedor"],
            ["entrega", "cuenta", "proveedor"],
        ],
        "reglas": {
            "tipo": "compra",
            "subtipo": "anticipo_proveedor",
        },
        "plantilla": {
            "lineas": [
                {"cuenta": "cuenta_anticipo_proveedor", "lado": "debe", "formula": "base"},
                {"cuenta": "cuenta_bancos_o_caja", "lado": "haber", "formula": "base"},
            ]
        },
    },

    "anticipo_de_cliente": {
        "aliases": [
            "anticipo de cliente",
            "anticipo de un cliente",
            "cobro anticipado de cliente",
            "entrega a cuenta del cliente",
            "anticipo recibido de cliente",
        ],
        "keywords_any": [
            "anticipo", "cliente", "cobro anticipado", "entrega a cuenta"
        ],
        "keywords_all": [
            ["anticipo", "cliente"],
            ["entrega", "cuenta", "cliente"],
        ],
        "reglas": {
            "tipo": "venta",
            "subtipo": "anticipo_cliente",
        },
        "plantilla": {
            "lineas": [
                {"cuenta": "cuenta_bancos_o_caja", "lado": "debe", "formula": "base"},
                {"cuenta": "cuenta_anticipo_cliente", "lado": "haber", "formula": "base"},
            ]
        },
    },

    "fianza_entregada": {
        "aliases": [
            "fianza entregada",
            "deposito entregado como fianza",
            "fianza por alquiler entregada",
            "constitucion de fianza",
        ],
        "keywords_any": [
            "fianza", "deposito", "deposito", "entregada"
        ],
        "keywords_all": [
            ["fianza", "entregada"],
            ["deposito", "fianza"],
        ],
        "reglas": {
            "tipo": "compra",
            "subtipo": "fianza_entregada",
        },
        "plantilla": {
            "lineas": [
                {"cuenta": "cuenta_fianza_constituida", "lado": "debe", "formula": "base"},
                {"cuenta": "cuenta_bancos_o_caja", "lado": "haber", "formula": "base"},
            ]
        },
    },

    "fianza_recibida": {
        "aliases": [
            "fianza recibida",
            "deposito recibido como fianza",
            "cobro de fianza",
            "fianza de cliente recibida",
        ],
        "keywords_any": [
            "fianza", "deposito", "deposito", "recibida"
        ],
        "keywords_all": [
            ["fianza", "recibida"],
            ["cobro", "fianza"],
        ],
        "reglas": {
            "tipo": "venta",
            "subtipo": "fianza_recibida",
        },
        "plantilla": {
            "lineas": [
                {"cuenta": "cuenta_bancos_o_caja", "lado": "debe", "formula": "base"},
                {"cuenta": "cuenta_fianza_recibida", "lado": "haber", "formula": "base"},
            ]
        },
    },

    "prestamo_bancario_recibido": {
        "aliases": [
            "prestamo bancario recibido",
            "recibimos un prestamo bancario",
            "entrada de prestamo bancario",
            "concesion de prestamo bancario",
        ],
        "keywords_any": [
            "prestamo", "prestamo", "bancario", "banco"
        ],
        "keywords_all": [
            ["prestamo", "banco"],
            ["prestamo", "bancario"],
        ],
        "reglas": {
            "tipo": "financiacion",
            "subtipo": "prestamo_recibido",
        },
        "plantilla": {
            "lineas": [
                {"cuenta": "cuenta_bancos", "lado": "debe", "formula": "base"},
                {"cuenta": "cuenta_prestamo_lp", "lado": "haber", "formula": "base"},
            ]
        },
    },

    "devolucion_principal_prestamo": {
        "aliases": [
            "devolucion del principal del prestamo",
            "amortizacion de prestamo",
            "reembolso de prestamo",
            "pago del principal del prestamo",
        ],
        "keywords_any": [
            "devolucion", "amortizacion", "amortizacion", "principal", "prestamo", "prestamo"
        ],
        "keywords_all": [
            ["principal", "prestamo"],
            ["amortizacion", "prestamo"],
            ["devolucion", "prestamo"],
        ],
        "reglas": {
            "tipo": "financiacion",
            "subtipo": "devolucion_prestamo",
        },
        "plantilla": {
            "lineas": [
                {"cuenta": "cuenta_prestamo_lp", "lado": "debe", "formula": "base"},
                {"cuenta": "cuenta_bancos", "lado": "haber", "formula": "base"},
            ]
        },
    },

    "pago_intereses_prestamo": {
        "aliases": [
            "pago de intereses del prestamo",
            "intereses del prestamo",
            "pago de intereses bancarios",
            "liquidacion de intereses",
        ],
        "keywords_any": [
            "intereses", "interes", "prestamo", "prestamo", "bancarios"
        ],
        "keywords_all": [
            ["intereses", "prestamo"],
            ["pago", "intereses"],
        ],
        "reglas": {
            "tipo": "financiacion",
            "subtipo": "intereses",
        },
        "plantilla": {
            "lineas": [
                {"cuenta": "cuenta_intereses_deudas", "lado": "debe", "formula": "base"},
                {"cuenta": "cuenta_bancos", "lado": "haber", "formula": "base"},
            ]
        },
    },

    # =========================================================
    # INMOVILIZADO MATERIAL
    # =========================================================
    "compra_inmovilizado_aplicaciones_informaticas": {
        "aliases": [
            "compra de software",
            "compra software",
            "compra de programa informatico",
            "compra de licencia",
            "compra de licencias",
            "adquisicion de software",
            "adquisicion de licencia",
            "suscripcion anual software",
            "licencia perpetua software",
        ],
        "keywords_any": [
            "software", "licencia", "licencias", "programa informatico",
            "programa", "erp", "crm"
        ],
        "keywords_all": [
            ["compra", "software"],
            ["compra", "licencia"],
            ["adquisicion", "software"],
        ],
        "reglas": {
            "tipo": "compra",
            "subtipo": "inmovilizado_intangible",
            "cuenta_activo": "206 Aplicaciones informaticas",
        },
        "plantilla": {
            "lineas": [
                {"cuenta": "cuenta_inmovilizado", "lado": "debe", "formula": "base"},
                {"cuenta": "cuenta_igic_soportado", "lado": "debe", "formula": "impuesto"},
                {"cuenta": "cuenta_proveedores_o_bancos", "lado": "haber", "formula": "total"},
            ]
        },
    },

    "compra_inmovilizado_equipos_informaticos": {
        "aliases": [
            "compra de ordenador",
            "compra ordenador",
            "compra de ordenadores",
            "compra ordenadores",
            "compra de portatil",
            "compra portatil",
            "compra de portatiles",
            "compra portatiles",
            "compra de pc",
            "compra pc",
            "compra de equipo informatico",
            "compra equipo informatico",
            "compra de equipos informaticos",
            "compra equipos informaticos",
            "adquisicion de ordenador",
            "adquisicion de equipos informaticos",
            "compra de monitor",
            "compra monitor",
            "compra de impresora",
            "compra impresora",
            "compra de escaner",
            "compra escaner",
            "compra de tablet",
            "compra tablet",
            "compra de servidor",
            "compra servidor",
            "compra de hardware",
            "compra hardware",
        ],
        "keywords_any": [
            "ordenador", "ordenadores", "portatil", "portatiles", "pc",
            "monitor", "impresora", "escaner", "scanner", "tablet",
            "servidor", "hardware", "equipo informatico", "equipos informaticos"
        ],
        "keywords_all": [
            ["compra", "ordenador"],
            ["compra", "portatil"],
            ["compra", "equipo informatico"],
            ["adquisicion", "hardware"],
        ],
        "reglas": {
            "tipo": "compra",
            "subtipo": "inmovilizado",
            "cuenta_activo": "217 Equipos para procesos de informacion",
        },
        "plantilla": {
            "lineas": [
                {"cuenta": "cuenta_inmovilizado", "lado": "debe", "formula": "base"},
                {"cuenta": "cuenta_igic_soportado", "lado": "debe", "formula": "impuesto"},
                {"cuenta": "cuenta_proveedores_o_bancos", "lado": "haber", "formula": "total"},
            ]
        },
    },

    "compra_inmovilizado_mobiliario": {
        "aliases": [
            "compra de mobiliario",
            "compra mobiliario",
            "adquisicion de mobiliario",
            "compra de muebles",
            "compra muebles",
            "compra de mesa",
            "compra mesa",
            "compra de mesas",
            "compra de silla",
            "compra silla",
            "compra de sillas",
            "compra sillas",
            "compra de armario",
            "compra armario",
            "compra de estanteria",
            "compra estanteria",
            "compra de mostrador",
            "compra mostrador",
        ],
        "keywords_any": [
            "mobiliario", "mueble", "muebles", "mesa", "mesas",
            "silla", "sillas", "armario", "armarios", "estanteria",
            "estanterias", "mostrador", "mostradores"
        ],
        "keywords_all": [
            ["compra", "mobiliario"],
            ["compra", "muebles"],
            ["adquisicion", "mobiliario"],
        ],
        "reglas": {
            "tipo": "compra",
            "subtipo": "inmovilizado",
            "cuenta_activo": "216 Mobiliario",
        },
        "plantilla": {
            "lineas": [
                {"cuenta": "cuenta_inmovilizado", "lado": "debe", "formula": "base"},
                {"cuenta": "cuenta_igic_soportado", "lado": "debe", "formula": "impuesto"},
                {"cuenta": "cuenta_proveedores_o_bancos", "lado": "haber", "formula": "total"},
            ]
        },
    },

    "compra_inmovilizado_maquinaria": {
        "aliases": [
            "compra de maquinaria",
            "compra maquinaria",
            "compra de maquina",
            "compra maquina",
            "compra de maquinas",
            "compra maquinas",
            "adquisicion de maquinaria",
            "adquisicion de maquina",
            "compra de equipo industrial",
            "compra equipo industrial",
            "compra de torno",
            "compra torno",
            "compra de fresadora",
            "compra fresadora",
        ],
        "keywords_any": [
            "maquinaria", "maquina", "maquinas", "torno",
            "fresadora", "equipo industrial", "equipos industriales"
        ],
        "keywords_all": [
            ["compra", "maquinaria"],
            ["compra", "maquina"],
            ["adquisicion", "maquinaria"],
        ],
        "reglas": {
            "tipo": "compra",
            "subtipo": "inmovilizado",
            "cuenta_activo": "213 Maquinaria",
        },
        "plantilla": {
            "lineas": [
                {"cuenta": "cuenta_inmovilizado", "lado": "debe", "formula": "base"},
                {"cuenta": "cuenta_igic_soportado", "lado": "debe", "formula": "impuesto"},
                {"cuenta": "cuenta_proveedores_o_bancos", "lado": "haber", "formula": "total"},
            ]
        },
    },

    "compra_inmovilizado_instalaciones": {
        "aliases": [
            "compra de instalacion",
            "compra instalacion",
            "compra de instalaciones",
            "compra instalaciones",
            "instalacion electrica",
            "instalacion de aire acondicionado",
            "instalacion de red",
            "instalacion tecnica",
        ],
        "keywords_any": [
            "instalacion", "instalaciones", "instalacion electrica",
            "aire acondicionado", "instalacion tecnica", "red"
        ],
        "keywords_all": [
            ["compra", "instalacion"],
            ["compra", "instalaciones"],
        ],
        "reglas": {
            "tipo": "compra",
            "subtipo": "inmovilizado",
            "cuenta_activo": "212 Instalaciones tecnicas",
        },
        "plantilla": {
            "lineas": [
                {"cuenta": "cuenta_inmovilizado", "lado": "debe", "formula": "base"},
                {"cuenta": "cuenta_igic_soportado", "lado": "debe", "formula": "impuesto"},
                {"cuenta": "cuenta_proveedores_o_bancos", "lado": "haber", "formula": "total"},
            ]
        },
    },

    "compra_inmovilizado_elementos_transporte": {
        "aliases": [
            "compra de vehiculo",
            "compra vehiculo",
            "compra de vehiculos",
            "compra vehiculos",
            "compra de coche",
            "compra coche",
            "compra de coche de empresa",
            "compra de furgoneta",
            "compra furgoneta",
            "compra de camion",
            "compra camion",
            "adquisicion de vehiculo",
            "adquisicion de coche",
        ],
        "keywords_any": [
            "vehiculo", "vehiculos", "coche", "coches", "furgoneta",
            "furgonetas", "camion", "camiones"
        ],
        "keywords_all": [
            ["compra", "vehiculo"],
            ["compra", "coche"],
            ["compra", "furgoneta"],
            ["adquisicion", "vehiculo"],
        ],
        "reglas": {
            "tipo": "compra",
            "subtipo": "inmovilizado",
            "cuenta_activo": "218 Elementos de transporte",
        },
        "plantilla": {
            "lineas": [
                {"cuenta": "cuenta_inmovilizado", "lado": "debe", "formula": "base"},
                {"cuenta": "cuenta_igic_soportado", "lado": "debe", "formula": "impuesto"},
                {"cuenta": "cuenta_proveedores_o_bancos", "lado": "haber", "formula": "total"},
            ]
        },
    },

    # =========================================================
    # GASTOS DE EXPLOTACION
    # =========================================================
    "gasto_arrendamientos": {
        "aliases": [
            "factura de alquiler",
            "pago de alquiler",
            "alquiler del local",
            "alquiler oficina",
            "alquiler nave",
            "renta local",
            "arrendamiento del local",
            "alquiler mensual",
        ],
        "keywords_any": [
            "alquiler", "arrendamiento", "renta"
        ],
        "keywords_all": [
            ["factura", "alquiler"],
            ["pago", "alquiler"],
        ],
        "reglas": {
            "tipo": "compra",
            "subtipo": "gasto",
            "cuenta_gasto": "621 Arrendamientos y canones",
        },
        "plantilla": {
            "lineas": [
                {"cuenta": "cuenta_gasto", "lado": "debe", "formula": "base"},
                {"cuenta": "cuenta_igic_soportado", "lado": "debe", "formula": "impuesto"},
                {"cuenta": "cuenta_proveedores_o_bancos", "lado": "haber", "formula": "total"},
            ]
        },
    },

    "gasto_reparaciones_conservacion": {
        "aliases": [
            "factura de reparacion",
            "factura reparacion",
            "reparacion de maquinaria",
            "reparacion de ordenador",
            "mantenimiento tecnico",
            "servicio tecnico",
            "conservacion del local",
        ],
        "keywords_any": [
            "reparacion", "reparaciones", "mantenimiento",
            "conservacion", "servicio tecnico"
        ],
        "keywords_all": [
            ["factura", "reparacion"],
            ["pago", "reparacion"],
            ["factura", "mantenimiento"],
        ],
        "reglas": {
            "tipo": "compra",
            "subtipo": "gasto",
            "cuenta_gasto": "622 Reparaciones y conservacion",
        },
        "plantilla": {
            "lineas": [
                {"cuenta": "cuenta_gasto", "lado": "debe", "formula": "base"},
                {"cuenta": "cuenta_igic_soportado", "lado": "debe", "formula": "impuesto"},
                {"cuenta": "cuenta_proveedores_o_bancos", "lado": "haber", "formula": "total"},
            ]
        },
    },

    "gasto_profesionales_independientes": {
        "aliases": [
            "factura de asesoria",
            "factura asesoria",
            "factura de asesoria",
            "factura asesoria fiscal",
            "factura abogado",
            "factura gestor",
            "factura consultoria",
            "honorarios profesionales",
            "factura notaria",
            "factura auditoria",
        ],
        "keywords_any": [
            "asesoria", "asesoria", "asesoria fiscal", "gestoria",
            "gestoria", "abogado", "consultoria", "consultoria",
            "honorarios", "notaria", "notaria", "auditoria", "auditoria"
        ],
        "keywords_all": [
            ["factura", "asesoria"],
            ["factura", "abogado"],
            ["factura", "consultoria"],
            ["honorarios", "profesionales"],
        ],
        "reglas": {
            "tipo": "compra",
            "subtipo": "gasto",
            "cuenta_gasto": "623 Servicios de profesionales independientes",
        },
        "plantilla": {
            "lineas": [
                {"cuenta": "cuenta_gasto", "lado": "debe", "formula": "base"},
                {"cuenta": "cuenta_igic_soportado", "lado": "debe", "formula": "impuesto"},
                {"cuenta": "cuenta_proveedores_o_bancos", "lado": "haber", "formula": "total"},
            ]
        },
    },

    "gasto_transportes": {
        "aliases": [
            "factura de transporte",
            "factura transporte",
            "gastos de transporte",
            "portes",
            "servicio de mensajeria",
            "factura de mensajeria",
            "envio de mercaderias",
            "transporte de mercaderias",
        ],
        "keywords_any": [
            "transporte", "portes", "mensajeria", "mensajeria",
            "envio", "envios", "paqueteria", "paqueteria"
        ],
        "keywords_all": [
            ["factura", "transporte"],
            ["gastos", "transporte"],
            ["factura", "mensajeria"],
        ],
        "reglas": {
            "tipo": "compra",
            "subtipo": "gasto",
            "cuenta_gasto": "624 Transportes",
        },
        "plantilla": {
            "lineas": [
                {"cuenta": "cuenta_gasto", "lado": "debe", "formula": "base"},
                {"cuenta": "cuenta_igic_soportado", "lado": "debe", "formula": "impuesto"},
                {"cuenta": "cuenta_proveedores_o_bancos", "lado": "haber", "formula": "total"},
            ]
        },
    },

    "gasto_primas_seguro": {
        "aliases": [
            "factura de seguro",
            "pago de seguro",
            "prima de seguro",
            "seguro anual",
            "seguro del local",
            "seguro del vehiculo",
            "seguro de responsabilidad civil",
        ],
        "keywords_any": [
            "seguro", "seguros", "prima", "poliza", "poliza"
        ],
        "keywords_all": [
            ["factura", "seguro"],
            ["pago", "seguro"],
            ["prima", "seguro"],
        ],
        "reglas": {
            "tipo": "compra",
            "subtipo": "gasto",
            "cuenta_gasto": "625 Primas de seguros",
        },
        "plantilla": {
            "lineas": [
                {"cuenta": "cuenta_gasto", "lado": "debe", "formula": "base"},
                {"cuenta": "cuenta_igic_soportado", "lado": "debe", "formula": "impuesto"},
                {"cuenta": "cuenta_proveedores_o_bancos", "lado": "haber", "formula": "total"},
            ]
        },
    },

    "gasto_servicios_bancarios": {
        "aliases": [
            "comision bancaria",
            "comision de banco",
            "gastos bancarios",
            "comision por transferencia",
            "comision mantenimiento cuenta",
        ],
        "keywords_any": [
            "comision", "comision", "bancaria", "bancario",
            "gastos bancarios"
        ],
        "keywords_all": [
            ["comision", "bancaria"],
            ["gastos", "bancarios"],
        ],
        "reglas": {
            "tipo": "compra",
            "subtipo": "financiero",
            "cuenta_gasto": "626 Servicios bancarios y similares",
        },
        "plantilla": {
            "lineas": [
                {"cuenta": "cuenta_gasto", "lado": "debe", "formula": "base"},
                {"cuenta": "cuenta_bancos", "lado": "haber", "formula": "base"},
            ]
        },
    },

    "gasto_publicidad": {
        "aliases": [
            "factura de publicidad",
            "factura publicidad",
            "campana publicitaria",
            "google ads",
            "facebook ads",
            "meta ads",
            "anuncio publicitario",
            "marketing digital",
            "servicios de publicidad",
        ],
        "keywords_any": [
            "publicidad", "marketing", "campana", "ads", "anuncio"
        ],
        "keywords_all": [
            ["factura", "publicidad"],
            ["servicio", "publicidad"],
            ["campana", "publicitaria"],
        ],
        "reglas": {
            "tipo": "compra",
            "subtipo": "gasto",
            "cuenta_gasto": "627 Publicidad, propaganda y relaciones publicas",
        },
        "plantilla": {
            "lineas": [
                {"cuenta": "cuenta_gasto", "lado": "debe", "formula": "base"},
                {"cuenta": "cuenta_igic_soportado", "lado": "debe", "formula": "impuesto"},
                {"cuenta": "cuenta_proveedores_o_bancos", "lado": "haber", "formula": "total"},
            ]
        },
    },

    "gasto_suministros": {
        "aliases": [
            "factura de luz",
            "factura luz",
            "factura de agua",
            "factura agua",
            "factura de electricidad",
            "factura electricidad",
            "factura de internet",
            "factura internet",
            "factura de telefono",
            "factura telefono",
            "factura de movil",
            "factura movil",
            "recibo de suministros",
        ],
        "keywords_any": [
            "luz", "agua", "electricidad", "internet", "telefono",
            "telefono", "movil", "movil", "fibra", "suministro", "suministros"
        ],
        "keywords_all": [
            ["factura", "luz"],
            ["factura", "agua"],
            ["factura", "internet"],
            ["factura", "telefono"],
        ],
        "reglas": {
            "tipo": "compra",
            "subtipo": "gasto",
            "cuenta_gasto": "628 Suministros",
        },
        "plantilla": {
            "lineas": [
                {"cuenta": "cuenta_gasto", "lado": "debe", "formula": "base"},
                {"cuenta": "cuenta_igic_soportado", "lado": "debe", "formula": "impuesto"},
                {"cuenta": "cuenta_proveedores_o_bancos", "lado": "haber", "formula": "total"},
            ]
        },
    },

    "gasto_otros_servicios": {
        "aliases": [
            "otros servicios",
            "gastos varios",
            "servicios diversos",
            "factura de limpieza",
            "factura limpieza",
            "factura vigilancia",
            "factura suscripcion",
            "factura plataforma",
        ],
        "keywords_any": [
            "limpieza", "vigilancia", "suscripcion", "suscripcion",
            "plataforma", "servicios diversos", "gastos varios"
        ],
        "keywords_all": [
            ["factura", "limpieza"],
            ["factura", "vigilancia"],
            ["factura", "suscripcion"],
        ],
        "reglas": {
            "tipo": "compra",
            "subtipo": "gasto",
            "cuenta_gasto": "629 Otros servicios",
        },
        "plantilla": {
            "lineas": [
                {"cuenta": "cuenta_gasto", "lado": "debe", "formula": "base"},
                {"cuenta": "cuenta_igic_soportado", "lado": "debe", "formula": "impuesto"},
                {"cuenta": "cuenta_proveedores_o_bancos", "lado": "haber", "formula": "total"},
            ]
        },
    },

    "gasto_tributos": {
        "aliases": [
            "pago de ibi",
            "pago de tasas",
            "pago de impuesto municipal",
            "tributos locales",
            "tasa de basura",
            "impuesto de circulacion",
        ],
        "keywords_any": [
            "ibi", "tasas", "tasa", "tributos", "impuesto municipal",
            "basura", "circulacion", "circulacion"
        ],
        "keywords_all": [
            ["pago", "ibi"],
            ["pago", "tasas"],
            ["pago", "tributos"],
        ],
        "reglas": {
            "tipo": "compra",
            "subtipo": "tributo",
            "cuenta_gasto": "631 Otros tributos",
        },
        "plantilla": {
            "lineas": [
                {"cuenta": "cuenta_gasto", "lado": "debe", "formula": "base"},
                {"cuenta": "cuenta_proveedores_o_bancos", "lado": "haber", "formula": "base"},
            ]
        },
    },

    # =========================================================
    # GASTOS FINANCIEROS
    # =========================================================
    "gasto_intereses_deudas": {
        "aliases": [
            "pago de intereses",
            "intereses de prestamo",
            "intereses bancarios",
            "liquidacion de intereses",
            "cargo por intereses",
        ],
        "keywords_any": [
            "intereses", "interes", "liquidacion de intereses", "prestamo", "prestamo"
        ],
        "keywords_all": [
            ["pago", "intereses"],
            ["intereses", "prestamo"],
            ["intereses", "bancarios"],
        ],
        "reglas": {
            "tipo": "compra",
            "subtipo": "financiero",
            "cuenta_gasto": "662 Intereses de deudas",
        },
        "plantilla": {
            "lineas": [
                {"cuenta": "cuenta_gasto", "lado": "debe", "formula": "base"},
                {"cuenta": "cuenta_bancos", "lado": "haber", "formula": "base"},
            ]
        },
    },

    # =========================================================
    # VENTAS / INGRESOS
    # =========================================================
    "venta_mercaderias": {
        "aliases": [
            "venta de mercaderias",
            "venta mercaderias",
            "venta de productos",
            "venta productos",
            "vendemos mercaderias",
            "factura a cliente por venta",
            "factura emitida por venta",
        ],
        "keywords_any": [
            "venta", "vendemos", "mercaderias", "mercancias",
            "productos", "producto"
        ],
        "keywords_all": [
            ["venta", "mercaderias"],
            ["venta", "productos"],
            ["factura", "venta"],
        ],
        "reglas": {
            "tipo": "venta",
            "subtipo": "venta",
            "cuenta_ingreso": "cuenta_ingreso_venta",
        },
        "plantilla": {
            "lineas": [
                {"cuenta": "cuenta_clientes_o_bancos", "lado": "debe", "formula": "total"},
                {"cuenta": "cuenta_ingreso_venta", "lado": "haber", "formula": "base"},
                {"cuenta": "cuenta_igic_repercutido", "lado": "haber", "formula": "impuesto"},
            ]
        },
    },

    "venta_servicios": {
        "aliases": [
            "prestacion de servicios",
            "prestacion de servicio",
            "servicio prestado",
            "factura de servicios",
            "factura emitida por servicios",
            "servicio de mantenimiento",
            "honorarios facturados",
        ],
        "keywords_any": [
            "servicio", "servicios", "prestacion", "prestacion",
            "mantenimiento", "honorarios", "consultoria", "consultoria"
        ],
        "keywords_all": [
            ["prestacion", "servicios"],
            ["factura", "servicios"],
            ["servicio", "prestado"],
        ],
        "reglas": {
            "tipo": "venta",
            "subtipo": "servicios",
            "cuenta_ingreso": "cuenta_ingreso_servicio",
        },
        "plantilla": {
            "lineas": [
                {"cuenta": "cuenta_clientes_o_bancos", "lado": "debe", "formula": "total"},
                {"cuenta": "cuenta_ingreso_servicio", "lado": "haber", "formula": "base"},
                {"cuenta": "cuenta_igic_repercutido", "lado": "haber", "formula": "impuesto"},
            ]
        },
    },

    "ingreso_alquileres": {
        "aliases": [
            "cobro de alquiler",
            "ingreso por alquiler",
            "factura de alquiler emitida",
            "alquiler cobrado",
            "arrendamiento facturado",
            "renta cobrada",
        ],
        "keywords_any": [
            "alquiler", "arrendamiento", "renta"
        ],
        "keywords_all": [
            ["cobro", "alquiler"],
            ["factura", "alquiler"],
            ["ingreso", "alquiler"],
        ],
        "reglas": {
            "tipo": "venta",
            "subtipo": "alquileres",
            "cuenta_ingreso": "cuenta_ingreso_alquiler",
        },
        "plantilla": {
            "lineas": [
                {"cuenta": "cuenta_clientes_o_bancos", "lado": "debe", "formula": "total"},
                {"cuenta": "cuenta_ingreso_alquiler", "lado": "haber", "formula": "base"},
                {"cuenta": "cuenta_igic_repercutido", "lado": "haber", "formula": "impuesto"},
            ]
        },
    },

    # =========================================================
    # ANTICIPOS
    # =========================================================
    "anticipo_a_proveedor": {
        "aliases": [
            "anticipo a proveedor",
            "pago anticipado a proveedor",
            "entrega a cuenta a proveedor",
            "anticipo de compra",
        ],
        "keywords_any": [
            "anticipo", "pago anticipado", "entrega a cuenta"
        ],
        "keywords_all": [
            ["anticipo", "proveedor"],
            ["entrega", "cuenta", "proveedor"],
        ],
        "reglas": {
            "tipo": "compra",
            "subtipo": "anticipo_proveedor",
            "cuenta_base": "407 Anticipos a proveedores",
        },
        "plantilla": {
            "lineas": [
                {"cuenta": "cuenta_personalizada_base", "lado": "debe", "formula": "base"},
                {"cuenta": "cuenta_bancos_o_caja", "lado": "haber", "formula": "base"},
            ]
        },
    },

    "anticipo_de_cliente": {
        "aliases": [
            "anticipo de cliente",
            "cobro anticipado de cliente",
            "entrega a cuenta del cliente",
            "anticipo recibido de cliente",
        ],
        "keywords_any": [
            "anticipo", "cobro anticipado", "entrega a cuenta"
        ],
        "keywords_all": [
            ["anticipo", "cliente"],
            ["entrega", "cuenta", "cliente"],
        ],
        "reglas": {
            "tipo": "venta",
            "subtipo": "anticipo_cliente",
            "cuenta_base": "438 Anticipos de clientes",
        },
        "plantilla": {
            "lineas": [
                {"cuenta": "cuenta_bancos_o_caja", "lado": "debe", "formula": "base"},
                {"cuenta": "cuenta_personalizada_base", "lado": "haber", "formula": "base"},
            ]
        },
    },

    # =========================================================
    # FIANZAS
    # =========================================================
    "fianza_constituida": {
        "aliases": [
            "constitucion de fianza",
            "fianza entregada",
            "fianza de alquiler entregada",
            "deposito entregado como fianza",
        ],
        "keywords_any": [
            "fianza", "deposito", "deposito"
        ],
        "keywords_all": [
            ["fianza", "entregada"],
            ["deposito", "fianza"],
        ],
        "reglas": {
            "tipo": "compra",
            "subtipo": "fianza",
            "cuenta_base": "260 Fianzas constituidas a largo plazo",
        },
        "plantilla": {
            "lineas": [
                {"cuenta": "cuenta_personalizada_base", "lado": "debe", "formula": "base"},
                {"cuenta": "cuenta_bancos_o_caja", "lado": "haber", "formula": "base"},
            ]
        },
    },

    "fianza_recibida": {
        "aliases": [
            "fianza recibida",
            "deposito recibido como fianza",
            "cobro de fianza",
            "fianza de cliente recibida",
        ],
        "keywords_any": [
            "fianza", "deposito", "deposito"
        ],
        "keywords_all": [
            ["fianza", "recibida"],
            ["cobro", "fianza"],
        ],
        "reglas": {
            "tipo": "venta",
            "subtipo": "fianza",
            "cuenta_base": "180 Fianzas recibidas a largo plazo",
        },
        "plantilla": {
            "lineas": [
                {"cuenta": "cuenta_bancos_o_caja", "lado": "debe", "formula": "base"},
                {"cuenta": "cuenta_personalizada_base", "lado": "haber", "formula": "base"},
            ]
        },
    },

    # =========================================================
    # PRESTAMOS
    # =========================================================
    "prestamo_recibido_banco": {
        "aliases": [
            "prestamo bancario recibido",
            "concesion de prestamo bancario",
            "entrada de prestamo bancario",
            "recibimos un prestamo del banco",
        ],
        "keywords_any": [
            "prestamo bancario", "prestamo bancario", "prestamo del banco", "prestamo del banco"
        ],
        "keywords_all": [
            ["prestamo", "banco"],
            ["prestamo", "bancario"],
        ],
        "reglas": {
            "tipo": "financiacion",
            "subtipo": "prestamo",
            "cuenta_pasivo": "170 Deudas a largo plazo con entidades de credito",
        },
        "plantilla": {
            "lineas": [
                {"cuenta": "cuenta_bancos", "lado": "debe", "formula": "base"},
                {"cuenta": "cuenta_pasivo", "lado": "haber", "formula": "base"},
            ]
        },
    },

    "devolucion_principal_prestamo": {
        "aliases": [
            "amortizacion de prestamo",
            "devolucion de principal del prestamo",
            "pago de cuota de prestamo",
            "reembolso de prestamo",
        ],
        "keywords_any": [
            "amortizacion", "amortizacion", "principal", "prestamo", "prestamo", "cuota prestamo"
        ],
        "keywords_all": [
            ["amortizacion", "prestamo"],
            ["devolucion", "prestamo"],
            ["principal", "prestamo"],
        ],
        "reglas": {
            "tipo": "financiacion",
            "subtipo": "prestamo",
            "cuenta_pasivo": "170 Deudas a largo plazo con entidades de credito",
        },
        "plantilla": {
            "lineas": [
                {"cuenta": "cuenta_pasivo", "lado": "debe", "formula": "base"},
                {"cuenta": "cuenta_bancos", "lado": "haber", "formula": "base"},
            ]
        },
    },

    # =========================================================
    # SOCIOS Y CAPITAL
    # =========================================================
    "aportacion_socios": {
        "aliases": [
            "aportacion de socios",
            "aportacion socio",
            "ingreso de socios",
            "socios aportan dinero",
        ],
        "keywords_any": [
            "aportacion", "aportacion", "socios", "socio"
        ],
        "keywords_all": [
            ["aportacion", "socios"],
            ["aportacion", "socio"],
        ],
        "reglas": {
            "tipo": "especial",
            "subtipo": "aportacion_socios",
            "cuenta_base": "118 Aportaciones de socios",
        },
        "plantilla": {
            "lineas": [
                {"cuenta": "cuenta_bancos", "lado": "debe", "formula": "base"},
                {"cuenta": "cuenta_personalizada_base", "lado": "haber", "formula": "base"},
            ]
        },
    },

    "ampliacion_capital": {
        "aliases": [
            "ampliacion de capital",
            "ampliacion capital",
            "suscripcion de capital",
            "desembolso de capital",
        ],
        "keywords_any": [
            "ampliacion", "ampliacion", "capital", "desembolso"
        ],
        "keywords_all": [
            ["ampliacion", "capital"],
            ["desembolso", "capital"],
        ],
        "reglas": {
            "tipo": "especial",
            "subtipo": "capital",
            "cuenta_base": "100 Capital social",
        },
        "plantilla": {
            "lineas": [
                {"cuenta": "cuenta_bancos", "lado": "debe", "formula": "base"},
                {"cuenta": "cuenta_personalizada_base", "lado": "haber", "formula": "base"},
            ]
        },
    },

    # =========================================================
    # NOMINAS Y SEGURIDAD SOCIAL
    # =========================================================
    "nomina_sueldos_salarios": {
        "aliases": [
            "pago de nomina",
            "registro de nomina",
            "nomina del mes",
            "sueldos y salarios",
            "pago a trabajadores",
        ],
        "keywords_any": [
            "nomina", "nomina", "sueldos", "salarios", "trabajadores"
        ],
        "keywords_all": [
            ["pago", "nomina"],
            ["registro", "nomina"],
            ["sueldos", "salarios"],
        ],
        "reglas": {
            "tipo": "especial",
            "subtipo": "nomina",
            "cuenta_base": "640 Sueldos y salarios",
        },
        "plantilla": {
            "lineas": [
                {"cuenta": "cuenta_personalizada_base", "lado": "debe", "formula": "base"},
                {"cuenta": "cuenta_bancos", "lado": "haber", "formula": "base"},
            ]
        },
    },

    "seguridad_social_empresa": {
        "aliases": [
            "seguridad social a cargo de la empresa",
            "cuota patronal",
            "seguros sociales empresa",
            "tc1",
        ],
        "keywords_any": [
            "seguridad social", "cuota patronal", "seguros sociales", "tc1"
        ],
        "keywords_all": [
            ["seguridad", "social", "empresa"],
            ["cuota", "patronal"],
        ],
        "reglas": {
            "tipo": "especial",
            "subtipo": "ss_empresa",
            "cuenta_base": "642 Seguridad Social a cargo de la empresa",
        },
        "plantilla": {
            "lineas": [
                {"cuenta": "cuenta_personalizada_base", "lado": "debe", "formula": "base"},
                {"cuenta": "cuenta_bancos", "lado": "haber", "formula": "base"},
            ]
        },
    },
}


def clasificar_desde_catalogo(texto):
    t = normalizar_texto(texto)

    mejor_clave = None
    mejor_definicion = None
    mejor_puntuacion = -1

    for clave, definicion in FAMILIAS_OPERACION.items():
        puntuacion = 0

        for alias in definicion.get("aliases", []):
            alias_n = normalizar_texto(alias)
            if alias_n and alias_n in t:
                puntuacion += 120

        for kw in definicion.get("keywords_any", []):
            kw_n = normalizar_texto(kw)
            if kw_n and kw_n in t:
                puntuacion += 20

        for grupo in definicion.get("keywords_all", []):
            if contiene_todas(t, grupo):
                puntuacion += 50

        # refuerzos especificos
        if clave == "compra_inmovilizado_equipos_informaticos":
            if any(x in t for x in ["ordenador", "portatil", "pc", "monitor", "impresora", "servidor", "hardware"]):
                puntuacion += 80

        if clave == "compra_inmovilizado_mobiliario":
            if any(x in t for x in ["mobiliario", "muebles", "mesa", "sillas", "armario", "estanteria"]):
                puntuacion += 80

        if clave == "compra_inmovilizado_maquinaria":
            if any(x in t for x in ["maquinaria", "maquina", "maquinas", "torno", "fresadora"]):
                puntuacion += 80

        if clave == "gasto_suministros":
            if any(x in t for x in ["luz", "agua", "internet", "telefono", "electricidad", "movil"]):
                puntuacion += 70

        if clave == "venta_servicios":
            if any(x in t for x in ["servicio", "servicios", "honorarios", "mantenimiento"]):
                puntuacion += 60

        if clave == "ingreso_alquileres":
            if any(x in t for x in ["alquiler", "arrendamiento", "renta"]):
                puntuacion += 60

        if puntuacion > mejor_puntuacion:
            mejor_puntuacion = puntuacion
            mejor_clave = clave
            mejor_definicion = definicion

    if mejor_clave and mejor_puntuacion > 0:
        return {
            "clave": mejor_clave,
            "definicion": mejor_definicion,
            "score": mejor_puntuacion,
        }

    return None