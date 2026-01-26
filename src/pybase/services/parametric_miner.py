"""
Parametric Pattern Mining Service for analyzing serialized model data.

Processes parameters and relations JSONB from serialized_models to:
- Extract parametric patterns (equations, dependencies)
- Find models with similar parametric structures
- Enable "find similar logic" search

Integrates with existing CosCAD retrieval system without modifying
master_serialize_and_index.py extraction.
"""

import ast
import re
from collections import defaultdict
from dataclasses import dataclass
from typing import Any

import numpy as np

from pybase.core.logging import get_logger

logger = get_logger(__name__)

# Target embedding dimension
PARAMETRIC_EMBEDDING_DIM = 128


@dataclass
class ParametricPattern:
    """Discovered parametric pattern in a model."""
    variable_count: int
    equation_count: int
    dependency_depth: int
    has_conditional: bool
    common_operations: dict[str, int]
    variable_usage: dict[str, int]
    pattern_hash: str


@dataclass
class MiningResult:
    """Result of parametric pattern mining."""
    pattern: ParametricPattern | None
    embedding: list[float] | None
    error: str | None = None


class ParametricMiner:
    """
    Mine parametric patterns from serialized model data.

    Reads from serialized_models:
    - parameters: Model parameters with names, values, types
    - relations: Parametric equations and dependencies

    Generates embeddings for "find similar logic" search.
    """

    # Operation regex patterns
    ARITHMETIC_OPS = ["+", "-", "*", "/", "**", "%"]
    COMPARISON_OPS = ["==", "!=", "<", ">", "<=", ">="]
    FUNCTIONS = [
        "sin", "cos", "tan", "asin", "acos", "atan",
        "sqrt", "abs", "log", "exp", "pow",
        "if", "else", "endif",
    ]

    def __init__(self, embedding_dim: int = PARAMETRIC_EMBEDDING_DIM):
        self.embedding_dim = embedding_dim

    def mine_from_serialized(
        self,
        parameters: dict[str, Any] | None,
        relations: dict[str, Any] | None,
    ) -> MiningResult:
        """
        Mine parametric patterns from existing serialized data.

        Args:
            parameters: JSONB from serialized_models.parameters
            relations: JSONB from serialized_models.relations

        Returns:
            MiningResult with pattern and embedding
        """
        try:
            pattern = self._extract_pattern(parameters, relations)
            embedding = self._pattern_to_embedding(pattern)

            return MiningResult(
                pattern=pattern,
                embedding=embedding,
                error=None,
            )

        except Exception as e:
            logger.error(f"Parametric mining failed: {e}")
            return MiningResult(
                pattern=None,
                embedding=None,
                error=str(e),
            )

    def _extract_pattern(
        self,
        parameters: dict[str, Any] | None,
        relations: dict[str, Any] | None,
    ) -> ParametricPattern:
        """Extract parametric pattern from parameters and relations."""
        # Count variables
        var_count = 0
        var_usage = defaultdict(int)

        if parameters:
            params = parameters.get("parameters", [])
            var_count = len(params)
            for param in params:
                name = param.get("name", "")
                if name:
                    var_usage[name] = var_usage.get(name, 0) + 1

        # Analyze relations/equations
        eq_count = 0
        has_conditional = False
        common_ops = defaultdict(int)
        max_depth = 0

        if relations:
            relation_list = relations.get("relations", [])
            eq_count = len(relation_list)

            for rel in relation_list:
                text = rel.get("text", "")
                if not text:
                    continue

                # Check for conditionals
                if re.search(r"\bif\b|\belse\b", text, re.IGNORECASE):
                    has_conditional = True

                # Count operations
                for op in self.ARITHMETIC_OPS + self.COMPARISON_OPS:
                    if op in text:
                        common_ops[op] += 1

                for func in self.FUNCTIONS:
                    if re.search(rf"\b{func}\b", text, re.IGNORECASE):
                        common_ops[func] += 1

                # Track variable usage
                var_usage.update(self._extract_variables_from_relation(text))

                # Estimate expression depth
                depth = self._estimate_expression_depth(text)
                max_depth = max(max_depth, depth)

        # Generate pattern hash
        pattern_str = self._pattern_signature(var_count, eq_count, dict(common_ops))
        pattern_hash = hash(pattern_str) & 0xFFFFFFFF

        return ParametricPattern(
            variable_count=var_count,
            equation_count=eq_count,
            dependency_depth=max_depth,
            has_conditional=has_conditional,
            common_operations=dict(common_ops),
            variable_usage=dict(var_usage),
            pattern_hash=str(pattern_hash),
        )

    def _pattern_to_embedding(self, pattern: ParametricPattern) -> list[float]:
        """Convert parametric pattern to embedding vector."""
        # Basic pattern features
        basic_features = [
            pattern.variable_count,
            pattern.equation_count,
            pattern.dependency_depth,
            1.0 if pattern.has_conditional else 0.0,
        ]

        # Log-transformed counts
        log_features = [
            np.log1p(pattern.variable_count),
            np.log1p(pattern.equation_count),
            np.log1p(pattern.dependency_depth),
        ]

        # Operation distribution (normalized)
        total_ops = sum(pattern.common_operations.values()) + 1
        op_features = []
        op_order = ["+", "-", "*", "/", "<", ">", "if", "sin", "cos", "sqrt"]
        for op in op_order:
            count = pattern.common_operations.get(op, 0)
            op_features.append(count / total_ops)

        # Variable usage diversity (entropy)
        var_values = list(pattern.variable_usage.values())
        if var_values:
            var_total = sum(var_values)
            var_probs = [v / var_total for v in var_values]
            entropy = -sum(p * np.log2(p + 1e-10) for p in var_probs if p > 0)
            max_entropy = np.log2(len(var_values)) if len(var_values) > 1 else 1
            diversity = entropy / max_entropy if max_entropy > 0 else 0
        else:
            diversity = 0.0

        diversity_features = [diversity, len(var_values)]

        # Combine all features
        all_features = (
            basic_features +   # 4 dims
            log_features +     # 3 dims
            op_features +      # 10 dims
            diversity_features # 2 dims
        )

        feature_vec = np.array(all_features, dtype=np.float32)

        # Pad to target dimension
        if len(feature_vec) < self.embedding_dim:
            padded = np.zeros(self.embedding_dim)
            padded[:len(feature_vec)] = feature_vec
            feature_vec = padded
        elif len(feature_vec) > self.embedding_dim:
            feature_vec = feature_vec[:self.embedding_dim]

        # L2 normalize
        norm = np.linalg.norm(feature_vec)
        if norm > 0:
            feature_vec = feature_vec / norm

        return feature_vec.tolist()

    def _extract_variables_from_relation(self, relation_text: str) -> dict[str, int]:
        """Extract variable names from relation text."""
        # Pattern: d0, d1, etc. or common parameter names
        patterns = [
            r'\b[dD]\d+\b',  # d0, d1, etc.
            r'\b[a-zA-Z_]\w*\b',  # Variable names
        ]

        variables = defaultdict(int)

        # Find all d-prefixed variables (common in CAD)
        for match in re.finditer(r'\b[dD]\d+\b', relation_text):
            var = match.group().lower()
            variables[var] += 1

        return variables

    def _estimate_expression_depth(self, expr: str) -> int:
        """Estimate nesting depth of expression."""
        try:
            # Remove whitespace
            expr = re.sub(r'\s+', '', expr)

            # Count nested parentheses
            max_depth = 0
            current_depth = 0

            for char in expr:
                if char == '(':
                    current_depth += 1
                    max_depth = max(max_depth, current_depth)
                elif char == ')':
                    current_depth = max(0, current_depth - 1)

            return max_depth

        except Exception:
            return 0

    def _pattern_signature(
        self,
        var_count: int,
        eq_count: int,
        ops: dict[str, int],
    ) -> str:
        """Generate string signature for pattern hashing."""
        parts = [f"v{var_count}", f"e{eq_count}"]

        if ops:
            sorted_ops = sorted(ops.items())
            parts.extend([f"{k}{v}" for k, v in sorted_ops])

        return "|".join(parts)

    def find_similar_parametric_models(
        self,
        query_embedding: list[float],
        model_embeddings: dict[str, list[float]],
        top_k: int = 10,
    ) -> list[tuple[str, float]]:
        """
        Find models with similar parametric structure.

        Args:
            query_embedding: Embedding from parametric pattern
            model_embeddings: Dict of {model_name: embedding}
            top_k: Number of results

        Returns:
            List of (model_name, similarity) tuples
        """
        if not model_embeddings:
            return []

        query_vec = np.array(query_embedding)
        query_norm = np.linalg.norm(query_vec)

        if query_norm == 0:
            return []

        similarities = []

        for model_name, emb in model_embeddings.items():
            emb_vec = np.array(emb)
            emb_norm = np.linalg.norm(emb_vec)

            if emb_norm == 0:
                continue

            sim = np.dot(query_vec, emb_vec) / (query_norm * emb_norm)
            similarities.append((model_name, float(sim)))

        # Sort by similarity
        similarities.sort(key=lambda x: x[1], reverse=True)

        return similarities[:top_k]

    def compare_parametric_structure(
        self,
        pattern1: ParametricPattern,
        pattern2: ParametricPattern,
    ) -> dict[str, Any]:
        """
        Compare two parametric patterns.

        Returns similarity metrics between patterns.
        """
        # Variable count similarity
        var_diff = abs(pattern1.variable_count - pattern2.variable_count)
        var_max = max(pattern1.variable_count, pattern2.variable_count, 1)
        var_sim = 1.0 - (var_diff / var_max)

        # Equation count similarity
        eq_diff = abs(pattern1.equation_count - pattern2.equation_count)
        eq_max = max(pattern1.equation_count, pattern2.equation_count, 1)
        eq_sim = 1.0 - (eq_diff / eq_max)

        # Conditional match
        conditional_match = 1.0 if pattern1.has_conditional == pattern2.has_conditional else 0.0

        # Operation overlap
        ops1 = set(pattern1.common_operations.keys())
        ops2 = set(pattern2.common_operations.keys())
        if ops1 or ops2:
            op_intersection = len(ops1 & ops2)
            op_union = len(ops1 | ops2)
            op_sim = op_intersection / op_union if op_union > 0 else 1.0
        else:
            op_sim = 1.0

        # Overall similarity
        overall = (var_sim + eq_sim + conditional_match + op_sim) / 4

        return {
            "overall_similarity": overall,
            "variable_similarity": var_sim,
            "equation_similarity": eq_sim,
            "conditional_match": conditional_match,
            "operation_similarity": op_sim,
        }


# Convenience functions
def mine_parametric_pattern(
    parameters: dict[str, Any] | None,
    relations: dict[str, Any] | None,
) -> tuple[ParametricPattern | None, list[float] | None]:
    """Quick mine parametric pattern from serialized data."""
    miner = ParametricMiner()
    result = miner.mine_from_serialized(parameters, relations)
    return result.pattern, result.embedding


def compare_models_parametric(
    params1: dict[str, Any] | None,
    rels1: dict[str, Any] | None,
    params2: dict[str, Any] | None,
    rels2: dict[str, Any] | None,
) -> dict[str, Any]:
    """Compare parametric structure of two models."""
    miner = ParametricMiner()

    result1 = miner.mine_from_serialized(params1, rels1)
    result2 = miner.mine_from_serialized(params2, rels2)

    if result1.pattern and result2.pattern:
        return miner.compare_parametric_structure(result1.pattern, result2.pattern)

    return {"overall_similarity": 0.0}
