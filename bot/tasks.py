import discord
from discord.ext import tasks
from jobs.mini_warning import find_users_to_warn

@tasks.loop(hours=1)
async def send_warning_loop(client: discord.Client):
    print("Checking and sending Mini warnings...")
    users_to_warn = await find_users_to_warn()  # Fetch users who need a warning
    msg = "this is your reminder to complete the Mini!"
    results = []
    for user in users_to_warn:
        discord_user = await client.fetch_user(user['discord_id_nbr'])
        try:
            await discord_user.send(f'Hi {user["name"]}, {msg}')
            results.append({'user': user['name'], 'status': 'Message sent'})
        except:
            results.append({'user': user['name'], 'status': 'Message failed'})

    # print
    print(f"Mini warning summary: {results}")

def setup_tasks(client: discord.Client):
    print("setup_tasks activated")
    send_warning_loop.start(client)
    print("send_warning_loop started")
