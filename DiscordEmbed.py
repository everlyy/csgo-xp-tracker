# https://discord.com/developers/docs/resources/channel#embed-object-embed-field-structure
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
