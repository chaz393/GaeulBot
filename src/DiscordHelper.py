import discord


class DiscordHelper:

    @staticmethod
    async def send_post(post, channel_id, files, client):
        date = post.date_local.strftime("%y%m%d")
        post_url = 'https://www.instagram.com/p/{0}/'.format(post.shortcode)
        channel = client.get_channel(channel_id)
        await channel.send('`{0} {1} {2} \n {3}`'.format(date, post.owner_username, post_url, post.caption))
        for file_on_disk in files:
            await channel.send(file=discord.File(file_on_disk))

    @staticmethod
    async def send_story(storyitem, channel_id, files, client):
        date = storyitem.date_local.strftime("%y%m%d")
        channel = client.get_channel(channel_id)
        await channel.send('`{0} {1} IG Story`'.format(date, storyitem.owner_username))
        for file_on_disk in files:
            await channel.send(file=discord.File(file_on_disk))

    @staticmethod
    async def send_message(message, channel_id, client):
        try:
            channel = client.get_channel(channel_id)
            await channel.send(message)
        except Exception as e:
            print(e)
