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

checking_loop_running = False

def steam_login():
	print(f"Logging in to Steam as {STEAM_USERNAME}")
	
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
	if DISABLE_STEAM_API:
		raise Exception("Steam API is disabled")

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
		XP_PER_LEVEL = 5000
		xp_difference = calculate_difference(tracked_user.xp, tracked_user.previous_xp, XP_PER_LEVEL)
		embed.add_field(name="XP", value=f"Was: *{tracked_user.previous_xp}*\nNow: *{tracked_user.xp}*\nDifference: *{xp_difference:+}*\nNeed *{XP_PER_LEVEL - tracked_user.xp}* XP for next level")
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

def get_tracking_list_difference():
	old_tracking_list = tracking_list.get_tracking_list()
	tracking_list.read_tracking_list_from_file()
	new_tracking_list = tracking_list.get_tracking_list()

	tracking_added = [steam_id for steam_id in new_tracking_list if steam_id not in old_tracking_list]
	tracking_removed = [steam_id for steam_id in old_tracking_list if steam_id not in new_tracking_list]
	return tracking_added, tracking_removed

def send_tracking_list_difference_if_needed(tracking_added, tracking_removed):
	if not SEND_TRACKING_LIST_UPDATES:
		return

	if len(tracking_added) == 0  and len(tracking_removed) == 0:
		print(f"No difference in tracking list.")
		return

	print(f"Tracking list difference: {len(tracking_added)=} {len(tracking_removed)=}")

	embed = DiscordEmbed()
	embed.set_title("XP Tracker users changed")

	if len(tracking_added):
		steam_ids_list = "\n".join(tracking_added)
		embed.add_field(name="Users Added", value=f"```{steam_ids_list}```")

	if len(tracking_removed):
		steam_ids_list = "\n".join(tracking_removed)
		embed.add_field(name="Users Removed", value=f"```{steam_ids_list}```")

	embed.set_timestamp(datetime.datetime.utcnow().isoformat())
	webhook.send(embed=embed)

def check_users():
	global checking_loop_running

	if checking_loop_running:
		return

	checking_loop_running = True

	while True:
		tracking_added, tracking_removed = get_tracking_list_difference()
		send_tracking_list_difference_if_needed(tracking_added, tracking_removed)

		for steam_id in tracking_list.get_tracking_list():
			print(f"Checking {steam_id}")
			check_user(steam_id)

		print(f"Next check in {CHECK_TIMEOUT} seconds.")
		gevent.sleep(CHECK_TIMEOUT)

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

	check_users()

if __name__ == "__main__":
	webhook.set_username(WEBHOOK_USERNAME)
	webhook.set_avatar_url(WEBHOOK_AVATAR_URL)

	steam_login()
	steam_client.run_forever()