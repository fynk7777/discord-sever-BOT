import discord
import os
import aiohttp
import asyncio
from keep_alive import keep_alive

# Discord Botのトークン
TOKEN = os.getenv("DISCORD_TOKEN")
COHERE_API_TOKEN = os.getenv("COHERE_API_TOKEN")

# トークンの確認（デバッグ用）
print(f'DISCORD_TOKEN: {TOKEN}')
print(f'COHERE_API_TOKEN: {COHERE_API_TOKEN}')

# Intentsの設定
intents = discord.Intents.default()
intents.dm_messages = True  # DMメッセージを受信するための設定
intents.messages = True      # サーバーでのメッセージを受信するための設定

# Discordクライアントの初期化
client = discord.Client(intents=intents)

@client.event
async def on_ready():
    print(f'{client.user} としてログインしました')

@client.event
async def on_message(message):
    if message.author == client.user:
        return

    if isinstance(message.channel, discord.DMChannel):
        # DMメッセージをCohereのAPIに送信してレスポンスを取得
        cohere_response = await send_to_cohere(message.content)

        # Cohereのレスポンスを返信
        await message.author.send(cohere_response)
    elif client.user in message.mentions:
        # メンションされたメッセージをCohereのAPIに送信してレスポンスを取得
        cohere_response = await send_to_cohere(message.content)

        # Cohereのレスポンスを返信
        await message.channel.send(f'{message.author.mention} {cohere_response}')

async def send_to_cohere(input_text):
    url = 'https://api.cohere.ai/v1/generate'  # 正しいエンドポイントを使用
    headers = {
        'Authorization': f'Bearer {COHERE_API_TOKEN}',  # 正しい形式のAPIキーを使用
        'Content-Type': 'application/json'
    }
    data = {
        'prompt': input_text,
        'model': 'command-nightly',  # 使用するモデルの指定（Cohereのドキュメントに基づく）
        'max_tokens': 50    # 最大トークン数の指定
    }

    print("Sending request to Cohere API...")
    print(f"Headers: {headers}")
    print(f"Data: {data}")

    async with aiohttp.ClientSession() as session:
        try:
            async with session.post(url, headers=headers, json=data) as response:
                print(f"Response status: {response.status}")
                if response.status == 200:
                    response_json = await response.json()
                    print(f"Response JSON: {response_json}")
                    # 'text'を取得する部分を修正
                    return response_json['generations'][0]['text']
                else:
                    error_message = await response.text()
                    print(f'エラーが発生しました: {response.status} - {error_message}')
                    return f'エラーが発生しました: {response.status} - {error_message}'
        except Exception as e:
            print(f'エラーが発生しました: {e}')
            return '申し訳ありませんが、現在リクエストを処理できませんでした。'

# Discordボットの起動とHTTPサーバーの起動
try:
    keep_alive()
    client.run(TOKEN)
except Exception as e:
    print(f'エラーが発生しました: {e}')
