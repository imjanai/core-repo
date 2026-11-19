"""
packages/vision/vlm.py — Vision-Language Model client for reasoning via vLLM / OpenAI API.
Performs room layout reasoning, uncertain symbol disambiguation, and circuit association.
"""

from __future__ import annotations

import base64
import json
import logging
import os
import re
from typing import Any

from openai import OpenAI
from pydantic import BaseModel, Field

from packages.schema import Project, Room, SourceType, Symbol, SymbolType

logger = logging.getLogger("imjan.vision.vlm")


class RoomProposal(BaseModel):
    name: str
    polygon: list[list[float]] = Field(default_factory=list)
    confidence: float = 0.8


class Reinterpretation(BaseModel):
    symbol_id: str
    new_type: SymbolType
    reason: str = ""
    confidence: float = 0.85


class VLMReasoningResult(BaseModel):
    rooms: list[RoomProposal] = Field(default_factory=list)
    reinterpretations: list[Reinterpretation] = Field(default_factory=list)
    circuits: dict[str, str] = Field(default_factory=dict)  # symbol_id -> circuit


def _clean_json_codeblock(raw: str) -> str:
    """Strips markdown code fences (```json ... ```) from model output."""
    raw = raw.strip()
    match = re.search(r"```(?:json)?\s*([\s\S]*?)\s*```", raw)
    if match:
        return match.group(1).strip()
    return raw


def get_vlm_client() -> tuple[OpenAI, str]:
    base_url = os.environ.get("VLLM_BASE_URL", "http://localhost:8000/v1")
    model = os.environ.get("VLLM_MODEL", "elektro-vl")
    client = OpenAI(base_url=base_url, api_key="not-needed")
    return client, model


def reason(project: Project, data: bytes, legend: list[dict[str, Any]] | None = None) -> Project:
    """
    Executes VLM visual reasoning stage using served Qwen-VL model via vLLM.
    If the vLLM server is not reachable, gracefully logs and proceeds without blocking.
    """
    vlm_enabled = os.environ.get("VLLM_ENABLED", "true").lower() in ("true", "1", "yes")
    if not vlm_enabled:
        project.meta["vlm_status"] = "disabled"
        return project

    uncertain_symbols = [s for s in project.symbols if s.confidence < 0.85]
    if not uncertain_symbols and project.rooms:
        # Nothing critical requires VLM reasoning
        project.meta["vlm_status"] = "skipped_all_confident"
        return project

    client, model_name = get_vlm_client()
    legend_info = json.dumps(legend or [], ensure_ascii=False)
    uncertain_ids = [{"id": s.id, "type": s.type.value, "x": s.x, "y": s.y} for s in uncertain_symbols[:20]]

    prompt = f"""Je bent een deskundige elektrotechnisch tekenaar en inspecteur.
Analyseer de bijgevoegde installatietekening en de herkende legenda:
LEGENDA: {legend_info}

Twijfelachtige symbolen: {json.dumps(uncertain_ids)}

Vraag:
1. Welke functionele ruimtes (bv. Keuken, Badkamer, Woonkamer) herken je?
2. Voor de twijfelachtige symbolen: welk SymbolType hoort hier echt bij op basis van context en legenda?
3. Geef het antwoord UITSLUITEND als geldige JSON met de volgende structuur:
{{
  "rooms": [{{"name": "Keuken", "polygon": [[0,0],[1000,0],[1000,1000],[0,1000]]}}],
  "reinterpretations": [{{"symbol_id": "...", "new_type": "wandcontactdoos", "reason": "naast aanrecht", "confidence": 0.95}}],
  "circuits": {{"symbol_id": "G1"}}
}}
"""

    b64_img = base64.b64encode(data).decode("utf-8")
    data_uri = f"data:image/png;base64,{b64_img}"

    try:
        response = client.chat.completions.create(
            model=model_name,
            messages=[{
                "role": "user",
                "content": [
                    {"type": "image_url", "image_url": {"url": data_uri}},
                    {"type": "text", "text": prompt},
                ],
            }],
            temperature=0.0,
            max_tokens=2048,
            timeout=15.0,  # Fast timeout so offline server doesn't hold up pipeline
        )

        content = response.choices[0].message.content or ""
        cleaned_json = _clean_json_codeblock(content)
        parsed_dict = json.loads(cleaned_json)
        result = VLMReasoningResult.model_validate(parsed_dict)

        # Apply VLM insights to Project
        # 1. Add rooms if missing
        existing_room_names = {r.name.lower() for r in project.rooms}
        for pr in result.rooms:
            if pr.name.lower() not in existing_room_names:
                project.rooms.append(Room(name=pr.name, polygon=pr.polygon))
                existing_room_names.add(pr.name.lower())

        # 2. Apply re-interpretations
        sym_dict = {s.id: s for s in project.symbols}
        for reint in result.reinterpretations:
            if reint.symbol_id in sym_dict:
                target = sym_dict[reint.symbol_id]
                target.type = reint.new_type
                target.confidence = reint.confidence
                target.source = SourceType.VLM
                target.attributes["vlm_reason"] = reint.reason

        # 3. Apply circuits
        for sid, circ in result.circuits.items():
            if sid in sym_dict and not sym_dict[sid].circuit:
                sym_dict[sid].circuit = circ

        project.meta["vlm_status"] = "success"
        project.meta["vlm_applied"] = {
            "rooms_added": len(result.rooms),
            "reinterpretations": len(result.reinterpretations),
        }

    except Exception as exc:
        logger.warning("VLM reasoning offline or unavailable (%s). Proceeding gracefully.", exc)
        project.meta["vlm_status"] = f"offline_fallback: {type(exc).__name__}"

    return project
