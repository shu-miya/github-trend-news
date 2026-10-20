# GitHub 人気ニュース

GitHub Trendingの人気リポジトリを日本語で紹介する日次・週次・月次ダッシュボード。

公開予定サイト: https://shu-miya.github.io/github-trend-news/

## 初回セットアップ

1. このリポジトリの Settings → Pages → Build and deployment → Source を GitHub Actions にする。
2. Actions → Collect GitHub Trending → Run workflow を1回手動実行する。
3. 実行結果が成功になりPagesが公開されたら、上記URLを開く。
4. 翌日以降は毎朝09:17（日本時間）頃にGitHub Actionsが自動取得する。実行時間は保証されない。

GitHub Actionsにコミット権限が無い場合は Settings → Actions → General → Workflow permissions を確認する。ワークフローには contents: write 権限が明示されている。

## 機能とデータ

GitHub Trendingの「掲載順位」と「当該期間で増えたスター数」を区別し、スナップショットを日付別にGitへ保存する。
PC/スマホ対応、日次・週次・月次切替、検索、カテゴリ分類、新規登場や順位上昇の比較を提供する。

Trendingには公式APIがなく、公開HTMLを解析する非公式実装。GitHub側の仕様変更やアクセス制限で取得に失敗することがある。5件未満の結果やスター増加数が取れないときには公開データを更新しない。

日本語の簡単な説明とカテゴリはリポジトリ名・説明文によるルール推定で、事実確認済みの解説記事ではない。
初回収集まではサイトに未取得と表示。デモ用の架空値は本番ランキングと混同しないよう区別している。

## ファイル構成

- site/ : GitHub Pagesの静的サイト
- src/collect.py : 日次・週次・月次収集
- tests/test_collect.py : パーサ・履歴保存のテスト
- .github/workflows/update.yml : 毎日収集し保存・配信
- .github/workflows/pages.yml : UIソース更新時の配信

## ローカルで検証

Python 3.12以上で requirements.txt をインストールし、python -m unittest discover -s tests -v でテスト。
python -m src.collect で取得し、python -m http.server 8000 --directory site で閲覧。

生成データは site/data/index.json、site/data/latest.json、site/data/snapshots/YYYY-MM-DD.json。
履歴は初回取得以降のみ蓄積され、過去へ遡って任意の当時のTrending順位を再現できるわけではない。
