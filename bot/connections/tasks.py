import discord
from discord.ext import tasks
from bot.functions.mini_warning import find_users_to_warn

@tasks.loop(hours=1)
async def send_warning_loop(client: discord.Client):
    users_to_warn = await find_users_to_warn()  # Fetch users who need a warning
    
    if len(users_to_warn) == 0:
        print("tasks.py: No users to warn about the Mini right now")
        return
    
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
    print(f"tasks.py: Mini warning summary: {results}")

def setup_tasks(client: discord.Client):
    send_warning_loop.start(client)
