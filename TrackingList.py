import json
import os

class TrackingList:
	def __init__(self, path):
		self.path = path
		self.__tracking_list = []
		self.__read()

	def __read(self):
		if not os.path.exists(self.path):
			self.__tracking_list = []
			return

		with open(self.path, "r") as file:
			self.__tracking_list = json.load(file)

	def __write(self):
		with open(self.path, "w") as file:
			file.write(json.dumps(self.__tracking_list, indent=4))

	def add_to_tracking_list(self, entry):
		self.__tracking_list.append(entry)
		self.__write()

	def read_tracking_list_from_file(self):
		self.__read()

	def get_tracking_list(self):
		return self.__tracking_list