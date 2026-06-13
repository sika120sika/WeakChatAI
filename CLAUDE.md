# WeakChatAI — Ollama ローカルコーディングチャット UI

## プロジェクト概要
Ollama で動くローカル LLM とブラウザからチャットできる Web アプリ。
コーディングアシスタント用途に特化。エージェントモードではファイル操作・コマンド実行も可能。

## ファイル構成
```
WeakChatAI/
├── index.html   # チャット UI 本体（全機能）
├── server.py    # エージェントモード用ローカルツールサーバー (port 3000, Python 標準ライブラリのみ)
├── README.md    # ユーザー向け機能説明・セットアップ手順
└── .gitignore
```
通常チャットは `index.html` を開くだけで動く。エージェントモードは `python server.py` が別途必要。

## README 管理ルール
**機能を追加・変更したら必ず README.md も更新すること。**
- 新機能 → 該当セクションの表に行を追加
- 既存機能の変更 → 説明を更新
- エージェントツールの追加 → 「エージェントツール」表に追記

## 技術スタック
| ライブラリ | バージョン | 用途 |
|---|---|---|
| marked.js | v9.1.6 (CDN) | Markdown レンダリング |
| highlight.js | v11.9 (CDN) | シンタックスハイライト |
| Ollama API | localhost:11434 | LLM バックエンド |

CSS フレームワーク・ビルドツール・Node.js は一切不使用。

## 動作環境
- Windows 11
- GTX 3070（VRAM 8GB）+ RAM 32GB
- 推奨モデル: **qwen2.5-coder:7b**（4.7GB、VRAM に完全収容、コーディング特化）

## Ollama セットアップ（初回のみ）
```powershell
# CORS 許可（永続設定）
[System.Environment]::SetEnvironmentVariable("OLLAMA_ORIGINS", "*", "User")
# → システムトレイの Ollama を Quit して再起動
```
`ollama serve` は不要。システムトレイアプリがサーバーを兼ねる。

## 実装済み機能
- [x] ストリーミングチャット（/api/chat → /api/generate 自動フォールバック）
- [x] Ollama からのモデル一覧自動取得・ドロップダウン切り替え
- [x] Markdown + シンタックスハイライト表示
- [x] 会話履歴の API 送信（文脈保持・num_ctx 指定で最大コンテキスト活用）
- [x] 会話リセット
- [x] コーディング用システムプロンプト（折りたたみ編集可・localStorage 保存）
- [x] クイックアクションボタン（レビュー / バグ修正 / リファクタリング / テスト生成 / 解説 / コミットメッセージ）
- [x] コードブロック: コピーボタン・言語ラベル
- [x] ファイルドラッグ&ドロップ（テキストファイルをコードブロックとして展開）
- [x] モデルダウンロード UI（/api/pull + リアルタイム進捗バー）
- [x] モデル削除（/api/delete・推奨外モデルも表示）
- [x] セッション保存・復元（localStorage）
- [x] 複数会話セッション管理（左サイドバー・自動タイトル・削除・切り替え・旧データ自動マイグレーション）
- [x] コンテキストメーター（累積トークンカウント・使用量バー・80% 超で警告・AI 要約圧縮）
- [x] エージェントモード（read_file / write_file / list_dir / run_command / search_content / find_files / get_tree）
- [x] エージェント起動時のプロジェクトツリー自動注入

## 高機能化アイデア（優先度順）

### 小規模（すぐ実装できる）
- [ ] レスポンス再生成ボタン（最後の AI 回答をやり直す）
- [ ] チャット履歴エクスポート（Markdown / JSON）
- [ ] モデルパラメータ調整 UI（temperature, top_p, repeat_penalty など）
- [ ] クリップボード取り込みボタン（クリップボードの内容をそのまま入力欄へ）
- [ ] ショートカットキーのカスタマイズ

### 中規模（エージェント拡張）
- [ ] ファイル差分表示（write_file 前後の diff を色付きで表示・承認フローに組み込む）
- [ ] テスト自動実行ループ（コード修正 → テスト実行 → 失敗時に再修正を繰り返す）
- [ ] Web 検索連携（DuckDuckGo API などでドキュメントを参照しながらコーディング）
- [ ] カスタムツール定義（JSON/YAML でユーザーが独自のエージェントツールを追加）
- [ ] ファイル監視（変更検知時に自動でレビュー依頼）

### 大規模（発展的）
- [ ] マルチモーダル対応（llava 等でスクリーンショット・図をそのまま貼って質問）
- [ ] RAG 的コードベース検索（大規模リポジトリをインデックス化し関連部分だけをコンテキストへ）
- [ ] タスクキュー（複数タスクをリストアップして順次自律実行）
- [ ] 複数ファイル一括編集（変更前後の diff 一覧を確認してまとめて承認）

## Ollama API リファレンス
| エンドポイント | メソッド | 用途 |
|---|---|---|
| `/api/tags` | GET | インストール済みモデル一覧 |
| `/api/chat` | POST | チャット（messages 配列、stream 対応）|
| `/api/generate` | POST | テキスト生成（prompt 文字列、stream 対応）|
| `/api/pull` | POST | モデルダウンロード（NDJSON 進捗ストリーム）|

### /api/pull レスポンス形式
```json
{"status":"pulling manifest"}
{"status":"pulling ...","digest":"sha256:...","total":4661211136,"completed":1234567}
{"status":"success"}
```

### /api/chat リクエスト形式
```json
{
  "model": "qwen2.5-coder:7b",
  "messages": [
    {"role": "system", "content": "システムプロンプト"},
    {"role": "user", "content": "質問"}
  ],
  "stream": true
}
```
ストリーミングレスポンスの各行: `json.message.content` にチャンクが入る。

## Git 操作メモ

リモートリポジトリ: https://github.com/sika120sika/WeakChatAI（SSH接続）

### PowerShell での注意点

**`gh` コマンドは毎回 PATH を補完する必要がある**（セッションをまたいで PATH が引き継がれないため）:
```powershell
$env:PATH += ";C:\Program Files\GitHub CLI"
gh auth status
```

**複数行コミットメッセージは PowerShell の here-string を使う**。
bash の `<<'EOF'` は PowerShell では動かないので注意:

```powershell
# OK — PowerShell here-string
$msg = @'
feat: add something

- detail 1
- detail 2
'@
git commit -m $msg

# NG — bash 構文は PowerShell では ParseError になる
git commit -m "$(cat <<'EOF'
...
EOF
)"
```

### 通常の作業フロー

```powershell
# 変更確認
git status
git diff

# ステージング（機密ファイルを誤って含めないよう個別指定）
git add index.html server.py README.md CLAUDE.md

# コミット（1行で済む場合）
git commit -m "fix: バグ修正の説明"

# push
git push
```

### ブランチ・タグ等
現状は `main` 1本運用。大きな機能追加時はブランチを切ること。

## 開発メモ
- `index.html` 単体で完結させること（外部ファイル禁止）
- CDN ライブラリは現行バージョンを固定して使う（marked@9.1.6、hljs@11.9）
- CSS 変数（`:root`）でテーマカラーを管理している
- `/api/chat` が 404 の場合は `/api/generate` に自動フォールバックする実装済み
