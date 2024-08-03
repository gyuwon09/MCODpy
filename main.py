from discord_webhook import DiscordWebhook, DiscordEmbed
import subprocess
import re
import configparser
import discord
import threading

#function for load properties from .properties 
def load_properties(file_path):
    config = configparser.ConfigParser()
    config.read(file_path, encoding='utf-8')
    return config

#load properties
config = load_properties('.properties')
WEBHOOK_URL = config['webhook']['url']
LAUNCHER = config['webhook']['launcher']
CHANNEL_ID = int(config['webhook']['channel_id'])

#extract player chatting from server log
def parse_log(log_file):
    match = re.search(r'\[\d{2}:\d{2}:\d{2}\] \[Server thread/INFO\] \[minecraft/MinecraftServer\]: <(.+)> (.+)', log_file)
    if match:
        user_id = match.group(1)
        message = match.group(2)
        return user_id, message
    return None, None

def send_to_discord(user_id, message):
    webhook = DiscordWebhook(url=WEBHOOK_URL)
    
    embed = DiscordEmbed(title=user_id, color='03b2f8')
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
        print(f'message recognition activated')

    async def on_message(self, message):
        if message.channel.id == CHANNEL_ID:
            print(message.content)
            send_command_to_process(process, f'tellraw @a "<{message.author}> {message.content}"')

intents = discord.Intents.default()
intents.message_content = True
client = MyClient(intents=intents)
client.run(config['webhook']['token'])
