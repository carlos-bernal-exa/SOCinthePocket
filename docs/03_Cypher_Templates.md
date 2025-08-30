# Cypher Templates

## Case + Rule
```cypher
MERGE (c:Case {id: $case_id})
MERGE (r:Rule {id: $rule_id})
MERGE (c)-[:TRIGGERED_BY]->(r)
```

## Observed Entities
```cypher
MERGE (i:IP {value: $ip})
MERGE (c:Case {id:$case_id})-[:OBSERVED_IN]->(i)
```

## Related Cases
```cypher
UNWIND $related AS rel
MATCH (c:Case {id:$case_id})
MERGE (d:Case {id: rel.id})
MERGE (c)-[r:RELATES_TO]->(d)
SET r.score = rel.score
```

## Knowledge Items
```cypher
MERGE (k:KnowledgeItem {id:$kid})
SET k.kind=$kind, k.author=$author, k.created_at=datetime($created_at)
```
