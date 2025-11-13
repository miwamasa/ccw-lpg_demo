"""
Dynamic Graph Builder for Generic LPG System

メタデータに基づいて動的にグラフを構築します。
"""

import networkx as nx
import pandas as pd
from typing import Dict, List, Any
from pathlib import Path


class DynamicGraphBuilder:
    """
    動的グラフビルダー

    schema.json の定義に基づいて、CSVファイルから
    Labeled Property Graph を構築します。
    """

    def __init__(self, schema: Dict, base_path: str = "."):
        """
        Args:
            schema: スキーマ定義
            base_path: データファイルの基準パス
        """
        self.schema = schema
        self.base_path = Path(base_path)
        self.graph = nx.MultiDiGraph()
        self._entity_node_map = {}  # エンティティ名 -> ノードIDのリスト

    def build_graph(self) -> nx.MultiDiGraph:
        """
        グラフを構築

        Returns:
            構築されたグラフ
        """
        print("=== グラフ構築開始 ===")

        # エンティティの読み込み
        for entity in self.schema["entities"]:
            self._load_entity(entity)

        # 関係の作成
        if "relationships" in self.schema:
            for relationship in self.schema["relationships"]:
                self._create_relationship(relationship)

        print("\n=== グラフ構築完了 ===")
        stats = self.get_graph_stats()
        print(f"ノード総数: {stats['total_nodes']}")
        print(f"エッジ総数: {stats['total_edges']}")
        print(f"ノードタイプ: {stats['node_types']}")
        print(f"エッジタイプ: {stats['edge_types']}")

        return self.graph

    def _load_entity(self, entity: Dict) -> None:
        """
        エンティティを読み込んでノードを作成

        Args:
            entity: エンティティ定義
        """
        entity_name = entity["name"]
        source = entity["source"]

        # CSVファイルのパス
        csv_path = self.base_path / source["path"]
        if not csv_path.exists():
            raise FileNotFoundError(f"データファイルが見つかりません: {csv_path}")

        # CSVを読み込み
        df = pd.read_csv(csv_path)

        # 各行をノードに変換
        node_ids = []
        for idx, row in df.iterrows():
            # ノードIDを生成
            node_id = self._generate_node_id(entity, row)

            # プロパティを抽出
            properties = self._extract_properties(entity, row)
            properties["label"] = entity_name  # ラベルを追加

            # ノードを追加
            self.graph.add_node(node_id, **properties)
            node_ids.append(node_id)

        # エンティティ -> ノードIDのマッピングを保存
        self._entity_node_map[entity_name] = node_ids

        print(f"✓ {entity_name}: {len(node_ids)}件のノードを追加")

    def _generate_node_id(self, entity: Dict, row: pd.Series) -> str:
        """
        ノードIDを生成

        Args:
            entity: エンティティ定義
            row: データ行

        Returns:
            ノードID
        """
        # id_fieldが指定されている場合
        if "id_field" in entity:
            return str(row[entity["id_field"]])

        # id_templateが指定されている場合
        if "id_template" in entity:
            template = entity["id_template"]

            # テンプレート中のフィールド参照を置換
            # 例: "INT_{facility_id}_{year}{month:02d}"
            import re

            # {field} または {field:format} のパターンを検索
            pattern = r'\{(\w+)(?::([^}]+))?\}'
            matches = re.finditer(pattern, template)

            node_id = template
            for match in matches:
                field = match.group(1)
                fmt = match.group(2)

                if field not in row:
                    raise ValueError(f"フィールド {field} がデータに存在しません")

                value = row[field]

                # フォーマット指定がある場合
                if fmt:
                    formatted_value = f"{value:{fmt}}"
                    node_id = node_id.replace(match.group(0), formatted_value)
                else:
                    node_id = node_id.replace(match.group(0), str(value))

            return node_id

        raise ValueError(f"エンティティ {entity['name']} にid_fieldまたはid_templateが必要です")

    def _extract_properties(self, entity: Dict, row: pd.Series) -> Dict[str, Any]:
        """
        プロパティを抽出

        Args:
            entity: エンティティ定義
            row: データ行

        Returns:
            プロパティ辞書
        """
        properties = {}
        property_defs = entity["properties"]

        for field_name, field_def in property_defs.items():
            if field_name not in row:
                # 必須フィールドでない場合はスキップ
                if not field_def.get("required", False):
                    continue
                raise ValueError(f"必須フィールド {field_name} がデータに存在しません")

            value = row[field_name]

            # エイリアスがある場合は別名で保存
            prop_name = field_def.get("alias", field_name)

            # 型変換
            field_type = field_def.get("type", "string")
            converted_value = self._convert_value(value, field_type)

            properties[prop_name] = converted_value

            # 元のフィールド名でも保存（エイリアスがある場合）
            if "alias" in field_def:
                properties[field_name] = converted_value

        return properties

    def _convert_value(self, value: Any, field_type: str) -> Any:
        """
        値を指定された型に変換

        Args:
            value: 変換する値
            field_type: 型名

        Returns:
            変換後の値
        """
        if pd.isna(value):
            return None

        if field_type == "integer":
            return int(value)
        elif field_type == "float":
            return float(value)
        elif field_type == "string":
            return str(value)
        elif field_type == "boolean":
            return bool(value)
        else:
            return value

    def _create_relationship(self, relationship: Dict) -> None:
        """
        関係（エッジ）を作成

        Args:
            relationship: 関係定義
        """
        rel_name = relationship["name"]
        from_entity = relationship["from_entity"]
        to_entity = relationship["to_entity"]
        join_condition = relationship["join_condition"]

        from_nodes = self._entity_node_map.get(from_entity, [])
        to_nodes = self._entity_node_map.get(to_entity, [])

        edges_added = 0
        for from_node in from_nodes:
            from_data = self.graph.nodes[from_node]

            for to_node in to_nodes:
                to_data = self.graph.nodes[to_node]

                # 結合条件を評価
                if self._evaluate_join_condition(join_condition, from_data, to_data):
                    # エッジのプロパティを抽出
                    edge_props = {"label": rel_name}

                    if "properties" in relationship:
                        for prop_name, prop_def in relationship["properties"].items():
                            if "source" in prop_def:
                                source = prop_def["source"]
                                if source.startswith("from."):
                                    field = source[5:]
                                    edge_props[prop_name] = from_data.get(field)
                                elif source.startswith("to."):
                                    field = source[3:]
                                    edge_props[prop_name] = to_data.get(field)
                            elif "value" in prop_def:
                                edge_props[prop_name] = prop_def["value"]

                    # エッジを追加
                    self.graph.add_edge(from_node, to_node, **edge_props)
                    edges_added += 1

        print(f"✓ {rel_name}: {edges_added}件のエッジを追加")

    def _evaluate_join_condition(self, condition: Dict, from_data: Dict, to_data: Dict) -> bool:
        """
        結合条件を評価

        Args:
            condition: 結合条件
            from_data: fromノードのデータ
            to_data: toノードのデータ

        Returns:
            条件を満たす場合True
        """
        from_field = condition.get("from_field")
        to_field = condition.get("to_field")

        if from_field and to_field:
            return from_data.get(from_field) == to_data.get(to_field)

        return False

    def get_nodes_by_entity(self, entity_name: str) -> List[str]:
        """
        エンティティに属するノードIDのリストを取得

        Args:
            entity_name: エンティティ名

        Returns:
            ノードIDのリスト
        """
        return self._entity_node_map.get(entity_name, [])

    def get_graph_stats(self) -> Dict[str, Any]:
        """
        グラフの統計情報を取得

        Returns:
            統計情報
        """
        node_labels = {}
        for node, data in self.graph.nodes(data=True):
            label = data.get('label', 'Unknown')
            node_labels[label] = node_labels.get(label, 0) + 1

        edge_labels = {}
        for u, v, key, data in self.graph.edges(data=True, keys=True):
            label = data.get('label', 'Unknown')
            edge_labels[label] = edge_labels.get(label, 0) + 1

        return {
            'total_nodes': self.graph.number_of_nodes(),
            'total_edges': self.graph.number_of_edges(),
            'node_types': node_labels,
            'edge_types': edge_labels
        }


if __name__ == '__main__':
    from metadata_loader import MetadataLoader

    # メタデータを読み込み
    loader = MetadataLoader()
    schema = loader.load_schema("config/schema.json")

    # グラフを構築
    builder = DynamicGraphBuilder(schema, base_path=".")
    graph = builder.build_graph()

    print("\n=== 構築されたグラフ ===")
    print(f"ノード数: {graph.number_of_nodes()}")
    print(f"エッジ数: {graph.number_of_edges()}")

    # Facilityノードの表示
    facility_nodes = builder.get_nodes_by_entity("Facility")
    print(f"\nFacilityノード: {len(facility_nodes)}件")
    for node_id in facility_nodes[:3]:  # 最初の3件
        print(f"  {node_id}: {graph.nodes[node_id]}")
