#!/usr/bin/python3
import os
import sys
import time
import pycurl
import config
import argparse
from io import BytesIO
from pprint import pprint
from googleapiclient.discovery import build


# Perform google search for given search term
# Stolen from StackOverflow
def google_search(search_term, **kwargs):
	api_key = config.api_key
	cse_id = config.cse_id
    service = build("customsearch", "v1", developerKey=api_key)
    result = service.cse().list(q="site:remywiki.com %s" % search_term, cx=cse_id, **kwargs).execute()
    return result["items"]


# Terminal output colors
# Stolen from StackOverflow
class bcolors:
    HEADER = '\033[95m'
    OKBLUE = '\033[94m'
    OKCYAN = '\033[96m'
    OKGREEN = '\033[92m'
    WARNING = '\033[93m'
    FAIL = '\033[91m'
    ENDC = '\033[0m'
    BOLD = '\033[1m'
    UNDERLINE = '\033[4m'


# Map list of difficulties from game row into dict
def map_difficulties_to_dict(current_difficulties, current_chart):
	return {
				"single":
				{
					"Beginner": current_difficulties[0],
					"Easy": current_difficulties[1], 
					"Medium": current_difficulties[2],
					"Hard": current_difficulties[3],
					"Challenge": current_difficulties[4]

				},
				"double":
				{
					"Easy": current_difficulties[5],
					"Medium": current_difficulties[6],
					"Hard": current_difficulties[7],
					"Challenge": current_difficulties[8]
				},
				"chart": current_chart
		}


# Check if the song has ever had chart updated
def has_modern_difficulties(difficulty_dict):
	modern_games = ["DanceDanceRevolution X", 
					"DanceDanceRevolution X2", 
					"DanceDanceRevolution X3 VS 2ndMIX",
					"DanceDanceRevolution (2013)",
					"DanceDanceRevolution (2014)",
					"DanceDanceRevolution A",
					"DanceDanceRevolution A20",
					"DanceDanceRevolution A20 PLUS"]

	for game in difficulty_dict.keys():
		for modern_game in modern_games:
			if modern_game in game:
				print("--> Found modern game: %s" % game)
				return True

	return False


# Curl web URL and return HTML
def get_page_contents(url):
	while True:
		try:
			response = BytesIO()
			c = pycurl.Curl()
			c.setopt(c.URL, url)
			c.setopt(c.WRITEDATA, response)
			c.perform()
			c.close()
			songpage = response.getvalue().decode()
			return songpage
		except Exception as e:
			print(str(e))
			print("--> Retrying...")
			time.sleep(10)

# Take a dictionary of all DDR games and find the legacy difficulty (lowest values)
def get_legacy_difficulty(difficulty_dict):

	legacy_difficulty = {
		"single":
		{
			"Beginner": "-",
			"Easy": "-", 
			"Medium": "-",
			"Hard": "-",
			"Challenge": "-"

		},
		"double":
		{
			"Easy": "-",
			"Medium": "-",
			"Hard": "-",
			"Challenge": "-"
		}

	}
	for game in difficulty_dict.keys():
		for style in difficulty_dict[game].keys():
			for difficulty in difficulty_dict[game][style]:
				legacy_entry = legacy_difficulty[style][difficulty]
				candidate_entry = difficulty_dict[game][style][difficulty]
				if not candidate_entry.isdigit():
					continue
				if legacy_entry == "-" or int(candidate_entry) < int(legacy_entry):
					legacy_difficulty[style][difficulty] = candidate_entry

	return legacy_difficulty


# Pull the page from remy wiki via direct URL or google
def google_song_data(songname):	
	try:

		results = google_search(songname)
		for result in results:
			url = result["link"]
			songpage = get_page_contents(url)
			if is_valid_songpage(songpage):
				print(bcolors.OKCYAN + "--> Found page for song: %s" % url + bcolors.ENDC)
				return songpage

	except Exception as e:
		print(str(e))
	# Sleep to avoid API overload
	finally:
		time.sleep(5)

	return None


# Make sure song page exists and has valid DDR data
def is_valid_songpage(songpage):
	for line in songpage.split("\n"):
		if "There is currently no text" in line:
			return False

		elif 'DanceDanceRevolution difficulty' in line:
			return True

	return False


# Take a dictionary of all DDR games and find the modern difficulty (highest values)
def get_modern_difficulty(difficulty_dict):
	modern_difficulty = {
		"single":
		{
			"Beginner": "-",
			"Easy": "-", 
			"Medium": "-",
			"Hard": "-",
			"Challenge": "-"

		},
		"double":
		{
			"Easy": "-",
			"Medium": "-",
			"Hard": "-",
			"Challenge": "-"
		}

	}

	# Use the largest value of all the games ratings for each style/difficulty
	for game in difficulty_dict.keys():
		for style in difficulty_dict[game].keys():
			for difficulty in difficulty_dict[game][style]:
				if "chart" in style:
					continue
				modern_entry = modern_difficulty[style][difficulty]
				candidate_entry = difficulty_dict[game][style][difficulty]
				if not candidate_entry.isdigit():
					continue
				if modern_entry == "-" or int(candidate_entry) > int(modern_entry):
					modern_difficulty[style][difficulty] = candidate_entry

	# Use the 1.5x scale for songs without official ratings
	if not has_modern_difficulties(difficulty_dict):
		print("--> No modern difficulties -- scaling by 1.5x")
		for style in modern_difficulty.keys():
			for difficulty in modern_difficulty[style]:
				difficulty_value = modern_difficulty[style][difficulty]
				if str(difficulty_value).isdigit():
					modern_difficulty[style][difficulty] = str(int(float(difficulty_value) * 1.5))

	return modern_difficulty


# Grab either legacy or modern difficulties for a given song from remywiki
def get_difficulty_from_web(songname, mode):
	difficulty_dict = {}

	url = 'https://remywiki.com/%s' % songname.replace(" ", "_")
	songpage = get_page_contents(url)

	in_table = False
	current_game = ""
	current_difficulties = []
	current_chart = ""
	special_chart = False
	present_chart = False
	ignored_games = ["Notecounts", "beatmania", "Dancing Stage", "PC", "S+", "pop'n", "GB", "DANCE WARS", "Solo"]

	# Validate the songpage the filename leads to. If it isn't valid, use Google to find a match
	if not is_valid_songpage(songpage):
		print(bcolors.WARNING + "--> Failed to lookup %s, trying Google" % songname + bcolors.ENDC)
		songpage = google_song_data(songname)
		if not songpage:
			print(bcolors.FAIL + "Google failed to find valid songpage for: %s" % songname + bcolors.ENDC)
			return None

	has_originals = False
	for line in songpage.split("\n"):
		# Replace markup characters
		line = line.replace("&#8594;", "->")
		line = line.replace("&#8593;", "")
		line = line.replace("&#8595;", "")

		# Make sure we are in a table with difficulty values
		if "Difficulty &amp; Notecounts" in line:
			in_table = True

		elif "Original Charts" in line:
			has_originals = True

		if in_table and '<span class="mw-headline"' in line and "<h4>" in line:
			current_chart = line.partition("</span></h4>")[0].rpartition(">")[2].replace('"', "")
		
		if in_table:
			# Each game starts off with this tag
			if "<td>" in line and "</td>" in line:
				# Get new game and reset difficulty values
				current_game = line.partition("<td>")[2].partition("</td>")[0]
				current_difficulties = []
				# Don't allow data from ignored games
				for ignored_game in ignored_games:
					if ignored_game in current_game:
						current_game = ""
			# Add difficulty values to current game if it's relevant
			if ("DDRMAX" in current_game or "DanceDanceRevolution" in current_game or "DDR" in current_game) and line.startswith("<td style="):
				# Strip HTML bold from values
				if "<b>" in line:
					line = line.replace("<b>", "").replace("</b>", "")

				# Look for a "present" chart
				if "present" in current_game.lower():
					present_chart = True

				current_difficulties.append(line.partition(';">')[2].partition("<")[0])
				# Track the number of actual difficulty values to prevent challenge-only charts from overwriting standard charts
				current_numeric_difficulties = len(current_difficulties) - current_difficulties.count("-")
				# Stick completed game values into dict of all games
				if current_game and len(current_difficulties) > 8 and (current_numeric_difficulties > 3 or has_originals is False):
					difficulty_dict[current_game] = map_difficulties_to_dict(current_difficulties, current_chart)

				elif current_game and len(current_difficulties) > 8 and current_chart in songname:
					special_chart = True
					difficulty_dict[current_game] = map_difficulties_to_dict(current_difficulties, current_chart)

	# For special edition songs, remove all but special charts
	if special_chart:
		temp_dict = difficulty_dict.copy()
		print("--> Song is special chart")
		for game in temp_dict.keys():
			chart = temp_dict[game]["chart"]
			if chart not in songname:
				difficulty_dict.pop(game, None)

	# If we have a "present" chart we should use it
	if present_chart:
		temp_dict = difficulty_dict.copy()
		print("--> Song has present chart")
		for game in temp_dict.keys():
			if "present" not in game.lower():
				difficulty_dict.pop(game, None)

	web_difficulty_dict = {}
	# No game data found
	if not difficulty_dict:
		return None
	# Pick out either the legacy or modern difficulties by provided flag
	if mode == "legacy":
		web_difficulty_dict = get_legacy_difficulty(difficulty_dict)
	elif mode == "modern":
		web_difficulty_dict = get_modern_difficulty(difficulty_dict)
	return web_difficulty_dict


# Read in step file and update difficulty ratings
def update_difficulty(filename, mode="modern", new_difficulties=[]):
	# Holds the difficulties that will be written to the file
	diff_dict = {}
	# Manual difficulty override
	if new_difficulties:
		new_difficulties = new_difficulties.split(",")
		# Add in dummy beginner chart if needed
		if len(new_difficulties) < 8:
			new_difficulties.insert(0, -1)
			diff_dict = {
				"single":
				{
					"Beginner": new_difficulties[0],
					"Easy": new_difficulties[1],
					"Medium": new_difficulties[2],
					"Hard": new_difficulties[3],
					"Challenge": new_difficulties[4]
				},
				"double": 
				{
					"Easy": new_difficulties[5],
					"Medium": new_difficulties[6],
					"Hard": new_difficulties[7],
					"Challenge": new_difficulties[8]
				}
			}
	# Automatic difficulty grabbing from web		
	else:
		songname = filename.rpartition(".")[0].rpartition("/")[2].replace("'","%27")
		# Build dictionary of all games and their difficulties for current song
		diff_dict = get_difficulty_from_web(songname, mode)
		# Games list came back empty, fail
		if not diff_dict:
			print(bcolors.FAIL + "Failed to update %s" % songname + bcolors.ENDC)
			return

	difficulty_names = ["Beginner", "Easy", "Medium", "Hard", "Challenge"]
	# Read in the current chart and replace the current difficulties with new ones
	file_lines = []
	with open(filename) as f:
		current_difficulty = ""
		current_mode = ""
		print("\nStyle  | Difficulty | Rating Change")
		print("-------|------------|-------------")
		file_lines = f.readlines()
		for i,line in enumerate(file_lines):
			# Parse .sm file
			if ".sm" in filename:
				line_text = line.strip().partition(":")[0]
				if "dance-" in line:
					current_mode = line_text.partition("dance-")[2]
					if "couple" in current_mode or "solo" in current_mode:
						current_mode = ""
						continue
				# Check for numeric difficulty rating on current line	
				elif current_mode and line_text in difficulty_names:
					current_difficulty = line_text
				if current_mode and len(line_text) <= 2 and line_text.isdigit():
					# Map the correct replacement value into the current difficulty
					replacement_difficulty = ""
					try:
						replacement_difficulty = diff_dict[current_mode][current_difficulty]
					except KeyError:
						print("{0} | {1:10} | {2} (skipped)".format(current_mode, current_difficulty, line_text))
						
					if not replacement_difficulty.isdigit():
						print("{0} | {1:10} | {2} (skipped)".format(current_mode, current_difficulty, line_text))
						continue
					if int(replacement_difficulty) < 1:
						continue
					print("{0} | {1:10} | {2}-->{3}".format(current_mode, current_difficulty, line_text, replacement_difficulty))
					file_lines[i] = line.replace(line_text, str(replacement_difficulty))
			# Parse .dwi file
			elif ".dwi" in filename:
				mapping_dict = {
					"BEGINNER": "Beginner",
					"BASIC": "Easy",
					"ANOTHER": "Medium",
					"MANIAC": "Hard",
					"SMANIAC": "Challenge"
				}
				line_text = line
				if "SINGLE" in line or "DOUBLE" in line:
					current_style = line_text.partition("#")[2].partition(":")[0]
					current_difficulty = line_text.partition(current_style + ":")[2].partition(":")[0]
					current_difficulty_num = line_text.partition(current_difficulty + ":")[2].partition(":")[0]
					# Remap to to simfile nomenclature
					current_style = current_style.lower()
					current_difficulty = mapping_dict[current_difficulty]
					replacement_difficulty = diff_dict[current_style][current_difficulty]

					if not replacement_difficulty.isdigit():
						print("{0} | {1:10} | {2} (skipped)".format(current_style, current_difficulty, current_difficulty_num))
						continue
					if int(replacement_difficulty) < 1:
						continue
					print("{0} | {1:10} | {2}-->{3}".format(current_style, current_difficulty, current_difficulty_num, replacement_difficulty))
					file_lines[i] = line.replace(current_difficulty_num, str(replacement_difficulty), 1)

		f.close()

	# Write new difficulties to the source file
	with open(filename, "w") as f:
		new_contents = "".join(file_lines)
		f.write(new_contents)
		f.close()
		print(bcolors.OKGREEN + "\nUpdated %s successfully" % songname + bcolors.ENDC)
		return True


if __name__ == "__main__":
	# Command line argument parsing
	parser = argparse.ArgumentParser(description='DDR difficulty editing script')
	parser.add_argument('-f','--file', help='Target file or directory',required=True)
	parser.add_argument('-d','--difficultylist',help='List of specified difficulties (comma separated)',required=False)
	parser.add_argument('-m','--mode', help='Legacy or Modern (default: Modern)',required=False)

	args = parser.parse_args()

	if not args.file:
		print("Please specify a file or folder.")

	if not args.mode:
		mode = "modern"
	else:
		mode = args.mode.lower()

	new_difficulties = []
	if args.difficultylist:
		new_difficulties = difficultylist

	# Update single file 
	if ".sm" in args.file.lower() or ".dwi" in args.file.lower():
		print("Updating %s\n" % (args.file))
		update_difficulty(args.file, mode=mode, new_difficulties=new_difficulties)
	# Update files from all contained folders
	else:
		file_list = []
		for root, dirs, files in os.walk(args.file, topdown=False):
			for name in files:
				filename = os.path.join(root, name)
				if filename.endswith(".sm") or filename.endswith(".dwi"):
					file_list.append(filename)

		updated = []
		failed = []
		for file in sorted(file_list):
			print("Updating %s\n" % (file))
			# True if success, False if failure
			success = update_difficulty(file, mode=mode)
			if success:
				updated.append(file.rpartition("/")[2])
			else:
				failed.append(file.rpartition("/")[2])

			print("\n------------------------------------")

		# Summary output
		print("|             SUMMARY              |")
		print("------------------------------------")
		print("Successfully updated %d item(s):" % len(updated))
		for item in updated:
			print("--> " + item)
		print("------------------------------------")

		print("Failed to update %d item(s):" % len(failed))
		for item in failed:
			print("--> " + item)
		print("------------------------------------\n")



