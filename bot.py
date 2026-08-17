import discord
from discord.ext import commands
from discord import app_commands, ui, ButtonStyle
from datetime import datetime

intents = discord.Intents.default()
intents.message_content = True
intents.members = True

bot = commands.Bot(command_prefix="/", intents=intents)
active_queue = {}

@bot.event
async def on_ready():
    print(f"✅ LOGGED IN AS: {bot.user}")
    try:
        synced = await bot.tree.sync()
        print(f"✅ SYNCED {len(synced)} COMMANDS")
    except Exception as e:
        print(f"❌ ERROR: {e}")

@bot.tree.command(name="startqueue", description="Start test queue")
@app_commands.checks.has_permissions(administrator=True)
async def startqueue(interaction: discord.Interaction, kit: str):
    if kit in active_queue:
        await interaction.response.send_message("❌ Queue already active!", ephemeral=True)
        return
    active_queue[kit] = []
    embed = discord.Embed(title=f"📋 TEST QUEUE — {kit.upper()}", color=0xf5b83d)
    embed.description = "No one in queue yet!"
    view = ui.View(timeout=None)
    
    async def update_msg():
        desc = ""
        if len(active_queue[kit]) > 0:
            for i, u in enumerate(active_queue[kit], 1):
                desc += f"{i}. {u.mention}\n"
        else:
            desc = "No one in queue yet!"
        embed.description = desc
        await msg.edit(embed=embed)
    
    class JoinBtn(ui.Button):
        def __init__(self):
            super().__init__(label="✅ JOIN", style=ButtonStyle.green)
        async def callback(self, inter):
            if inter.user in active_queue[kit]:
                await inter.response.send_message("❌ Already in queue!", ephemeral=True)
                return
            active_queue[kit].append(inter.user)
            await update_msg()
            await inter.response.send_message("✅ Joined queue!", ephemeral=True)
    
    class LeaveBtn(ui.Button):
        def __init__(self):
            super().__init__(label="❌ LEAVE", style=ButtonStyle.red)
        async def callback(self, inter):
            if inter.user not in active_queue[kit]:
                await inter.response.send_message("❌ Not in queue!", ephemeral=True)
                return
            active_queue[kit].remove(inter.user)
            await update_msg()
            await inter.response.send_message("✅ Left queue!", ephemeral=True)
    
    view.add_item(JoinBtn())
    view.add_item(LeaveBtn())
    await interaction.response.send_message(embed=embed, view=view)
    msg = await interaction.original_response()

@bot.tree.command(name="create", description="Create test ticket")
@app_commands.checks.has_permissions(administrator=True)
async def create(interaction: discord.Interaction, user: discord.Member, kit: str):
    ch_name = f"sts-{kit}-{user.name[:8]}".lower()
    overwrites = {
        interaction.guild.default_role: discord.PermissionOverwrite(view_channel=False),
        user: discord.PermissionOverwrite(view_channel=True, send_messages=True),
        interaction.user: discord.PermissionOverwrite(view_channel=True, send_messages=True, manage_channels=True)
    }
    ch = await interaction.guild.create_text_channel(ch_name, overwrites=overwrites)
    emb = discord.Embed(title="⚔️ TESTING", color=0xf5b83d)
    emb.description = f"Tester: {interaction.user.mention}\nPlayer: {user.mention}\n\nEnjoy your testing!"
    
    class CloseBtn(ui.View):
        @ui.button(label="🔒 CLOSE", style=ButtonStyle.danger)
        async def close(self, inter, btn):
            if inter.user != interaction.user:
                await inter.response.send_message("❌ Only tester can close!", ephemeral=True)
                return
            await inter.channel.delete()
    
    await ch.send(f"{interaction.user.mention} {user.mention}", embed=emb, view=CloseBtn())
    await interaction.response.send_message(f"✅ Created: {ch.mention}", ephemeral=True)

@bot.tree.command(name="result", description="Submit test result")
@app_commands.checks.has_permissions(administrator=True)
async def result(interaction: discord.Interaction, player: discord.Member, tester: discord.Member, region: str, username: str, oldtier: str, nowtier: str):
    emb = discord.Embed(title="🏆 TEST RESULT", color=0x2ecc71, timestamp=datetime.now())
    emb.add_field(name="Player", value=player.mention, inline=True)
    emb.add_field(name="Tester", value=tester.mention, inline=True)
    emb.add_field(name="Region", value=region.upper(), inline=True)
    emb.add_field(name="Username", value=f"`{username}`", inline=False)
    emb.add_field(name="Old Tier", value=oldtier.upper(), inline=True)
    emb.add_field(name="New Tier", value=nowtier.upper(), inline=True)
    await interaction.response.send_message(embed=emb)

# ===== YOUR TOKEN IS ALREADY HERE! ✅ =====
TOKEN = "MTUzODUyNTY4ODM3MjUzNTI5Ng.GPKe8d.P7hchzpD1dcjugxNO44Uz7vFg_AbHVQLN0sqNQ"

bot.run(TOKEN)
        
