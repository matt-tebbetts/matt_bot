
## tasks
@tasks.loop(hours=1)
async def send_warning_loop():
    print("Checking and sending Mini warnings...")
    users_to_warn = await find_users_to_warn(client)
    
    results = []

    for user in users_to_warn:
        try:
            await send_dm(user['discord_id_nbr'], f'Hi {user["name"]}, this is your reminder to complete the Mini!')
            results.append({'user': user['name'], 'status': 'Message sent'})
        except discord.Forbidden:
            results.append({'user': user['name'], 'status': 'Not in guild'})
        except Exception as e:
            results.append({'user': user['name'], 'status': f'Error: {e}'})

    print("Summary of actions taken:")
    for result in results:
        print(f"- {result['user']}: {result['status']}")

@send_warning_loop.before_loop
async def before_send_warning_loop():
    await client.wait_until_ready()
## /tasks
