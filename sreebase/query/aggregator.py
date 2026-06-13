"""
SreeBase Query Language — Aggregator
====================================

Processes pre-filtered documents to compute grouped mathematical summaries.
"""

from typing import Any, Dict, List
from sreebase.query.ast_nodes import AggregateStatement
from sreebase.errors import ExecutionError

class Aggregator:
    @staticmethod
    def aggregate(statement: AggregateStatement, documents: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
        # 1. Group documents by the group_by field
        bins: Dict[Any, List[Dict[str, Any]]] = {}
        for doc in documents:
            key = doc.get(statement.group_by)
            # We can group by None/null if the field is missing
            if key not in bins:
                bins[key] = []
            bins[key].append(doc)

        # 2. Compute calculations per bin
        results = []
        for key, group_docs in bins.items():
            result_row = {statement.group_by: key}
            
            for calc in statement.calculations:
                func_name = calc.func_name.lower()
                field = calc.field
                
                # Output key format: e.g. "sum(age)"
                out_key = f"{func_name}()" if not field else f"{func_name}({field})"
                
                if func_name == "count":
                    result_row[out_key] = len(group_docs)
                elif func_name == "sum":
                    if not field:
                        raise ExecutionError("sum() requires a field argument.")
                    total = 0
                    for d in group_docs:
                        val = d.get(field, 0)
                        if isinstance(val, (int, float)):
                            total += val
                    result_row[out_key] = total
                elif func_name == "avg":
                    if not field:
                        raise ExecutionError("avg() requires a field argument.")
                    total = 0
                    count = 0
                    for d in group_docs:
                        val = d.get(field)
                        if isinstance(val, (int, float)):
                            total += val
                            count += 1
                    result_row[out_key] = (total / count) if count > 0 else 0
                else:
                    raise ExecutionError(f"Unknown aggregation function: {func_name}")
            
            results.append(result_row)
            
        return results
