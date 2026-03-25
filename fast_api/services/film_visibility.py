"""Единый фильтр индекса movies: исключить soft-deleted документы (в т.ч. без поля is_deleted в старых индексах)."""

# must_not term is_deleted:true — документы без поля не считаются удалёнными
ELASTIC_EXCLUDE_DELETED_MOVIES = {"term": {"is_deleted": True}}
