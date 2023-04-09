from config import *
from csgo.client import CSGOClient
from discord import app_commands
from steam.steamid import SteamID
from steam.client import SteamClient
from csgo.enums import ECsgoGCMsg
import asyncio
import DatabaseManager
import discord
import os
import requests
import time
import csgo

steam_client = SteamClient()
csgo_client = CSGOClient(steam_client)

discord_intents = discord.Intents.default()
discord_client = discord.Client(intents=discord_intents)
discord_client.sync_tree = DISCORD_SYNC_TREE
command_tree = app_commands.CommandTree(discord_client)
update_channel = None

database = DatabaseManager.DatabaseManager(DATABASE_PATH)

async def check_owner(interaction):
	if OWNER_ONLY_MODE and interaction.user.id != discord_client.application.owner.id:
		raise Exception("Trying to run command as non-owner in owner-only mode.")

def steam_login():
	if steam_client.logged_on: 
		return

	if not os.path.exists(CREDENTIALS_LOCATION):
		os.makedirs(CREDENTIALS_LOCATION)
	steam_client.set_credential_location(CREDENTIALS_LOCATION)

	if steam_client.relogin_available: 
		steam_client.relogin()
	elif steam_client.login_key is not None: 
		steam_client.login(username=STEAM_USERNAME, login_key=steam_client.login_key)
	else: 
		steam_client.cli_login(username=STEAM_USERNAME, password=STEAM_PASSWORD)

def get_user_name_and_avatar(steam_id, api_key):
	params = {
		"key": api_key,
		"steamids": steam_id
	}

	response = requests.get("https://api.steampowered.com/ISteamUser/GetPlayerSummaries/v0002/", params=params)
	response.raise_for_status()

	json = response.json()
	for player in json["response"]["players"]:
		if player["steamid"] != str(steam_id):
			continue
		return player["personaname"], player["avatarfull"]

	raise Exception("Could't get user name or avatar")

def launch_csgo():
	if csgo_client.connection_status == csgo.enums.GCConnectionStatus.NO_SESSION:
		print("NO_SESSION: Logging in and launching CS:GO again.")
		steam_login()
		csgo_client.launch()

def get_user_level_and_xp(steam_id):
	launch_csgo()
	inspect_params = { "account_id": SteamID(steam_id).as_32, "request_level": 32 }
	
	for i in range(5):
		csgo_client.send(ECsgoGCMsg.EMsgGCCStrike15_v2_ClientRequestPlayersProfile, inspect_params)
		response = csgo_client.wait_event(ECsgoGCMsg.EMsgGCCStrike15_v2_PlayersProfile, timeout=10)
		if response is not None:
			break

	if response is None:
		raise Exception("CS:GO sent an empty response.")

	profile = response[0].account_profiles[0]
	return profile.player_level, max(0, profile.player_cur_xp - 327680000)

@steam_client.on("logged_on")
def steam_logged_on():
	print(f"Logged in as {steam_client.user.steam_id} ({steam_client.user.name})")

async def steam_idle():
	while True:
		steam_client.idle()
		await asyncio.sleep(.1)

async def send_update(user, level, xp):
	global update_channel

	name = str(user.steam_id)
	avatar = ""

	try:
		name, avatar = get_user_name_and_avatar(user.steam_id, STEAM_API_KEY)
	except:
		pass

	embed = discord.Embed(
		title=f"{name}'s XP changed",
		url=f"https://steamcommunity.com/profiles/{user.steam_id}"
	)

	embed.set_thumbnail(url=avatar)

	if user.current_level != level:
		embed.add_field(name="Level change", value=f"was: *{user.current_level}*\nnow: *{level}*", inline=False)

	if user.current_xp != xp:
		embed.add_field(name="XP change", value=f"was: *{user.current_xp}*\nnow: *{xp}*", inline=False)

	await update_channel.send(embed=embed)

async def check_tracking():
	users = database.get_users()
	
	for user in users:
		for i in range(3):
			try:
				level, xp = get_user_level_and_xp(user.steam_id)
			except Exception as e:
				print(f"Error checking tracking: {e}")
				continue
			if level != user.current_level or xp != user.current_xp:
				await send_update(user, level, xp)
				database.update_user_level_and_xp(user.steam_id, level, xp)
			else:
				print(f"No change for {user.steam_id}")
			break

async def check_tracking_loop():
	while True:
		await check_tracking()
		await asyncio.sleep(CHECK_TIMEOUT)

@discord_client.event
async def on_ready():
	global update_channel

	update_channel = discord_client.get_channel(DISCORD_UPDATE_CHANNEL)
	if update_channel is None:
		print(f"Couldn't find channel {DISCORD_UPDATE_CHANNEL}. Quitting.")
		os._exit(1)

	discord_client.loop.create_task(steam_idle())
	discord_client.loop.create_task(check_tracking_loop())
	steam_login()

	if discord_client.sync_tree:
		print(f"Synchronizing command tree...")
		await command_tree.sync()
		discord_client.sync_tree = False

	print(f"Ready")

@command_tree.command(description="Add a user to track")
@app_commands.describe(steam_id="SteamID64 of user you want to track")
async def add_user(interaction, steam_id: str):
	await interaction.response.defer()

	try:
		await check_owner(interaction)
	except Exception as e:
		await interaction.followup.send(e)
		return

	try:
		steam_id = int(steam_id)
		if steam_id <= 0x0110000100000000 or steam_id > 0x01100001FFFFFFFF:
			raise Exception("Steam ID is outside ID64 range.")
	except Exception as e:
		await interaction.followup.send(f"`{steam_id}` is not a valid Steam ID.\n{e}")
		return

	if database.get_user_by_steam_id(steam_id) is not None:
		await interaction.followup.send(f"User `{steam_id}` is already being tracked.")
		return

	try:
		level, xp = get_user_level_and_xp(steam_id)
	except Exception as e:
		await interaction.followup.send(f"Couldn't get level and XP for `{steam_id}`. Not tracking user.\n{e}")
		return

	try:
		name, avatar = get_user_name_and_avatar(steam_id, STEAM_API_KEY)
	except Exception as e:
		await interaction.followup.send(f"Couldn't get name and avatar for `{steam_id}`. Not tracking user.\n{e}")
		return

	try:
		database.add_user(steam_id, interaction.user.id, level, xp)
	except Exception as e:
		await interaction.followup.send(f"Couldn't add user.\n{e}")

	embed = discord.Embed(
		title=f"Added {name}",
		url=f"https://steamcommunity.com/profiles/{steam_id}"
	)

	embed.set_thumbnail(url=avatar)
	embed.add_field(name="Current level and XP", value=f"level {level}, {xp} XP")

	await interaction.followup.send(embed=embed)

@command_tree.command(description="Remove a user from tracking")
@app_commands.describe(steam_id="SteamID64 of user you want to remove (must be added by you)")
async def remove_user(interaction, steam_id: str):
	await interaction.response.defer()

	try:
		await check_owner(interaction)
	except Exception as e:
		await interaction.followup.send(e)
		return

	try:
		steam_id = int(steam_id)
		if steam_id <= 0x0110000100000000 or steam_id > 0x01100001FFFFFFFF:
			raise Exception("Steam ID is outside ID64 range.")
	except Exception as e:
		await interaction.followup.send(f"`{steam_id}` is not a valid Steam ID.\n{e}")
		return

	tracked_user = database.get_user_by_steam_id(steam_id)
	if tracked_user is None:
		await interaction.followup.send(f"User `{steam_id}` is not being tracked.")
		return

	if int(tracked_user.discord_id) != interaction.user.id:
		await interaction.followup.send(f"Can't delete a user that you didn't add. {type(tracked_user.discord_id)=} {type(interaction.user.id)=}")
		return

	try:
		database.remove_user(steam_id, interaction.user.id)
	except Exception as e:
		await interaction.followup.send(f"Could not remove user.\n{e}")

	await interaction.followup.send(f"Stopped tracking `{tracked_user.steam_id}`.")

if __name__ == "__main__":
	discord_client.run(DISCORD_TOKEN)