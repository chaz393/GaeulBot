import discord
import os
from discord import errors
from datetime import timezone
import pytz


class DiscordHelper:

    @staticmethod
    async def send_post(post, channel_id, files, client):
        channel = client.get_channel(channel_id)
        message = DiscordHelper.build_post_message(post)
        await channel.send(message)
        for file_on_disk in files:
            await channel.send(file=discord.File(file_on_disk))

    @staticmethod
    def build_post_message(post):
        date = post.date.replace(tzinfo=timezone.utc).astimezone(tz=pytz.timezone('Asia/Seoul')).strftime("%y%m%d")
        post_url = 'https://www.instagram.com/p/{0}/'.format(post.shortcode)
        message = ('`{0} {1} {2}'.format(date, post.owner_username, post_url))
        if len(post.caption) > 0:
            message = message + '\n{0}'.format(post.caption)
        message = message + '`'
        return message

    @staticmethod
    async def send_story(storyitem, channel_id, files, client):
        date = storyitem.date.replace(tzinfo=timezone.utc).astimezone(tz=pytz.timezone('Asia/Seoul')).strftime("%y%m%d")
        channel = client.get_channel(channel_id)
        await channel.send('`{0} {1} IG Story`'.format(date, storyitem.owner_username))
        for file_on_disk in files:
            await channel.send(file=discord.File(file_on_disk))

    @staticmethod
    async def send_message(message, channel_id, client):
        try:
            channel = client.get_channel(channel_id)
            await channel.send(message)
        except errors.Forbidden:
            print('Can\'t send message in {0}, permission denied'.format(channel_id))
        except Exception as e:
            print(e)

    @staticmethod
    def user_has_mod_role(user):
        for role in user.roles:
            if role.name.lower().contains("mod"):
                return True
        return False

    @staticmethod
    def user_is_allowed_to_register(user, user_whitelisted, guild):
        return user.id == guild.owner.id or \
               user_whitelisted or \
               DiscordHelper.user_has_mod_role(user) or \
               str(user.id) == os.getenv('BOT_OWNER_ID')

    @staticmethod
    def user_is_mod(user, guild):
        return user.id == guild.owner.id or \
               DiscordHelper.user_has_mod_role(user) or \
               str(user.id) == os.getenv('BOT_OWNER_ID')
