"""
Rule Engine for Generic LPG System

宣言的なルールを解釈して、グラフの変換を実行します。
"""

import networkx as nx
from typing import Dict, List, Any, Tuple
from expression_evaluator import ExpressionEvaluator
import re


class RuleEngine:
    """
    ルールエンジン

    transformations.json のルールを解釈して、
    グラフに対する変換を実行します。

    サポートする変換タイプ:
    1. cross_link: 横断的なリンク作成
    2. derived_node: 派生ノードの生成
    3. enrich_properties: プロパティの追加
    4. aggregation: 集約ノードの生成
    """

    def __init__(self, graph: nx.MultiDiGraph, builder):
        """
        Args:
            graph: 変換対象のグラフ
            builder: DynamicGraphBuilder インスタンス
        """
        self.graph = graph
        self.builder = builder
        self.evaluator = ExpressionEvaluator(graph)
        self.transformation_log = []

    def apply_transformations(self, transformations: List[Dict]) -> None:
        """
        すべての変換を順次適用

        Args:
            transformations: 変換ルールのリスト
        """
        print("\n=== 知識変換開始 ===")

        for trans in transformations:
            trans_id = trans["id"]
            trans_type = trans["type"]

            print(f"\n[{trans_id}] {trans.get('description', '')} ({trans_type})")

            try:
                if trans_type == "cross_link":
                    self._apply_cross_link(trans)
                elif trans_type == "derived_node":
                    self._apply_derived_node(trans)
                elif trans_type == "enrich_properties":
                    self._apply_enrich_properties(trans)
                elif trans_type == "aggregation":
                    self._apply_aggregation(trans)
                else:
                    print(f"  ⚠ 未対応の変換タイプ: {trans_type}")

            except Exception as e:
                print(f"  ✗ エラー: {e}")
                raise

        print("\n=== 知識変換完了 ===")
        self._print_transformation_summary()

    def _apply_cross_link(self, trans: Dict) -> None:
        """
        横断リンク変換を適用

        異なるエンティティ間に新しい関係を作成
        """
        from_entity = trans["from_entity"]
        to_entity = trans["to_entity"]
        link_label = trans["link_label"]
        condition = trans["condition"]

        from_nodes = self.builder.get_nodes_by_entity(from_entity)
        to_nodes = self.builder.get_nodes_by_entity(to_entity)

        links_added = 0
        for from_node in from_nodes:
            from_data = self.graph.nodes[from_node]

            for to_node in to_nodes:
                to_data = self.graph.nodes[to_node]

                # 条件を評価
                context = {"from": from_data, "to": to_data}
                if self.evaluator.evaluate_condition(condition, context):
                    # エッジのプロパティを準備
                    edge_props = {"label": link_label}

                    if "properties" in trans:
                        for prop_name, prop_def in trans["properties"].items():
                            if "value" in prop_def:
                                edge_props[prop_name] = prop_def["value"]
                            elif "expression" in prop_def:
                                edge_props[prop_name] = self.evaluator.evaluate(
                                    prop_def["expression"], context
                                )

                    # エッジを追加
                    self.graph.add_edge(from_node, to_node, **edge_props)
                    links_added += 1

        self.transformation_log.append({
            "id": trans["id"],
            "type": "cross_link",
            "count": links_added
        })
        print(f"  ✓ {links_added}件のリンクを追加")

    def _apply_derived_node(self, trans: Dict) -> None:
        """
        派生ノード変換を適用

        既存ノードから計算により新しいノードを生成
        """
        output_entity = trans["output_entity"]
        source_entities = trans["source_entities"]
        join_condition = trans["join_condition"]
        node_id_template = trans.get("node_id_template", "")
        properties_def = trans.get("properties", {})
        edges_def = trans.get("edges", [])

        # ソースエンティティのノードを取得
        entity_nodes = {}
        for alias, entity_name in source_entities.items():
            entity_nodes[alias] = self.builder.get_nodes_by_entity(entity_name)

        # 最初のエンティティを基準にループ
        first_alias = list(source_entities.keys())[0]
        nodes_created = 0

        for first_node in entity_nodes[first_alias]:
            first_data = self.graph.nodes[first_node]
            context = {first_alias: first_data, f"{first_alias}_node_id": first_node}

            # 他のエンティティとのマッチングを探す
            matched = self._find_matching_nodes(
                first_alias, first_node, first_data,
                source_entities, entity_nodes, join_condition
            )

            if matched:
                context.update(matched)

                # ノードIDを生成
                node_id = self._generate_node_id_from_template(node_id_template, context)

                # プロパティを計算
                properties = {"label": output_entity}
                for prop_name, prop_def in properties_def.items():
                    try:
                        if "value" in prop_def:
                            value = prop_def["value"]
                        elif "source" in prop_def:
                            value = self._resolve_source(prop_def["source"], context)
                        elif "expression" in prop_def:
                            value = self.evaluator.evaluate(prop_def["expression"], context)
                        else:
                            continue

                        # 四捨五入
                        if "round" in prop_def and isinstance(value, (int, float)):
                            value = round(value, prop_def["round"])

                        properties[prop_name] = value
                    except Exception as e:
                        print(f"    ⚠ プロパティ {prop_name} の計算に失敗: {e}")

                # ノードを追加
                self.graph.add_node(node_id, **properties)
                nodes_created += 1

                # エッジを作成
                self._create_derived_edges(node_id, edges_def, context)

        self.transformation_log.append({
            "id": trans["id"],
            "type": "derived_node",
            "count": nodes_created
        })
        print(f"  ✓ {nodes_created}件のノードを生成")

    def _find_matching_nodes(self, first_alias: str, first_node: str, first_data: Dict,
                            source_entities: Dict, entity_nodes: Dict,
                            join_condition: Dict) -> Dict:
        """
        結合条件に合致するノードを検索

        Returns:
            マッチしたノードのデータ（alias -> data のdict）
        """
        matched = {}
        matched_entities = set()

        for alias, entity_name in source_entities.items():
            if alias == first_alias:
                continue

            for candidate_node in entity_nodes[alias]:
                candidate_data = self.graph.nodes[candidate_node]

                # コンテキストを準備
                context = {
                    first_alias: first_data,
                    alias: candidate_data
                }
                context.update(matched)

                # 結合条件を評価
                if self.evaluator.evaluate_condition(join_condition, context):
                    matched[alias] = candidate_data
                    matched[f"{alias}_node_id"] = candidate_node
                    matched_entities.add(alias)
                    break

        # すべてのエンティティがマッチした場合のみ成功
        required_entities = len(source_entities) - 1  # first_alias を除く
        return matched if len(matched_entities) == required_entities else None

    def _generate_node_id_from_template(self, template: str, context: Dict) -> str:
        """
        テンプレートからノードIDを生成

        Args:
            template: ノードIDテンプレート（例: "INT_{emission.facility_id}_{emission.year}"）
            context: コンテキスト

        Returns:
            生成されたノードID
        """
        node_id = template

        # {entity.field} または {entity.field:format} のパターンを置換
        pattern = r'\{([^}:]+)(?::([^}]+))?\}'
        matches = re.finditer(pattern, template)

        for match in matches:
            ref = match.group(1)  # entity.field
            fmt = match.group(2)  # format (オプション)

            # entity.field を解決
            value = self._resolve_source(ref, context)

            # フォーマット適用
            if fmt:
                formatted = f"{value:{fmt}}"
                node_id = node_id.replace(match.group(0), formatted)
            else:
                node_id = node_id.replace(match.group(0), str(value))

        return node_id

    def _resolve_source(self, source: str, context: Dict) -> Any:
        """
        ソース参照を解決

        Args:
            source: ソース参照（例: "emission.year"）
            context: コンテキスト

        Returns:
            解決された値
        """
        parts = source.split(".")
        if len(parts) == 2:
            entity, field = parts
            if entity in context:
                return context[entity].get(field)

        raise ValueError(f"ソース参照を解決できません: {source}")

    def _create_derived_edges(self, node_id: str, edges_def: List[Dict], context: Dict) -> None:
        """
        派生ノードのエッジを作成

        Args:
            node_id: 新しいノードのID
            edges_def: エッジ定義のリスト
            context: コンテキスト
        """
        for edge_def in edges_def:
            from_ref = edge_def["from"]
            to_ref = edge_def["to"]
            label = edge_def["label"]

            # ノード参照を解決
            from_node = self._resolve_node_reference(from_ref, node_id, context)
            to_node = self._resolve_node_reference(to_ref, node_id, context)

            if from_node and to_node:
                edge_props = {"label": label}

                if "properties" in edge_def:
                    for prop_name, prop_def in edge_def["properties"].items():
                        if "value" in prop_def:
                            edge_props[prop_name] = prop_def["value"]

                self.graph.add_edge(from_node, to_node, **edge_props)

    def _resolve_node_reference(self, ref: str, current_node: str, context: Dict) -> str:
        """
        ノード参照を解決

        Args:
            ref: ノード参照（"new_node", "emission", "facility" 等）
            current_node: 現在のノードID
            context: コンテキスト

        Returns:
            ノードID
        """
        if ref == "new_node":
            return current_node

        # エンティティのノードIDを取得
        node_id_key = f"{ref}_node_id"
        if node_id_key in context:
            return context[node_id_key]

        # 親ノードを探す（facility等）
        if ref == "facility":
            # EmissionRecordやEnergyRecordから施設IDを抽出
            for alias, data in context.items():
                if isinstance(data, dict) and "facility_id" in data:
                    return data["facility_id"]

        return None

    def _apply_enrich_properties(self, trans: Dict) -> None:
        """
        プロパティ追加変換を適用

        既存ノードに新しいプロパティを動的に追加
        """
        target_entity = trans["target_entity"]
        enrichments = trans["enrichments"]

        # ターゲットノードを取得（グラフから直接取得）
        target_nodes = [n for n, d in self.graph.nodes(data=True)
                       if d.get('label') == target_entity]

        # 集約値を事前計算
        self.evaluator.clear_cache()
        precomputed = {}
        for enrichment in enrichments:
            prop_name = enrichment["property"]
            if "expression" in enrichment:
                expression = enrichment["expression"]
                # 集約関数を含む式を事前計算
                if "avg(" in expression or "sum(" in expression:
                    precomputed[prop_name] = self.evaluator.evaluate(expression, {})

        # 各ノードにプロパティを追加
        enriched_count = 0
        for node_id in target_nodes:
            node_data = self.graph.nodes[node_id]
            context = {"node": node_data}

            # 事前計算された値をコンテキストに追加
            context.update(precomputed)

            for enrichment in enrichments:
                prop_name = enrichment["property"]

                try:
                    if "rules" in enrichment:
                        # ルールベースの値決定
                        value = self._evaluate_rules(enrichment["rules"], context)
                    elif "expression" in enrichment:
                        # 事前計算済みの場合はそれを使用
                        if prop_name in precomputed:
                            value = precomputed[prop_name]
                        else:
                            value = self.evaluator.evaluate(enrichment["expression"], context)
                    elif "value" in enrichment:
                        value = enrichment["value"]
                    else:
                        continue

                    # 四捨五入
                    if "round" in enrichment and isinstance(value, (int, float)):
                        value = round(value, enrichment["round"])

                    # プロパティを追加
                    self.graph.nodes[node_id][prop_name] = value
                    enriched_count += 1

                except Exception as e:
                    print(f"    ⚠ ノード {node_id} のプロパティ {prop_name} の追加に失敗: {e}")

        self.transformation_log.append({
            "id": trans["id"],
            "type": "enrich_properties",
            "count": len(target_nodes)
        })
        print(f"  ✓ {len(target_nodes)}件のノードにプロパティを追加")

    def _evaluate_rules(self, rules: List[Dict], context: Dict) -> Any:
        """
        ルールを評価して値を決定

        Args:
            rules: ルールのリスト
            context: コンテキスト

        Returns:
            最初にマッチしたルールの値
        """
        for rule in rules:
            condition = rule["condition"]

            # "true" は常に真
            if condition == "true":
                return rule["value"]

            # 条件式を評価
            try:
                if self.evaluator.evaluate(condition, context):
                    return rule["value"]
            except Exception as e:
                print(f"      ⚠ ルール条件の評価に失敗: {condition}, {e}")

        return None

    def _apply_aggregation(self, trans: Dict) -> None:
        """
        集約変換を適用

        複数のノードから統計情報を計算して新しいノードを生成
        """
        output_entity = trans["output_entity"]
        group_by_entity = trans["group_by_entity"]
        aggregate_entity = trans["aggregate_entity"]
        node_id_template = trans.get("node_id_template", "")
        aggregations = trans.get("aggregations", {})
        properties_def = trans.get("properties", {})
        edges_def = trans.get("edges", [])

        # グループ化エンティティのノードを取得
        group_nodes = self.builder.get_nodes_by_entity(group_by_entity)

        nodes_created = 0
        for group_node in group_nodes:
            group_data = self.graph.nodes[group_node]

            # このグループに属する集約対象ノードを取得
            aggregate_nodes = []
            for successor in self.graph.successors(group_node):
                if self.graph.nodes[successor].get("label") == aggregate_entity:
                    aggregate_nodes.append(successor)

            if not aggregate_nodes:
                continue

            # 集約値を計算
            agg_values = {}
            for agg_name, agg_def in aggregations.items():
                function = agg_def["function"]
                field = agg_def.get("field", "")

                if function == "count":
                    value = len(aggregate_nodes)
                else:
                    values = [self.graph.nodes[n][field] for n in aggregate_nodes if field in self.graph.nodes[n]]
                    if values:
                        if function == "avg":
                            value = sum(values) / len(values)
                        elif function == "sum":
                            value = sum(values)
                        elif function == "max":
                            value = max(values)
                        elif function == "min":
                            value = min(values)
                        else:
                            value = 0
                    else:
                        value = 0

                # 四捨五入
                if "round" in agg_def and isinstance(value, (int, float)):
                    value = round(value, agg_def["round"])

                agg_values[agg_name] = value

            # ノードIDを生成
            context = {"facility": group_data, **agg_values}
            node_id = self._generate_node_id_from_template(node_id_template, context)

            # プロパティを構築
            properties = {"label": output_entity}
            properties.update(agg_values)

            for prop_name, prop_def in properties_def.items():
                if "value" in prop_def:
                    properties[prop_name] = prop_def["value"]
                elif "source" in prop_def:
                    properties[prop_name] = self._resolve_source(prop_def["source"], context)

            # ノードを追加
            self.graph.add_node(node_id, **properties)
            nodes_created += 1

            # エッジを作成
            for edge_def in edges_def:
                from_ref = edge_def["from"]
                to_ref = edge_def["to"]
                label = edge_def["label"]

                if from_ref == "facility" and to_ref == "new_node":
                    self.graph.add_edge(group_node, node_id, label=label)
                elif from_ref == "new_node" and to_ref == "aggregated_nodes":
                    for agg_node in aggregate_nodes:
                        self.graph.add_edge(node_id, agg_node, label=label)

        self.transformation_log.append({
            "id": trans["id"],
            "type": "aggregation",
            "count": nodes_created
        })
        print(f"  ✓ {nodes_created}件の集約ノードを生成")

    def _print_transformation_summary(self) -> None:
        """変換サマリーを表示"""
        print("\n=== 変換サマリー ===")
        for log in self.transformation_log:
            print(f"  {log['id']} ({log['type']}): {log['count']}件")


if __name__ == '__main__':
    from metadata_loader import MetadataLoader
    from dynamic_graph_builder import DynamicGraphBuilder

    # メタデータを読み込み
    loader = MetadataLoader()
    schema = loader.load_schema("config/schema.json")
    transformations_def = loader.load_transformations("config/transformations.json")

    # グラフを構築
    builder = DynamicGraphBuilder(schema, base_path=".")
    graph = builder.build_graph()

    # 変換を適用
    engine = RuleEngine(graph, builder)
    transformations = loader.get_enabled_transformations()
    engine.apply_transformations(transformations)

    # 結果を表示
    print("\n=== 変換後のグラフ ===")
    stats = builder.get_graph_stats()
    print(f"ノード総数: {stats['total_nodes']}")
    print(f"エッジ総数: {stats['total_edges']}")
    print(f"ノードタイプ: {stats['node_types']}")
    print(f"エッジタイプ: {stats['edge_types']}")
