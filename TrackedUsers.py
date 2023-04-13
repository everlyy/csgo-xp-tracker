class TrackedUser:
	def __init__(self, steam_id):
		self.steam_id = steam_id
		self.first_check = True
		self.level = -1
		self.xp = -1
		self.previous_level = -1
		self.previous_xp = -1

	def update_level_and_xp(self, new_level, new_xp, change_callback):
		if new_level == self.level and new_xp == self.xp:
			return

		self.previous_level = self.level
		self.previous_xp = self.xp
		self.level = new_level
		self.xp = new_xp

		change_callback(self)
		self.first_check = False

class TrackedUsers:
	def __init__(self):
		self.__tracked_users = []

	def find_tracked_user_by_steam_id(self, steam_id):
		for user in self.__tracked_users:
			if user.steam_id == steam_id:
				return user

		new_user = TrackedUser(steam_id)
		self.__tracked_users.append(new_user)
		return new_user