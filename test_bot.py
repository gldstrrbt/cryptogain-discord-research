import discord
import asyncio
import random
import json
import re
import os
from datetime import datetime, timedelta, time
from collections import defaultdict
import aiohttp

class CryptoGainEngagementBot(discord.Client):
	def __init__(self):
		super().__init__()
		
		# ---- Configuration ----
		self.CHART_FOLDER = "watermarked_charts/"
		self.DATA_FILE = "engagement_data.json"
		self.CREDENTIALS_FILE = "credentials.json"
		
		# Engagement settings
		self.min_delay = 30  # seconds
		self.max_delay = 180  # seconds
		self.daily_engagement_cap = 25  # max total engagements per day
		self.channel_engagement_cap = 4  # max engagements per channel per day
		self.promotion_cooldown_hours = 48  # hours between promotions in same channel
		
		# ---- Tracking Data ----
		self.engagement_history = defaultdict(list)  # channel_id -> list of timestamps
		self.promotion_history = defaultdict(float)  # channel_id -> last promotion timestamp
		self.user_interactions = defaultdict(int)  # user_id -> interaction count
		self.conversation_threads = {}  # message_id -> thread context
		
		# Load previous data if exists
		self.load_data()
		
		# Chart collection
		self.charts = self.load_charts()
		
		# ---- Engagement Strategy ----
		self.current_phase = "authentic"  # "authentic", "subtle", "relationship", "promotional"
		# self.phase_start_date = datetime.datetime.now()
		self.phase_start_date = datetime.now()
		self.phase_durations = {
			"authentic": 14,      # 2 weeks
			"subtle": 14,         # 2 weeks
			"relationship": 14,   # 2 weeks
			"promotional": 30     # ongoing
		}
		
		# Activity patterns (day_of_week -> engagement level)
		self.activity_patterns = {
			0: "medium",    # Monday
			1: "low",       # Tuesday
			2: "high",      # Wednesday  
			3: "low",       # Thursday
			4: "medium",    # Friday
			5: "low",       # Saturday
			6: "low"        # Sunday
		}
		
		self.engagement_levels = {
			"high": {"min": 8, "max": 12},
			"medium": {"min": 5, "max": 7},
			"low": {"min": 2, "max": 4}
		}
		
		# Today's engagement budget
		# self.today = datetime.datetime.now().date()
		self.today = datetime.now().date()
		self.today_engagement_count = 0
		self.channel_engagement_counts = defaultdict(int)
		
		# Set active hours (in UTC)
		self.active_hours = {
			"start": 13,  # 9 AM EST / 6 AM PST
			"end": 23     # 7 PM EST / 4 PM PST
		}
		
		# Keywords to track for different conversation types
		self.keyword_categories = {
			"technical_analysis": [
				"macd", "rsi", "bollinger", "indicator", "chart pattern", "fibonacci", 
				"support", "resistance", "trend line", "moving average", "divergence"
			],
			"app_complaints": [
				"expensive app", "subscription", "paywall", "locked feature", "premium",
				"TabTrader", "GoodCrypto", "Binance app", "not worth", "too costly"
			],
			"privacy_concerns": [
				"privacy", "data collection", "tracking", "security", "leaked", "breach",
				"keylogger", "spyware", "permissions", "access"
			],
			"recommendation_requests": [
				"recommend", "alternative", "instead of", "better app", "looking for",
				"suggest", "what app", "which app", "good app for"
			]
		}

		self.crypto_list_cache = None
		self.crypto_cache_time = None
		self.crypto_cache_duration = timedelta(hours=24)  # Cache crypto list for 24 hours

	
	def load_data(self):
		"""Load previous engagement data if exists"""
		try:
			with open(self.DATA_FILE, 'r') as f:
				data = json.load(f)
				self.engagement_history = defaultdict(list, data.get('engagement_history', {}))
				self.promotion_history = defaultdict(float, data.get('promotion_history', {}))
				self.user_interactions = defaultdict(int, data.get('user_interactions', {}))
				self.current_phase = data.get('current_phase', 'authentic')
				# self.phase_start_date = datetime.datetime.fromisoformat(data.get('phase_start_date', datetime.datetime.now().isoformat()))
				self.phase_start_date = datetime.fromisoformat(data.get('phase_start_date', datetime.now().isoformat()))
		except (FileNotFoundError, json.JSONDecodeError):
			pass
	
	def save_data(self):
		"""Save engagement data"""
		data = {
			'engagement_history': dict(self.engagement_history),
			'promotion_history': dict(self.promotion_history),
			'user_interactions': dict(self.user_interactions),
			'current_phase': self.current_phase,
			'phase_start_date': self.phase_start_date.isoformat()
		}
		
		with open(self.DATA_FILE, 'w') as f:
			json.dump(data, f, indent=2)
	
	def load_charts(self):
		"""Load chart images from the charts folder"""
		charts = {}
		
		if not os.path.exists(self.CHART_FOLDER):
			os.makedirs(self.CHART_FOLDER)
			print(f"Created {self.CHART_FOLDER} directory. Please add watermarked chart images.")
			return {}
		
		for filename in os.listdir(self.CHART_FOLDER):
			if filename.lower().endswith(('.png', '.jpg', '.jpeg')):
				# Parse filename to extract categories and tags
				# Expected format: BTC_USDT_MACD_Divergence.png
				parts = filename.split('.')[0].split('_')
				if len(parts) >= 3:
					pair = f"{parts[0]}/{parts[1]}"
					tags = parts[2:]
					
					for tag in tags:
						if tag not in charts:
							charts[tag] = []
						charts[tag].append({
							'filename': filename,
							'pair': pair,
							'path': os.path.join(self.CHART_FOLDER, filename)
						})
		
		return charts
	

	def update_phase(self):
		"""Check and update the current engagement phase based on time elapsed"""
		# now = datetime.datetime.now()
		now = datetime.now()
		days_in_phase = (now - self.phase_start_date).days
		
		if days_in_phase >= self.phase_durations[self.current_phase]:
			# Advance to next phase
			if self.current_phase == "authentic":
				self.current_phase = "subtle"
			elif self.current_phase == "subtle":
				self.current_phase = "relationship"
			elif self.current_phase == "relationship":
				self.current_phase = "promotional"
			
			self.phase_start_date = now
			print(f"Advanced to {self.current_phase} phase")
			self.save_data()
	

	def reset_daily_counters(self):
		"""Reset daily engagement counters if it's a new day"""
		# today = datetime.datetime.now().date()
		today = datetime.now().date()
		if today != self.today:
			self.today = today
			self.today_engagement_count = 0
			self.channel_engagement_counts = defaultdict(int)
			print(f"Reset daily counters for {today}")
	

	def should_engage_now(self):
		"""Determine if we should be engaging right now based on time of day and activity pattern"""
		self.reset_daily_counters()
		
		# Check if we've hit daily cap
		if self.today_engagement_count >= self.daily_engagement_cap:
			return False
		
		# Check if within active hours
		now = datetime.now().time()
		# Use the imported time class directly, not as datetime.time
		active_start = time(hour=self.active_hours["start"])
		active_end = time(hour=self.active_hours["end"])
		
		if not (active_start <= now <= active_end):
			return False
		
		# Rest of method remains the same
		day_of_week = datetime.now().weekday()
		pattern = self.activity_patterns[day_of_week]
		
		engagement_chance = {
			"high": 0.8,
			"medium": 0.5,
			"low": 0.3
		}[pattern]
		
		return random.random() < engagement_chance
	


	def can_engage_in_channel(self, channel_id):
		"""Check if we can engage in this specific channel"""
		# Don't exceed channel cap
		if self.channel_engagement_counts[channel_id] >= self.channel_engagement_cap:
			return False
		
		# Check last engagement in this channel (space them out)
		recent_engagements = [
			ts for ts in self.engagement_history[channel_id] 
			# if (datetime.datetime.now() - datetime.datetime.fromisoformat(ts)).seconds < 1800  # 30 minutes
			if (datetime.now() - datetime.fromisoformat(ts)).seconds < 1800  # 30 minutes
		]
		
		if recent_engagements:
			return False
			
		return True
	


	def categorize_message(self, message):
		"""Categorize message based on content"""
		content = message.content.lower()
		categories = []
		
		for category, keywords in self.keyword_categories.items():
			if any(keyword in content for keyword in keywords):
				categories.append(category)
		
		return categories
	
	def can_promote_in_channel(self, channel_id):
		"""Check if we can do promotional content in this channel"""
		# Only promote in promotional phase
		if self.current_phase != "promotional":
			return False
			
		# Check cooldown period
		last_promotion = self.promotion_history.get(channel_id, 0)
		if last_promotion:
			# hours_since = (datetime.datetime.now() - datetime.datetime.fromisoformat(last_promotion)).total_seconds() / 3600
			hours_since = (datetime.now() - datetime.fromisoformat(last_promotion)).total_seconds() / 3600
			if hours_since < self.promotion_cooldown_hours:
				return False
		
		return True
	
	def select_relevant_chart(self, message_content):
		"""Select a relevant chart based on message content"""
		if not self.charts:
			return None
			
		content = message_content.lower()
		
		# Extract potential cryptocurrency pairs
		pair_pattern = r'([a-z]{2,5})[/]([a-z]{2,5})'
		pairs = re.findall(pair_pattern, content)
		
		# Look for indicator keywords
		found_charts = []
		
		# First try to match both pair and indicator
		for tag, chart_list in self.charts.items():
			if tag.lower() in content:
				for chart in chart_list:
					pair = chart['pair'].lower()
					if pair in content:
						found_charts.append(chart)
		
		# If nothing found, match just on indicator
		if not found_charts:
			for tag, chart_list in self.charts.items():
				if tag.lower() in content:
					found_charts.extend(chart_list)
		
		# If still nothing, match on any common crypto pair mentioned
		if not found_charts and pairs:
			for tag, chart_list in self.charts.items():
				for chart in chart_list:
					for pair in pairs:
						pair_str = f"{pair[0]}/{pair[1]}".lower()
						if pair_str in chart['pair'].lower():
							found_charts.append(chart)
		
		if found_charts:
			# Return a random chart from the matches to avoid always using the same one
			return random.choice(found_charts)
		
		return None
	
	async def send_delayed_response(self, channel, content, chart_path=None):
		"""Send a response after a random delay to appear more natural"""
		# Track that we're going to engage
		self.today_engagement_count += 1
		self.channel_engagement_counts[channel.id] += 1
		# self.engagement_history[channel.id].append(datetime.datetime.now().isoformat())
		self.engagement_history[channel.id].append(datetime.now().isoformat())
		
		# Random delay
		delay = random.randint(self.min_delay, self.max_delay)
		await asyncio.sleep(delay)
		
		try:
			if chart_path:
				# Send message with chart
				await channel.send(content, file=discord.File(chart_path))
			else:
				# Send text only
				await channel.send(content)
		except Exception as e:
			print(f"Error sending message: {e}")
		
		# Save updated data
		self.save_data()
	
	async def on_ready(self):
		print(f'Logged in as {self.user}')
		print(f'Currently in {len(self.guilds)} servers')
		
		# Print out current engagement phase
		self.update_phase()
		print(f"Current engagement phase: {self.current_phase}")
		# print(f"Days in this phase: {(datetime.datetime.now() - self.phase_start_date).days}")
		print(f"Days in this phase: {(datetime.now() - self.phase_start_date).days}")
		
		# Print available charts
		chart_count = sum(len(charts) for charts in self.charts.values())
		print(f"Loaded {chart_count} charts across {len(self.charts)} categories")
		
		# Print activity schedule
		print("Activity schedule:")
		for day, level in self.activity_patterns.items():
			day_name = ["Monday", "Tuesday", "Wednesday", "Thursday", "Friday", "Saturday", "Sunday"][day]
			print(f"  {day_name}: {level.capitalize()} ({self.engagement_levels[level]['min']}-{self.engagement_levels[level]['max']} engagements)")
	

	async def get_channel_context(self, channel, limit=10):
		"""
		Fetch recent message history from a channel to provide context
		
		Args:
			channel: The Discord channel object
			limit: Number of recent messages to fetch (default 10)
			
		Returns:
			A formatted string containing recent conversation context
		"""
		context = []
		try:
			# Get messages before the current one
			async for msg in channel.history(limit=limit):
				timestamp = msg.created_at.strftime("%H:%M:%S")
				author = msg.author.display_name
				content = msg.content
				
				# Skip empty messages or those with only attachments
				if not content:
					continue
					
				# Format the message
				context.append(f"[{timestamp}] {author}: {content}")
			
			# Reverse to get chronological order
			context.reverse()
			return "\n".join(context)
		except Exception as e:
			print(f"Error fetching channel context: {e}")
			return ""
		

	async def get_crypto_list(self):
		"""Fetch and cache list of cryptocurrencies from CoinGecko"""
		# Check if we have a valid cache
		now = datetime.now()
		if (self.crypto_list_cache is not None and 
			self.crypto_cache_time is not None and 
			now - self.crypto_cache_time < self.crypto_cache_duration):
			return self.crypto_list_cache
		
		# No valid cache, fetch from API
		try:
			async with aiohttp.ClientSession() as session:
				url = "https://api.coingecko.com/api/v3/coins/list"
				async with session.get(url) as response:
					if response.status == 200:
						self.crypto_list_cache = await response.json()
						self.crypto_cache_time = now
						print(f"Updated crypto list from CoinGecko: {len(self.crypto_list_cache)} coins")
						return self.crypto_list_cache
					else:
						print(f"CoinGecko API error: {response.status}")
						# Return cached version if available, even if expired
						if self.crypto_list_cache:
							return self.crypto_list_cache
		except Exception as e:
			print(f"Error fetching crypto list: {e}")
			if self.crypto_list_cache:
				return self.crypto_list_cache
		
		# If all fails, return empty list
		return []
	

	async def identify_cryptocurrencies(self, conversation_context):
		"""
		Scan conversation context to identify mentioned cryptocurrencies
		
		Args:
			conversation_context: String containing recent chat messages
			
		Returns:
			List of dictionaries with information about identified cryptocurrencies
		"""
		# Get cryptocurrency list from CoinGecko
		crypto_list = await self.get_crypto_list()
		if not crypto_list:
			return []
		
		# Common crypto symbols patterns
		symbol_pattern = r'\b(BTC|ETH|USDT|BNB|SOL|XRP|ADA|DOGE|AVAX|DOT|MATIC|LINK|UNI|ATOM|LTC|BCH|XLM|ALGO|FIL|NEAR|AAVE|XMR|EOS|SAND|MANA|SHIB|VET|EGLD|FTM|HBAR|THETA|HNT|WAVES|CAKE|AXS|XTZ|FLOW|KSM|CHZ|BAT|LRC|YFI|ZEC|ICX|ENJ|COMP|DASH|CELO|ZIL|AR|RVN|IOTA|GRT)\b'
		
		# Potential crypto patterns
		ticker_pattern = r'\b[A-Z]{2,5}\b'
		
		# Create lookup dictionaries for faster matching
		symbol_to_crypto = {crypto['symbol'].upper(): crypto for crypto in crypto_list}
		id_to_crypto = {crypto['id'].lower(): crypto for crypto in crypto_list}
		
		# First check for common crypto symbols using regex
		common_symbols = set(re.findall(symbol_pattern, conversation_context.upper()))
		
		# Then check for any potential ticker symbols
		potential_tickers = set(re.findall(ticker_pattern, conversation_context.upper())) - common_symbols
		
		# Also look for crypto names (not just symbols)
		context_words = set(re.findall(r'\b[a-zA-Z]{3,}\b', conversation_context.lower()))
		
		# Combine results
		found_cryptos = []

		excluded_symbols = ["one", "joe", "api", "make", "reddit", "cool", "now", "good", "for", "not", "we", "tip", "that", "high", "would", "home","long"]
		
		# Add common symbols (these are almost certainly cryptos)
		for symbol in common_symbols:
			if symbol.upper() in symbol_to_crypto:
				crypto = symbol_to_crypto[symbol.upper()]
				if crypto['symbol'].lower() not in excluded_symbols:	
					found_cryptos.append({
						'id': crypto['id'],
						'symbol': crypto['symbol'].upper(),
						'name': crypto['name'],
						'confidence': 'high'
					})
		
		# Check potential tickers against CoinGecko data
		# for ticker in potential_tickers:
		# 	if ticker.upper() in symbol_to_crypto:
		# 		crypto = symbol_to_crypto[ticker.upper()]
		# 		# Only add if not already found as common symbol
		# 		if not any(c['id'] == crypto['id'] for c in found_cryptos):
		# 			found_cryptos.append({
		# 				'id': crypto['id'],
		# 				'symbol': crypto['symbol'].upper(),
		# 				'name': crypto['name'],
		# 				'confidence': 'medium'
		# 			})
		
		# Check for crypto names in context
		for word in context_words:
			if word in id_to_crypto:
				crypto = id_to_crypto[word]
				# Only add if not already found
				if not any(c['id'] == crypto['id'] for c in found_cryptos):
					if crypto['symbol'].lower() not in excluded_symbols:
						found_cryptos.append({
							'id': crypto['id'],
							'symbol': crypto['symbol'].upper(),
							'name': crypto['name'],
							'confidence': 'high'
						})
		
		return found_cryptos


	async def on_message(self, message):


		# MESSAGE TO SELF # 
		# MESSAGE TO SELF # 
		# MESSAGE TO SELF # 
		# MESSAGE TO SELF #
		# HAVE LLM NOT USE EM DASHES AT ALL.
		# MUST MIMIC THE STYLE OF DISCUSSION IN AUTHENTIC WAY BASED ON CONVERSATION CONTEXT GIVEN
		# MUST ONLY RESPOND WITH MESSAGE TEXT AND NOTHING ELSE
		# MUST ONLY WRITE ONE SENTENCE AT A TIME... TWO MAX AND RARELY TWO AT A TIME 
		# 
		# ADD FUNCTION TO POST ONE CHART IMAGE DAILY TO:  
		# GUILD: CRYPTOCURRENCY
		# CHANNEL: BOTS-AIRDROPS-CHARTS  
		#  

		print("*"*50)
		try:
			print("guild: " + str(message.guild))
		except:
			pass
		try:
			print("guild_id: " + str(message.guild_id))
		except:
			pass
		print("channel: " + str(message.channel))

		try:
			print("activity: " + str(message.activity))
		except:
			pass
		try:		
			print("total_results: " + str(message.total_results))
		except:
			pass

		categories = self.categorize_message(message)
		print("categories: " + str(categories))
		conversation_context = await self.get_channel_context(message.channel)
		mentioned_cryptos = await self.identify_cryptocurrencies(conversation_context)
		print("mentioned_cryptos: " + str(mentioned_cryptos))
		# for a in conversation_context:
		# 	print("conversation_context: a" + str(a))
		print(str(conversation_context))
		print("*"*50)

		if message.author == self.user:
			return
		
		# Ignore DMs for now
		if isinstance(message.channel, discord.DMChannel):
			return
			
		# Check if we should be engaging at all right now
		if not self.should_engage_now():
			return
			
		# Check if we can engage in this specific channel
		if not self.can_engage_in_channel(message.channel.id):
			return

		# Process the message
		categories = self.categorize_message(message)
		if not categories:
			return  # No relevant topics detected
		
		# Update user interaction count
		self.user_interactions[str(message.author.id)] += 1
		
		# Determine if this is a good promotion opportunity
		can_promote = self.can_promote_in_channel(message.channel.id) and "recommendation_requests" in categories
		
		# Check if we should attach a chart (only in subtle phase or later)
		chart = None
		if self.current_phase in ["subtle", "relationship", "promotional"] and "technical_analysis" in categories:
			chart = self.select_relevant_chart(message.content)
		
		# ======= LLM INTEGRATION PSEUDO CODE =======
		# Here's where you'd integrate your LLM:
		
		# response = llm.generate(
		#     context={
		#         "message": message.content,
		#         "categories": categories,
		#         "phase": self.current_phase,
		#         "can_promote": can_promote,
		#         "has_chart": chart is not None,
		#         "chart_details": chart,
		#         "user_interaction_count": self.user_interactions[str(message.author.id)],
		#         "channel_name": message.channel.name
		#     }
		# )
		
		# For testing without LLM, use hardcoded responses:
		# ==========================================
		# print("chart: ")
		# print(chart)
		# print("categories: ")
		# print(categories)
		# print("messages: ")
		# print(messages)
		# print("*"*50)
		# print("*"*50)
		# Placeholder response logic until LLM integration
		# if "technical_analysis" in categories:
		# 	if chart:
		# 		response = f"I've been looking at this {chart['pair']} chart with {chart['filename'].split('_')[2]}. Notice anything interesting about the pattern?"
		# 	else:
		# 		response = "Technical analysis is fascinating. What indicators do you typically rely on for your trading decisions?"
		# elif "app_complaints" in categories:
		# 	response = "Yeah, I've run into those limitations too. What features are you finding most frustrating?"
		# elif "privacy_concerns" in categories:
		# 	response = "Privacy is a huge concern in crypto. I always check what data apps are collecting before I install them."
		# elif "recommendation_requests" in categories:
		# 	if can_promote:
		# 		response = "I've actually been building an app called CryptoGain that addresses a lot of these issues. It offers unlimited free indicators and doesn't collect any user data. Happy to share more if you're interested."
		# 		self.promotion_history[message.channel.id] = datetime.datetime.now().isoformat()
		# 	else:
		# 		response = "Finding the right app can be challenging. What specific features are most important for your trading style?"
		# else:
		# 	return  # No relevant response
			
		# # Send the response with optional chart
		# chart_path = chart['path'] if chart else None
		# await self.send_delayed_response(message.channel, response, chart_path)

# Initialize and run bot
bot = CryptoGainEngagementBot()
bot.run(os.getenv("DISCORD_BOT_TOKEN", ""))