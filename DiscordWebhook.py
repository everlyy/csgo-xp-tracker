import requests

# https://discord.com/developers/docs/resources/channel#embed-object
class DiscordEmbed:
	def __init__(self):
		self.embed = {}

	def set_title(self, title):
		self.embed["title"] = title

	def set_description(self, description):
		self.embed["description"] = description

	def set_url(self, url):
		self.embed["url"] = url

	def set_timestamp(self, timestamp):
		self.embed["timestamp"] = timestamp

	def set_thumbnail(self, url, proxy_url=None, height=None, width=None):
		self.embed["thumbnail"] = { 
			"url": url 
		}

		if proxy_url is not None: self.embed["thumbnail"]["proxy_url"] = proxy_url
		if height is not None: self.embed["thumbnail"]["height"] = height
		if width is not None: self.embed["thumbnail"]["width"] = width

	def add_field(self, name, value, inline=None):
		if "fields" not in self.embed:
			self.embed["fields"] = []

		field = {
			"name": name,
			"value": value
		}

		if inline is not None: field["inline"] = inline

		self.embed["fields"].append(field)

	def set_footer(self, text, icon_url=None, proxy_icon_url=None):
		self.embed["footer"] = {
			"text": text
		}

		if icon_url is not None: self.embed["footer"]["icon_url"] = icon_url
		if proxy_icon_url is not None: self.embed["footer"]["proxy_icon_url"] = proxy_icon_url

class DiscordWebhook:
	def __init__(self, url):
		self.url = url
		self.webhook = {}

	def set_username(self, username):
		self.webhook["username"] = username

	def set_avatar_url(self, avatar_url):
		self.webhook["avatar_url"] = avatar_url

	def send(self, content=None, embed=None):
		if content is not None: self.webhook["content"] = content
		if embed is not None: self.webhook["embeds"] = [ embed.embed ]

		response = requests.post(self.url, json=self.webhook)
		response.raise_for_status()