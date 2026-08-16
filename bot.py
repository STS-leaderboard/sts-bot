import discord
from discord import app_commands
from discord.ext import commands
import os
from datetime import datetime

# ─── CONFIG ───
TESTER_ROLE_NAMES = ["Tester", "Testers", "Staff", "Admin", "Owner"]
KITS = ["Sword", "Axe", "Mace", "UHC", "Nethpot", "Diapot", "DiaSMP", 
        "Minecart", "NethSMP", "Shieldless UHC", "Spear", "Crystal", "Axe/Shield"]
REGIONS = ["AS", "NA", "EU"]

intents = discord.Intents.default()
intents.message_content = True
intents.members = True

bot = commands.Bot(command_prefix="!", intents=intents)
tree = bot.tree

# ─── STORAGE ───
queues = {}       # {kit: [user1, user2, ...]}
tickets = {}      # {channel_id: {"tester": tester_id, "player": player_id, "kit": kit}}

# ─── PERMISSION CHECK ───
def is_tester(interaction: discord.Interaction):
    if not interaction.user.guild:
        return False
    role_names = [r.name for r in interaction.user.roles]
    return any(r in role_names for r in TESTER_ROLE_NAMES)

async def tester_only(interaction: discord.Interaction):
    if not is_tester(interaction):
        await interaction.response.send_message("❌ **Only Testers can use this command!**", ephemeral=True)
        return False
    return True

# ─── ON READY ───
@bot.event
async def on_ready():
    await tree.sync()
    print(f"✅ Logged in as {bot.user} — ALL COMMANDS SYNCED!")

# ─── 1️⃣ /startqueue ───
@tree.command(name="startqueue", description="Start a queue for a kit")
@app_commands.describe(kit="Choose a kit")
async def startqueue(interaction: discord.Interaction, kit: str):
    if not await tester_only(interaction):
        return

    if kit not in KITS:
        return await interaction.response.send_message(f"❌ Invalid kit! Choose: {', '.join(KITS)}", ephemeral=True)

    queues[kit] = []

    embed = discord.Embed(title=f"🔔 {kit} Testing Queue — JOIN BELOW", color=discord.Color.gold())
    embed.description = "Click **✅ Join** to enter queue\nClick **❌ Leave** to exit\n\n**Current Queue:**\n*Empty*"

    class QueueView(discord.ui.View):
        def __init__(self):
            super().__init__(timeout=None)

        @discord.ui.button(label="✅ Join", style=discord.ButtonStyle.green, custom_id=f"join_{kit}")
        async def join_btn(self, i: discord.Interaction, b: discord.ui.Button):
            if i.user.id in queues[kit]:
                return await i.response.send_message("❌ You're already in queue!", ephemeral=True)
            queues[kit].append(i.user.id)
            await i.channel.send(f"✅ **{i.user.mention} joined the queue!**", delete_after=10)
            await i.response.send_message(f"✅ You joined {kit} queue!", ephemeral=True)
            await update_queue_display(i.channel, kit)

        @discord.ui.button(label="❌ Leave", style=discord.ButtonStyle.red, custom_id=f"leave_{kit}")
        async def leave_btn(self, i: discord.Interaction, b: discord.ui.Button):
            if i.user.id not in queues[kit]:
                return await i.response.send_message("❌ You're not in queue!", ephemeral=True)
            queues[kit].remove(i.user.id)
            await i.channel.send(f"👋 **{i.user.mention} left the queue!**", delete_after=10)
            await i.response.send_message("👋 You left the queue.", ephemeral=True)
            await update_queue_display(i.channel, kit)

    async def update_queue_display(channel, kit):
        qlist = queues.get(kit, [])
        desc = ""
        if not qlist:
            desc = "*Empty*"
        else:
            for idx, uid in enumerate(qlist, 1):
                desc += f"{idx}. <@{uid}>\n"
        embed.description = f"Click **✅ Join** to enter queue\nClick **❌ Leave** to exit\n\n**Current Queue:**\n{desc}"
        await channel.edit(embed=embed)

    await interaction.response.send_message(embed=embed, view=QueueView())

# ─── 2️⃣ /endqueue ───
@tree.command(name="endqueue", description="Close the current queue")
async def endqueue(interaction: discord.Interaction):
    if not await tester_only(interaction):
        return
    queues.clear()
    await interaction.response.send_message("🔒 **Queue Closed!**", ephemeral=False)

# ─── 3️⃣ /nextplayer ───
@tree.command(name="nextplayer", description="Move to next player in queue")
async def nextplayer(interaction: discord.Interaction):
    if not await tester_only(interaction):
        return
    if not queues:
        return await interaction.response.send_message("❌ No active queue!", ephemeral=True)

    kit = next(iter(queues.keys()))
    if not queues[kit]:
        return await interaction.response.send_message("❌ Queue is empty!", ephemeral=True)

    first = queues[kit].pop(0)
    await interaction.response.send_message(f"▶️ **Next Up: <@{first}> — {kit} Testing!**")

# ─── 4️⃣ /create ───
@tree.command(name="create", description="Create a test ticket channel")
@app_commands.describe(user="Mention the player", kit="Choose a kit")
async def create_ticket(interaction: discord.Interaction, user: discord.Member, kit: str):
    if not await tester_only(interaction):
        return

    if kit not in KITS:
        return await interaction.response.send_message(f"❌ Invalid kit! Choose: {', '.join(KITS)}", ephemeral=True)

    channel_name = f"sts-{kit.lower().replace(' ', '-')}-{user.name}".replace("/", "-")

    overwrites = {
        interaction.guild.default_role: discord.PermissionOverwrite(view_channel=False),
        interaction.user: discord.PermissionOverwrite(view_channel=True, send_messages=True),
        user: discord.PermissionOverwrite(view_channel=True, send_messages=True),
    }

    channel = await interaction.guild.create_text_channel(
        name=channel_name,
        overwrites=overwrites,
        reason=f"Test Ticket — {kit}"
    )

    tickets[channel.id] = {
        "tester": interaction.user.id,
        "player": user.id,
        "kit": kit
    }

    class CloseView(discord.ui.View):
        def __init__(self):
            super().__init__(timeout=None)

        @discord.ui.button(label="🔒 Close Testing", style=discord.ButtonStyle.danger, custom_id="close_ticket")
        async def close_btn(self, i: discord.Interaction, b: discord.ui.Button):
            ticket = tickets.get(i.channel.id)
            if not ticket or i.user.id != ticket["tester"]:
                return await i.response.send_message("❌ **Only the Tester can close this ticket!**", ephemeral=True)
            await i.channel.delete(reason="Ticket Closed")

    embed = discord.Embed(color=discord.Color.dark_theme())
    embed.description = f"""
{user.mention} Testing!
--------------------------------------------------------
**Tester:** {interaction.user.mention}
**Player:** {user.mention}
--------------------------------------------------------
Please enjoy Your Testing And Have fun!
--------------------------------------------------------
"""
    await channel.send(embed=embed, view=CloseView())
    await interaction.response.send_message(f"✅ Ticket Created! → {channel.mention}", ephemeral=True)

# ─── 5️⃣ /result ───
@tree.command(name="result", description="Post test results")
@app_commands.describe(
    player="Mention the player",
    tester="Mention the tester",
    region="Region",
    username="Minecraft Username",
    oldtier="Previous Tier",
    nowtier="New Tier Earned"
)
async def result(
    interaction: discord.Interaction,
    player: discord.Member,
    tester: discord.Member,
    region: app_commands.Choice[str],
    username: str,
    oldtier: str,
    nowtier: str
):
    if not await tester_only(interaction):
        return

    ticket = tickets.get(interaction.channel.id)
    if not ticket:
        return await interaction.response.send_message("❌ **No open ticket here! Use this command inside the player's ticket channel only.**", ephemeral=True)
    if ticket["tester"] != interaction.user.id:
        return await interaction.response.send_message("❌ **Only the assigned Tester can post results!**", ephemeral=True)

    kit = ticket["kit"]
    embed = discord.Embed(
        title=f"🏆 {username}'s Test Results",
        color=discord.Color.red(),
        timestamp=datetime.utcnow()
    )
    embed.set_thumbnail(url=f"https://mc-heads.net/avatar/{username}/100.png")
    embed.add_field(name="Tester", value=f"{tester.mention}", inline=False)
    embed.add_field(name="Kit", value=kit, inline=False)
    embed.add_field(name="Region", value=region.value, inline=False)
    embed.add_field(name="Username", value=f"`{username}`", inline=False)
    embed.add_field(name="Previous Tier", value=f"`{oldtier}`", inline=False)
    embed.add_field(name="Rank Earned", value=f"`{nowtier}`", inline=False)

    await interaction.response.send_message(embed=embed)

# ─── RUN BOT ───
TOKEN = os.getenv("BOT_TOKEN")
if not TOKEN:
    print("⚠️ BOT_TOKEN not found! Set it in Environment Variables.")
else:
    bot.run(TOKEN)
