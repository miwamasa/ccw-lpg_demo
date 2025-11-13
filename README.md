# LPG Knowledge Transformation Demo

## 概要
このプロジェクトは、Labeled Property Graph (LPG) の柔軟性を実証します。
既存のCSVデータをグラフ化し、新しい関係性やマッピングを導入することで、
知識の変換・合成を行い、環境データシートとして出力します。

## LPGの柔軟性の特徴

### 1. 動的なスキーマ
- ノードやエッジに任意のプロパティを追加可能
- 既存のグラフ構造を変更せずに拡張できる

### 2. 多様な関係性の表現
- 複数の異なる関係タイプを同時に表現
- 関係にもプロパティを付与可能

### 3. 知識の変換と合成
- 既存の関係から新しい関係を推論
- 複数のデータソースを統合
- メタデータの付与と集約

## プロジェクト構成

```
lpg_demo/
├── README.md                 # このファイル
├── data/                     # サンプルCSVデータ
│   ├── facilities.csv       # 施設データ
│   ├── emissions.csv        # 排出量データ
│   └── energy.csv           # エネルギー使用データ
├── src/
│   ├── graph_builder.py     # グラフ構築
│   ├── knowledge_transform.py # 知識変換
│   └── report_generator.py  # レポート生成
├── tests/
│   └── test_lpg_demo.py     # テストケース
└── output/
    └── environmental_report.csv # 出力データシート
```

## 使用方法

```bash
python src/main.py
```

## 変換の流れ

1. **データ取り込み**: CSV → LPGノード
2. **関係性構築**: 基本的なエッジ作成
3. **知識変換**: 新しい関係性の推論
4. **データ合成**: 複数ソースの統合
5. **レポート生成**: 環境データシート出力
