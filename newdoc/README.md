# 汎用的LPGシステム - 実装完了レポート

## 概要

このプロジェクトは、メタデータ駆動型の汎用的なLabeled Property Graph (LPG) システムを実装しました。
従来のハードコードされたシステムを、宣言的な設定ファイル（JSON）で制御できる柔軟なシステムに進化させました。

## 実装内容

### 1. 設計仕様

**ドキュメント**: `newdoc/GENERIC_LPG_SPEC.md`

- メタデータ駆動型アーキテクチャの設計
- 宣言的変換ルールの定義
- 4つの変換タイプ（cross_link, derived_node, enrich_properties, aggregation）
- 式評価エンジンの仕様

### 2. メタデータ定義

#### スキーマ定義 (`config/schema.json`)

CSVファイルとグラフ構造のマッピングを定義：

- **エンティティ定義**: Facility, EmissionRecord, EnergyRecord
- **プロパティマッピング**: CSV列からノードプロパティへの変換
- **関係定義**: HAS_EMISSION, HAS_ENERGY
- **ノードID生成**: テンプレートベースのID生成

#### 変換ルール定義 (`config/transformations.json`)

宣言的な変換ルールを定義：

1. **横断リンク** (`link_emission_and_energy`)
   - 排出記録とエネルギー記録を時系列で結合
   - 結果: 10件のCORRELATES_WITHリンク

2. **派生ノード生成** (`calculate_intensity`)
   - CO2排出原単位、水使用原単位を計算
   - 結果: 10件のIntensityMetricsノード

3. **プロパティ追加** (`classify_performance`)
   - ベンチマークと比較してパフォーマンス評価を付与
   - 結果: 10件のノードにperformance_ratingを追加

4. **集約** (`create_facility_summary`)
   - 施設ごとの統計サマリーを生成
   - 結果: 5件のAggregationReportノード

### 3. 実装コンポーネント

#### `src2/expression_evaluator.py`

式評価エンジン：

- **算術演算**: +, -, *, /, **, %
- **比較演算**: ==, !=, <, >, <=, >=
- **論理演算**: and, or, not
- **集約関数**: avg(), sum(), max(), min(), count(), stddev()
- **ユーティリティ**: now(), round(), abs(), len()
- **フィールド参照**: entity.field, node.field

#### `src2/metadata_loader.py`

メタデータローダー：

- スキーマと変換ルールの読み込み
- 構造の妥当性検証
- エンティティ・変換の検索機能

#### `src2/dynamic_graph_builder.py`

動的グラフビルダー：

- メタデータに基づくグラフ構築
- CSVデータの動的読み込み
- ノードIDのテンプレート生成
- 関係の自動作成

#### `src2/rule_engine.py`

ルールエンジン：

- 4つの変換タイプの実行
- 条件式の評価
- 派生ノードの生成
- プロパティの動的追加
- 集約計算

#### `src2/main_generic.py`

メイン実行スクリプト：

- コマンドライン引数の処理
- 5ステップの処理フロー
- レポート生成
- 統計情報の表示

## 実行結果

### テスト実行

```bash
$ python src2/main_generic.py
```

**グラフ構築結果**:
- 初期ノード: 25件（Facility: 5, EmissionRecord: 10, EnergyRecord: 10）
- 初期エッジ: 20件（HAS_EMISSION: 10, HAS_ENERGY: 10）

**知識変換結果**:
- 横断リンク: 10件
- 派生ノード: 10件（IntensityMetrics）
- プロパティ追加: 10件
- 集約ノード: 5件（AggregationReport）

**最終グラフ統計**:
- 総ノード数: 40件
- 総エッジ数: 75件
- ノードタイプ: 5種類
- エッジタイプ: 8種類

### レポート出力

**環境パフォーマンスレポート** (`output/environmental_report.csv`):
- 施設別の集約統計
- CO2排出原単位の平均・最大・最小
- 再生可能エネルギー比率
- 5施設のサマリー

**詳細メトリクスレポート** (`output/detailed_metrics.csv`):
- 月次詳細データ
- CO2排出原単位、水使用原単位
- パフォーマンス評価
- 10レコード（5施設 × 2ヶ月）

## システムの利点

### 1. コード変更不要

新しいデータソースや変換をJSONで追加可能：

```bash
# 新しいエンティティを追加
vi config/schema.json

# 新しい変換ルールを追加
vi config/transformations.json

# 実行（コード変更なし）
python src2/main_generic.py
```

### 2. ドメイン非依存

環境データだけでなく、あらゆるドメインに適用可能：

```bash
# 人事データへの適用例
python src2/main_generic.py \
  --schema config/hr_schema.json \
  --transformations config/hr_transformations.json \
  --output hr_output/
```

### 3. 宣言的で理解しやすい

「何をするか」を明確に記述：

```json
{
  "type": "derived_node",
  "expression": "emission.co2_emissions_kg / energy.electricity_kwh"
}
```

### 4. テスタビリティ

メタデータの妥当性を検証可能：

```python
loader = MetadataLoader()
loader.validate_schema(schema)
loader.validate_transformations(transformations)
```

### 5. バージョニング

メタデータをGit管理可能：

```bash
git log config/schema.json
git diff config/transformations.json
```

## 比較：従来システム vs 汎用システム

| 項目 | 従来システム (src/) | 汎用システム (src2/) |
|------|-------------------|---------------------|
| データ構造 | ハードコード | JSON定義 |
| 変換ロジック | 専用メソッド | 宣言的ルール |
| 拡張性 | コード修正必要 | JSON追加のみ |
| 再利用性 | ドメイン固定 | ドメイン非依存 |
| テスタビリティ | テストケース固定 | メタデータ検証 |
| 保守性 | 低い | 高い |

## 使用例

### 基本的な使用

```bash
# デフォルト設定で実行
python src2/main_generic.py

# カスタム設定で実行
python src2/main_generic.py \
  --schema config/custom_schema.json \
  --transformations config/custom_transformations.json \
  --base-path /data \
  --output /output
```

### 新しいエンティティの追加

`config/schema.json` に追加：

```json
{
  "name": "Supplier",
  "source": {"type": "csv", "path": "data/suppliers.csv"},
  "id_field": "supplier_id",
  "properties": {
    "supplier_id": {"type": "string", "required": true},
    "supplier_name": {"type": "string", "required": true}
  }
}
```

### 新しい変換の追加

`config/transformations.json` に追加：

```json
{
  "id": "link_facility_and_supplier",
  "type": "cross_link",
  "from_entity": "Facility",
  "to_entity": "Supplier",
  "link_label": "SUPPLIED_BY",
  "condition": {
    "operator": "AND",
    "conditions": [
      {
        "type": "field_match",
        "from_expression": "from.supplier_id",
        "to_expression": "to.supplier_id"
      }
    ]
  }
}
```

## 技術スタック

- **Python 3.11+**
- **NetworkX 3.5**: グラフデータ構造
- **Pandas 2.3**: データ処理
- **JSON**: メタデータ定義

## ディレクトリ構造

```
ccw-lpg_demo/
├── config/                          # メタデータ定義
│   ├── schema.json                  # スキーマ定義
│   └── transformations.json         # 変換ルール定義
│
├── data/                            # 入力データ
│   ├── facilities.csv
│   ├── emissions.csv
│   └── energy.csv
│
├── src/                             # 従来システム（参考用）
│   ├── graph_builder.py
│   ├── knowledge_transform.py
│   ├── report_generator.py
│   └── main.py
│
├── src2/                            # 汎用システム（新実装）
│   ├── expression_evaluator.py     # 式評価エンジン
│   ├── metadata_loader.py          # メタデータローダー
│   ├── dynamic_graph_builder.py    # 動的グラフビルダー
│   ├── rule_engine.py              # ルールエンジン
│   └── main_generic.py             # メイン実行スクリプト
│
├── newdoc/                          # 設計ドキュメント
│   ├── GENERIC_LPG_SPEC.md         # 仕様書
│   └── README.md                    # このファイル
│
├── doc/                             # 技術ドキュメント（従来）
│   ├── TECHNICAL_GUIDE.md
│   └── EXECUTION_REPORT.md
│
└── output/                          # 出力レポート
    ├── environmental_report.csv
    └── detailed_metrics.csv
```

## まとめ

この実装により、以下を実現しました：

1. ✅ **柔軟性**: メタデータ駆動で様々なデータ構造に対応
2. ✅ **拡張性**: コード変更なしで機能追加
3. ✅ **再利用性**: 異なるドメインで再利用可能
4. ✅ **保守性**: 宣言的な定義で理解・修正が容易
5. ✅ **トレーサビリティ**: すべての変換履歴を保持

LPGの柔軟性を最大限に活用した、次世代のデータ統合・変換システムです。

---

**実装日**: 2025-11-13
**実装者**: Claude Code
**システムステータス**: ✅ 全機能正常動作
**テスト結果**: ✅ すべての変換が成功
