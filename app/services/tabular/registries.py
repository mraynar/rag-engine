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
            "container throughput": 10,
            "throughput": 5,
            "actual": 4,
            "budget": 4,
            "performance": 4,
            "target": 3,
            "realisasi": 3,
        }
    },
    "Realisasi UC": {
        "keywords": {
            "realisasi uc": 9,
            "realisasi": 6,
            "uc": 8,
            "unit cost": 6,
            "unit cost realization": 6,
            "total teus": 5,
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
            "transhipment": 10,
            "transshipment": 10,
            "vessel revenue": 12,
            "total loading": 10,
            "loading": 7,
            "discharge": 7,
            "alih muat": 8,
            "alih": 4,
            "muat": 4,
        }
    },
    "RestNDisc": {
        "keywords": {
            "restndisc": 10,
            "keringanan": 8,
            "diskon": 7,
            "discount": 7,
            "permohonan": 7,
            "persetujuan": 6,
            "surat jawaban": 6,
        }
    },
    "Komersial Dashboard": {
        "keywords": {
            "komersial": 10,
            "dashboard": 8,
            "all revenue": 10,
            "total all revenue": 10,
            "revenue": 10,
            "pendapatan": 10,
            "total pendapatan": 10,
            "jumlah pendapatan": 10,
        }
    },
    "Vessel Service": {
        "keywords": {
            "vessel service": 10,
            "service": 6,
            "total call": 8,
            "call": 5,
            "routes": 5,
            "bmph": 5,
            "gmph": 5,
        }
    },
    "Overview Box": {
        "keywords": {
            "overview box": 12,
            "box": 6,
            "boxes": 6,
            "teus domestik": 12,
            "teus internasional": 12,
            "teus international": 12,
            "jumlah teus domestik": 12,
            "jumlah teus internasional": 12,
            "kategori domestik": 10,
            "kategori internasional": 10,
            "per kategori": 8,
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
    },
    "Overview Box": {
        "domestic": "DOMESTIK",
        "domestik": "DOMESTIK",
        "international": "INTERNATIONAL",
        "internasional": "INTERNATIONAL",
    },
}

# Vessel operator codes
OPERATORS = [
    "SPI", "TIL", "MSC", "MSK", "ONE", "CMA", "COSCO", "OOCL",
    "HMM", "YANG", "EVERGREEN", "APL", "PIL", "WHL", "KMTC",
    "RCL", "SITC", "GOLD", "TS", "SINOKOR", "HEUNG", "SAMUDERA",
    "TEMAS", "MERATUS", "TANTO", "CNC", "MPN", "SAI", "OGS",
    "ANL", "CMA CGM", "WAN HAI", "MAERSK", "EVERGREEN LINE"
]

# Natural language column aliases
COLUMN_ALIASES = {
    "throughput": "TEUS",
    "teus": "TEUS",
    "market share": "%",
    "market share percentage": "%",
    "realisasi uc": "TOTAL",
    "total realisasi": "TOTAL",
    "uc": "TOTAL",
    "productivity": "BCH",
    "performance": "ACTUAL VS BUDGET",
    "boxes": "Boxes",
    "box": "Boxes",
    "crane hours": "BCH",
    "ship hours": "BSH",
    "bch": "BCH",
    "bsh": "BSH",
    "total call": "TOTAL CALL",
    "total calls": "TOTAL CALL",
    "call": "TOTAL CALL",
    "calls": "TOTAL CALL",
    "actual": "ACTUAL",
    "budget": "BUDGET",
    "actual throughput": "ACTUAL",
    "nominal persetujuan": "NOMINAL PERSETUJUAN KERINGANAN",
    "nominal persetujuan keringanan": "NOMINAL PERSETUJUAN KERINGANAN",
    "keringanan": "NOMINAL PERSETUJUAN KERINGANAN",
    # Revenue & Pendapatan aliases
    "pendapatan": "TOTAL ALL REVENUE",
    "total pendapatan": "TOTAL ALL REVENUE",
    "jumlah pendapatan": "TOTAL ALL REVENUE",
    "jumlah total pendapatan": "TOTAL ALL REVENUE",
    "revenue": "TOTAL ALL REVENUE",
    "total revenue": "TOTAL ALL REVENUE",
    "total all revenue": "TOTAL ALL REVENUE",
    "all revenue": "TOTAL ALL REVENUE",
    # Explicit container sizes for Transhipment & Realisasi UC
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
    # English lowercase (full names - must match DB stored values e.g. 'March', 'January')
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
