#!/usr/bin/env bash
# shiftvote2 の API (Flask/SQLite CGI) を さくらインターネットへデプロイする。
# フロントエンド (GitHub Pages) は別途 GitHub Actions で自動デプロイされる。
#
# 使い方:
#   1) .env.deploy.example をコピーして .env.deploy を作る
#   2) bash scripts/deploy.sh
set -euo pipefail

DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
ENV_FILE="$DIR/.env.deploy"

if [ ! -f "$ENV_FILE" ]; then
  echo "❌ $ENV_FILE が見つかりません。.env.deploy.example をコピーして作成してください" >&2
  exit 1
fi
# shellcheck source=/dev/null
source "$ENV_FILE"

: "${DEPLOY_HOST:?DEPLOY_HOST を .env.deploy に設定してください}"
: "${DEPLOY_USER:?DEPLOY_USER を .env.deploy に設定してください}"
: "${DEPLOY_PATH:?DEPLOY_PATH を .env.deploy に設定してください}"

TARGET="${DEPLOY_USER}@${DEPLOY_HOST}"

echo "🚀 ${TARGET}:${DEPLOY_PATH} へAPIをアップロードします"
ssh "$TARGET" "mkdir -p '${DEPLOY_PATH}'"
scp "$DIR/api-cgi/app.py" "$DIR/api-cgi/index.cgi" "$DIR/api-cgi/.htaccess" "$DIR/api-cgi/seed_data.py" "$DIR/api-cgi/requirements.txt" "${TARGET}:${DEPLOY_PATH}/"
ssh "$TARGET" "chmod +x '${DEPLOY_PATH}/index.cgi'"
echo "✅ API配置完了"

echo "🚀 依存パッケージを確認します (共有venv)"
ssh "$TARGET" "~/venv/bin/python -c 'import flask; print(\"flask\", flask.__version__)'" || {
  echo "⚠️  共有venvにFlaskが見つかりません。手動で ~/venv/bin/pip install -r requirements.txt --user を実行してください" >&2
}

echo "ℹ️  初回のみ: ssh ${TARGET} してデータディレクトリを用意し、seed_data.py を実行してください:"
echo "   ssh ${TARGET} \"mkdir -p ~/shiftvote2-data && SHIFTVOTE_DATA_DIR=~/shiftvote2-data ~/venv/bin/python ${DEPLOY_PATH}/seed_data.py\""
