import discord
from discord.ext import commands, tasks
from discord import app_commands
import json
import os
import traceback
import logging
import datetime
from datetime import timezone, timedelta
from flask import Flask
import threading
import requests

# ====== 基本設定 ======
logging.basicConfig(level=logging.INFO)

TOKEN = os.environ.get("DISCORD_TOKEN")
REVIEW_CHANNEL_FILE = "review_channel.json"

if not TOKEN:
    raise ValueError("[ERROR] 找不到 DISCORD_TOKEN，請在 Render 環境變數中設定。")

# ====== Discord Bot ======
intents = discord.Intents.default()
intents.message_content = True
intents.guilds = True
bot = commands.Bot(command_prefix="!", intents=intents)

# ====== 評價頻道設定 ======
review_channels = {}
if os.path.exists(REVIEW_CHANNEL_FILE):
    try:
        with open(REVIEW_CHANNEL_FILE, "r", encoding="utf-8") as f:
            review_channels = json.load(f)
    except Exception:
        print("[ERROR] 載入評價頻道失敗。")
        traceback.print_exc()

def save_review_channel(guild_id, channel_id):
    review_channels[str(guild_id)] = channel_id
    try:
        with open(REVIEW_CHANNEL_FILE, "w", encoding="utf-8") as f:
            json.dump(review_channels, f, ensure_ascii=False, indent=2)
    except Exception:
        print("[ERROR] 保存評價頻道失敗。")
        traceback.print_exc()

# ====== Bot 事件 ======
TEST_GUILD_ID = int(os.environ.get("TEST_GUILD_ID", 0))

@bot.event
async def on_ready():
    try:
        if TEST_GUILD_ID:
            guild = discord.Object(id=TEST_GUILD_ID)
            await bot.tree.sync(guild=guild)
            print(f"[INFO] 已登入 {bot.user}，指令同步到測試伺服器 {TEST_GUILD_ID}")
        else:
            await bot.tree.sync()
            print(f"[INFO] 已登入 {bot.user}，全域指令同步完成")
    except Exception:
        traceback.print_exc()

# ====== 評價系統 ======
class ReviewModal(discord.ui.Modal, title="提交評價"):
    def __init__(self, target_user: discord.User, messages_to_delete: list):
        super().__init__()
        self.target_user = target_user
        self.messages_to_delete = messages_to_delete

        self.product = discord.ui.TextInput(
            label="購買商品名稱",
            style=discord.TextStyle.short,
            placeholder="請輸入商品名稱",
            max_length=50
        )
        self.rating = discord.ui.TextInput(
            label="評分（1-5）",
            style=discord.TextStyle.short,
            placeholder="請輸入 1 到 5",
            max_length=1
        )
        self.feedback = discord.ui.TextInput(
            label="評語",
            style=discord.TextStyle.paragraph,
            placeholder="寫點評語吧...",
            max_length=100
        )

        self.add_item(self.product)
        self.add_item(self.rating)
        self.add_item(self.feedback)

    async def on_submit(self, interaction: discord.Interaction):
        if interaction.user.id != self.target_user.id:
            await interaction.response.send_message("❌ 你不是評價對象，無法提交。", ephemeral=True)
            return

        try:
            guild_id = str(interaction.guild.id)
            channel_id = review_channels.get(guild_id)
            if not channel_id:
                await interaction.response.send_message("❌ 尚未設定評價頻道。", ephemeral=True)
                return

            channel = bot.get_channel(channel_id)
            if channel is None:
                await interaction.response.send_message("❌ 找不到評價頻道。", ephemeral=True)
                return

            try:
                rating_val = int(self.rating.value.strip())
            except ValueError:
                await interaction.response.send_message("❌ 評分格式錯誤，請輸入 1 到 5 的整數。", ephemeral=True)
                return

            if rating_val < 1 or rating_val > 5:
                await interaction.response.send_message("❌ 評分需為 1 到 5。", ephemeral=True)
                return

            star_emoji = "⭐"
            empty_star_emoji = "☆"
            stars = star_emoji * rating_val + empty_star_emoji * (5 - rating_val)

            now = datetime.datetime.now(timezone(timedelta(hours=8)))
            time_str = now.strftime("%Y-%m-%d %H:%M:%S")

            embed = discord.Embed(
                title=f"📝 新的商品評價 - {self.product.value}",
                description=f"來自：{interaction.user.mention}",
                color=discord.Color.blurple(),
                timestamp=now
            )
            embed.add_field(name="商品", value=self.product.value, inline=False)
            embed.add_field(name="評分", value=f"{stars} (`{rating_val}/5`)", inline=False)
            embed.add_field(name="評價內容", value=self.feedback.value or "（使用者未留下內容）", inline=False)
            embed.add_field(name="時間", value=time_str, inline=False)
            embed.set_author(name=interaction.user.display_name, icon_url=interaction.user.display_avatar.url)
            embed.set_footer(text="感謝您的回饋！")

            await channel.send(embed=embed)
            await interaction.response.send_message(f"✅ 你的評價已提交到 {channel.mention}", ephemeral=True)

            for msg in self.messages_to_delete:
                try:
                    await msg.delete()
                except Exception:
                    pass

            await interaction.channel.send("## 💕 感謝您的評價！您的回饋對我們非常重要～ 歡迎再次回來逛逛！")

        except Exception:
            traceback.print_exc()
            await interaction.response.send_message("❌ 評價提交失敗，請稍後再試。", ephemeral=True)

# ====== 設定評價頻道 ======
@bot.tree.command(name="setreviewchannel", description="設定評價發送頻道（管理員限定）")
@app_commands.checks.has_permissions(administrator=True)
async def setreviewchannel(interaction: discord.Interaction, channel: discord.TextChannel):
    try:
        await interaction.response.defer(thinking=True)
        save_review_channel(interaction.guild.id, channel.id)
        embed = discord.Embed(
            title="✅ 設定成功",
            description=f"已設定評價頻道為 {channel.mention}",
            color=discord.Color.green(),
            timestamp=datetime.datetime.now(timezone(timedelta(hours=8)))
        )
        embed.set_author(name=interaction.user.display_name, icon_url=interaction.user.display_avatar.url)
        embed.set_footer(text="請確保機器人有頻道發言權限")
        await interaction.followup.send(embed=embed, ephemeral=True)
    except Exception:
        traceback.print_exc()
        await interaction.followup.send("❌ 設定頻道失敗，請稍後再試。", ephemeral=True)

# ====== 叫出評價介面 ======
@bot.tree.command(name="reviews", description="叫出評價介面（選擇一個人來填寫）")
@app_commands.describe(user="選擇要被評價的使用者")
async def reviews(interaction: discord.Interaction, user: discord.User):
    try:
        await interaction.response.defer()
        messages_to_delete = []

        msg1 = await interaction.channel.send(f"{user.mention} 麻煩幫我點擊下方按鈕來填寫評價~")
        messages_to_delete.append(msg1)

        view = discord.ui.View(timeout=180)
        button = discord.ui.Button(label="填寫評價", style=discord.ButtonStyle.success)

        async def button_callback(btn_interaction: discord.Interaction):
            if btn_interaction.user.id != user.id:
                await btn_interaction.response.send_message("❌ 你不是評價對象，無法填寫。", ephemeral=True)
                return
            await btn_interaction.response.send_modal(ReviewModal(user, messages_to_delete))

        button.callback = button_callback
        view.add_item(button)

        embed = discord.Embed(
            title="📝 評價系統",
            description=f"只有 {user.mention} 可以點擊下方按鈕來填寫評價。",
            color=discord.Color.purple(),
            timestamp=datetime.datetime.now(timezone(timedelta(hours=8)))
        )

        msg2 = await interaction.channel.send(embed=embed, view=view)
        messages_to_delete.append(msg2)

    except Exception:
        traceback.print_exc()
        await interaction.followup.send("❌ 發送評價介面失敗。", ephemeral=True)

# ====== Minimal Web Server + Keep Alive ======
app = Flask("")

@app.route("/")
def home():
    return "Bot is running!"

def run_web():
    port = int(os.environ.get("PORT", 10000))
    app.run(host="0.0.0.0", port=port)

@tasks.loop(minutes=5)
async def keep_alive():
    url = os.environ.get("RENDER_EXTERNAL_URL")
    if url:
        try:
            requests.get(url, timeout=5)
            print("[INFO] Ping Render Web Server to keep alive.")
        except Exception:
            pass

@bot.event
async def on_connect():
    if not keep_alive.is_running():
        keep_alive.start()

# ====== 啟動 Bot 與 Web Server ======
if __name__ == "__main__":
    threading.Thread(target=run_web, daemon=True).start()
    bot.run(TOKEN)
