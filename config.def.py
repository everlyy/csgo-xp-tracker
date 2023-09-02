# Login for account that checks the XP
# This account can't be used at the same time as the checker is running
STEAM_USERNAME = "steam username"
STEAM_PASSWORD = "steam password"

# Steam API key for getting account name and avatar
# If you disable it, you wont see user's names or avatars
STEAM_API_KEY = "steam api key"
DISABLE_STEAM_API = False

# Path where logins for Steam will be saved
CREDENTIALS_LOCATION = "credentials"

# Webhook that will be used to post XP updates
DISCORD_UPDATE_WEBHOOK = "webhook url"
WEBHOOK_USERNAME = "XP Tracker"
WEBHOOK_AVATAR_URL = "https://cdn.discordapp.com/embed/avatars/0.png"

# Path for list of users being tracked
TRACKING_LIST_PATH = "tracking_list.json"

# Send message if user is added/removed
SEND_TRACKING_LIST_UPDATES = True

# Timeout between checks (in seconds)
CHECK_TIMEOUT = 60

# Shared secret for Steam Guard (base64 encoded), if you don't have one just set this to None
SHARED_SECRET = None