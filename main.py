import discord
import os
from discord import app_commands
from discord.ext import commands
from keep_alive import keep_alive

intents = discord.Intents.default()
intents.message_content = True

bot = commands.Bot(command_prefix='!', intents=intents)

# 応答する単語リスト
respond_words = []

# 役職の名前を設定（あなたのDiscordサーバーでの役職名に置き換えてください）
role_name = "Lounge staff"

@bot.event
async def on_ready():
    print(f'We have logged in as {bot.user}')
    try:
        synced = await bot.tree.sync()
        print(f'Synced {len(synced)} commands')
    except Exception as e:
        print(f'Error syncing commands: {e}')

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
        await interaction.response.send_message(f'現在の応答単語リスト:\n{words_str}')
    else:
        await interaction.response.send_message('現在、応答単語は登録されていません。')

@bot.event
async def on_message(message):
    if message.author == bot.user:
        return

    for word in respond_words:
        if word in message.content:
            await message.reply(f'({word})という言葉は不適切です。禁止単語リストに含まれています。({word})とは送らないようにしましょう')
            break

    await bot.process_commands(message)

keep_alive()
bot.run(os.getenv('DISCORD_TOKEN'))
