"""
packages/vision — Computer vision and Vision-Language models.
Includes YOLO/SAHI detector, PaddleOCR legend extractor, and Qwen-VL vLLM reasoning client.
"""

from packages.vision.detector import detect_symbols
from packages.vision.ocr import extract_legend
from packages.vision.vlm import reason

__all__ = ["detect_symbols", "extract_legend", "reason"]
