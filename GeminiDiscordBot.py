import os
import re

import aiohttp
import discord
import google.generativeai as genai
from discord.ext import commands
from dotenv import load_dotenv

message_history = {}

load_dotenv()

GOOGLE_AI_KEY = os.getenv("GOOGLE_AI_KEY")
DISCORD_BOT_TOKEN = os.getenv("DISCORD_BOT_TOKEN")
MAX_HISTORY = int(os.getenv("MAX_HISTORY"))

# ... (rest of the code remains unchanged)

#---------------------------------------------Discord Code-------------------------------------------------
# Initialize Discord bot
bot = commands.Bot(command_prefix="!", intents=discord.Intents.default())

@bot.event
async def on_ready():
    print("----------------------------------------")
    print(f'Gemini Bot Logged in as {bot.user}')
    print("----------------------------------------")

# On Message Function
@bot.event
async def on_message(message):
    # Ignore messages sent by the bot
    if message.author == bot.user or message.mention_everyone:
        return

    # Check if the bot is mentioned or the message is a DM
    if bot.user.mentioned_in(message) or isinstance(message.channel, discord.DMChannel):
        # Start Typing to seem like something happened
        cleaned_text = clean_discord_message(message.content)

        async with message.channel.typing():
            # Check for image attachments
            if message.attachments:
                print("New Image Message FROM:" + str(message.author.id) + ": " + cleaned_text)
                # Currently no chat history for images
                for attachment in message.attachments:
                    # these are the only image extensions it currently accepts
                    if any(attachment.filename.lower().endswith(ext) for ext in ['.png', '.jpg', '.jpeg', '.gif', '.webp']):
                        await message.add_reaction('🎨')

                        async with aiohttp.ClientSession() as session:
                            async with session.get(attachment.url) as resp:
                                if resp.status != 200:
                                    await message.channel.send('Unable to download the image.')
                                    return
                                image_data = await resp.read()
                                response_text = await generate_response_with_image_and_text(image_data, cleaned_text)
                                # Split the Message so discord does not get upset
                                await split_and_send_messages(message, response_text, 1700)
                                return
            # Not an Image do text response
            else:
                print("New Message FROM:" + str(message.author.id) + ": " + cleaned_text)
                # Check for Keyword Reset
                if "RESET" in cleaned_text:
                    # End back message
                    if message.author.id in message_history:
                        del message_history[message.author.id]
                    await message.channel.send("🤖 History Reset for user: " + str(message.author.name))
                    return
                await message.add_reaction('💬')

                # Check if history is disabled just send response
                if MAX_HISTORY == 0:
                    response_text = await generate_response_with_text(cleaned_text)
                    # add AI response to history
                    await split_and_send_messages(message, response_text, 1700)
                    return

                # Add users question to history
                update_message_history(message.author.id, cleaned_text)
                response_text = await generate_response_with_text(get_formatted_message_history(message.author.id))
                # add AI response to history
                update_message_history(message.author.id, response_text)
                # Split the Message so discord does not get upset
                await split_and_send_messages(message, response_text, 1700)

# ----------------------------------------- Slash Commands -------------------------------------------------

@bot.slash(name="reset", description="Reset chat history")
async def reset(ctx):
    # Reset chat history for the user
    if ctx.author.id in message_history:
        del message_history[ctx.author.id]
    await ctx.send("🤖 History Reset for user: " + str(ctx.author.name))

@bot.slash(name="history", description="View chat history")
async def history(ctx):
    # Get and send chat history for the user
    history_text = get_formatted_message_history(ctx.author.id)
    await ctx.send(history_text)

@bot.slash(name="generate", description="Generate response")
async def generate(ctx, *, text: str):
    # Generate response and send it
    response_text = await generate_response_with_text(text)
    update_message_history(ctx.author.id, text)
    update_message_history(ctx.author.id, response_text)
    await ctx.send(response_text)

# --------------------------------------------- Run Bot -------------------------------------------------
bot.run(DISCORD_BOT_TOKEN)
