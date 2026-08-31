"""
Registries for datasets, sheets, operators, columns, and month normalization.
"""

# Dataset keyword scoring for routing
DATASET_REGISTRY = {
    "Overview Vessel": {
        "keywords": {
            "vessel": 5,
            "bch": 4,
            "bsh": 4,
            "berth": 4,
            "crane": 3,
            "productivity": 4,
            "throughput": 3,
            "teus": 3,
            "boxes": 3,
            "kapal": 5,
        }
    },
    "Container Throughput": {
        "keywords": {
            "throughput": 5,
            "actual": 4,
            "budget": 4,
            "performance": 4,
            "target": 3,
            "realisasi": 4,
        }
    },
    "Realisasi UC": {
        "keywords": {
            "realisasi uc": 9,
            "realisasi": 7,
            "uc": 8,
            "unit cost": 6,
            "unit cost realization": 6,
            "total": 4,
            "revenue": 3,
        }
    },
    "Market Share": {
        "keywords": {
            "market": 5,
            "share": 5,
            "operator": 4,
            "percentage": 4,
            "pangsa": 5,
            "pasar": 5,
        }
    },
    "Transhipment": {
        "keywords": {
            "transhipment": 5,
            "transshipment": 5,
            "alih": 4,
            "muat": 4,
            "container": 3,
        }
    }
}

# Sheet name aliases to canonical names
SHEET_REGISTRY = {
    "Overview Vessel": {
        "domestic": "DOMESTIC",
        "domestik": "DOMESTIC",
        "international": "INTERNATIONAL",
        "internasional": "INTERNATIONAL",
    },
    "Container Throughput": {
        "domestic": "Domestik",
        "domestik": "Domestik",
        "international": "Internasional",
        "internasional": "Internasional",
    },
    "Market Share": {
        "domestic": "V.OPR DOM",
        "domestik": "V.OPR DOM",
        "international": "V.OPR INT",
        "internasional": "V.OPR INT",
    },
    "Transhipment": {
        "transhipment": "Transhipment",
    }
}

# Vessel operator codes
OPERATORS = [
    "SPI", "TIL", "MSC", "MSK", "ONE", "CMA", "COSCO", "OOCL",
    "HMM", "YANG", "EVERGREEN", "APL", "PIL", "WHL", "KMTC",
    "RCL", "SITC", "GOLD", "TS", "SINOKOR", "HEUNG", "SAMUDERA",
    "TEMAS", "MERATUS", "TANTO", "CNC", "MPN", "SAI", "OGS"
]

# Natural language column aliases
COLUMN_ALIASES = {
    "throughput": "TEUS",
    "teus": "TEUS",
    "market share": "%",
    "market share percentage": "%",
    "customer": "LOP",
    "customers": "LOP",
    "realisasi uc": "TOTAL",
    "total realisasi": "TOTAL",
    "uc": "TOTAL",
    "unit cost": "TOTAL REVENUE",
    "revenue": "TOTAL REVENUE",
    "productivity": "BCH",
    "performance": "ACTUAL VS BUDGET",
    "boxes": "Boxes",
    "box": "Boxes",
    "aktivitas": "TEUS",
    "crane hours": "BCH",
    "ship hours": "BSH",
    "bch": "BCH",
    "bsh": "BSH",
    # Explicit container sizes for Transhipment
    "20'": "20'",
    "20’": "20'",
    "20 feet": "20'",
    "20ft": "20'",
    "container 20": "20'",
    "container 20'": "20'",
    "kontainer 20": "20'",
    "kontainer 20'": "20'",
    "40'": "40'",
    "40’": "40'",
    "40 feet": "40'",
    "40ft": "40'",
    "container 40": "40'",
    "container 40'": "40'",
    "kontainer 40": "40'",
    "kontainer 40'": "40'",
}

# Month normalization map
MONTH_NORMALIZE_MAP = {
    # English lowercase
    "january": {"id": "Januari", "code": 1},
    "february": {"id": "Februari", "code": 2},
    "march": {"id": "Maret", "code": 3},
    "april": {"id": "April", "code": 4},
    "may": {"id": "Mei", "code": 5},
    "june": {"id": "Juni", "code": 6},
    "july": {"id": "Juli", "code": 7},
    "august": {"id": "Agustus", "code": 8},
    "september": {"id": "September", "code": 9},
    "october": {"id": "Oktober", "code": 10},
    "november": {"id": "November", "code": 11},
    "december": {"id": "Desember", "code": 12},
    
    # Indonesian lowercase
    "januari": {"id": "Januari", "code": 1},
    "februari": {"id": "Februari", "code": 2},
    "maret": {"id": "Maret", "code": 3},
    "mei": {"id": "Mei", "code": 5},
    "juni": {"id": "Juni", "code": 6},
    "juli": {"id": "Juli", "code": 7},
    "agustus": {"id": "Agustus", "code": 8},
    "oktober": {"id": "Oktober", "code": 10},
    "november": {"id": "November", "code": 11},
    "desember": {"id": "Desember", "code": 12},
    
    # Abbreviated
    "jan": {"id": "Januari", "code": 1},
    "feb": {"id": "Februari", "code": 2},
    "mar": {"id": "Maret", "code": 3},
    "apr": {"id": "April", "code": 4},
    "jun": {"id": "Juni", "code": 6},
    "jul": {"id": "Juli", "code": 7},
    "aug": {"id": "Agustus", "code": 8},
    "sep": {"id": "September", "code": 9},
    "oct": {"id": "Oktober", "code": 10},
    "nov": {"id": "November", "code": 11},
    "dec": {"id": "Desember", "code": 12},
    
    # Numeric strings
    "1": {"id": "Januari", "code": 1},
    "2": {"id": "Februari", "code": 2},
    "3": {"id": "Maret", "code": 3},
    "4": {"id": "April", "code": 4},
    "5": {"id": "Mei", "code": 5},
    "6": {"id": "Juni", "code": 6},
    "7": {"id": "Juli", "code": 7},
    "8": {"id": "Agustus", "code": 8},
    "9": {"id": "September", "code": 9},
    "10": {"id": "Oktober", "code": 10},
    "11": {"id": "November", "code": 11},
    "12": {"id": "Desember", "code": 12},
}
