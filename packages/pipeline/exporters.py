"""
packages/pipeline/exporters.py — Output generators for Step 9: Excel (openpyxl), PDF (WeasyPrint), DXF (ezdxf).
"""

from __future__ import annotations

import io
import logging
from typing import Any

from packages.drawing import export_project_to_dxf
from packages.schema import Project

logger = logging.getLogger("imjan.pipeline.exporters")


def export_materials_excel(project: Project) -> bytes:
    """Generates a professional Excel bill of materials (openpyxl)."""
    import openpyxl
    from openpyxl.styles import Alignment, Font, PatternFill

    wb = openpyxl.Workbook()
    ws = wb.active
    ws.title = "Materiaallijst"

    # Header styling
    header_fill = PatternFill(start_color="1F497D", end_color="1F497D", fill_type="solid")
    header_font = Font(name="Calibri", size=11, bold=True, color="FFFFFF")

    title_cell = ws.cell(row=1, column=1, value=f"Materiaallijst — {project.name or project.id}")
    title_cell.font = Font(name="Calibri", size=14, bold=True)
    ws.row_dimensions[1].height = 25

    headers = ["#", "Symbooltype", "ETIM-code", "Omschrijving", "Aantal", "Eenheid", "Stuksprijs (€)", "Totaalprijs (€)"]
    ws.append([])  # Blank row

    ws.append(headers)
    for col_num in range(1, len(headers) + 1):
        cell = ws.cell(row=3, column=col_num)
        cell.fill = header_fill
        cell.font = header_font
        cell.alignment = Alignment(horizontal="center", vertical="center")

    total_sum = 0.0
    for idx, mat in enumerate(project.materials, start=1):
        unit_price = mat.unit_price or 0.0
        tot = mat.total_price or (unit_price * mat.quantity)
        total_sum += tot
        row = [
            idx,
            mat.symbol_type.value,
            mat.etim_code or "-",
            mat.description,
            mat.quantity,
            mat.unit,
            f"{unit_price:.2f}",
            f"{tot:.2f}",
        ]
        ws.append(row)

    # Total row
    last_row = ws.max_row + 1
    ws.cell(row=last_row, column=4, value="TOTAAL (excl. BTW)").font = Font(bold=True)
    total_cell = ws.cell(row=last_row, column=8, value=f"€ {total_sum:.2f}")
    total_cell.font = Font(bold=True)
    total_cell.alignment = Alignment(horizontal="right")

    # Column widths
    widths = [6, 22, 14, 40, 10, 10, 15, 15]
    for i, w in enumerate(widths, start=1):
        col_letter = openpyxl.utils.get_column_letter(i)
        ws.column_dimensions[col_letter].width = w

    buf = io.BytesIO()
    wb.save(buf)
    return buf.getvalue()


def export_quote_pdf(project: Project) -> bytes:
    """Generates a PDF quote using Jinja2 and WeasyPrint."""
    from jinja2 import Template

    html_template = """<!DOCTYPE html>
<html>
<head>
<meta charset="utf-8">
<style>
  body { font-family: Helvetica, Arial, sans-serif; margin: 40px; color: #333; }
  h1 { color: #1F497D; border-bottom: 2px solid #1F497D; padding-bottom: 8px; }
  .summary { margin: 20px 0; padding: 12px; background: #f4f6f9; border-radius: 4px; }
  table { width: 100%; border-collapse: collapse; margin-top: 20px; }
  th, td { border: 1px solid #ddd; padding: 8px 12px; text-align: left; }
  th { background-color: #1F497D; color: white; }
  tr:nth-child(even) { background-color: #fafafa; }
  .total-row { font-weight: bold; background-color: #eaeef5; }
  .warning { color: #c0392b; font-size: 0.9em; margin-top: 15px; }
</style>
</head>
<body>
  <h1>Offerte & Materiaaloverzicht</h1>
  <div class="summary">
    <p><strong>Project ID:</strong> {{ project.id }}</p>
    <p><strong>Naam:</strong> {{ project.name or "Installatieproject" }}</p>
    <p><strong>Aantal symbolen:</strong> {{ project.symbols|length }} | <strong>Ruimtes:</strong> {{ project.rooms|length }}</p>
  </div>

  <h2>Materiaalspecificatie</h2>
  <table>
    <thead>
      <tr>
        <th>Omschrijving</th>
        <th>Type</th>
        <th>Aantal</th>
        <th>Stukprijs</th>
        <th>Totaal</th>
      </tr>
    </thead>
    <tbody>
      {% for m in project.materials %}
      <tr>
        <td>{{ m.description }}</td>
        <td>{{ m.symbol_type.value }}</td>
        <td>{{ m.quantity }} {{ m.unit }}</td>
        <td>€ {{ "%.2f"|format(m.unit_price or 0) }}</td>
        <td>€ {{ "%.2f"|format(m.total_price or 0) }}</td>
      </tr>
      {% endfor %}
      <tr class="total-row">
        <td colspan="4" style="text-align: right;">Totaal excl. BTW:</td>
        <td>€ {{ "%.2f"|format(total_price) }}</td>
      </tr>
    </tbody>
  </table>

  {% if project.warnings %}
  <h2>Aandachtspunten en NEN 1010 / AREI validatie</h2>
  <ul>
    {% for w in project.warnings %}
    <li class="warning"><strong>[{{ w.code }}] ({{ w.severity }}):</strong> {{ w.message }}</li>
    {% endfor %}
  </ul>
  {% endif %}
</body>
</html>
"""
    tmpl = Template(html_template)
    total_price = sum(m.total_price or 0.0 for m in project.materials)
    rendered_html = tmpl.render(project=project, total_price=total_price)

    try:
        from weasyprint import HTML
        return HTML(string=rendered_html).write_pdf()
    except Exception as exc:
        logger.warning("WeasyPrint render error (%s). Falling back to HTML bytes.", exc)
        return rendered_html.encode("utf-8")


def export_project_dxf(project: Project) -> bytes:
    """Generates an updated DXF drawing of the project."""
    return export_project_to_dxf(project)
