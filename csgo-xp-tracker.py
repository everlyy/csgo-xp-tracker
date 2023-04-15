from config import *
from csgo.client import CSGOClient
from csgo.enums import ECsgoGCMsg
from DiscordWebhook import DiscordWebhook, DiscordEmbed
from steam.client import SteamClient
from steam.steamid import SteamID
from TrackedUsers import TrackedUsers
from TrackingList import TrackingList
import csgo
import gevent
import os
import requests
import datetime

steam_client = SteamClient()
csgo_client = CSGOClient(steam_client)
tracking_list = TrackingList(TRACKING_LIST_PATH)
tracked_users = TrackedUsers()

webhook = DiscordWebhook(DISCORD_UPDATE_WEBHOOK)

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

def launch_csgo():
	if csgo_client.connection_status == csgo.enums.GCConnectionStatus.NO_SESSION:
		steam_login()
		csgo_client.launch()

def get_user_level_and_xp(steam_id):
	launch_csgo()

	inspect_params = { "account_id": SteamID(steam_id).as_32, "request_level": 32 }
	csgo_client.send(ECsgoGCMsg.EMsgGCCStrike15_v2_ClientRequestPlayersProfile, inspect_params)
	response = csgo_client.wait_event(ECsgoGCMsg.EMsgGCCStrike15_v2_PlayersProfile, timeout=5)

	if response is None:
		raise Exception("CS:GO sent an empty response.")

	profile = response[0].account_profiles[0]
	return profile.player_level, max(0, profile.player_cur_xp - 327680000)

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

	raise Exception(f"Could't find {steam_id} in response.")

def calculate_difference(now, previous, _max):
	difference = now - previous
	if difference < 0:
		difference += _max
	return difference

def user_xp_changed(tracked_user):
	if tracked_user.first_check:
		print(f"First change for {tracked_user.steam_id}. Not sending message.")
		return

	print(f"Change for {tracked_user.steam_id}. Sending message.")

	username = f"`{tracked_user.steam_id}`"
	avatar = ""

	try:
		username, avatar = get_user_name_and_avatar(tracked_user.steam_id, STEAM_API_KEY)
	except Exception as e:
		print(f"Could't get username and avatar for {tracked_user.steam_id}: {e}")
		pass

	embed = DiscordEmbed()
	embed.set_title(f"{username}'s XP Changed")
	embed.set_url(f"https://steamcommunity.com/profiles/{tracked_user.steam_id}")
	embed.set_thumbnail(avatar)
	embed.set_timestamp(datetime.datetime.utcnow().isoformat())

	if tracked_user.level != tracked_user.previous_level:
		level_difference = calculate_difference(tracked_user.level, tracked_user.previous_level, 40)
		embed.add_field(name="Level", value=f"Was: *{tracked_user.previous_level}*\nNow: *{tracked_user.level}*\nDifference: *{level_difference:+}*")
	else:
		embed.add_field(name="Level (unchanged)", value=f"Now: *{tracked_user.level}*")

	if tracked_user.xp != tracked_user.previous_xp:
		xp_difference = calculate_difference(tracked_user.xp, tracked_user.previous_xp, 5000)
		embed.add_field(name="XP", value=f"Was: *{tracked_user.previous_xp}*\nNow: *{tracked_user.xp}*\nDifference: *{xp_difference:+}*")
	else:
		embed.add_field(name="XP (unchanged)", value=f"Now: *{tracked_user.xp}*")

	webhook.send(embed=embed)

def check_user(steam_id):
	tracked_user = tracked_users.find_tracked_user_by_steam_id(steam_id)

	try:
		level, xp = get_user_level_and_xp(tracked_user.steam_id)
	except Exception as e:
		print(f"Couldn't get level and XP for {tracked_user.steam_id}: {e}")
		return

	print(f"Got level and xp for {steam_id}: {level=} {xp=}")
	tracked_user.update_level_and_xp(level, xp, user_xp_changed)

@steam_client.on("logged_on")
def steam_client_logged_on():
	print("Steam client logged on")
	csgo_client.launch()

@csgo_client.on("ready")
def csgo_client_ready():
	print("CS:GO client ready")

	embed = DiscordEmbed()
	embed.set_title("XP Tracker started")
	embed.add_field(name="Users", value=f"Tracking {len(tracking_list.get_tracking_list())} user(s)")
	embed.add_field(name="Checking", value=f"Checking every {CHECK_TIMEOUT} seconds")
	embed.set_timestamp(datetime.datetime.utcnow().isoformat())
	webhook.send(embed=embed)

	while True:
		for steam_id in tracking_list.get_tracking_list():
			print(f"Checking {steam_id}")
			check_user(steam_id)

		print(f"Next check in {CHECK_TIMEOUT} seconds.")
		gevent.sleep(CHECK_TIMEOUT)

if __name__ == "__main__":
	webhook.set_username(WEBHOOK_USERNAME)
	webhook.set_avatar_url(WEBHOOK_AVATAR_URL)

	steam_login()
	steam_client.run_forever()