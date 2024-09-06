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

    # Print a summary of actions taken
    print("Summary of actions taken:")
    for result in results:
        print(f"- {result['user']}: {result['status']}")

def setup_tasks(client: discord.Client):
    send_warning_loop.start(client)
