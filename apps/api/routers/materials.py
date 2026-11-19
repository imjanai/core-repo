"""
apps/api/routers/materials.py

GET  /projects/{id}/materials           — JSON materiaallijst
GET  /projects/{id}/materials?format=xlsx — Excel-download
GET  /projects/{id}/materials?format=pdf  — PDF-offerte
"""

import io
from typing import Annotated, Literal

from fastapi import APIRouter, Depends, HTTPException, Query
from fastapi.responses import StreamingResponse
from pydantic import BaseModel
from sqlalchemy.ext.asyncio import AsyncSession

from apps.api.core.database import get_db
from apps.api.models.db import ProjectRow
from packages.schema import MaterialLine, ProjectStatus

router = APIRouter()


class MaterialsResponse(BaseModel):
    project_id: str
    total_price: float | None
    currency: str = "EUR"
    items: list[MaterialLine]


@router.get("/{project_id}/materials")
async def get_materials(
    project_id: str,
    db: Annotated[AsyncSession, Depends(get_db)],
    fmt: Literal["json", "xlsx", "pdf"] = Query("json", alias="format"),
):
    """
    Geeft de materiaallijst terug.

    - `format=json`  → JSON (standaard)
    - `format=xlsx`  → Excel-download
    - `format=pdf`   → PDF-offerte
    """
    row = await db.get(ProjectRow, project_id)
    if not row:
        raise HTTPException(status_code=404, detail="Project niet gevonden.")
    if ProjectStatus(row.status) not in (ProjectStatus.DONE,):
        raise HTTPException(
            status_code=409,
            detail=f"Pipeline nog niet klaar (status: {row.status}).",
        )

    items = [MaterialLine(**m) for m in (row.materials or [])]
    total = (
        sum(m.total_price for m in items if m.total_price is not None)
        if items
        else None
    )

    if fmt == "json":
        return MaterialsResponse(
            project_id=project_id, total_price=total, items=items
        )

    if fmt == "xlsx":
        xlsx_bytes = _build_xlsx(items, project_id)
        return StreamingResponse(
            io.BytesIO(xlsx_bytes),
            media_type="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
            headers={
                "Content-Disposition": f'attachment; filename="materiaal_{project_id}.xlsx"'
            },
        )

    if fmt == "pdf":
        pdf_bytes = _build_pdf(items, project_id, total)
        return StreamingResponse(
            io.BytesIO(pdf_bytes),
            media_type="application/pdf",
            headers={
                "Content-Disposition": f'attachment; filename="offerte_{project_id}.pdf"'
            },
        )


# ---------------------------------------------------------------------------
# Excel-builder (openpyxl)
# ---------------------------------------------------------------------------


def _build_xlsx(items: list[MaterialLine], project_id: str) -> bytes:
    import openpyxl
    from openpyxl.styles import Font, PatternFill, Alignment

    wb = openpyxl.Workbook()
    ws = wb.active
    ws.title = "Materiaallijst"

    header_font = Font(bold=True, color="FFFFFF")
    header_fill = PatternFill(fill_type="solid", fgColor="1A1A2E")

    headers = ["Omschrijving", "ETIM-code", "Eenheid", "Aantal", "Stukprijs (€)", "Totaal (€)"]
    for col, h in enumerate(headers, 1):
        cell = ws.cell(row=1, column=col, value=h)
        cell.font = header_font
        cell.fill = header_fill
        cell.alignment = Alignment(horizontal="center")

    for row_idx, item in enumerate(items, 2):
        ws.cell(row=row_idx, column=1, value=item.description)
        ws.cell(row=row_idx, column=2, value=item.etim_code or "")
        ws.cell(row=row_idx, column=3, value=item.unit)
        ws.cell(row=row_idx, column=4, value=item.quantity)
        ws.cell(row=row_idx, column=5, value=item.unit_price)
        ws.cell(row=row_idx, column=6, value=item.total_price)

    for col in ws.columns:
        max_len = max((len(str(c.value or "")) for c in col), default=10)
        ws.column_dimensions[col[0].column_letter].width = min(max_len + 4, 50)

    buf = io.BytesIO()
    wb.save(buf)
    return buf.getvalue()


# ---------------------------------------------------------------------------
# PDF-builder (WeasyPrint + Jinja2)
# ---------------------------------------------------------------------------


def _build_pdf(
    items: list[MaterialLine], project_id: str, total: float | None
) -> bytes:
    from jinja2 import Environment, BaseLoader
    from weasyprint import HTML

    template_str = """
<!DOCTYPE html>
<html lang="nl">
<head>
<meta charset="utf-8">
<style>
  body { font-family: 'Helvetica Neue', Arial, sans-serif; font-size: 11px; color: #111; }
  h1 { font-size: 18px; margin-bottom: 4px; }
  .sub { color: #666; font-size: 10px; margin-bottom: 24px; }
  table { width: 100%; border-collapse: collapse; }
  th { background: #1a1a2e; color: #fff; padding: 6px 8px; text-align: left; }
  td { padding: 5px 8px; border-bottom: 1px solid #e5e5e5; }
  tr:nth-child(even) td { background: #f8f8f8; }
  .total { font-weight: bold; text-align: right; margin-top: 12px; }
</style>
</head>
<body>
  <h1>Materiaallijst / Offerte</h1>
  <p class="sub">Project: {{ project_id }}</p>
  <table>
    <thead>
      <tr>
        <th>Omschrijving</th><th>ETIM</th><th>Eenheid</th>
        <th>Aantal</th><th>Stukprijs</th><th>Totaal</th>
      </tr>
    </thead>
    <tbody>
      {% for item in items %}
      <tr>
        <td>{{ item.description }}</td>
        <td>{{ item.etim_code or '' }}</td>
        <td>{{ item.unit }}</td>
        <td>{{ item.quantity }}</td>
        <td>{% if item.unit_price is not none %}€ {{ '%.2f'|format(item.unit_price) }}{% endif %}</td>
        <td>{% if item.total_price is not none %}€ {{ '%.2f'|format(item.total_price) }}{% endif %}</td>
      </tr>
      {% endfor %}
    </tbody>
  </table>
  {% if total is not none %}
  <p class="total">Totaal excl. BTW: € {{ '%.2f'|format(total) }}</p>
  {% endif %}
</body>
</html>
"""
    env = Environment(loader=BaseLoader())
    tmpl = env.from_string(template_str)
    html = tmpl.render(items=items, project_id=project_id, total=total)
    return HTML(string=html).write_pdf()
