import discord
import os
import aiohttp
import asyncio
import random
import io
from discord.ext import commands
from datetime import datetime, timedelta
from keep_alive import keep_alive

# Discord Botのトークン
TOKEN = os.getenv("DISCORD_TOKEN")
COHERE_API_TOKEN = os.getenv("COHERE_API_TOKEN")

# 画像を送信するチャンネルのID
TARGET_CHANNEL_ID = 1257585023125684256  # 画像を格納しているチャンネルのIDを設定する

# Intentsの設定
intents = discord.Intents.default()
intents.dm_messages = True  # DMメッセージを受信するための設定
intents.messages = True      # サーバーでのメッセージを受信するための設定
intents.message_content = True
intents.members = True


# Botクライアントの初期化
bot = commands.Bot(command_prefix='/', intents=intents)
bot = commands.Bot(command_prefix='!', intents=intents)
intents = discord.Intents.default()
intents.message_content = True
intents.members = True
client = discord.Client(intents=intents)

respond_words = []
# 応答ワードのリストを読み込む
role_name = "Lounge staff"
# 起動時に動作する処理

@bot.event
async def on_ready():
    print(f'{bot.user} としてログインしました^o^')
    try:
        synced = await bot.tree.sync()
        print(f'Synced {len(synced)} commands')
    except Exception as e:
        print(f'Error syncing commands: {e}')

@bot.tree.command(name="add", description="禁止単語を追加します(Lounge staffのみ)")
async def add(interaction: discord.Interaction, word: str):
    member = interaction.user
    guild = interaction.guild
    role = discord.utils.get(guild.roles, name=role_name)
    if role and role in member.roles:
        if word and word not in respond_words:
            respond_words.append(word)
            await interaction.response.send_message(f'「{word}」を禁止単語リストに追加しました。')
        else:
            await interaction.response.send_message('その単語は既にリストに存在するか、無効な単語です。')
    else:
        await interaction.response.send_message(f'このコマンドは役職「{role_name}」を持っているメンバーのみが使用できます。')

@bot.tree.command(name="remove", description="禁止単語を削除します(Lounge staffのみ)")
async def remove(interaction: discord.Interaction, word: str):
    member = interaction.user
    guild = interaction.guild
    role = discord.utils.get(guild.roles, name=role_name)
    if role and role in member.roles:
        if word in respond_words:
            respond_words.remove(word)
            await interaction.response.send_message(f'「{word}」を禁止単語リストから削除しました。')
        else:
            await interaction.response.send_message('その単語はリストに存在しません。')
    else:
        await interaction.response.send_message(f'このコマンドは役職「{role_name}」を持っているメンバーのみが使用できます。')

@bot.tree.command(name="list", description="禁止単語一覧を表示させます")
async def list_words(interaction: discord.Interaction):
    if respond_words:
        words_str = "\n".join(respond_words)
        await interaction.response.send_message(f'現在の禁止単語リスト:\n{words_str}')
    else:
        await interaction.response.send_message('現在、禁止単語は登録されていません。')

@bot.event
async def on_message(message):
    if message.author == bot.user:
        return

    # word_message の処理
    for word in respond_words:
        if word in message.content:
            await message.reply(f'その({word})という言葉は不適切です。禁止単語リストに含まれています')
            break

    # AIによる応答
    if bot.user in message.mentions:
        for mention in message.mentions:
            if mention == bot.user:
                response = await send_to_cohere(message.content)
                print(f'AIによる応答: {response}')
                await message.reply(response)  # メンションしたコメントに対して返信する
                break

    # 画像を送信する処理
    if message.content == 'ハゲ':
        await send_random_image(message.channel)

    # BUMP通知機能
    if message.author.id == 302050872383242240:
        embeds = message.embeds
        if embeds is not None and len(embeds) != 0:
            if "表示順をアップしたよ" in (embeds[0].description or ""):
                await handle_bump_notification(message)

    await bot.process_commands(message)

async def send_random_image(channel):
    target_channel = bot.get_channel(TARGET_CHANNEL_ID)
    if not target_channel:
        await channel.send("ターゲットチャンネルが見つかりませんでした。")
        return

    images = []

    async for msg in target_channel.history(limit=None):
        print(f'Checking message from {msg.author}: {msg.content}')  # メッセージ内容のログ
        for attachment in msg.attachments:
            print(f'Found attachment: {attachment.url}')  # 画像URLのログ
            print(f'Attachment details: {attachment}')  # 添付ファイルの詳細をログに出力
            images.append(attachment.url)  # URLを画像リストに追加
            print(f'Added to images list: {attachment.url}')  # 画像リストに追加されたことをログに出力

    print(f'Images list: {images}')  # 画像リストの内容を出力するログ

    if not images:
        await channel.send("画像が見つかりませんでした。")
        return

    selected_image = random.choice(images)
    print(f'Selected image: {selected_image}')  # 選択された画像URLのログ

    try:
        async with aiohttp.ClientSession() as session:
            async with session.get(selected_image) as resp:
                if resp.status != 200:
                    print(f'Failed to download image: {resp.status}')
                    await channel.send("画像のダウンロードに失敗しました。")
                    return
                data = await resp.read()

            await channel.send(file=discord.File(io.BytesIO(data), 'image.png'))
    except Exception as e:
        print(f'Error occurred: {e}')
        await channel.send("画像の送信中にエラーが発生しました。")

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

    print("Cohere APIにリクエストを送信中...")
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

async def handle_bump_notification(message):
    master = datetime.now() + timedelta(hours=2)
    notice_embed = discord.Embed(
        title="BUMPを検知しました",
        description=f"<t:{int(master.timestamp())}:f> 頃に通知します",
        color=0x00BFFF,
        timestamp=datetime.now()
    )
    await message.channel.send(embed=notice_embed)
    await asyncio.sleep(7200)
    notice_embed = discord.Embed(
        title="BUMPが可能です！",
        description="</bump:947088344167366698> でBUMPできます",
        color=0x00BFFF,
        timestamp=datetime.now()
    )
    await message.channel.send(embed=notice_embed)

# Discordボットの起動とHTTPサーバーの起動
try:
    keep_alive()
    bot.run(TOKEN)
except Exception as e:
    print(f'エラーが発生しました: {e}')
