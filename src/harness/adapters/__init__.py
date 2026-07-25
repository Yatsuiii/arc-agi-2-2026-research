"""Translation layer: solver-specific archive schema -> harness schema.

Every module here is the only place its solver's field names may appear.
`features/`, `verifier/` and `allocator/` are written entirely against
`src/harness/schemas.py` and must never import an adapter.
"""
