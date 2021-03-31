# About
This script will convert the difficulty ratings of .sm and .dwi simfiles according to the ratings on https://remywiki.com. 
This tool only works for songs featured on official DanceDanceRevolution games. It accepts either a single simfile or a folder containing song folders with simfiles within, such as the Songs folder in Stepmania or Outfox. 

## Behavior 
The script will attempt to locate the song on the remywiki by direct URL using the simfile's filename. For example "Holic" is located at https://remywiki.com/Holic. If the wiki page does not exist because the file is named inaccurately, the script will use Google to search the remywiki for the song. If all of the target files are named correctly, the Google API is not necessary. 

For 1-20 scale conversion, the script will prioritize games on the remywiki which include the "->Present" indicator since these are the most current charts for the song. If there is no such game to reference, the script will prioritize any games using the 1-20 scale. If no such game contains the target song, the script will select ratings from a game containing the song and multiply them by a factor of 1.5. 

# Modes
1. "Modern" mode (default) will convert 1-10 scale songs to 1-20 scale
2. "Legacy" mode will convert 1-20 scale songs to 1-10 scale

# Requirements
- python 3
- pycurl library
- Google API library

# Usage
## Single simfile
$ python3 ddredit.py [-m {modern | legacy}] [-d ...] -f simfile.sm

## Directory of folders containing simfiles
$ python3 ddredit.py [-m {modern | legacy}] [-d ...] -f simfiledirectory

## Manually specified difficulties
Difficulties should be a comma-separated list. Any unused difficulties should be a "-" character. 

The order must be:
`single-beginner, single-easy, single-medium, single-hard, single-challenge, double-easy, double-medium, double-hard, double-challenge`

Example:
$ python3 ddredit.py -d 1,3,5,7,9,3,5,7,9 -f simfile.sm
