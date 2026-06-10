"""Proposal knowledge base (RFQ "Ask Me Anything").

Each topic maps to:
  - text:    a grounded, conversational answer (may contain light HTML such as
             <strong>/<em>; rendered as rich text by the frontend).
  - slides:  proposal slides shown in the side panel, in order. Each is
             {"image": <stem>, "label": <caption>}; the image is served at
             /slides/{stem}.jpg (exported from the proposal decks — ORALS and the
             RFQ Response).
  - aliases: extra phrasings used only to strengthen semantic retrieval (never
             shown). These mirror the canonical demo questions.

This is the single source of truth for proposal content; the retriever indexes it
and the summariser grounds Claude on it. Content is server-controlled and trusted.
There are no pre-fed prompt chips and no "I can't answer that" fallback: any
question is routed to the best-matching topic via semantic search.
"""
from __future__ import annotations

# Concise greeting for the main/landing screen.
WELCOME_MESSAGE = (
    "Hi, I'm your <strong>Medias Co-Driver</strong>. How can I help — order or "
    "proposal question?"
)

# Shown whenever a message isn't a clear order action or proposal question.
# Light HTML (<strong>, <br>) is rendered as rich text by the UI.
CO_DRIVER_GREETING = (
    "Hello! I'm your <strong>Schaeffler Medias Co-Driver</strong>. I didn't quite catch "
    "that — here's what I can help with:<br><br>"
    "🛒 <strong>Place an order</strong><br>"
    "💬 <strong>Ask about Accenture's Medias proposal</strong><br><br>"
    "Which would you like to explore?"
)

FLOWS: dict[str, dict] = {
    # 1) How could Accenture help Schaeffler realize this vision? -> ORALS slides 6, 7 & 8.
    "realize_vision": {
        "text": (
            "Accenture helps Schaeffler turn medias from a portal into a conversational "
            "sales platform by scoping the MVP <strong>by AI complexity, not just feature "
            "count</strong>: 12 services across three categories (Deterministic, "
            "Conversational, Agentic), each sized S/M/L. And it's built on what you "
            "already have — the <strong>existing medias and Azure AI setup</strong> "
            "(design system, agents &amp; tools, security, infrastructure, portability "
            "and observability) is reused, not replaced."
        ),
        "slides": [
            {"image": "orals-6", "label": "We scope the MVP by AI complexity — 12 services, 3 categories, S·M·L sizing"},
            {"image": "orals-7", "label": "Every service mapped by category and size — the two levers that drive cost"},
            {"image": "orals-8", "label": "The technical foundation — the existing medias and Azure AI setup we build on"},
        ],
        "aliases": [
            "How could Accenture help Schaeffler to realize this vision?",
            "How can Accenture help us realize the vision?",
            "What is the value proposition and overview?",
            "how is the MVP scoped and sized; technical foundation",
        ],
    },

    # 2) Now that we know what we want to realize — what's the Accenture approach and
    #    what will they do? -> ORALS slides 9, 10, 12, 18 & 20.
    "approach": {
        "text": (
            "Accenture delivers in <strong>four phases to one hard deadline — GISM in "
            "February 2027</strong>: a six-week <strong>Discovery &amp; Design</strong> "
            "to lock scope and architecture; ~14 weeks of agile <strong>Build</strong> to "
            "build, integrate and validate all 12 services; a <strong>Test</strong> phase "
            "where SIT confirms it works and UAT confirms it's right for the business; "
            "and four weeks of <strong>Hypercare</strong> for dedicated post-launch "
            "support at the highest-risk moment."
        ),
        "slides": [
            {"image": "orals-9", "label": "Four phases, one hard deadline — GISM February 2027"},
            {"image": "orals-10", "label": "Discovery & Design — six weeks to eliminate every build-phase blocker"},
            {"image": "orals-12", "label": "Build — 14 weeks of agile delivery across all 12 services"},
            {"image": "orals-18", "label": "Test — SIT confirms it works, UAT confirms it's right for the business"},
            {"image": "orals-20", "label": "Hypercare — four weeks of dedicated post-launch support"},
        ],
        "aliases": [
            "Now that we know what we want to realize, what's the Accenture approach and what will they do to realize this?",
            "What is the Accenture approach?",
            "What will Accenture do to realize this?",
            "phases, timeline, discovery build test hypercare, go-live",
        ],
    },

    # 3) How would Accenture collaborate with us / staff this project?
    #    -> ORALS slides 21 & 22.
    "collaboration": {
        "text": (
            "Accenture proposes a <strong>phased shoring model</strong>: onshore-heavy "
            "during Discovery &amp; Design (where architecture and functional decisions "
            "need client proximity), transitioning to offshore-heavy through Build and "
            "Test for cost-efficient, scaled delivery. It's <strong>one delivery team</strong> "
            "combining local proximity with global specialist scale — German-based key "
            "roles alongside an offshore core delivery team, under a joint Schaeffler–"
            "Accenture steering structure."
        ),
        "slides": [
            {"image": "orals-21", "label": "Delivery Model — Phased Shoring Approach"},
            {"image": "orals-22", "label": "One delivery team — local proximity with global specialist scale"},
        ],
        "aliases": [
            "And how would Accenture collaborate with us? How would they staff this project?",
            "How would Accenture collaborate with us?",
            "How would they staff the project?",
            "team proposal, on-offshore, RACI, working model",
        ],
    },

    # 4) Has Accenture done this before? -> ORALS slides 23 & 24.
    "credentials": {
        "text": (
            "Yes — Accenture is the <strong>#1 partner to enterprises building "
            "production-grade agentic AI</strong>, with 2,000+ GenAI projects delivered, "
            "a Microsoft/Azure strategic alliance, the AI Refinery enterprise agentic "
            "platform and $3B invested in AI. We bring <strong>five directly comparable "
            "credentials</strong> — including a live GenAI travel companion on Azure "
            "OpenAI handling ~300k sessions/month — scored against Schaeffler's exact "
            "capability requirements."
        ),
        "slides": [
            {"image": "orals-23", "label": "The #1 partner to enterprises building production-grade agentic AI"},
            {"image": "orals-24", "label": "Five comparable credentials scored against Schaeffler's requirements"},
        ],
        "aliases": [
            "Has Accenture done this before?",
            "What is your experience and track record?",
            "Show me comparable credentials and case studies.",
            "proven references",
        ],
    },

    # 5) What makes Accenture a suitable partner? -> ORALS slides 25, 26, 27 & 28.
    "why_accenture": {
        "text": (
            "Accenture is a <strong>trusted partner — less ramp-up, more delivery from "
            "day one</strong>: a dedicated senior account team, deep Schaeffler knowledge, "
            "and #1-partner power across your cloud and software ecosystem. Our work is "
            "<strong>built on real delivery, not prototypes</strong> — proven Super Agents "
            "and broad platform/protocol coverage — backed by unmatched AI capabilities, "
            "reinvention leadership and industry expertise (1,600+ GenAI professionals, "
            "1,450 patents, recognised leader by Forrester and Everest Group)."
        ),
        "slides": [
            {"image": "orals-25", "label": "A trusted partner — less ramp-up, more delivery from day one"},
            {"image": "orals-26", "label": "Built on real delivery, not prototypes"},
            {"image": "orals-27", "label": "Unmatched AI capabilities, reinvention leadership and industry expertise"},
            {"image": "orals-28", "label": "AI leadership, accomplishments and global partner ecosystem"},
        ],
        "aliases": [
            "What makes Accenture a suitable partner?",
            "Why Accenture? Why choose Accenture?",
            "What makes you the right partner?",
            "unique position, AI leadership",
        ],
    },

    # Greeting for the landing screen (no pre-fed prompt chips).
    "welcome": {
        "text": WELCOME_MESSAGE,
        "slides": [],
        "aliases": [],
    },
}

# Fallback when answering: any unmatched question still gets the best overview.
DEFAULT_INTENT = "realize_vision"
