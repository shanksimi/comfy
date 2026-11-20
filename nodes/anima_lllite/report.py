from __future__ import annotations

from collections import Counter
from dataclasses import dataclass
from typing import Optional


LLLITE_REPORT = "SHANK_LLLITE_REPORT"


@dataclass
class LLLiteReport:
    filename: str
    strength: float
    modules: int
    start_percent: float
    end_percent: float
    preserve_wrapper: bool
    counts: Optional[Counter] = None
    previous: Optional[LLLiteReport] = None

    def summary(self):
        if self.previous is None:
            return self._node_summary()
        reports = self._chain()
        applied = sum(bool(report.counts and report.counts["applied"]) for report in reports)
        return f"LLLite | {applied}/{len(reports)} applied"

    def _chain(self):
        reports = [self]
        previous = self.previous
        while previous is not None:
            reports.append(previous)
            previous = previous.previous
        reports.reverse()
        return reports

    def _node_summary(self):
        counts = self.counts
        if counts is None or not counts["evaluations"]:
            return "LLLite NOT VERIFIED | no model evaluations"
        applied = counts["applied"]
        if applied:
            return f"LLLite APPLIED | {applied} layer calls"
        if self.strength == 0:
            return "LLLite SKIPPED | strength 0"
        if counts["outside_window"] == counts["evaluations"]:
            return "LLLite SKIPPED | outside sampling window"
        return "LLLite NOT APPLIED | no layer corrections"

    def metadata_text(self):
        return " || ".join(report._node_metadata_text() for report in self._chain())

    def _node_metadata_text(self):
        details = (
            f"{self._node_summary()} | {self.filename} | strength {self.strength:g}"
            f" | start_percent={self.start_percent:g} | end_percent={self.end_percent:g}"
            f" | preserve_wrapper={str(self.preserve_wrapper).lower()} | {self.modules} modules"
        )
        if self.counts is None:
            return details
        counts = self.counts
        return (
            f"{details} | {counts['evaluations']} model evaluations"
            f" | outside window {counts['outside_window']}"
            f" | batch mismatch {counts['batch_mismatch']}"
            f" | token mismatch {counts['token_mismatch']}"
            f" | missing conditioning {counts['missing_conditioning']}"
        )
