from decimal import Decimal

from jinja2 import Environment

from packages.materials.quotes import Quote, compare_quotes, quote_lines

_TEMPLATE = """<!doctype html>
<html lang="nl"><head><meta charset="utf-8">
<style>
@page { margin: 22mm; }
body { font: 11pt sans-serif; color: #172d34; }
h1 { margin-bottom: 8pt; } p { margin: 4pt 0; }
table { width: 100%; border-collapse: collapse; margin-top: 18pt; }
th, td { padding: 6pt 4pt; border-bottom: 1px solid #cad5d5; text-align: left; }
th { background: #eef4f4; }
.total { margin-top: 14pt; text-align: right; font-weight: bold; }
</style></head><body>
<h1>{{ title }}</h1>
<p>{{ quote.project_name }} · {{ quote.created_at.strftime('%d/%m/%Y') }}</p>
{% if quote.customer %}<p>Klant · {{ quote.customer }}</p>{% endif %}
<p>Offerte {{ quote.title }} · {{ quote.id[:8] }}</p>
{% if previous %}<p>Vorige offerte {{ previous.title }} · {{ previous.id[:8] }}</p>{% endif %}
<table><thead><tr>
{% for header in headers %}<th>{{ header }}</th>{% endfor %}
</tr></thead><tbody>
{% for row in rows %}<tr>{% for cell in row %}<td>{{ cell }}</td>{% endfor %}</tr>{% endfor %}
</tbody></table>
{% if previous %}<p>Vorig totaal {{ euros(before_total) }} · Nieuw totaal {{ euros(after_total) }}</p>{% endif %}
<p class="total">{{ total_label }} {{ euros(total) }} excl. btw</p>
</body></html>"""


def euros(cents: int) -> str:
    absolute = abs(cents)
    sign = "−" if cents < 0 else ""
    return f"{sign}€ {absolute // 100},{absolute % 100:02d}"


def quantity_label(quantity: Decimal) -> str:
    return format(quantity.normalize(), "f").replace(".", ",")


def _quote_html(quote: Quote, previous: Quote | None) -> str:
    lines = quote_lines(quote)
    after_total = sum(line.amount for line in lines.values())
    before_total = 0
    if previous:
        before_total = sum(line.amount for line in quote_lines(previous).values())
        title = "Wijzigingsstaat"
        total_label = "Netto prijsverschil"
        headers = ["Werk of materiaal", "Eenheid", "Vorig / nieuw aantal",
                   "Vorige / nieuwe prijs", "Verschil"]
        rows = [
            (line.description, line.unit, f"{quantity_label(line.before_quantity)} / {quantity_label(line.after_quantity)}",
             f"{euros(line.before_price)} / {euros(line.after_price)}", euros(line.delta))
            for line in compare_quotes(previous, quote)
        ]
    else:
        title = "Offerte"
        total_label = "Totaal"
        headers = ["Werk of materiaal", "Aantal", "Eenheid", "Eenheidsprijs", "Bedrag"]
        rows = [(line.description, quantity_label(line.quantity), line.unit, euros(line.price), euros(line.amount))
                for line in lines.values()]
    template = Environment(autoescape=True).from_string(_TEMPLATE)
    return template.render(
        title=title, quote=quote, previous=previous, headers=headers, rows=rows,
        total=after_total - before_total, total_label=total_label,
        after_total=after_total, before_total=before_total, euros=euros,
    )


def render_quote_pdf(quote: Quote, previous: Quote | None) -> bytes:
    from weasyprint import HTML

    return HTML(string=_quote_html(quote, previous)).write_pdf()
