import discord
from discord.ext import commands
import os
import aiohttp
import asyncio
from datetime import datetime, timedelta
from keep_alive import keep_alive

# Discord Botのトークン
TOKEN = os.getenv("DISCORD_TOKEN")
COHERE_API_TOKEN = os.getenv("COHERE_API_TOKEN")

# 追加する禁止単語リスト
banned_words = ["禁止ワード1", "禁止ワード2", "禁止ワード3"]

# Intentsの設定
intents = discord.Intents.default()
intents.dm_messages = True  # DMメッセージを受信するための設定
intents.messages = True      # サーバーでのメッセージを受信するための設定

# Botクライアントの初期化
bot = commands.Bot(command_prefix='/', intents=intents)

@bot.event
async def on_ready():
    print(f'{bot.user} としてログインしました')

# コマンドの定義
@bot.command(name='word', help='禁止ワードを追加または削除します')
async def word(ctx):
    embed = discord.Embed(title='禁止ワード管理',
                          description='どの操作を行いますか？',
                          color=0x00BFFF)
    embed.add_field(name='1️⃣ 追加', value='禁止ワードを追加します', inline=False)
    embed.add_field(name='2️⃣ 削除', value='禁止ワードを削除します', inline=False)

    await ctx.send(embed=embed)

    def check(msg):
        return msg.author == ctx.author and msg.channel == ctx.channel

    try:
        msg = await bot.wait_for('message', timeout=60.0, check=check)
    except asyncio.TimeoutError:
        await ctx.send('操作がタイムアウトしました。もう一度試してください。')
        return

    choice = msg.content.lower()
    if choice == '1' or choice == '追加':
        await add_word(ctx)
    elif choice == '2' or choice == '削除':
        await remove_word(ctx)
    else:
        await ctx.send('無効な選択です。もう一度試してください。')

async def add_word(ctx):
    await ctx.send('追加する禁止ワードを入力してください。')

    def check(msg):
        return msg.author == ctx.author and msg.channel == ctx.channel

    try:
        msg = await bot.wait_for('message', timeout=60.0, check=check)
    except asyncio.TimeoutError:
        await ctx.send('操作がタイムアウトしました。もう一度試してください。')
        return

    word = msg.content.strip()
    if word:
        if word not in banned_words:
            banned_words.append(word)
            await ctx.send(f'"{word}" を禁止ワードに追加しました。')
        else:
            await ctx.send(f'"{word}" は既に禁止ワードです。')

async def remove_word(ctx):
    await ctx.send('削除する禁止ワードを入力してください。')

    def check(msg):
        return msg.author == ctx.author and msg.channel == ctx.channel

    try:
        msg = await bot.wait_for('message', timeout=60.0, check=check)
    except asyncio.TimeoutError:
        await ctx.send('操作がタイムアウトしました。もう一度試してください。')
        return

    word = msg.content.strip()
    if word:
        if word in banned_words:
            banned_words.remove(word)
            await ctx.send(f'"{word}" を禁止ワードから削除しました。')
        else:
            await ctx.send(f'"{word}" は禁止ワードではありません。')

@bot.event
async def on_message(message):
    if message.author == bot.user:
        return

    if isinstance(message.channel, discord.DMChannel):
        # DMメッセージをCohereのAPIに送信してレスポンスを取得
        cohere_response = await send_to_cohere(message.content)

        # Cohereのレスポンスを返信
        await message.author.send(cohere_response)
    elif bot.user in message.mentions:
        # メンションされたメッセージをCohereのAPIに送信してレスポンスを取得
        cohere_response = await send_to_cohere(message.content)

        # Cohereのレスポンスを返信
        await message.channel.send(f'{message.author.mention} {cohere_response}')

    # 追加：禁止単語のチェック
    for word in banned_words:
        if word in message.content:
            await message.channel.send(f'{message.author.mention} さん、"{word}" という単語は不適切です。')

    # BUMP通知機能
    if message.author.id == 302050872383242240:
        embeds = message.embeds
        if embeds is not None and len(embeds) != 0:
            if "表示順をアップしたよ" in (embeds[0].description or ""):
                await handle_bump_notification(message)

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
        description=f"</bump:947088344167366698> でBUMPできます",
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
