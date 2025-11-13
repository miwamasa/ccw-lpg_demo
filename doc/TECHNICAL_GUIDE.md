# LPGの柔軟性と知識変換・合成

## 目次
1. [LPG（Labeled Property Graph）とは](#lpgとは)
2. [LPGの柔軟性の本質](#lpgの柔軟性の本質)
3. [知識変換の実践例](#知識変換の実践例)
4. [このデモで実現したこと](#このデモで実現したこと)
5. [実装パターンとベストプラクティス](#実装パターンとベストプラクティス)

---

## LPGとは

Labeled Property Graph (LPG) は、以下の要素で構成されるグラフデータモデルです：

### 基本要素
- **ノード（Nodes）**: エンティティを表現
  - ラベル（Label）: ノードのタイプ（例: `Facility`, `EmissionRecord`）
  - プロパティ（Properties）: 属性の集合（例: `name="東京工場"`, `capacity=5000`）

- **エッジ（Edges）**: ノード間の関係を表現
  - ラベル（Label）: 関係のタイプ（例: `HAS_EMISSION`, `CORRELATES_WITH`）
  - プロパティ（Properties）: 関係の属性（例: `year=2024`, `created_by="transformer"`）

### RDB（リレーショナルデータベース）との比較

| 特性 | RDB | LPG |
|------|-----|-----|
| スキーマ | 固定（事前定義が必須） | 柔軟（動的に変更可能） |
| 関係の表現 | 外部キー、結合テーブル | エッジ（ファーストクラスオブジェクト） |
| 属性の追加 | ALTER TABLE必要 | ノード/エッジに直接追加可能 |
| 複雑な関係 | JOIN処理が複雑化 | グラフトラバーサルで自然に表現 |
| データの拡張性 | スキーマ変更でダウンタイム発生 | 既存データに影響なく拡張 |

---

## LPGの柔軟性の本質

### 1. スキーマフリーな拡張性

**RDBの場合（従来のアプローチ）**:
```sql
-- 新しい列を追加するにはスキーマ変更が必要
ALTER TABLE facilities ADD COLUMN performance_rating VARCHAR(20);
-- 既存のすべての行に影響し、ダウンタイムが発生する可能性
```

**LPGの場合（柔軟なアプローチ）**:
```python
# 既存のノードに動的にプロパティを追加
graph.nodes[node_id]['performance_rating'] = 'Excellent'
graph.nodes[node_id]['benchmark_score'] = 0.95
graph.nodes[node_id]['evaluation_date'] = '2024-11-13'
# スキーマ変更不要、既存データに影響なし
```

### 2. 多様な関係性の共存

LPGでは、同じノード間に複数の異なる関係を持たせることができます。

```python
# 基本的な関係
graph.add_edge('F001', 'EMI_F001_202401', label='HAS_EMISSION')

# 後から追加した関係（既存に影響なし）
graph.add_edge('EMI_F001_202401', 'ENE_F001_202401', 
               label='CORRELATES_WITH',
               correlation_type='temporal_match',
               confidence=0.98)

# さらに派生関係を追加
graph.add_edge('INT_F001_202401', 'EMI_F001_202401',
               label='DERIVED_FROM_EMISSION',
               calculation_method='intensity_formula')
```

### 3. メタデータの動的付与

実行時にメタ情報を追加し、コンテキストを豊かにできます。

```python
# 計算結果のメタデータを追加
graph.nodes[intensity_id]['performance_rating'] = 'Good'
graph.nodes[intensity_id]['avg_benchmark'] = 0.433
graph.nodes[intensity_id]['rating_timestamp'] = datetime.now().isoformat()
graph.nodes[intensity_id]['evaluated_by'] = 'system'
graph.nodes[intensity_id]['evaluation_version'] = 'v2.1'
```

### 4. 段階的な知識の蓄積

初期データ → 派生データ → メタデータという階層的な知識構造を構築できます。

```
[生データ] 
  ↓ 変換1: データ統合
[横断的リンク]
  ↓ 変換2: メトリクス計算
[派生知識]
  ↓ 変換3: 評価・分類
[メタ情報]
  ↓ 変換4: 集約
[レポートノード]
```

---

## 知識変換の実践例

このデモで実装した4つの変換パターン：

### 変換1: 横断的データリンク

**目的**: 異なるデータソース間の関連性を明示化

**実装**:
```python
# 同じ施設・同じ期間の排出記録とエネルギー記録をリンク
if (emission_facility_id == energy_facility_id and
    emission_year_month == energy_year_month):
    graph.add_edge(
        emission_record_id,
        energy_record_id,
        label='CORRELATES_WITH',
        relation_type='temporal_match',
        created_by='transformer'
    )
```

**価値**:
- 元のCSVファイルには存在しない関係性を可視化
- 時系列の対応関係を明確化
- 分析時の結合処理が不要に

### 変換2: 派生メトリクスの生成

**目的**: 生データから新しい知識を合成

**実装**:
```python
# 排出量とエネルギー使用量から原単位を計算
co2_intensity = co2_emissions_kg / electricity_kwh
water_intensity = water_usage_m3 / electricity_kwh

# 新しいノードとして追加
graph.add_node(
    intensity_id,
    label='IntensityMetrics',
    co2_intensity_kg_per_kwh=co2_intensity,
    water_intensity_m3_per_kwh=water_intensity,
    derived_from='emission_and_energy'
)

# 元データへの参照を保持
graph.add_edge(intensity_id, emission_id, label='DERIVED_FROM_EMISSION')
graph.add_edge(intensity_id, energy_id, label='DERIVED_FROM_ENERGY')
```

**価値**:
- 計算ロジックがグラフ構造に埋め込まれる
- データの出所（Provenance）が明確
- 再計算時の依存関係が追跡可能

### 変換3: 評価・分類の付与

**目的**: ベンチマークと比較してメタ情報を追加

**実装**:
```python
# 全体平均を計算
avg_co2_intensity = calculate_average(all_intensities)

# 各ノードに評価を付与
for node in intensity_nodes:
    co2_int = graph.nodes[node]['co2_intensity_kg_per_kwh']
    renewable = graph.nodes[node]['renewable_ratio']
    
    # パフォーマンス分類
    if co2_int < avg_co2_intensity * 0.8 and renewable > 0.25:
        performance = 'Excellent'
    elif co2_int < avg_co2_intensity and renewable > 0.15:
        performance = 'Good'
    # ... 以下略
    
    # 動的にプロパティを追加
    graph.nodes[node]['performance_rating'] = performance
    graph.nodes[node]['avg_benchmark'] = avg_co2_intensity
```

**価値**:
- 既存ノードを変更せずに新しい視点を追加
- 評価基準の変更が容易
- 複数の評価軸を並行して保持可能

### 変換4: 集約ノードの生成

**目的**: 複数の詳細データをサマリーとして統合

**実装**:
```python
# 施設ごとの集約統計を計算
agg_data = {
    'avg_co2_intensity': mean(co2_values),
    'max_co2_intensity': max(co2_values),
    'min_co2_intensity': min(co2_values),
    'avg_renewable_ratio': mean(renewable_values),
    'num_records': len(metrics)
}

# 集約ノードを作成
graph.add_node(aggregation_id, label='AggregationReport', **agg_data)

# 集約元データへのリンクを保持
for metric in source_metrics:
    graph.add_edge(aggregation_id, metric, label='AGGREGATES')
```

**価値**:
- レポート生成用の事前集計データを保持
- 詳細データへのドリルダウンが可能
- 集計ロジックの変更が局所化

---

## このデモで実現したこと

### データフロー全体像

```
[CSV入力]
  facilities.csv ──┐
  emissions.csv ───┼─→ [グラフ構築]
  energy.csv ──────┘       ↓
                    [初期LPG: 25ノード, 20エッジ]
                           ↓
                    [知識変換1: 横断リンク]
                           ↓ +10エッジ
                    [知識変換2: 派生メトリクス]
                           ↓ +10ノード, +30エッジ
                    [知識変換3: 評価付与]
                           ↓ プロパティ追加
                    [知識変換4: 集約]
                           ↓ +5ノード, +15エッジ
                    [最終LPG: 40ノード, 75エッジ]
                           ↓
                    [レポート生成]
                           ↓
           ┌───────────────┴───────────────┐
    environmental_report.csv    detailed_metrics.csv
        (施設別サマリー)           (月次詳細)
```

### 実現した柔軟性の具体例

1. **スキーマの動的拡張**
   - 初期: 基本プロパティのみ（name, capacity等）
   - 追加: performance_rating, avg_benchmark等
   - 影響範囲: 変更したノードのみ

2. **多層的な関係性**
   ```
   Facility
     ├─ HAS_EMISSION → EmissionRecord
     ├─ HAS_ENERGY → EnergyRecord
     ├─ HAS_INTENSITY → IntensityMetrics
     │    ├─ DERIVED_FROM_EMISSION → EmissionRecord
     │    └─ DERIVED_FROM_ENERGY → EnergyRecord
     └─ HAS_AGGREGATION → AggregationReport
          └─ AGGREGATES → IntensityMetrics
   ```

3. **知識の合成**
   - 排出データ + エネルギーデータ → 原単位メトリクス
   - 原単位メトリクス群 → 施設別集約レポート
   - ベンチマーク + 個別値 → パフォーマンス評価

4. **トレーサビリティ**
   - 集約レポート → どの原単位から計算されたか
   - 原単位 → どの排出・エネルギーデータから導出されたか
   - すべての変換ステップが追跡可能

---

## 実装パターンとベストプラクティス

### パターン1: エッジによる関係の型付け

```python
# ❌ 悪い例: 型情報がない
graph.add_edge(nodeA, nodeB)

# ✅ 良い例: ラベルで関係の意味を明示
graph.add_edge(nodeA, nodeB, 
               label='CORRELATES_WITH',
               relation_type='temporal_match',
               confidence=0.95)
```

### パターン2: プロパティによる文脈の保持

```python
# ❌ 悪い例: メタデータが失われる
graph.nodes[node_id]['value'] = calculated_value

# ✅ 良い例: 計算の文脈を保持
graph.nodes[node_id]['value'] = calculated_value
graph.nodes[node_id]['calculated_at'] = timestamp
graph.nodes[node_id]['calculation_method'] = 'method_name'
graph.nodes[node_id]['source_version'] = 'v1.0'
```

### パターン3: 派生ノードと元データのリンク

```python
# ❌ 悪い例: 出所が不明
derived_node = create_derived_data(source_nodes)
graph.add_node(derived_node)

# ✅ 良い例: 出所を明示
derived_node = create_derived_data(source_nodes)
graph.add_node(derived_node, label='DerivedMetrics')
for source in source_nodes:
    graph.add_edge(derived_node, source, label='DERIVED_FROM')
```

### パターン4: バージョニングと監査証跡

```python
# ✅ 変換履歴を記録
transformation_record = {
    'type': 'metric_calculation',
    'timestamp': datetime.now().isoformat(),
    'source_nodes': [node1, node2],
    'algorithm': 'intensity_v1',
    'parameters': {'threshold': 0.8}
}

graph.nodes[new_node]['transformation_history'] = [transformation_record]
```

### パターン5: 段階的な変換の適用

```python
# ✅ 変換を小さなステップに分解
class KnowledgeTransformer:
    def __init__(self, graph):
        self.graph = graph
        self.transformations = []  # 変換履歴
    
    def apply_transformation_1(self):
        # 変換を適用
        ...
        # 履歴を記録
        self.transformations.append({
            'name': 'transformation_1',
            'timestamp': now(),
            'changes': {...}
        })
    
    def apply_transformation_2(self):
        # 独立した変換として実装
        ...
```

---

## まとめ

### LPGが実現する柔軟性

1. **スキーマレス**: データ構造の事前定義が不要
2. **拡張性**: 既存データに影響を与えずに機能追加
3. **表現力**: 複雑な関係を自然に表現
4. **トレーサビリティ**: データの出所と変換履歴を保持
5. **段階的構築**: 必要に応じて知識を蓄積

### このアプローチの利点

- **開発速度**: スキーマ変更のオーバーヘッドが最小
- **保守性**: 変更の影響範囲が局所的
- **分析の柔軟性**: 新しい視点を動的に追加可能
- **データ統合**: 異なるソースを自然に統合

### 適用シーン

- **環境データ管理**: このデモのような排出量・エネルギー管理
- **知識グラフ**: エンティティ間の複雑な関係を表現
- **データリネージ**: データの変換履歴を追跡
- **推薦システム**: ユーザーとアイテムの多様な関係
- **ネットワーク分析**: ソーシャルグラフ、組織図など

LPGの柔軟性を活用することで、データの成長と進化に対応できる、
拡張性の高いシステムを構築できます。
