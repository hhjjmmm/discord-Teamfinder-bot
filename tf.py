import discord
from discord import app_commands
from discord.ext import commands, tasks
import asyncio
import os
from dotenv import load_dotenv

# .env 파일 로드
load_dotenv()

# 환경 변수 가져오기
DISCORD_TOKEN = os.getenv("DISCORD_TOKEN")
TARGET_CHANNEL_IDS = [int(x) for x in os.getenv("TARGET_CHANNEL_IDS").split(",")]

intents = discord.Intents.default()
intents.message_content = True  # 메시지 읽기 권한 활성화
intents.voice_states = True  # 음성 상태 권한 활성화

bot = commands.Bot(command_prefix="!", intents=intents)

ANNOUNCEMENT_INTERVAL = 30 * 60  # 30분 (단위: 초)
announcements = {channel_id: [] for channel_id in TARGET_CHANNEL_IDS}  # 채널별 메시지 관리


@bot.event
async def on_ready():
    try:
        await bot.tree.sync()  # 모든 서버에 슬래시 명령어 강제 동기화
        print("슬래시 명령어가 모든 서버에 동기화되었습니다.")
    except Exception as e:
        print(f"명령어 동기화 실패: {e}")
    print(f"{bot.user}로 로그인되었습니다.")

    if not announcement_task.is_running():
        announcement_task.start()


@bot.tree.command(name="청소", description="명령어를 사용한 사용자의 메시지를 삭제합니다.")
async def 청소(interaction: discord.Interaction):
    # 메시지 관리 권한 확인
    if not interaction.channel.permissions_for(interaction.user).manage_messages:
        await interaction.response.send_message("이 명령어를 사용할 권한이 없습니다.", ephemeral=True)
        return

    # 메시지 삭제 시작 알림
    await interaction.response.send_message("내 메시지를 삭제 중입니다...", ephemeral=True)

    deleted_count = 0
    async for message in interaction.channel.history(limit=None):  # 채널 내 모든 메시지 가져오기
        if message.author == interaction.user:  # 명령어를 사용한 사용자와 메시지 작성자가 동일한지 확인
            try:
                await message.delete()
                deleted_count += 1
                if deleted_count % 20 == 0:  # 초당 20개 삭제 제한
                    await asyncio.sleep(1)
            except discord.Forbidden:
                print(f"삭제할 수 없는 메시지: {message.content}")
            except discord.HTTPException as e:
                print(f"메시지 삭제 실패: {e}")

    # 삭제 완료 메시지
    if deleted_count > 0:
        await interaction.followup.send(f"메시지 {deleted_count}개를 삭제했습니다.", ephemeral=True)
    else:
        await interaction.followup.send("삭제할 메시지가 없습니다.", ephemeral=True)


@bot.tree.command(name="팀", description="팀원 모집 메시지를 작성합니다.")
async def 팀(interaction: discord.Interaction, 내용: str = "설명 없음"):
    if interaction.user.voice:
        channel = interaction.user.voice.channel
        channel_link = f"https://discord.com/channels/{interaction.guild.id}/{channel.id}"
        embed = discord.Embed(
            title="팀원 모집",
            description=f"{interaction.user.mention} 님이 팀원 모집 중입니다.\n[음성 채널로 이동]({channel_link})",
            color=0x00ff00
        )
        embed.add_field(name="카테고리", value="일반", inline=True)
        embed.add_field(name="채널명", value=f"{channel.name}", inline=True)
        embed.add_field(name="멤버", value=f"{len(channel.members)}/{channel.user_limit if channel.user_limit else '제한 없음'}", inline=True)
        embed.add_field(name="내용", value=내용, inline=False)
        view = discord.ui.View()
        button = discord.ui.Button(label="음성 채널 입장", url=channel_link)
        view.add_item(button)
        await interaction.response.send_message(embed=embed, view=view)
    else:
        await interaction.response.send_message(f"{interaction.user.mention} 님은 음성 채널에 입장해 있지 않습니다.")


@tasks.loop(seconds=ANNOUNCEMENT_INTERVAL)
async def announcement_task():
    global announcements
    for channel_id in TARGET_CHANNEL_IDS:
        channel = bot.get_channel(channel_id)
        if channel is None:
            print(f"Channel with ID {channel_id} not found. Skipping.")
            continue
        embed = discord.Embed(
            title="자동 공지",
            description="1. 초대 하고자하는 음성 채널 입장\n"
                        "2. 모집 채널에서 /팀 모집 내용or설명 - 참가해있는 음성채널로 팀원 모집글을 올립니다\n"
                        "/팀 << 명령어를 사용하여 모집하여주세요.",
            color=0xff0000
        )
        embed.add_field(name="필독", value="이 서버 외 게임활동 적발시 처벌", inline=False)
        message = await channel.send(embed=embed)
        announcements[channel_id].append(message)
        if len(announcements[channel_id]) > 1:
            old_message = announcements[channel_id].pop(0)
            await old_message.delete()


bot.run(DISCORD_TOKEN)