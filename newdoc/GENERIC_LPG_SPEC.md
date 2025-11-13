# 汎用的LPGシステム仕様書

## 概要

このドキュメントは、メタデータ駆動型の汎用的なLabeled Property Graph (LPG) システムの設計仕様を定義します。
宣言的な設定ファイル（JSON）を使用することで、コード変更なしに様々なデータソースとビジネスロジックに対応できる
柔軟なシステムを実現します。

## 設計思想

### 従来の課題

現在のシステムでは以下の課題があります：

1. **ハードコードされたスキーマ**: ノードタイプ（Facility, EmissionRecord等）がコードに固定
2. **ハードコードされた変換ロジック**: 4つの変換関数が専用実装
3. **拡張性の低さ**: 新しいデータソースや変換を追加するにはコード修正が必要
4. **再利用性の欠如**: 他のドメインに適用するには全面的な書き換えが必要

### 汎用システムの原則

1. **データ駆動**: すべての構造定義をメタデータ（JSON）で記述
2. **宣言的**: 「何をするか」を記述し、「どうやるか」はエンジンが解決
3. **拡張性**: 新しいデータソースや変換をJSONで追加可能
4. **疎結合**: スキーマ、データ、変換ルールを分離
5. **トレーサビリティ**: すべての変換の履歴を保持

## システムアーキテクチャ

```
┌─────────────────┐
│  メタデータ層   │  schema.json, transformations.json
├─────────────────┤
│  ルール層       │  RuleEngine, ExpressionEvaluator
├─────────────────┤
│  グラフ層       │  DynamicGraphBuilder, LPG (NetworkX)
├─────────────────┤
│  データ層       │  CSV Files
└─────────────────┘
```

## コア機能

### 1. メタデータ駆動のグラフ構築

#### schema.json の役割

- CSVファイルとノードタイプのマッピング
- カラム名とプロパティのマッピング
- ノード間の関係（エッジ）の定義
- ノードIDの生成ルール

#### 設計パターン

```json
{
  "version": "1.0",
  "entities": [
    {
      "name": "Facility",
      "source": "data/facilities.csv",
      "id_field": "facility_id",
      "properties": {
        "facility_id": {"type": "string", "required": true},
        "facility_name": {"type": "string", "required": true, "alias": "name"},
        "facility_type": {"type": "string"},
        "location": {"type": "string"},
        "capacity": {"type": "integer"}
      }
    }
  ],
  "relationships": [
    {
      "name": "HAS_EMISSION",
      "from_entity": "Facility",
      "to_entity": "EmissionRecord",
      "join_condition": {
        "from_field": "facility_id",
        "to_field": "facility_id"
      }
    }
  ]
}
```

### 2. 宣言的変換ルール

#### transformations.json の役割

- ノード間のリンク作成ルール
- 派生ノードの生成ルール
- プロパティの計算・追加ルール
- 集約ルール

#### 変換タイプ

##### 2.1 横断リンク (Cross-Link)

異なるエンティティ間に新しい関係を作成

```json
{
  "type": "cross_link",
  "name": "link_emission_and_energy",
  "description": "排出記録とエネルギー記録の相関リンク",
  "from_entity": "EmissionRecord",
  "to_entity": "EnergyRecord",
  "link_label": "CORRELATES_WITH",
  "condition": {
    "operator": "AND",
    "conditions": [
      {
        "type": "field_match",
        "from_field": "facility_id",
        "to_field": "facility_id"
      },
      {
        "type": "field_match",
        "from_field": "year",
        "to_field": "year"
      },
      {
        "type": "field_match",
        "from_field": "month",
        "to_field": "month"
      }
    ]
  },
  "properties": {
    "relation_type": "temporal_match",
    "created_by": "transformer"
  }
}
```

##### 2.2 派生ノード (Derived Node)

既存ノードから計算により新しいノードを生成

```json
{
  "type": "derived_node",
  "name": "calculate_intensity",
  "description": "CO2排出原単位の計算",
  "output_entity": "IntensityMetrics",
  "source_entities": {
    "emission": "EmissionRecord",
    "energy": "EnergyRecord"
  },
  "join_condition": {
    "type": "AND",
    "conditions": [
      {"field": "emission.facility_id", "equals": "energy.facility_id"},
      {"field": "emission.year", "equals": "energy.year"},
      {"field": "emission.month", "equals": "energy.month"}
    ]
  },
  "node_id_template": "INT_{emission.facility_id}_{emission.year}{emission.month:02d}",
  "properties": {
    "year": {"source": "emission.year"},
    "month": {"source": "emission.month"},
    "co2_intensity_kg_per_kwh": {
      "expression": "emission.co2_emissions_kg / energy.electricity_kwh",
      "round": 4
    },
    "water_intensity_m3_per_kwh": {
      "expression": "emission.water_usage_m3 / energy.electricity_kwh",
      "round": 6
    },
    "renewable_ratio": {"source": "energy.renewable_ratio"}
  },
  "edges": [
    {
      "from": "parent_facility",
      "to": "new_node",
      "label": "HAS_INTENSITY"
    },
    {
      "from": "new_node",
      "to": "emission",
      "label": "DERIVED_FROM_EMISSION"
    },
    {
      "from": "new_node",
      "to": "energy",
      "label": "DERIVED_FROM_ENERGY"
    }
  ]
}
```

##### 2.3 プロパティ追加 (Property Enrichment)

既存ノードに新しいプロパティを動的に追加

```json
{
  "type": "enrich_properties",
  "name": "classify_performance",
  "description": "パフォーマンス評価の付与",
  "target_entity": "IntensityMetrics",
  "enrichments": [
    {
      "property": "avg_benchmark",
      "expression": "avg(IntensityMetrics.co2_intensity_kg_per_kwh)"
    },
    {
      "property": "performance_rating",
      "rules": [
        {
          "condition": "node.co2_intensity_kg_per_kwh < avg_benchmark * 0.8 AND node.renewable_ratio > 0.25",
          "value": "Excellent"
        },
        {
          "condition": "node.co2_intensity_kg_per_kwh < avg_benchmark AND node.renewable_ratio > 0.15",
          "value": "Good"
        },
        {
          "condition": "node.co2_intensity_kg_per_kwh < avg_benchmark * 1.2",
          "value": "Average"
        },
        {
          "condition": "true",
          "value": "NeedsImprovement"
        }
      ]
    },
    {
      "property": "rating_timestamp",
      "expression": "now()"
    }
  ]
}
```

##### 2.4 集約 (Aggregation)

複数のノードから統計情報を計算して新しいノードを生成

```json
{
  "type": "aggregation",
  "name": "create_facility_summary",
  "description": "施設別集約レポート",
  "output_entity": "AggregationReport",
  "group_by_entity": "Facility",
  "aggregate_entity": "IntensityMetrics",
  "node_id_template": "AGG_{facility_id}_2024",
  "aggregations": {
    "avg_co2_intensity": {
      "function": "avg",
      "field": "co2_intensity_kg_per_kwh",
      "round": 4
    },
    "max_co2_intensity": {
      "function": "max",
      "field": "co2_intensity_kg_per_kwh",
      "round": 4
    },
    "min_co2_intensity": {
      "function": "min",
      "field": "co2_intensity_kg_per_kwh",
      "round": 4
    },
    "avg_renewable_ratio": {
      "function": "avg",
      "field": "renewable_ratio",
      "round": 3
    },
    "num_records": {
      "function": "count"
    }
  },
  "properties": {
    "facility_id": {"source": "facility.facility_id"},
    "facility_name": {"source": "facility.name"},
    "facility_type": {"source": "facility.facility_type"},
    "period": {"value": "2024-Q1"},
    "aggregation_type": {"value": "facility_summary"}
  },
  "edges": [
    {
      "from": "facility",
      "to": "new_node",
      "label": "HAS_AGGREGATION"
    },
    {
      "from": "new_node",
      "to": "aggregated_nodes",
      "label": "AGGREGATES"
    }
  ]
}
```

## 式評価エンジン

### サポートする演算

#### 算術演算
- `+`, `-`, `*`, `/`, `%`, `**` (累乗)

#### 比較演算
- `==`, `!=`, `<`, `>`, `<=`, `>=`

#### 論理演算
- `AND`, `OR`, `NOT`

#### 集約関数
- `avg(entity.field)`: 平均値
- `sum(entity.field)`: 合計
- `max(entity.field)`: 最大値
- `min(entity.field)`: 最小値
- `count(entity)`: 件数
- `stddev(entity.field)`: 標準偏差

#### ユーティリティ関数
- `now()`: 現在時刻（ISO8601）
- `round(value, decimals)`: 四捨五入
- `abs(value)`: 絶対値
- `len(value)`: 長さ

### フィールド参照

- `entity.field`: エンティティのフィールド参照
- `node.field`: 現在のノードのフィールド
- `parent.field`: 親ノードのフィールド

## 実装コンポーネント

### 1. MetadataLoader

**責務**: メタデータの読み込みと検証

```python
class MetadataLoader:
    def load_schema(self, schema_path: str) -> dict
    def load_transformations(self, transformations_path: str) -> dict
    def validate_schema(self, schema: dict) -> bool
    def validate_transformations(self, transformations: dict) -> bool
```

### 2. DynamicGraphBuilder

**責務**: メタデータに基づくグラフ構築

```python
class DynamicGraphBuilder:
    def __init__(self, schema: dict)
    def load_entity(self, entity_name: str) -> None
    def create_relationships(self) -> None
    def get_nodes_by_entity(self, entity_name: str) -> list
```

### 3. RuleEngine

**責務**: 変換ルールの解釈と実行

```python
class RuleEngine:
    def __init__(self, graph: nx.MultiDiGraph, transformations: dict)
    def apply_transformation(self, transformation: dict) -> None
    def apply_cross_link(self, rule: dict) -> None
    def apply_derived_node(self, rule: dict) -> None
    def apply_enrich_properties(self, rule: dict) -> None
    def apply_aggregation(self, rule: dict) -> None
```

### 4. ExpressionEvaluator

**責務**: 式の評価

```python
class ExpressionEvaluator:
    def __init__(self, graph: nx.MultiDiGraph)
    def evaluate(self, expression: str, context: dict) -> any
    def evaluate_condition(self, condition: dict, context: dict) -> bool
    def evaluate_aggregation(self, function: str, entity: str, field: str) -> any
```

## データフロー

```
1. メタデータ読み込み
   ├─ schema.json の読み込み
   └─ transformations.json の読み込み

2. グラフ構築
   ├─ エンティティの読み込み（CSV → ノード）
   └─ 基本関係の作成（エッジ）

3. 変換実行
   ├─ 横断リンクの作成
   ├─ 派生ノードの生成
   ├─ プロパティの追加
   └─ 集約ノードの生成

4. レポート出力
   └─ グラフからCSV/JSON出力
```

## 利点

### 1. コード変更不要

新しいデータソースや変換をJSONで追加可能

### 2. ドメイン非依存

環境データだけでなく、あらゆるドメインに適用可能

### 3. 宣言的で理解しやすい

「何をするか」を明確に記述

### 4. テスタビリティ

メタデータの妥当性を検証可能

### 5. バージョニング

メタデータをGit管理可能

## 拡張性

### 新しいデータソースの追加

schema.jsonにエンティティ定義を追加するだけ

### 新しい変換の追加

transformations.jsonに変換ルールを追加するだけ

### カスタム関数の追加

ExpressionEvaluatorにカスタム関数を登録

## 使用例

```bash
# メタデータの準備
vi config/schema.json
vi config/transformations.json

# システム実行
python src/main_generic.py \
  --schema config/schema.json \
  --transformations config/transformations.json \
  --output output/

# 新しいドメインへの適用
python src/main_generic.py \
  --schema config/hr_schema.json \
  --transformations config/hr_transformations.json \
  --output hr_output/
```

## まとめ

この汎用的LPGシステムは、以下を実現します：

1. **柔軟性**: メタデータ駆動で様々なデータ構造に対応
2. **拡張性**: コード変更なしで機能追加
3. **再利用性**: 異なるドメインで再利用可能
4. **保守性**: 宣言的な定義で理解・修正が容易
5. **トレーサビリティ**: すべての変換履歴を保持

LPGの柔軟性を最大限に活用した、次世代のデータ統合・変換システムです。
