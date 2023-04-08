import sqlite3

class TrackedUser:
	def __init__(self, steam_id, discord_id, current_level, current_xp):
		self.steam_id = steam_id
		self.discord_id = discord_id
		self.current_level = current_level
		self.current_xp = current_xp

class DatabaseManager:
	def __init__(self, db_path):
		self.path = db_path

	def __open_db(self):
		db = sqlite3.connect(self.path)
		db.execute("CREATE TABLE IF NOT EXISTS tracking (steam_id INT PRIMARY KEY NOT NULL, discord_id TEXT NOT NULL, current_level INT NOT NULL, current_xp INT NOT NULL)")
		return db

	def add_user(self, steam_id, discord_id, current_level, current_xp):
		db = self.__open_db()

		command = "INSERT INTO tracking VALUES (?, ?, ?, ?)"
		args = (steam_id, discord_id, current_level, current_xp)
		db.execute(command, args)

		db.commit()
		db.close()

	def get_user_by_steam_id(self, steam_id):
		db = self.__open_db()

		command = "SELECT * from tracking WHERE steam_id = ?"
		args = (steam_id, )
		for row in db.execute(command, args):
			db.close()
			return TrackedUser(*row)	

		db.close()
		return None

	def get_users(self):
		db = self.__open_db()

		users = []

		command = "SELECT * FROM tracking"
		for row in db.execute(command):
			users.append(TrackedUser(*row))

		db.close()
		return users

	def update_user_level_and_xp(self, steam_id, level, xp):
		db = self.__open_db()

		command = "UPDATE tracking SET current_level = ?, current_xp = ? WHERE steam_id = ?"
		args = (level, xp, steam_id)
		db.execute(command, args)

		db.commit()
		db.close()