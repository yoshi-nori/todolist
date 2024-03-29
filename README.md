# タスク管理型Webアプリケーション
日々の作業効率を可視化することで作業に対するモチベーションと作業効率を高めていけるタスク管理型のWebアプリケーションです。

## 概要
- 1日に行う **「作業」** に対して **「タスク」** を登録し、作業を開始すると、タスク項目ごとにカウントダウンが行われ、最終的に実行した作業効率を評価することができます。

- 評価は、 **「タスク」** ごと、 **「作業」** ごと（タスクごとの重み配分を考慮）にできます。

- 日々の作業を可視化することで、自身の作業を振り返りながらモチベーションの維持や作業効率に対する意識を高めていくことができます。

## 機能一覧
- タスク登録・編集・削除機能
- 1日の作業の登録・編集・削除機能
- 複数のタスクの一括編集機能
- 登録したタスクのカウントダウン機能
- 実行済み作業の評価を行う機能
- 日々の作業効率を可視化する機能
- 認証機能
- 日時入力フォームのカレンダー表示機能
- ページネーション機能
- 1対多の関係


## 使用技術一覧
- サーバーサイド：Python 3.9.13
- フレームワーク：Django 3.2
- フロントエンド：jQuery
- データベース：PostgreSQL
- インフラ：Heroku