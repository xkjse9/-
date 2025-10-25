import discord
from discord.ext import commands
from discord import app_commands
import os

# ====== 基本設定 ======
intents = discord.Intents.default()
bot = commands.Bot(command_prefix="!", intents=intents)

# ====== 啟動訊息 ======
@bot.event
async def on_ready():
    print(f"✅ Bot 已登入為：{bot.user}")
    try:
        synced = await bot.tree.sync()
        print(f"🌐 已同步 {len(synced)} 個指令。")
    except Exception as e:
        print(f"❌ 指令同步失敗: {e}")

# ====== /reviews 指令 ======
@bot.tree.command(name="reviews", description="發送評價介面")
async def reviews(interaction: discord.Interaction):
    # 讓指令者只看到提示訊息（唯獨）
    await interaction.response.defer(ephemeral=True)

    # 建立 Embed
    embed = discord.Embed(
        title="🌟 請留下您的評價",
        description="請選擇您對機器人的評價：",
        color=discord.Color.blurple()
    )

    # 建立評價按鈕
    class ReviewView(discord.ui.View):
        def __init__(self):
            super().__init__(timeout=None)

        @discord.ui.button(label="⭐ 1 星", style=discord.ButtonStyle.secondary)
        async def one_star(self, interaction: discord.Interaction, button: discord.ui.Button):
            await interaction.response.send_message("您給了 **1 星** 🌟", ephemeral=True)

        @discord.ui.button(label="⭐⭐ 2 星", style=discord.ButtonStyle.secondary)
        async def two_star(self, interaction: discord.Interaction, button: discord.ui.Button):
            await interaction.response.send_message("您給了 **2 星** 🌟", ephemeral=True)

        @discord.ui.button(label="⭐⭐⭐ 3 星", style=discord.ButtonStyle.secondary)
        async def three_star(self, interaction: discord.Interaction, button: discord.ui.Button):
            await interaction.response.send_message("您給了 **3 星** 🌟", ephemeral=True)

        @discord.ui.button(label="⭐⭐⭐⭐ 4 星", style=discord.ButtonStyle.primary)
        async def four_star(self, interaction: discord.Interaction, button: discord.ui.Button):
            await interaction.response.send_message("您給了 **4 星** 🌟", ephemeral=True)

        @discord.ui.button(label="⭐⭐⭐⭐⭐ 5 星", style=discord.ButtonStyle.success)
        async def five_star(self, interaction: discord.Interaction, button: discord.ui.Button):
            await interaction.response.send_message("您給了 **5 星** 🌟，感謝支持！", ephemeral=True)

    # 發送公開的評價介面（所有人可見）
    channel = interaction.channel
    await channel.send(embed=embed, view=ReviewView())

    # 回覆指令者（只有他看得到）
    await interaction.followup.send("✅ 已送出評價介面。", ephemeral=True)


# ====== 啟動機器人 ======
TOKEN = os.getenv("DISCORD_TOKEN")  # Render 的環境變數中設定
bot.run(TOKEN)
