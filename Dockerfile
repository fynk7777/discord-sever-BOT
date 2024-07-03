# ベースイメージを指定
FROM python:3.9-slim

# 作業ディレクトリを設定
WORKDIR /app

# 必要なファイルをコピー
COPY main.py .
COPY keep_alive.py .
COPY requirements.txt .

# Pythonパッケージをインストール
RUN pip install --no-cache-dir -r requirements.txt

COPY . .

# コンテナを起動し、ボットを実行
CMD ["python", "main.py"]
