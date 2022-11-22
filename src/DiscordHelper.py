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
        header_message = await channel.send(message)
        skipped = 0
        for file_on_disk in files:
            size = os.path.getsize(file_on_disk)/1024/1024  # bytes to MB
            if size < 8:  # 8MB is the max file size allowed for a non-nitro account
                await channel.send(file=discord.File(file_on_disk))
            else:
                skipped = skipped + 1
                print('{0} is {1}M, skipping file'.format(file_on_disk, round(size, 2)))
        if skipped == len(files):
            if skipped == 0:
                print('deleting post {0}, no files found'.format(post.shortcode))
            else:
                print('deleting post {0}, all messages were skipped'.format(post.shortcode))
            await header_message.delete()

    @staticmethod
    def build_post_message(post):
        date = post.date.replace(tzinfo=timezone.utc).astimezone(tz=pytz.timezone('Asia/Seoul')).strftime("%y%m%d")
        post_url = 'https://www.instagram.com/p/{0}/'.format(post.shortcode)
        message = ('`{0} {1} {2}'.format(date, post.owner_username, post_url))
        if post.caption is not None and len(post.caption) > 0:
            message = message + '\n{0}'.format(post.caption)
        message = message + '`'
        return message

    @staticmethod
    async def send_story(storyitem, channel_id, files, client):
        date = storyitem.date.replace(tzinfo=timezone.utc).astimezone(tz=pytz.timezone('Asia/Seoul')).strftime("%y%m%d")
        channel = client.get_channel(channel_id)
        header_message = await channel.send('`{0} {1} IG Story`'.format(date, storyitem.owner_username))
        skipped = 0
        for file_on_disk in files:
            size = os.path.getsize(file_on_disk)/1024/1024  # bytes to MB
            if size < 8:  # 8MB is the max file size allowed for a non-nitro account
                await channel.send(file=discord.File(file_on_disk))
            else:
                skipped = skipped + 1
                print('{0} is {1}M, skipping file'.format(file_on_disk, round(size, 2)))
        if skipped == len(files):
            if skipped == 0:
                print('deleting story {0}, no files found'.format(storyitem.shortcode))
            else:
                print('deleting story {0}, all messages were skipped'.format(storyitem.shortcode))
            await header_message.delete()

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
            if 'mod' in role.name.lower():
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

    # this responds to the interaction
    # be careful using if there's a chance the interaction could have already been responded to
    @staticmethod
    async def send_story_status(logged_in, stories_are_enabled, interaction):
        if not logged_in and stories_are_enabled:
            await interaction.response.send_message("Stories are enabled but unavailable due to login error. "
                                                    "Check logs")
        elif logged_in and stories_are_enabled:
            await interaction.response.send_message("Stories are enabled")
        elif not stories_are_enabled:
            await interaction.response.send_message("Stories are disabled")