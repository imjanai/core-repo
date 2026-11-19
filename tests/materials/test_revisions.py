from packages.schema import Symbol, SymbolType
from packages.schema.revisions import compare_symbols


def test_revision_reports_moves_additions_and_ambiguity():
    def symbol(x):
        return Symbol(type=SymbolType.WANDCONTACTDOOS, x=x, y=0)

    before = [symbol(0), symbol(1000)]
    after = [symbol(80), symbol(999), symbol(1001), symbol(2000)]
    changes = compare_symbols(before, after)

    assert [(change.kind, change.before and change.before.x, change.after and change.after.x)
            for change in changes] == [
        ("moved", 0, 80),
        ("uncertain", 1000, None),
        ("uncertain", None, 999),
        ("uncertain", None, 1001),
        ("added", None, 2000),
    ]
