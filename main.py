from discord_webhook import DiscordWebhook, DiscordEmbed
import subprocess
import re
import configparser
import discord
import threading
import sys
import time

#function for load properties from .properties 
def load_properties(file_path):
    config = configparser.ConfigParser()
    config.read(file_path, encoding='utf-8')
    return config

#load properties
try:
    config = load_properties('properties.properties')
except:
    print("properties file not found")
    time.sleep(5)
    sys.exit()

WEBHOOK_URL = config['webhook']['url']
LAUNCHER = config['webhook']['launcher']
CHANNEL_ID = int(config['webhook']['channel_id'])
message_color = config['webhook']['message_color']

#extract player chatting from server log
def parse_log(log_file):
    match = re.search(r'\[\d{2}:\d{2}:\d{2}\] \[Server thread/INFO\]: <(.+)> (.+)', log_file)
    if match:
        user_id = match.group(1)
        message = match.group(2)
        print(user_id,":",message)
        return user_id, message
    return None, None

def send_to_discord(user_id, message):
    webhook = DiscordWebhook(url=WEBHOOK_URL)
    try:
        embed = DiscordEmbed(title=user_id, color=message_color)
        embed.add_embed_field(name='',value=message, inline=False)
    except:
        print("\n[        Error suspect        ]\ncheck 'message_color' varibles in '.properties' file\n")
        embed = DiscordEmbed(title=user_id, color="FF0000")
        embed.add_embed_field(name='',value=message, inline=False)
        
    
    webhook.add_embed(embed)
    response = webhook.execute()
    
    if response.status_code != 200:
        print(f"Error sending message to Discord: {response.status_code}, {response.content}")

def try_decode(output):
    try:
        return output.decode('utf-8').strip()
    except UnicodeDecodeError:
        try:
            return output.decode('cp949').strip()
        except UnicodeDecodeError:
            return output.decode('latin-1').strip()

def run_command(cmd):
    process = subprocess.Popen(cmd, stdout=subprocess.PIPE, stderr=subprocess.STDOUT, stdin=subprocess.PIPE)
    
    def read_output():
        while True:
            output = process.stdout.readline()
            if output == b'' and process.poll() is not None:
                break
            if output:
                log_line = try_decode(output)
                user_id, message = parse_log(log_line)
                if user_id and message:
                    send_to_discord(user_id, message)
                else:
                    print(log_line)

    threading.Thread(target=read_output, daemon=True).start()
    return process

def send_command_to_process(process, command):
    # 명령어를 프로세스의 표준 입력에 전송합니다.
    process.stdin.write((command + '\n').encode('utf-8'))
    process.stdin.flush()

process = run_command(['cmd', '/c', LAUNCHER])

class MyClient(discord.Client):
    async def on_ready(self):
        print(f'[     message recognition activated     ]')

    async def on_message(self, message):
        if message.author == self.user or message.author.bot or message.webhook_id:
            return
        
        if message.channel.id == CHANNEL_ID:
            print("discord message : ",message.content)
            send_command_to_process(process, f'tellraw @a "<{message.author}> {message.content}"')

intents = discord.Intents.default()
intents.message_content = True
client = MyClient(intents=intents)
client.run(config['webhook']['token'])
