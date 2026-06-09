"""Proposal Q&A ("Ask Me Anything" about Accenture's RFQ response).

A knowledge-base-driven Q&A layer that sits alongside the guided ordering
workflow. A unified router (app/router.py) decides, per message, whether a turn
is handled by the ordering orchestrator or answered from the proposal here.

Modules:
  - flows:      the FLOWS knowledge base (one node per proposal topic).
  - retriever:  lightweight stdlib TF-IDF semantic search over the flows.
  - routing:    regex intent patterns + semantic retrieval -> a proposal topic.
  - summarize:  optional grounded Claude summarisation of a topic's content.
  - service:    ProposalService — ties the above together into proposal turns.
"""
from __future__ import annotations

from .service import ProposalReply, ProposalService, Suggestion

__all__ = ["ProposalService", "ProposalReply", "Suggestion"]
