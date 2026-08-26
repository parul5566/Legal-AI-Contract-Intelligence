"""Clause & risk taxonomies."""

CLAUSE_CATEGORIES = {
    "payment_terms": {
        "label": "Payment Terms",
        "keywords": [
            "payment", "invoice", "fees", "fee", "compensation", "net 30", "net 60",
            "net \\d+", "purchase price", "remuneration", "amount payable", "pay",
            "paid", "payable", "interest",
        ],
    },
    "term_termination": {
        "label": "Term & Termination",
        "keywords": [
            "termination", "term of this agreement", "expire", "renewal",
            "terminate", "effective date", "wind-down",
        ],
    },
    "confidentiality": {
        "label": "Confidentiality",
        "keywords": [
            "confidential information", "non-disclosure", "nondisclosure",
            "confidentiality", "trade secrets", "disclose",
        ],
    },
    "indemnification": {
        "label": "Indemnification",
        "keywords": ["indemnif", "hold harmless", "defend", "indemnity"],
    },
    "liability": {
        "label": "Liability",
        "keywords": [
            "liability", "damages", "consequential", "limitation of liability",
            "aggregate liability", "cap",
        ],
    },
    "intellectual_property": {
        "label": "Intellectual Property",
        "keywords": [
            "intellectual property", "copyright", "patent", "trademark",
            "ownership of", "licen[cs]e", "work product", "ip rights",
        ],
    },
    "data_protection": {
        "label": "Data Protection",
        "keywords": [
            "personal data", "data protection", "gdpr", "privacy",
            "processing of data", "security breach", "ccpa",
        ],
    },
    "governing_law": {
        "label": "Governing Law",
        "keywords": ["governing law", "jurisdiction", "laws of", "venue", "governed by"],
    },
    "dispute_resolution": {
        "label": "Dispute Resolution",
        "keywords": [
            "arbitration", "dispute resolution", "mediation", "arbitrator",
            "binding arbitration", "courts of",
        ],
    },
    "non_compete": {
        "label": "Non-Compete",
        "keywords": ["non-compete", "noncompete", "competitive", "compete with"],
    },
    "non_solicitation": {
        "label": "Non-Solicitation",
        "keywords": ["non-solicit", "solicit", "hire any employee", "non-solicitation"],
    },
    "renewal": {
        "label": "Renewal",
        "keywords": ["renew", "auto-renew", "automatic renewal", "evergreen", "successive term"],
    },
    "warranty": {
        "label": "Warranty",
        "keywords": ["warrant", "warranty", "representations", "as-is", "disclaim"],
    },
    "force_majeure": {
        "label": "Force Majeure",
        "keywords": ["force majeure", "acts of god", "unforeseeable event"],
    },
    "assignment": {
        "label": "Assignment",
        "keywords": ["assign", "assignment", "novation", "transfer this agreement"],
    },
    "insurance": {
        "label": "Insurance",
        "keywords": ["insurance", "insured", "coverage of at least", "liability insurance"],
    },
    "compliance": {
        "label": "Compliance Obligations",
        "keywords": [
            "compliance", "applicable law", "anti-corruption", "fcpa",
            "regulatory", "sanctions",
        ],
    },
}

# categories that most commercial contracts should contain
EXPECTED_CATEGORIES = [
    "payment_terms",
    "term_termination",
    "confidentiality",
    "liability",
    "governing_law",
    "dispute_resolution",
]

RISK_CATEGORIES = {
    "financial": "Financial Risk",
    "legal": "Legal Risk",
    "compliance": "Compliance Risk",
    "operational": "Operational Risk",
    "data_privacy": "Data Privacy Risk",
    "liability_exposure": "Liability Exposure",
    "unfavorable_termination": "Unfavorable Termination Conditions",
    "unlimited_liability": "Unlimited Liability",
    "one_sided_indemnity": "One-sided Indemnification",
    "auto_renewal": "Automatic Renewal",
    "missing_clause": "Missing Clauses",
    "ambiguity": "Ambiguous Language",
    "unusual_obligation": "Unusual Contractual Obligations",
}


def category_label(cat: str) -> str:
    return CLAUSE_CATEGORIES.get(cat, {}).get("label", cat.replace("_", " ").title())


def risk_label(cat: str) -> str:
    return RISK_CATEGORIES.get(cat, cat.replace("_", " ").title())


SEVERITY_ORDER = {"low": 1, "medium": 2, "high": 3, "critical": 4}
