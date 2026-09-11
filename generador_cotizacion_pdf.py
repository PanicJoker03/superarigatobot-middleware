"""
Generador de reportes de cotización de laboratorio (estilo Laboratorio Ramos).

Uso:
    python generador_cotizacion_pdf.py entrada.json salida
    (genera salida.pdf y salida.png)

El JSON de entrada debe tener esta forma:

{
  "laboratorio": {
    "nombre": "Laboratorio Alfonso Ramos S.A. de C.V.",
    "logo_texto_linea1": "Laboratorio",
    "logo_texto_linea2": "Ramos"
  },
  "folio": "26081818035",
  "fecha": "18/08/2026",
  "estudios": [
    {
      "clave": "1",
      "nombre": "CITOLOGIA HEMATICA",
      "precio_lista": 250.00,
      "descuento": 0.00,
      "precio_final": 250.00,
      "indicaciones": "Presentarse en el laboratorio con un ayuno de 8 - 10 horas."
    },
    {
      "clave": "PBQ24",
      "nombre": "PERFIL BIOQUIMICO 24 ELEMENTOS",
      "precio_lista": 1190.00,
      "descuento": 0.00,
      "precio_final": 1190.00,
      "indicaciones": "- PERFIL DE QUIMICAS, PROTEINAS SERICAS, PRUEBAS FUNCIONALES HEPATICAS, FOSFORO SERICO, SODIO SERICO, MAGNESIO SERICO (MG), POTASIO SERICO, HIERRO SERICO, GAMA GLUTAMIL TRANSFERASA SERICA (GGT), CLORUROS SERICOS, CALCIO SERICO:\nPresentarse en el laboratorio con un ayuno de 8 - 10 horas."
    }
  ],
  "subtotal": 1440.00,
  "descuento": 0.00,
  "cargo": 0.00,
  "total": 1440.00,
  "nota_precios": "*Precios con IVA incluido"
}

Campos opcionales: si "subtotal"/"descuento"/"cargo"/"total" no vienen, se calculan
a partir de los estudios (descuento = precio_lista - precio_final; cargo = 0).
"""

import json
import sys
import os
from reportlab.lib.pagesizes import letter
from reportlab.lib.colors import HexColor
from reportlab.lib.utils import ImageReader
from reportlab.pdfgen import canvas
from reportlab.pdfbase.pdfmetrics import stringWidth

PAGE_W, PAGE_H = letter

# ---- paleta / estilo -------------------------------------------------
NAVY = HexColor("#1b2a5e")
GREY_HEADER_BG = HexColor("#e9e9e9")
GREY_LINE = HexColor("#bdbdbd")
BLACK = HexColor("#000000")

MARGIN_L = 40
MARGIN_R = 40
CONTENT_W = PAGE_W - MARGIN_L - MARGIN_R

FONT_REG = "Helvetica"
FONT_BOLD = "Helvetica-Bold"
FONT_OBL = "Helvetica-Oblique"

class GeneradorCotizacionPDF:
    #def __init__(self):
        #self.data_path = data_path
    def money(self, v):
        try:
            return f"${float(v):,.2f}"
        except (TypeError, ValueError):
            return "$0.00"


    def draw_logo(self, c, x, y):
        """Círculo simple con una cruz/loop estilo 'R' para simular el logo,
        más el texto 'Laboratorio / Ramos' al lado."""
        r = 22
        c.saveState()
        c.setStrokeColor(NAVY)
        c.setLineWidth(2)
        c.circle(x + r, y, r, stroke=1, fill=0)
        c.setFont(FONT_BOLD, 20)
        c.setFillColor(NAVY)
        c.drawCentredString(x + r, y - 7, "R")
        # asterisco decorativo (como en el original)
        c.setFillColor(HexColor("#2e7dd7"))
        c.setFont(FONT_BOLD, 14)
        c.restoreState()

    def draw_header(self, c, data):
        top = PAGE_H - 50
        lab = data.get("laboratorio", {})

        # Logo
        logo_path = os.path.join(
            os.path.dirname(os.path.abspath(__file__)),
            "labs_ramos_logo.png",
        )

        if os.path.exists(logo_path):
            logo = ImageReader(logo_path)

            c.drawImage(
                logo,
                MARGIN_L,
                top - 30,
                width=45,
                height=38,
                preserveAspectRatio=True,
                mask="auto",
            )
        else:
            # Optional fallback if the image is missing
            c.setFont(FONT_REG, 8)
            c.setFillColor(HexColor("#cc0000"))
            c.drawString(MARGIN_L, top - 25, "Logo no encontrado")

        c.setFillColor(NAVY)
        c.setFont(FONT_BOLD, 15)
        c.drawString(
            MARGIN_L + 52,
            top - 8,
            lab.get("logo_texto_linea1", "Laboratorio"),
        )

        c.drawString(
            MARGIN_L + 52,
            top - 24,
            lab.get("logo_texto_linea2", ""),
        )

        c.setFillColor(HexColor("#2e7dd7"))
        c.setFont(FONT_BOLD, 12)
        c.drawString(MARGIN_L + 52, top - 38, "*")

        # Nombre de empresa y folio
        c.setFillColor(BLACK)
        c.setFont(FONT_BOLD, 13)
        c.drawCentredString(
            PAGE_W / 2 + 30,
            top - 8,
            lab.get("nombre", ""),
        )

        c.setFont(FONT_REG, 10)
        folio = data.get("folio", "")

        c.drawCentredString(
            PAGE_W / 2 + 30,
            top - 24,
            f"Cotización de estudios: {folio}",
        )

        return top - 60

    """
    def draw_header(c, data):
        top = PAGE_H - 50
        lab = data.get("laboratorio", {})
    
        # logo
        draw_logo(c, MARGIN_L, top - 15)
        c.setFont(FONT_BOLD, 15)
        c.setFillColor(NAVY)
        c.drawString(MARGIN_L + 52, top - 8, lab.get("logo_texto_linea1", "Laboratorio"))
        c.drawString(MARGIN_L + 52, top - 24, lab.get("logo_texto_linea2", ""))
        c.setFillColor(HexColor("#2e7dd7"))
        c.setFont(FONT_BOLD, 12)
        c.drawString(MARGIN_L + 52, top - 38, "*")
    
        # nombre empresa + folio (centrado/derecha)
        c.setFillColor(BLACK)
        c.setFont(FONT_BOLD, 13)
        c.drawCentredString(PAGE_W / 2 + 30, top - 8, lab.get("nombre", ""))
        c.setFont(FONT_REG, 10)
        folio = data.get("folio", "")
        c.drawCentredString(PAGE_W / 2 + 30, top - 24, f"Cotización de estudios: {folio}")
    
        return top - 60
    """

    def draw_fecha(self, c, data, y):
        c.setFont(FONT_BOLD, 10)
        c.setFillColor(BLACK)
        c.drawString(MARGIN_L, y, f"Fecha: {data.get('fecha', '')}")
        return y - 22


    def wrap_text(self, c, text, font, size, max_width):
        """Envuelve texto (respetando saltos de línea explícitos \n) a max_width."""
        lines = []
        for raw_line in text.split("\n"):
            words = raw_line.split(" ")
            cur = ""
            for w in words:
                trial = (cur + " " + w).strip()
                if stringWidth(trial, font, size) <= max_width:
                    cur = trial
                else:
                    if cur:
                        lines.append(cur)
                    cur = w
            lines.append(cur)
        return lines


    def draw_price_header_row(self, c, x, y, w):
        """Fila de encabezado: Precio de lista | Desc. | Precio (Final)"""
        col_w = 90  # ancho fijo por columna de precio (no proporcional al total)
        labels_x = x + w - 3 * col_w
        c.setFont(FONT_BOLD, 8.5)
        c.setFillColor(BLACK)
        headers = ["Precio de lista", "Desc.", "Precio (Final)"]
        for i, h in enumerate(headers):
            cx = labels_x + i * col_w + col_w / 2
            c.drawCentredString(cx, y, h)
        c.setLineWidth(0.6)
        c.setStrokeColor(GREY_LINE)
        c.line(x, y - 5, x + w, y - 5)
        return labels_x, col_w


    def draw_study_block(self, c, x, y, w, estudio, row_h_header=16):
        """Dibuja: fila Clave+Nombre con precios a la derecha, luego Indicaciones.
        Devuelve el nuevo y (bajo el bloque)."""
        labels_x, col_w = self.draw_price_header_row(c, x, y, w)
        y -= row_h_header

        # clave + nombre
        clave = estudio.get("clave", "")
        nombre = estudio.get("nombre", "")
        c.setFont(FONT_BOLD, 9.5)
        c.setFillColor(BLACK)
        clave_label = f"Clave: {clave}"
        c.drawString(x, y, clave_label)
        clave_w = stringWidth(clave_label, FONT_BOLD, 9.5)
        nombre_x = x + clave_w + 15
        nombre_max_w = labels_x - nombre_x - 10  # no invadir la zona de precios

        nombre_lines = self.wrap_text(c, nombre, FONT_BOLD, 9.5, max(nombre_max_w, 20))
        line_h_name = 12
        for i, line in enumerate(nombre_lines):
            c.drawString(nombre_x, y - i * line_h_name, line)

        # precios en esa misma fila (alineados con la primera línea del nombre)
        precio_lista = estudio.get("precio_lista", 0)
        precio_final = estudio.get("precio_final", precio_lista)
        descuento = estudio.get("descuento", round(float(precio_lista) - float(precio_final), 2))
        c.setFont(FONT_REG, 9.5)
        vals = [self.money(precio_lista), self.money(descuento), self.money(precio_final)]
        for i, v in enumerate(vals):
            cx = labels_x + i * col_w + col_w / 2
            c.drawCentredString(cx, y, v)

        y -= (len(nombre_lines) - 1) * line_h_name
        y -= 14
        c.setStrokeColor(GREY_LINE)
        c.setLineWidth(0.6)
        c.line(x, y + 4, x + w, y + 4)
        y -= 10

        # indicaciones
        indicaciones = estudio.get("indicaciones", "")
        if indicaciones:
            c.setFont(FONT_BOLD, 9)
            c.drawString(x, y, "Indicaciones")
            ind_x = x + 62
            ind_w = w - 62
            c.setFont(FONT_REG, 8.5)
            lines = self.wrap_text(c, indicaciones, FONT_REG, 8.5, ind_w)
            line_h = 11
            cy = y
            for i, line in enumerate(lines):
                c.drawString(ind_x, cy, line)
                cy -= line_h
            y = cy - 6
        else:
            y -= 10

        c.setStrokeColor(GREY_LINE)
        c.line(x, y + 6, x + w, y + 6)
        y -= 16
        return y


    def draw_totals_table(self, c, x, y, w, data):
        subtotal = data.get("subtotal")
        descuento = data.get("descuento", 0)
        cargo = data.get("cargo", 0)
        total = data.get("total")

        if subtotal is None or total is None:
            computed_sub = sum(float(e.get("precio_lista", 0)) for e in data.get("estudios", []))
            computed_total = sum(float(e.get("precio_final", e.get("precio_lista", 0))) for e in data.get("estudios", []))
            subtotal = subtotal if subtotal is not None else computed_sub
            total = total if total is not None else computed_total

        headers = ["SUBTOTAL", "DESCUENTO", "CARGO", "TOTAL A PAGAR"]
        values = [self.money(subtotal), self.money(descuento), self.money(cargo), self.money(total)]

        col_w = w / 4
        row_h = 20

        c.setStrokeColor(GREY_LINE)
        c.setLineWidth(0.7)
        # bordes exteriores
        c.rect(x, y - 2 * row_h, w, 2 * row_h, stroke=1, fill=0)
        # línea horizontal media
        c.line(x, y - row_h, x + w, y - row_h)
        # líneas verticales
        for i in range(1, 4):
            c.line(x + i * col_w, y - 2 * row_h, x + i * col_w, y)

        c.setFont(FONT_BOLD, 9)
        c.setFillColor(BLACK)
        for i, h in enumerate(headers):
            c.drawCentredString(x + i * col_w + col_w / 2, y - row_h + 6, h)

        c.setFont(FONT_REG, 9.5)
        for i, v in enumerate(values):
            c.drawCentredString(x + i * col_w + col_w / 2, y - 2 * row_h + 6, v)

        return y - 2 * row_h - 10


    def generate_pdf(self, data, out_path):
        c = canvas.Canvas(out_path, pagesize=letter)
        y = PAGE_H
        y = self.draw_header(c, data)
        y = self.draw_fecha(c, data, y)

        x = MARGIN_L
        w = CONTENT_W

        for estudio in data.get("estudios", []):
            # salto de página si no hay espacio suficiente
            if y < 140:
                c.showPage()
                y = PAGE_H - 50

            y = self.draw_study_block(c, x, y, w, estudio)

        # nota de precios
        nota = data.get("nota_precios", "*Precios con IVA incluido")
        if nota:
            c.setFont(FONT_OBL, 8)
            c.setFillColor(BLACK)
            c.drawRightString(x + w, y + 4, nota)
            y -= 14

        if y < 90:
            c.showPage()
            y = PAGE_H - 60

        self.draw_totals_table(c, x, y, w, data)

        c.save()


    def pdf_to_png(self, pdf_path, png_path_no_ext, dpi=200):
        from pdf2image import convert_from_path
        pages = convert_from_path(pdf_path, dpi=dpi)
        # una sola página esperada para este reporte; si hay más, guarda todas
        if len(pages) == 1:
            pages[0].save(png_path_no_ext + ".png", "PNG")
        else:
            for i, page in enumerate(pages, 1):
                page.save(f"{png_path_no_ext}_p{i}.png", "PNG")

# prompt> En base al historial de nuestra conversacion,
# realiza una cotizacion.
# retorna formato json en funcion de esta plantilla ....
#           este es el catalogo de precios ...


def main():
    if len(sys.argv) < 3:
        print("Uso: python generador_cotizacion_pdf.py entrada.json salida_sin_extension")
        sys.exit(1)

    json_path = sys.argv[1]
    out_base = sys.argv[2]

    with open(json_path, "r", encoding="utf-8") as f:
        data = json.load(f)

    generador_pdf = GeneradorCotizacionPDF(json_path)
    pdf_path = out_base + ".pdf"
    generador_pdf.generate_pdf(data, pdf_path)
    # generador_pdf.pdf_to_png(pdf_path, out_base)
    print(f"Generado: {pdf_path}")


if __name__ == "__main__":
    main()
