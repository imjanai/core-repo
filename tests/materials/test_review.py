from packages.materials import compute_materials
from packages.schema import Correction, CorrectionAction, Project, SourceType, Symbol, SymbolType
from packages.schema.review import apply_corrections


def test_review_replays_corrections_and_recalculates_materials():
    original = Symbol(type=SymbolType.WANDCONTACTDOOS, x=1, y=2)
    corrections = [
        Correction(id="added", project_id="project", action=CorrectionAction.ADD,
                   new_type=SymbolType.SCHAKELAAR, new_x=10, new_y=20),
        Correction(project_id="project", action=CorrectionAction.CHANGE_TYPE, symbol_id="added",
                   new_type=SymbolType.LICHTPUNT, new_x=11, new_y=21),
        Correction(project_id="project", action=CorrectionAction.REMOVE, symbol_id=original.id),
    ]

    project = compute_materials(Project(symbols=apply_corrections([original], corrections)))

    assert original.source == SourceType.VECTOR
    assert [(s.id, s.type, s.x, s.y, s.source) for s in project.symbols] == [
        ("added", SymbolType.LICHTPUNT, 11, 21, SourceType.HUMAN),
    ]
    assert any(line.symbol_type == SymbolType.LICHTPUNT for line in project.materials)
    assert all(line.symbol_type != SymbolType.WANDCONTACTDOOS for line in project.materials)
