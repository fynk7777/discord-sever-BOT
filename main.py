import os
import aiohttp
import asyncio
import re
from datetime import datetime, timedelta

import discord
from discord import app_commands
from discord.ext import commands, tasks

from keep_alive import keep_alive


# Discord Botのトークン
TOKEN = os.getenv("DISCORD_TOKEN")
COHERE_API_TOKEN = os.getenv("COHERE_API_TOKEN")

# Intentsの設定
intents = discord.Intents.all()

# Botクライアントの初期化
bot = commands.Bot(command_prefix='!', intents=intents)

# グローバル変数でソースチャンネルとデスティネーションチャンネルのペアを管理
channel_pairs = {}

#カスタム返信のリストを初期化
custom_replies = {}

respond_words = ["死ね","殺す","虐待"]
# 応答ワードのリストを読み込む
role_name = "Lounge staff"
original_nicknames = {}
# ユーザーごとの不適切な単語使用回数を記録する辞書
user_word_counts = {}

# BOTロールと参加者ロールの名前を定義
BOT_ROLE_NAME = "BOT"
PARTICIPANT_ROLE_NAME = "参加者"

ALLOWED_USERS = [1212687868603007067]  # ユーザーIDを追加

BOT_ID = 1256561371127091230

nick_edit_in_progress = set()

BOT_CHANNEL_MAP = {
    1265253957073240195: {"channel_id": 1285683713975386132, "base_name": "colormasterbot"},
    1271574158295306291: {"channel_id": 1285683752122585222, "base_name": "fortnite-server"},
    1261624239879094333: {"channel_id": 1285683805096775824, "base_name": "lounge-url"},
    1258570205815246948: {"channel_id": 1285683876282237089, "base_name": "mikan-mk専用bot"},
    1274367166979903570: {"channel_id": 1285685038628733021, "base_name": "raimu-server"},
    1256561371127091230: {"channel_id": 1285683956762673244, "base_name": "ハゲサーバー専用bot"},
}
YELLOW_CHANNEL_ID = 1285693670267420684  # いずれかのBOTがオフラインの場合に変更するチャンネルのID
YELLOW_CHANNEL_BASE_NAME = "監視必要bot"  # いずれかのBOTがオフラインの場合のチャンネル名


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

# スラッシュコマンドの定義
@bot.tree.command(name="transfer", description="Set destination channel to transfer messages to")
@app_commands.describe(destination_channel="Destination channel ID")
async def transfer(interaction: discord.Interaction, destination_channel: str):
    if interaction.user.id in ALLOWED_USERS:
        global channel_pairs
        try:
            destination_channel_id = int(destination_channel)
            source_channel_id = interaction.channel_id  # コマンドが使われたチャンネルをソースチャンネルに設定
            channel_pairs[source_channel_id] = destination_channel_id
            await interaction.response.send_message(f"Messages from this channel will be transferred to <#{destination_channel_id}>")
        except ValueError:
            await interaction.response.send_message("Invalid channel ID. Please enter a valid integer.", ephemeral=True)
    else:
        await interaction.response.send_message('このコマンドを実行する権限がありません。', ephemeral=True)

@bot.tree.command(name="status",description="ステータスを設定するコマンドです")
@app_commands.describe(text="ステータスを設定します")
async def text(interaction: discord.Interaction, text: str):
    if interaction.user.id in ALLOWED_USERS:
        await bot.change_presence(status=discord.Status.online, activity=discord.CustomActivity(name=f'{text}'))
        await interaction.response.send_message(f'ステータスを「{text}」に設定しました。',ephemeral=True)
    else:
        await interaction.response.send_message('このコマンドを実行する権限がありません。', ephemeral=True)

# /addreply コマンドの処理
@bot.tree.command(name="reply_add", description="カスタム返信を追加します")
async def reply_add(interaction: discord.Interaction, trigger: str, response: str):
    custom_replies[trigger] = response
    member = interaction.user
    guild = interaction.guild
    role = discord.utils.get(guild.roles, name=role_name)
    if role and role in member.roles:
        await interaction.response.send_message(f'追加されました: {trigger} -> {response}')
    else:
        await interaction.response.send_message(f'このコマンドは役職「{role_name}」を持っているメンバーのみが使用できます。')

# /removereply コマンドの処理
@bot.tree.command(name="reply_remove", description="カスタム返信を削除します")
async def reply_remove(interaction: discord.Interaction, trigger: str):
    member = interaction.user
    guild = interaction.guild
    role = discord.utils.get(guild.roles, name=role_name)
    if role and role in member.roles:
        if trigger in custom_replies:
            del custom_replies[trigger]
            await interaction.response.send_message(f'削除されました: {trigger}')
        else:
            await interaction.response.send_message(f'見つかりません: {trigger}')
    else:
        await interaction.response.send_message(f'このコマンドは役職「{role_name}」を持っているメンバーのみが使用できます。')

# /listreply コマンドの処理
@bot.tree.command(name="reply_list", description="カスタム返信リストを表示します")
async def reply_list(interaction: discord.Interaction):
    if custom_replies:
        reply_list = '\n'.join([f'{trigger} -> {response}' for trigger, response in custom_replies.items()])
        await interaction.response.send_message(f'カスタム返信リスト:\n{reply_list}')
    else:
        await interaction.response.send_message('カスタム返信はありません。')



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
                        await asyncio.sleep(1)  # 5秒待機
                    else:
                        print(f"An error occurred: {e}")

@bot.tree.command(name="word_add", description=f"禁止単語を追加します({role_name}だけが使用できます)")
async def word_add(interaction: discord.Interaction, word: str):
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

@bot.tree.command(name="word_remove", description=f"禁止単語を削除します({role_name}だけが使用できます)")
async def word_remove(interaction: discord.Interaction, word: str):
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

@bot.tree.command(name="word_list", description="禁止単語一覧を表示します")
async def word_list(interaction: discord.Interaction):
    if respond_words:
        words_str = "\n".join(respond_words)
        await interaction.response.send_message(f'現在の禁止単語リスト:\n{words_str}')
    else:
        await interaction.response.send_message('現在、禁止単語は登録されていません。')

@bot.tree.command(name="word_specific_hide", description=f"特定のユーザーの不適切な言葉をいった回数をあなたにだけ表示させます")
async def word_specific_hide(interaction: discord.Interaction, user: discord.Member):
    member = interaction.user
    guild = interaction.guild
    if user.id in user_word_counts:
            count = user_word_counts[user.id]
            await interaction.response.send_message(f'あなたは、{user.name} が {count} 回 不適切な単語を使用していることを確認しました。', ephemeral=True)
    else:
            await interaction.response.send_message(f'{user.name} は、不適切な単語を使用していません。', ephemeral=True)


@bot.tree.command(name="word_everyone_open", description=f"全員の不適切な言葉をいった回数を全員に表示させます")
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
        
@bot.tree.command(name="word_specific_open", description=f"特定のユーザーの不適切な言葉をいった回数を全員に表示させます")
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

@bot.tree.command(name="word_everyone_hide", description=f"特定のユーザーの不適切な言葉をいった回数をあなたにだけ表示させます")
async def word_everyone_hide(interaction: discord.Interaction):
    member = interaction.user
    guild = interaction.guild
    sorted_counts = sorted(user_word_counts.items(), key=lambda item: item[1], reverse=True)
    if sorted_counts:
            result = "\n".join(f"{guild.get_member(item[0]).name}: {item[1]} 回" for item in sorted_counts)
            await interaction.response.send_message(f"不適切な単語の使用回数 (多い順):\n{result}", ephemeral=True)
    else:
            await interaction.response.send_message("まだ不適切な単語の使用はありません。", ephemeral=True)

@bot.tree.command(name="word_set_count", description=f"特定のユーザーの不適切な言葉の使用回数を設定します")
async def word_set_count(interaction: discord.Interaction, user: discord.Member, count: int):
    if interaction.user.id != 1212687868603007067:
        await interaction.response.send_message('このコマンドを実行する権限がありません。', ephemeral=True)
        return

    # 指定したユーザーの不適切な単語使用回数を設定
    if count >= 0:
        user_word_counts[user.id] = count

    # レスポンスの送信
    await interaction.response.send_message(f'{user.name} の不適切な単語使用回数を {count} に設定しました。', ephemeral=True)

@bot.event
async def on_member_update(before, after):
    global nick_edit_in_progress

    # ニックネームが変更されたかを確認
    if before.nick != after.nick:
        guild = after.guild

        # BOTが変更をしている場合は無視
        if after.id in nick_edit_in_progress:
            return

        # 最新の監査ログを取得 (アクションが「ニックネーム変更」であるもの)
        async for entry in guild.audit_logs(limit=1, action=discord.AuditLogAction.member_update):
            # 変更された対象が本人でなく、ボットでもないかを確認
            if entry.target.id == after.id and entry.user.id != after.id and entry.user.id != BOT_ID:
                # 許可されたユーザーか確認
                if entry.user.id not in ALLOWED_USERS:
                    # 元のニックネームを取得
                    original_nickname = before.nick if before.nick else before.name
                    original_nicknames[before.id] = original_nickname

                    # ニックネーム変更中のユーザーを記録
                    nick_edit_in_progress.add(after.id)
                    
                    # 元のニックネームに戻す
                    try:
                        await after.edit(nick=original_nicknames[before.id])
                        print(f'{entry.user} が {after.name} のニックネームを変更しましたが、元のニックネームに戻しました。')
                    except discord.Forbidden:
                        print(f'{after.name} のニックネームを戻す権限がありません')
                    except discord.HTTPException as e:
                        print(f'ニックネームを戻す際にエラーが発生しました: {e}')
                    finally:
                        # ニックネーム変更が完了したらフラグを解除
                        nick_edit_in_progress.remove(after.id)


@bot.event
async def on_message(message):
    global channel_pairs, user_word_counts, respond_words
    if message.author == bot.user:
        return

    # メッセージ内のリンクを検出
    message_link_pattern = re.compile(r'https://discord.com/channels/(\d+)/(\d+)/(\d+)')
    match = message_link_pattern.search(message.content)

    if match:
        guild_id = int(match.group(1))
        channel_id = int(match.group(2))
        message_id = int(match.group(3))

        # メッセージを取得
        guild = bot.get_guild(guild_id)
        if guild:
            channel = guild.get_channel(channel_id)
            if channel:
                try:
                    target_message = await channel.fetch_message(message_id)
                        # メッセージリンクのURLを作成
                    message_link = f"https://discord.com/channels/{guild_id}/{channel_id}/{message_id}"

                        # 埋め込みメッセージを作成
                    embed = discord.Embed(
                        description=f"{target_message.content}\nFrom {channel.mention}",
                        color=discord.Color.blue(),
                        timestamp=target_message.created_at
                        )
                    author_avatar_url = target_message.author.display_avatar.url
                    embed.set_author(name=target_message.author.display_name, icon_url=author_avatar_url)

                    # 画像添付ファイルを追加
                    for attachment in target_message.attachments:
                        embed.set_image(url=attachment.url)

                    # メッセージリンクを追加
                    button = discord.ui.Button(label="メッセージ先はこちら", url=message_link)
                    view = discord.ui.View()
                    view.add_item(button)

                    await message.channel.send(embed=embed, view=view)

                except discord.NotFound:
                    await message.channel.send('メッセージが見つかりませんでした。')
                except discord.Forbidden:
                    await message.channel.send('メッセージを表示する権限がありません。')
                except discord.HTTPException as e:
                    await message.channel.send(f'メッセージの取得に失敗しました: {e}')

    # メッセージ転送の処理
    if message.channel.id in channel_pairs and not message.author.bot:
        destination_channel_id = channel_pairs[message.channel.id]
        destination_channel = bot.get_channel(destination_channel_id)
        if destination_channel:
            await destination_channel.send(message.content)

    # 不適切な言葉の処理
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

    # 自動返信
    response = custom_replies.get(message.content)
    if response:
        await message.reply(response)

    await bot.process_commands(message)

    # 「r!test」が送信された場合に「あ」と返す
    if message.content == "b!test" or message.content == "h!test":
        await message.channel.send("GitHubで起動されています")

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

class MyClient(discord.Client):
    async def on_ready(self):
        print(f'Logged in as {self.user} (ID: {self.user.id})')
        await self.update_all_channel_names()

    async def update_all_channel_names(self):
        guild = discord.utils.get(self.guilds)
        all_online = True  # 全てのBOTがオンラインかどうか

        for bot_id, info in BOT_CHANNEL_MAP.items():
            target_bot = guild.get_member(bot_id)
            channel = guild.get_channel(info["channel_id"])
            base_name = info["base_name"]

            if target_bot:
                status = target_bot.status
                if status == discord.Status.online:
                    new_name = f"🟢{base_name}"
                else:
                    new_name = f"🔴{base_name}"
                    all_online = False  # いずれかのBOTがオフライン

                # チャンネル名が異なる場合のみ変更
                if channel and channel.name != new_name:
                    await channel.edit(name=new_name)
                    print(f"チャンネル名を '{new_name}' に変更しました。")

        # いずれかのBOTがオフラインの場合にYELLOW_CHANNELを🟡にする
        yellow_channel = guild.get_channel(YELLOW_CHANNEL_ID)
        if yellow_channel:
            if not all_online:
                new_name = f"🟡{YELLOW_CHANNEL_BASE_NAME}"
            else:
                new_name = f"🟢{YELLOW_CHANNEL_BASE_NAME}"  # 全てオンラインなら🟢

            # YELLOW_CHANNELの名前を更新
            if yellow_channel.name != new_name:
                await yellow_channel.edit(name=new_name)
                print(f"チャンネル名を '{new_name}' に変更しました。（Yellow Channel）")

    async def on_presence_update(self, before, after):
        if after.id in BOT_CHANNEL_MAP:  # ターゲットBOTの状態が変わったとき
            await self.update_all_channel_names()

async def send_update_message():
    update_id = 1258593677748736120
    user_id = 1212687868603007067  # bakabonnpapa のユーザーID を設定する
    user = await bot.fetch_user(user_id)
    update = await bot.fetch_channel(update_id)
    await user.send("アップデートしました!!")
    await update.send("アップデートしました!!")

# Discordボットの起動とHTTPサーバーの起動
try:
    keep_alive()
    bot.run(TOKEN)
except Exception as e:
    print(f'エラーが発生しました: {e}')
