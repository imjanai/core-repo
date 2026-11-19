from collections.abc import Iterable

from packages.schema import Correction, CorrectionAction, SourceType, Symbol


def apply_corrections(symbols: Iterable[Symbol], corrections: Iterable[Correction]) -> list[Symbol]:
    reviewed = {symbol.id: symbol.model_copy(deep=True) for symbol in symbols}
    for correction in corrections:
        action = correction.action
        new_x, new_y = correction.new_x, correction.new_y
        if action == CorrectionAction.ADD:
            if correction.new_type is not None and new_x is not None and new_y is not None:
                reviewed[correction.id] = Symbol(
                    id=correction.id, type=correction.new_type,
                    x=new_x, y=new_y, source=SourceType.HUMAN,
                )
            continue

        symbol = reviewed.get(correction.symbol_id) if correction.symbol_id else None
        if symbol is None:
            continue
        if action == CorrectionAction.REMOVE:
            del reviewed[symbol.id]
        elif action == CorrectionAction.CHANGE_TYPE and correction.new_type is not None:
            symbol.type = correction.new_type
            if new_x is not None and new_y is not None:
                symbol.x, symbol.y = new_x, new_y
            symbol.source = SourceType.HUMAN
            symbol.confidence = 1.0
        elif action == CorrectionAction.MOVE:
            if new_x is not None and new_y is not None:
                symbol.x, symbol.y = new_x, new_y
                symbol.source = SourceType.HUMAN
                symbol.confidence = 1.0
    return list(reviewed.values())
