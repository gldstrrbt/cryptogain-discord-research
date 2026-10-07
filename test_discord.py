import os
import discord
import asyncio

client = discord.Client()

# Track servers we've already seen
discovered_servers = set()

@client.event
async def on_ready():
	print(f'Logged in as {client.user}')
	print("on_ready: discover_servers start!")
	# Start the discovery process
	await discover_servers()

# @client.event
# async def on_message(message):
# 	print(client.user)
# 	print(message.author)
# 	print(message)
# 	print(message.content)
# 	print(message.author != client.user)
# 	print("*"*50)
# 	if message.author != client.user:
# 		await message.channel.send('Hello!')
# 	return

# 	# if message.content.startswith('$hello'):
# 	# await message.channel.send('Hello!')

@client.event
async def on_typing(message, something, asdf):
	print(client.user)
	# print(message.author)
	print(message)
	print(something)
	print(asdf)
	# print(message.content)
	# print(message.author != client.user)
	print("*"*50)
	# if message.author != client.user:
	# 	await message.channel.send('Hello!')
	return

	# if message.content.startswith('$hello'):
	# await message.channel.send('Hello!')




async def discover_servers():
	"""Find and join crypto-related servers"""
	# Base servers to start exploration from (public crypto servers)
	seed_servers = [
		"cryptotrading", "cryptosignals", "defiprotocols", 
		"cryptonews", "altcoins", "bitcointrading"
	]
	print("discover_servers: client.guilds: ")
	print(client.guilds)
	# Search for invites in messages
	for guild in client.guilds:
		print("discover_servers: guild: ")
		print(guild)
		for channel in guild.text_channels:
			print(channel)
			try:
				# Look through recent messages for invite links
				async for message in channel.history(limit=100):
					print(message.content)
					if "discord.gg/" in message.content:
						# Extract invite code
						invite_code = message.content.split("discord.gg/")[1].split()[0]
						if invite_code not in discovered_servers:
							discovered_servers.add(invite_code)
							# Join the server
							try:
								invite = await client.fetch_invite(f"https://discord.gg/{invite_code}")
								await invite.accept()
								print(f"Joined server: {invite.guild.name}")
								# Wait to avoid rate limits
								await asyncio.sleep(3600)  # Join max 1 server per hour
							except Exception as e:
								print(f"Failed to join with code {invite_code}: {e}")
			except Exception:
				# Skip channels we can't access
				continue
			print("*"*50 )

@client.event
async def on_message(message):
	# Listen for messages with invite links
	if message.author != client.user and "discord.gg/" in message.content:
		invite_code = message.content.split("discord.gg/")[1].split()[0]
		if invite_code not in discovered_servers:
			discovered_servers.add(invite_code)
			try:
				invite = await client.fetch_invite(f"https://discord.gg/{invite_code}")
				# Filter for crypto-related servers
				if any(keyword in invite.guild.name.lower() for keyword in 
					  ["crypto", "bitcoin", "eth", "trading", "defi", "finance", "invest"]):
					await invite.accept()
					print(f"Joined server: {invite.guild.name}")
					# Wait to avoid rate limits
					await asyncio.sleep(3600)
			except Exception as e:
				print(f"Failed to join: {e}")


client.run(os.getenv("DISCORD_BOT_TOKEN", ""))
