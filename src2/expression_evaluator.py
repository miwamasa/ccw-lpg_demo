"""
Expression Evaluator for Generic LPG System

式の評価を行うエンジン。条件式、計算式、集約関数をサポート。
"""

import re
from typing import Any, Dict, List
from datetime import datetime
import statistics


class ExpressionEvaluator:
    """
    式評価エンジン

    サポートする機能:
    - 算術演算: +, -, *, /, **, %
    - 比較演算: ==, !=, <, >, <=, >=
    - 論理演算: and, or, not
    - 集約関数: avg(), sum(), max(), min(), count(), stddev()
    - ユーティリティ関数: now(), round(), abs(), len()
    - フィールド参照: entity.field, node.field
    """

    def __init__(self, graph=None):
        """
        Args:
            graph: NetworkX グラフ（集約関数で使用）
        """
        self.graph = graph
        self._aggregation_cache = {}

    def evaluate(self, expression: str, context: Dict[str, Any]) -> Any:
        """
        式を評価

        Args:
            expression: 評価する式（文字列）
            context: 変数のコンテキスト（例: {"node": {...}, "emission": {...}}）

        Returns:
            評価結果
        """
        # コンテキスト変数を準備
        local_vars = self._prepare_context(context)

        # 関数呼び出しを処理
        expression = self._replace_functions(expression, local_vars)

        # フィールド参照を置換
        expression = self._replace_field_references(expression, local_vars)

        try:
            # Python式として評価
            result = eval(expression, {"__builtins__": {}}, local_vars)
            return result
        except Exception as e:
            raise ValueError(f"式の評価に失敗: {expression}, エラー: {e}")

    def evaluate_condition(self, condition: Dict, context: Dict[str, Any]) -> bool:
        """
        条件オブジェクトを評価

        Args:
            condition: 条件定義（dict形式）
            context: コンテキスト

        Returns:
            真偽値
        """
        if "operator" in condition:
            operator = condition["operator"].upper()
            conditions = condition.get("conditions", [])

            if operator == "AND":
                return all(self.evaluate_condition(c, context) for c in conditions)
            elif operator == "OR":
                return any(self.evaluate_condition(c, context) for c in conditions)
            elif operator == "NOT":
                return not self.evaluate_condition(conditions[0], context)

        if condition["type"] == "field_match":
            from_val = self.evaluate(condition["from_expression"], context)
            to_val = self.evaluate(condition["to_expression"], context)
            return from_val == to_val

        if condition["type"] == "expression":
            return bool(self.evaluate(condition["expression"], context))

        return False

    def evaluate_aggregation(self, function: str, entity: str, field: str) -> Any:
        """
        集約関数を評価

        Args:
            function: 集約関数名（avg, sum, max, min, count, stddev）
            entity: エンティティ名
            field: フィールド名

        Returns:
            集約結果
        """
        cache_key = f"{function}_{entity}_{field}"
        if cache_key in self._aggregation_cache:
            return self._aggregation_cache[cache_key]

        if not self.graph:
            raise ValueError("グラフが設定されていません")

        # エンティティのノードを取得
        nodes = [n for n, d in self.graph.nodes(data=True)
                if d.get('label') == entity]

        if function == "count":
            result = len(nodes)
        else:
            # フィールドの値を収集
            values = []
            for node in nodes:
                node_data = self.graph.nodes[node]
                if field in node_data:
                    values.append(node_data[field])

            if not values:
                result = 0
            elif function == "avg":
                result = statistics.mean(values)
            elif function == "sum":
                result = sum(values)
            elif function == "max":
                result = max(values)
            elif function == "min":
                result = min(values)
            elif function == "stddev":
                result = statistics.stdev(values) if len(values) > 1 else 0
            else:
                raise ValueError(f"未対応の集約関数: {function}")

        self._aggregation_cache[cache_key] = result
        return result

    def clear_cache(self):
        """集約キャッシュをクリア"""
        self._aggregation_cache.clear()

    def _prepare_context(self, context: Dict[str, Any]) -> Dict[str, Any]:
        """コンテキストを準備"""
        local_vars = {}

        for key, value in context.items():
            if isinstance(value, dict):
                local_vars[key] = value
            else:
                local_vars[key] = value

        return local_vars

    def _replace_functions(self, expression: str, context: Dict[str, Any]) -> str:
        """
        関数呼び出しを置換

        サポート:
        - now(): 現在時刻
        - avg(Entity.field): 平均
        - sum(Entity.field): 合計
        - max(Entity.field): 最大
        - min(Entity.field): 最小
        - count(Entity): 件数
        - stddev(Entity.field): 標準偏差
        """
        # now() の置換
        if "now()" in expression:
            expression = expression.replace("now()", f"'{datetime.now().isoformat()}'")

        # 集約関数の置換
        agg_pattern = r'(avg|sum|max|min|count|stddev)\((\w+)(?:\.(\w+))?\)'
        matches = re.finditer(agg_pattern, expression)

        for match in matches:
            func = match.group(1)
            entity = match.group(2)
            field = match.group(3) if match.group(3) else None

            if func == "count" and not field:
                result = self.evaluate_aggregation(func, entity, "")
            elif field:
                result = self.evaluate_aggregation(func, entity, field)
            else:
                continue

            expression = expression.replace(match.group(0), str(result))

        return expression

    def _replace_field_references(self, expression: str, context: Dict[str, Any]) -> str:
        """
        フィールド参照を置換

        例: node.co2_intensity_kg_per_kwh -> context['node']['co2_intensity_kg_per_kwh']
        """
        # フィールド参照のパターン: entity.field
        pattern = r'(\w+)\.(\w+)'
        matches = re.finditer(pattern, expression)

        replacements = []
        for match in matches:
            entity = match.group(1)
            field = match.group(2)

            if entity in context and isinstance(context[entity], dict):
                if field in context[entity]:
                    value = context[entity][field]
                    # 値の型に応じて適切に置換
                    if isinstance(value, str):
                        replacements.append((match.group(0), f"'{value}'"))
                    else:
                        replacements.append((match.group(0), str(value)))

        # 置換を適用（長い一致から優先）
        for old, new in sorted(replacements, key=lambda x: len(x[0]), reverse=True):
            expression = expression.replace(old, new, 1)

        return expression


if __name__ == '__main__':
    # テスト
    evaluator = ExpressionEvaluator()

    # 算術演算のテスト
    context = {
        'emission': {'co2_emissions_kg': 45000, 'facility_id': 'F001'},
        'energy': {'electricity_kwh': 100000, 'facility_id': 'F001'},
        'node': {'co2_intensity_kg_per_kwh': 0.45, 'renewable_ratio': 0.3}
    }

    # 計算式
    result = evaluator.evaluate(
        "emission.co2_emissions_kg / energy.electricity_kwh",
        context
    )
    print(f"計算結果: {result}")  # 0.45

    # 条件評価
    condition = {
        "operator": "AND",
        "conditions": [
            {
                "type": "field_match",
                "from_expression": "emission.facility_id",
                "to_expression": "energy.facility_id"
            }
        ]
    }
    result = evaluator.evaluate_condition(condition, context)
    print(f"条件評価: {result}")  # True

    # 比較演算
    result = evaluator.evaluate(
        "node.co2_intensity_kg_per_kwh < 0.5 and node.renewable_ratio > 0.2",
        context
    )
    print(f"比較演算: {result}")  # True
