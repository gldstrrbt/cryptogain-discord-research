import os
import discord
import asyncio
import re
import json
from datetime import datetime

client = discord.Client()
tracked_servers = {}
invite_links = {}

# File to save our findings
SERVER_DATA_FILE = "crypto_servers.json"
INVITE_LINKS_FILE = "crypto_invites.json"

# Load existing data if available
try:
	with open(SERVER_DATA_FILE, 'r') as f:
		tracked_servers = json.load(f)
except:
	tracked_servers = {}

try:
	with open(INVITE_LINKS_FILE, 'r') as f:
		invite_links = json.load(f)
except:
	invite_links = {}

@client.event
async def on_ready():
	print(f'Logged in as {client.user}')
	print(f'Currently in {len(client.guilds)} servers')
	
	# Start monitoring current servers
	await analyze_current_servers()
	
	# Start collecting invite links
	await collect_invite_links()

async def analyze_current_servers():
	"""Analyze servers we're already in and collect data"""
	print("Analyzing current servers...")
	
	for guild in client.guilds:
		# Skip servers we've already fully analyzed
		if str(guild.id) in tracked_servers and tracked_servers[str(guild.id)].get('fully_analyzed', False):
			continue
			
		print(f"Analyzing: {guild.name}")
		
		# Store basic info
		tracked_servers[str(guild.id)] = {
			'name': guild.name,
			'member_count': guild.member_count,
			'joined_at': datetime.now().isoformat(),
			'channels': [],
			'crypto_keywords': {},
			'fully_analyzed': False
		}
		
		# Analyze channels
		for channel in guild.text_channels:
			channel_data = {
				'name': channel.name,
				'id': str(channel.id),
				'topic': channel.topic
			}
			tracked_servers[str(guild.id)]['channels'].append(channel_data)
			
			# Count crypto keywords in channel names/topics
			crypto_keywords = ["bitcoin", "crypto", "eth", "trading", "defi", "nft", "blockchain"]
			for keyword in crypto_keywords:
				if keyword in channel.name.lower() or (channel.topic and keyword in channel.topic.lower()):
					tracked_servers[str(guild.id)]['crypto_keywords'][keyword] = tracked_servers[str(guild.id)]['crypto_keywords'].get(keyword, 0) + 1
		
		# Save after each server analysis
		with open(SERVER_DATA_FILE, 'w') as f:
			json.dump(tracked_servers, f, indent=2)
			
		tracked_servers[str(guild.id)]['fully_analyzed'] = True
	
	print(f"Successfully analyzed {len(client.guilds)} servers")

async def collect_invite_links():
	"""Collect invite links from messages for manual joining"""
	print("Starting invite link collection from current servers...")
	
	for guild in client.guilds:
		print(f"Scanning for invites in: {guild.name}")
		
		for channel in guild.text_channels:
			try:
				# Look through recent messages for invite links
				async for message in channel.history(limit=100):
					invite_matches = re.findall(r'discord\.gg/([a-zA-Z0-9]+)', message.content)
					for invite_code in invite_matches:
						if invite_code not in invite_links:
							try:
								invite = await client.fetch_invite(f"https://discord.gg/{invite_code}")
								# Store information about the invite
								invite_links[invite_code] = {
									'guild_name': invite.guild.name,
									'member_count': invite.guild.member_count if hasattr(invite.guild, 'member_count') else 'Unknown',
									'found_in': guild.name,
									'found_at': datetime.now().isoformat(),
									'full_url': f"https://discord.gg/{invite_code}",
									'joined': False
								}
								print(f"Found invite to: {invite.guild.name} (Members: {invite_links[invite_code]['member_count']})")
								
								# Save after each new invite found
								with open(INVITE_LINKS_FILE, 'w') as f:
									json.dump(invite_links, f, indent=2)
									
								# Small delay to avoid rate limits
								await asyncio.sleep(2)
							except Exception as e:
								print(f"Error fetching invite {invite_code}: {e}")
			except Exception as e:
				print(f"Error accessing channel: {e}")
				continue
	
	print(f"Completed invite collection. Found {len(invite_links)} unique server invites.")
	print("To join these servers, open crypto_invites.json and use the links manually.")

@client.event
async def on_message(message):
	"""Monitor incoming messages for invite links"""
	if message.author != client.user:
		invite_matches = re.findall(r'discord\.gg/([a-zA-Z0-9]+)', message.content)
		for invite_code in invite_matches:
			if invite_code not in invite_links:
				try:
					invite = await client.fetch_invite(f"https://discord.gg/{invite_code}")
					# Store information about the invite
					invite_links[invite_code] = {
						'guild_name': invite.guild.name,
						'member_count': invite.guild.member_count if hasattr(invite.guild, 'member_count') else 'Unknown',
						'found_in': message.guild.name,
						'found_at': datetime.now().isoformat(),
						'full_url': f"https://discord.gg/{invite_code}",
						'joined': False
					}
					print(f"Found new invite in message: {invite.guild.name}")
					
					# Save after each new invite
					with open(INVITE_LINKS_FILE, 'w') as f:
						json.dump(invite_links, f, indent=2)
				except Exception as e:
					pass  # Silently fail on message monitoring

# Get some known crypto server invites for testing
known_crypto_invites = [
	"bitcoincash",
	"chainlink",
	"cryptotraders",
	"ethtrader",
	"stellarnetwork",
	"vechain"
]

@client.event
async def on_guild_join(guild):
	"""Track when we join a new guild"""
	print(f"Joined new server: {guild.name}")
	await analyze_current_servers()

print("Starting invite collector...")
client.run(os.getenv("DISCORD_BOT_TOKEN", ""))