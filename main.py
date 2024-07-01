import discord
import cohere
import os

# 環境変数からトークンを取得
DISCORD_TOKEN = os.getenv("DISCORD_TOKEN")
COHERE_API_KEY = os.getenv("COHERE_API_KEY")

# DiscordクライアントとCohereクライアントを設定
intents = discord.Intents.default()
intents.message_content = True
client = discord.Client(intents=intents)
co = cohere.Client(COHERE_API_KEY)

@client.event
async def on_ready():
    print(f'We have logged in as {client.user}')

@client.event
async def on_message(message):
    if message.author == client.user:
        return

    if isinstance(message.channel, discord.DMChannel):
        response = co.generate(
            model='xlarge',
            prompt=message.content,
            max_tokens=50
        )
        await message.channel.send(response.generations[0].text)

client.run(DISCORD_TOKEN)
