"""
Metadata Loader for Generic LPG System

スキーマと変換ルールのメタデータを読み込み、検証します。
"""

import json
from pathlib import Path
from typing import Dict, List, Any


class MetadataLoader:
    """
    メタデータローダー

    schema.json と transformations.json を読み込み、
    構造の妥当性を検証します。
    """

    def __init__(self):
        self.schema = None
        self.transformations = None

    def load_schema(self, schema_path: str) -> Dict:
        """
        スキーマファイルを読み込む

        Args:
            schema_path: schema.jsonのパス

        Returns:
            スキーマ定義（dict）
        """
        path = Path(schema_path)
        if not path.exists():
            raise FileNotFoundError(f"スキーマファイルが見つかりません: {schema_path}")

        with open(path, 'r', encoding='utf-8') as f:
            self.schema = json.load(f)

        self.validate_schema(self.schema)
        print(f"✓ スキーマを読み込みました: {schema_path}")
        return self.schema

    def load_transformations(self, transformations_path: str) -> Dict:
        """
        変換ルールファイルを読み込む

        Args:
            transformations_path: transformations.jsonのパス

        Returns:
            変換ルール定義（dict）
        """
        path = Path(transformations_path)
        if not path.exists():
            raise FileNotFoundError(f"変換ルールファイルが見つかりません: {transformations_path}")

        with open(path, 'r', encoding='utf-8') as f:
            self.transformations = json.load(f)

        self.validate_transformations(self.transformations)
        print(f"✓ 変換ルールを読み込みました: {transformations_path}")
        return self.transformations

    def validate_schema(self, schema: Dict) -> bool:
        """
        スキーマの妥当性を検証

        Args:
            schema: スキーマ定義

        Returns:
            True（検証成功）

        Raises:
            ValueError: 検証失敗時
        """
        if "version" not in schema:
            raise ValueError("スキーマにversionが必要です")

        if "entities" not in schema:
            raise ValueError("スキーマにentitiesが必要です")

        entities = schema["entities"]
        if not isinstance(entities, list) or len(entities) == 0:
            raise ValueError("entitiesは空でないリストである必要があります")

        # エンティティの検証
        entity_names = set()
        for entity in entities:
            if "name" not in entity:
                raise ValueError("エンティティにnameが必要です")

            name = entity["name"]
            if name in entity_names:
                raise ValueError(f"重複するエンティティ名: {name}")
            entity_names.add(name)

            if "source" not in entity:
                raise ValueError(f"エンティティ {name} にsourceが必要です")

            if "properties" not in entity:
                raise ValueError(f"エンティティ {name} にpropertiesが必要です")

            # id_field または id_template のいずれかが必要
            if "id_field" not in entity and "id_template" not in entity:
                raise ValueError(f"エンティティ {name} にid_fieldまたはid_templateが必要です")

        # 関係の検証
        if "relationships" in schema:
            relationships = schema["relationships"]
            for rel in relationships:
                if "name" not in rel:
                    raise ValueError("関係にnameが必要です")

                if "from_entity" not in rel or "to_entity" not in rel:
                    raise ValueError(f"関係 {rel['name']} にfrom_entityとto_entityが必要です")

                from_entity = rel["from_entity"]
                to_entity = rel["to_entity"]

                if from_entity not in entity_names:
                    raise ValueError(f"関係 {rel['name']} の from_entity {from_entity} が存在しません")

                if to_entity not in entity_names:
                    raise ValueError(f"関係 {rel['name']} の to_entity {to_entity} が存在しません")

        print(f"  エンティティ: {len(entities)}件")
        print(f"  関係: {len(schema.get('relationships', []))}件")
        return True

    def validate_transformations(self, transformations: Dict) -> bool:
        """
        変換ルールの妥当性を検証

        Args:
            transformations: 変換ルール定義

        Returns:
            True（検証成功）

        Raises:
            ValueError: 検証失敗時
        """
        if "version" not in transformations:
            raise ValueError("変換ルールにversionが必要です")

        if "transformations" not in transformations:
            raise ValueError("変換ルールにtransformationsが必要です")

        trans_list = transformations["transformations"]
        if not isinstance(trans_list, list):
            raise ValueError("transformationsはリストである必要があります")

        # 各変換の検証
        trans_ids = set()
        trans_types = {"cross_link": 0, "derived_node": 0, "enrich_properties": 0, "aggregation": 0}

        for trans in trans_list:
            if "id" not in trans:
                raise ValueError("変換にidが必要です")

            trans_id = trans["id"]
            if trans_id in trans_ids:
                raise ValueError(f"重複する変換ID: {trans_id}")
            trans_ids.add(trans_id)

            if "type" not in trans:
                raise ValueError(f"変換 {trans_id} にtypeが必要です")

            trans_type = trans["type"]
            if trans_type not in trans_types:
                raise ValueError(f"未対応の変換タイプ: {trans_type}")

            trans_types[trans_type] += 1

            # タイプ別の検証
            if trans_type == "cross_link":
                self._validate_cross_link(trans)
            elif trans_type == "derived_node":
                self._validate_derived_node(trans)
            elif trans_type == "enrich_properties":
                self._validate_enrich_properties(trans)
            elif trans_type == "aggregation":
                self._validate_aggregation(trans)

        print(f"  変換ルール: {len(trans_list)}件")
        for trans_type, count in trans_types.items():
            if count > 0:
                print(f"    - {trans_type}: {count}件")

        return True

    def _validate_cross_link(self, trans: Dict):
        """横断リンク変換の検証"""
        required = ["from_entity", "to_entity", "link_label", "condition"]
        for field in required:
            if field not in trans:
                raise ValueError(f"cross_link変換 {trans['id']} に{field}が必要です")

    def _validate_derived_node(self, trans: Dict):
        """派生ノード変換の検証"""
        required = ["output_entity", "source_entities", "join_condition", "properties"]
        for field in required:
            if field not in trans:
                raise ValueError(f"derived_node変換 {trans['id']} に{field}が必要です")

    def _validate_enrich_properties(self, trans: Dict):
        """プロパティ追加変換の検証"""
        required = ["target_entity", "enrichments"]
        for field in required:
            if field not in trans:
                raise ValueError(f"enrich_properties変換 {trans['id']} に{field}が必要です")

    def _validate_aggregation(self, trans: Dict):
        """集約変換の検証"""
        required = ["output_entity", "group_by_entity", "aggregate_entity", "aggregations"]
        for field in required:
            if field not in trans:
                raise ValueError(f"aggregation変換 {trans['id']} に{field}が必要です")

    def get_entity_by_name(self, name: str) -> Dict:
        """
        エンティティ定義を名前で取得

        Args:
            name: エンティティ名

        Returns:
            エンティティ定義
        """
        if not self.schema:
            raise ValueError("スキーマが読み込まれていません")

        for entity in self.schema["entities"]:
            if entity["name"] == name:
                return entity

        raise ValueError(f"エンティティが見つかりません: {name}")

    def get_enabled_transformations(self) -> List[Dict]:
        """
        有効な変換ルールのリストを取得

        Returns:
            有効な変換ルールのリスト
        """
        if not self.transformations:
            raise ValueError("変換ルールが読み込まれていません")

        return [t for t in self.transformations["transformations"]
                if t.get("enabled", True)]


if __name__ == '__main__':
    # テスト
    loader = MetadataLoader()

    try:
        # スキーマの読み込み
        schema = loader.load_schema("config/schema.json")
        print(f"\nスキーマ情報:")
        print(f"  バージョン: {schema['version']}")
        print(f"  エンティティ数: {len(schema['entities'])}")

        # 変換ルールの読み込み
        transformations = loader.load_transformations("config/transformations.json")
        print(f"\n変換ルール情報:")
        print(f"  バージョン: {transformations['version']}")
        print(f"  変換数: {len(transformations['transformations'])}")

        # エンティティ取得のテスト
        facility = loader.get_entity_by_name("Facility")
        print(f"\nFacilityエンティティ:")
        print(f"  ソース: {facility['source']['path']}")
        print(f"  プロパティ数: {len(facility['properties'])}")

    except Exception as e:
        print(f"エラー: {e}")
