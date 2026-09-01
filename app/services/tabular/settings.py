"""
Configuration settings for tabular query planning.
"""

# Enable LLM fallback when deterministic query building fails
ENABLE_LLM_QUERY_BUILDER = True

# Enable automatic retry on empty/invalid results
ENABLE_RETRY_ENGINE = True

# Enable observability logging and metrics
ENABLE_OBSERVABILITY = True

# Return debug block in production responses
RETURN_DEBUG_BLOCK = False

# Enable query result caching (disabled in MVP)
ENABLE_QUERY_CACHE = False
