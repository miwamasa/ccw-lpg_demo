以下がシナリオである、LPGへの拡張、変換とあるのは、プロパティやリンクを追加するというイメージ、必要ならばノードを増やす。

1)csvで、工場の生産情報、原単位、などがバラバラに保存
2)csvにメタデータ(json)を付与して、LPGに変換
3)個々のLPGに対して、newscenario/manufacturing-ontology.ttlの構造に従った、新しいLPGへ拡張および変換を行う
4)3で作成したLPGに対して、これを外部報告で使うためのモデル、newscenario/ghg-report-ontology.ttlに従ったLPGへ変換する、
5)/ghg-report-ontology.ttlに従った、csvファイルを出力