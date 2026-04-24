from apertura_pdf import procesar_balance_pdf_a_apertura

pdf_path = "Balance Seralven.pdf"
fecha_apertura = "2026-01-01"

resultado = procesar_balance_pdf_a_apertura(pdf_path, fecha_apertura)

print("VALIDACION:")
print(resultado["validacion"])

print("\nLINEAS:")
for linea in resultado["lineas"]:
    print(linea)