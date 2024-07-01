import discord
import requests
from keep_alive import keep_alive

# Discord Botのトークン
TOKEN = 'あなたのDiscordボットのトークン'

# CohereのAPIトークン
COHERE_API_TOKEN = 'あなたのCohereのAPIトークン'

# Discordクライアントの初期化
client = discord.Client()

@client.event
async def on_ready():
    print(f'{client.user} としてログインしました')

@client.event
async def on_message(message):
    if message.author == client.user:
        return

    if isinstance(message.channel, discord.DMChannel):
        # メッセージをCohereのAPIに送信してレスポンスを取得
        cohere_response = send_to_cohere(message.content)

        # Cohereのレスポンスを返信
        await message.author.send(cohere_response)

def send_to_cohere(input_text):
    url = 'https://api.cohere.ai/bots/respond'
    headers = {
        'Authorization': f'Token {COHERE_API_TOKEN}',
        'Content-Type': 'application/json'
    }
    data = {
        'prompt': input_text
    }

    response = requests.post(url, headers=headers, json=data)

    if response.status_code == 200:
        return response.json()['text']
    else:
        return '申し訳ありませんが、現在リクエストを処理できませんでした。'

# Discordボットの起動とHTTPサーバーの起動
keep_alive()
client.run(TOKEN)
