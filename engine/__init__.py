"""
engine/__init__.py
Public re-exports for the PPTX Animation Engine package.
"""

from engine.rules_loader import RulesConfig, load_rules

__all__ = [
    "load_rules",
    "RulesConfig",
]
