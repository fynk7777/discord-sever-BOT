import discord
import os
import aiohttp
import asyncio
import random
import io
from discord.ext import commands,tasks
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

# ユーザーごとの不適切な単語使用回数を記録する辞書
user_word_counts = {}

# BOTロールと参加者ロールの名前を定義
BOT_ROLE_NAME = "BOT"
PARTICIPANT_ROLE_NAME = "ハゲ(参加者)"

# 起動時に動作する処理
@bot.event
async def on_ready():
    print(f'{bot.user} としてログインしました^o^')
    try:
        synced = await bot.tree.sync()
        print(f'Synced {len(synced)} commands')
    except Exception as e:
        print(f'Error syncing commands: {e}')
    # ボットが準備完了したらタスクを開始
    check_members.start()  # この行を追加
    # bakabonnpapa に DM を送信
    await send_update_message()

@tasks.loop(seconds=1)  # 1秒ごとにチェック
async def check_members():
    for guild in bot.guilds:
        bot_role = discord.utils.get(guild.roles, name=BOT_ROLE_NAME)
        participant_role = discord.utils.get(guild.roles, name=PARTICIPANT_ROLE_NAME)
        if bot_role and participant_role:
            for member in guild.members:
                try:
                    if bot_role in member.roles and participant_role in member.roles:
                        # BOTロールがついている人から参加者ロールを削除
                        await member.remove_roles(participant_role)
                        print(f"Removed {PARTICIPANT_ROLE_NAME} role from {member.name}")
                    elif bot_role not in member.roles and participant_role not in member.roles:
                        # BOTロールがついていない人に参加者ロールを追加
                        await member.add_roles(participant_role)
                        print(f"Added {PARTICIPANT_ROLE_NAME} role to {member.name}")
                except discord.errors.Forbidden:
                    print(f"Failed to modify role for {member.name}: Missing Permissions")
                except discord.HTTPException as e:
                    if e.status == 429:
                        print(f"Too Many Requests: {e}")
                        await asyncio.sleep(5)  # 5秒待機
                    else:
                        print(f"An error occurred: {e}")

@bot.tree.command(name="add", description="Add a word to the respond list (role only)")
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

@bot.tree.command(name="remove", description="Remove a word from the respond list (role only)")
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

@bot.tree.command(name="list", description="Show the list of respond words")
async def list_words(interaction: discord.Interaction):
    if respond_words:
        words_str = "\n".join(respond_words)
        await interaction.response.send_message(f'現在の禁止単語リスト:\n{words_str}')
    else:
        await interaction.response.send_message('現在、禁止単語は登録されていません。')

@bot.tree.command(name="hideout", description="Show the count of inappropriate words used by a user (role only) - Hidden from others")
async def hideout(interaction: discord.Interaction, user: discord.Member):
    member = interaction.user
    guild = interaction.guild
    role = discord.utils.get(guild.roles, name=role_name)
    if role and role in member.roles:
        if user.id in user_word_counts:
            count = user_word_counts[user.id]
            await interaction.response.send_message(f'あなたは、{user.name} が {count} 回 不適切な単語を使用していることを確認しました。', ephemeral=True)
        else:
            await interaction.response.send_message(f'{user.name} は、不適切な単語を使用していません。', ephemeral=True)
    else:
        await interaction.response.send_message(f'このコマンドは役職「{role_name}」を持っているメンバーのみが使用できます。')

@bot.tree.command(name="openout", description="Show the count of inappropriate words used by a user (role only) - Visible to everyone")
async def openout(interaction: discord.Interaction, user: discord.Member):
    member = interaction.user
    guild = interaction.guild
    role = discord.utils.get(guild.roles, name=role_name)
    if role and role in member.roles:
        if user.id in user_word_counts:
            count = user_word_counts[user.id]
            await interaction.response.send_message(f'{user.name} は {count} 回 不適切な単語を使用しています。')
        else:
            await interaction.response.send_message(f'{user.name} は、不適切な単語を使用していません。')
    else:
        await interaction.response.send_message(f'このコマンドは役職「{role_name}」を持っているメンバーのみが使用できます。')

@bot.tree.command(name="openall", description="Show the count of inappropriate words used by all users (role only) - Visible to everyone")
async def openall(interaction: discord.Interaction):
    member = interaction.user
    guild = interaction.guild
    role = discord.utils.get(guild.roles, name=role_name)
    if role and role in member.roles:
        sorted_counts = sorted(user_word_counts.items(), key=lambda item: item[1], reverse=True)
        if sorted_counts:
            result = "\n".join(f"{guild.get_member(item[0]).name}: {item[1]} 回" for item in sorted_counts)
            await interaction.response.send_message(f"不適切な単語の使用回数 (多い順):\n{result}")
        else:
            await interaction.response.send_message("まだ不適切な単語の使用はありません。")
    else:
        await interaction.response.send_message(f'このコマンドは役職「{role_name}」を持っているメンバーのみが使用できます。')

@bot.tree.command(name="hideall", description="Show the count of inappropriate words used by all users (role only) - Hidden from others")
async def hideall(interaction: discord.Interaction):
    member = interaction.user
    guild = interaction.guild
    role = discord.utils.get(guild.roles, name=role_name)
    if role and role in member.roles:
        sorted_counts = sorted(user_word_counts.items(), key=lambda item: item[1], reverse=True)
        if sorted_counts:
            result = "\n".join(f"{guild.get_member(item[0]).name}: {item[1]} 回" for item in sorted_counts)
            await interaction.response.send_message(f"不適切な単語の使用回数 (多い順):\n{result}", ephemeral=True)
        else:
            await interaction.response.send_message("まだ不適切な単語の使用はありません。", ephemeral=True)
    else:
        await interaction.response.send_message(f'このコマンドは役職「{role_name}」を持っているメンバーのみが使用できます。')

@bot.event
async def on_message(message):
    if message.author == bot.user:
        return

    # word_message の処理
    for word in respond_words:
        if word in message.content:
            await message.reply(f'その({word})という言葉は不適切です。禁止単語リストに含まれています')
            if message.author.id in user_word_counts:
                user_word_counts[message.author.id] += 1
            else:
                user_word_counts[message.author.id] = 1
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

async def send_update_message():
    user_id = 1212687868603007067  # bakabonnpapa のユーザーID を設定する
    user = await bot.fetch_user(user_id)
    await user.send("アップデートしました!!")

# Discordボットの起動とHTTPサーバーの起動
try:
    keep_alive()
    bot.run(TOKEN)
except Exception as e:
    print(f'エラーが発生しました: {e}')
