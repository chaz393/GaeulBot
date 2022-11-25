import discord
import os
import contextlib
import datetime
import time
import traceback
import random
import asyncio
from discord import app_commands
from discord import Interaction
from discord.ext import tasks
from ItemType import ItemType
from PostgresDao import PostgresDao
from InstaHelper import InstaHelper
from DiscordHelper import DiscordHelper
from GaeulBotExceptions import UserAlreadyRegisteredException
from GaeulBotExceptions import UserNotRegisteredException
from GaeulBotExceptions import UserNotFoundException
from GaeulBotExceptions import UserAlreadyWhitelistedException
from GaeulBotExceptions import UserNotWhitelistedException
from GaeulBotExceptions import FilesNotFoundException


time.sleep(5)  # give time for db to start up

disable_insta_login = False

postgresDao = PostgresDao()
instaHelper = InstaHelper()
intents = discord.Intents.default()
intents.members = True
intents.guilds = True
first_refresh = True
client = discord.Client(intents=intents)
help_text = 'Use /register {username} to register a user. (/register p_fall99) \n' \
            'Use /refresh to refresh the current users. \n' \
            'Use /users to see current users. \n' \
            'Use /unregister {username} to unregister a user. (/unregister p_fall99) \n' \
            'If you have any questions join the GaeulBot server for help https://discord.gg/63fdDSzdrr'
tree = app_commands.CommandTree(client)
guild = None
if os.getenv('DEV_MODE') is not None and os.getenv('DEV_MODE').lower() == "true" and os.getenv('DEV_GUILD'):
    print(f"Dev mode, setting guild to {os.getenv('DEV_GUILD')}")
    guild = discord.Object(id=int(os.getenv('DEV_GUILD')))


@tree.command(name="ping", description="pong", guild=guild)
async def command_ping(interaction: Interaction):
    await interaction.response.send_message("pong")


@tree.command(name="help", description="Posts a help message with some command usage", guild=guild)
async def command_help(interaction: Interaction):
    await interaction.response.send_message(help_text)


@tree.command(name="refresh", description="Refreshes users in this channel", guild=guild)
async def command_refresh(interaction: Interaction):
    print(f"refreshing users in {interaction.channel.name} {interaction.channel.id}")
    await interaction.response.defer()
    users = postgresDao.get_registered_users_in_channel(interaction.channel.id)
    enabled_users = get_enabled_users(users)
    if len(enabled_users) == 0:
        await interaction.edit_original_response(content=f"There are no registered users in {interaction.channel.name}")
        return
    else:
        duration = await refresh_users(enabled_users, False, interaction.channel.id)
        await interaction.edit_original_response(content=f"Refresh completed in {duration}s")
        return


@tree.command(name="refresh-all", description="Refreshes all users in all channels", guild=guild)
async def command_refresh_all(interaction: Interaction):
    if not str(interaction.user.id) == os.getenv('BOT_OWNER_ID'):
        await interaction.response.send_message("You do not have permission to use this command")
        return
    await interaction.response.defer()
    print(f"refreshing all, called in {interaction.channel.name} {interaction.channel.id}")
    all_users = postgresDao.get_all_enabled_users()
    if len(all_users) == 0:
        await interaction.edit_original_response(content="There are no registered users")
        return
    else:
        duration = await refresh_users(all_users, True, interaction.channel.id)
        await interaction.edit_original_response(content=f"Done auto refreshing in {duration}s")
        return


@tree.command(name="refresh-stories", description="Refreshes stories for users in this channel", guild=guild)
async def command_refresh_stories(interaction: Interaction):
    if not instaHelper.logged_in or not postgresDao.stories_are_enabled():
        await interaction.response.send_message("Stories are not enabled or are unavailable")
        return
    await interaction.response.defer()
    users = postgresDao.get_registered_users_in_channel(interaction.channel.id)
    enabled_users = get_enabled_users(users)
    if len(enabled_users) == 0:
        await interaction.edit_original_response(content=f"There are no registered users in {interaction.channel.name}")
        return
    else:
        start_time = datetime.datetime.now().timestamp()
        await refresh_stories(users, False, interaction.channel.id)
        end_time = datetime.datetime.now().timestamp()
        duration = round(end_time - start_time, 1)
        await interaction.edit_original_response(content=f"Refresh completed in {duration}s")
        return


@tree.command(name="users", description="Prints a list of users registered in this channel", guild=guild)
async def command_users(interaction: Interaction):
    users = postgresDao.get_registered_users_in_channel(interaction.channel.id)
    users_string = get_users_string(users)
    if len(users) == 0:
        await interaction.response.send_message(f"There are no registered users in {interaction.channel.name}")
    else:
        await interaction.response.send_message(f"Currently registered users in {interaction.channel.name}:"
                                                f" ```{users_string}```")


@tree.command(name="users-all", description="Prints a list of all users registered in any channel", guild=guild)
async def command_users_all(interaction: Interaction):
    if not str(interaction.user.id) == os.getenv('BOT_OWNER_ID'):
        await interaction.response.send_message("You do not have permission to use this command")
        return
    users = postgresDao.get_all_users()
    users_string = get_users_string(users)
    if len(users) == 0:
        await interaction.response.send_message("There are no registered users")
    else:
        await interaction.response.send_message(f"Currently registered users: ```{users_string}```")


@tree.command(name="registrations",
              description="Prints a list of all users and which channels they're registered in",
              guild=guild)
async def command_registrations(interaction: Interaction):
    await interaction.response.defer()
    users = postgresDao.get_all_users()
    for user in users:
        channels = postgresDao.get_channels_for_user(user)
        await DiscordHelper.send_message(get_channels_string(user, channels), interaction.channel.id, client)
    await interaction.edit_original_response(content="Done printing registrations")


@tree.command(name="stories", description="Prints whether or not stories are enabled", guild=guild)
async def command_stories(interaction: Interaction):
    await DiscordHelper.send_story_status(instaHelper.logged_in,
                                          postgresDao.stories_are_enabled(),
                                          postgresDao.get_disable_auto_refresh_stories(),
                                          interaction)


@tree.command(name="set-stories-enabled", description="Enabled or disables stories globally", guild=guild)
async def command_set_stories_enabled(interaction: Interaction, enable: bool):
    if not str(interaction.user.id) == os.getenv('BOT_OWNER_ID'):
        await interaction.response.send_message("You do not have permission to use this command")
        return
    if enable:
        postgresDao.enable_stories()
    else:
        postgresDao.disable_stories()
    await DiscordHelper.send_story_status(instaHelper.logged_in,
                                          postgresDao.stories_are_enabled(),
                                          postgresDao.get_disable_auto_refresh_stories(),
                                          interaction)


@tree.command(name="retry-instagram-login", description="Retries instagram login", guild=guild)
async def command_retry_instagram_login(interaction: Interaction):
    if not str(interaction.user.id) == os.getenv('BOT_OWNER_ID'):
        await interaction.response.send_message("You do not have permission to use this command")
        return
    if postgresDao.stories_are_enabled():
        print("retrying insta login")
        await interaction.response.send_message("Attempting login...")
        try_insta_login()
    else:
        await interaction.response.send_message("Stories are not enabled")


@tree.command(name="register", description="Register an instagram user to this channel", guild=guild)
async def command_register(interaction: Interaction, username: str):
    if not DiscordHelper.user_is_allowed_to_register(interaction.user, False, interaction.guild):
        await interaction.response.send_message("You do not have permission to use this command")
        return
    print(f"registering {username} in {interaction.channel.name} {interaction.channel.id}")
    await interaction.response.defer()
    try:
        register_user(username, interaction.channel.id)
        await interaction.edit_original_response(content=f"{username} has been registered")
        return
    except UserAlreadyRegisteredException:
        print(f"{username} is already registered in {interaction.channel.id}")
        await interaction.edit_original_response(content=
                                                 f"{username} is already registered in {interaction.channel.name}")
        return
    except UserNotFoundException:
        print(f"{username} was not found on instagram, check the spelling")
        await interaction.edit_original_response(content=f"{username} was not found on instagram, check the spelling")
        return
    except Exception as e:
        print(e)
        await interaction.edit_original_response(content="An error has occurred")
        return


@tree.command(name="unregister", description="Unregisters an instagram user from this channel", guild=guild)
async def command_unregister(interaction: Interaction, username: str):
    if not DiscordHelper.user_is_allowed_to_register(interaction.user, False, interaction.guild):
        await interaction.response.send_message("You do not have permission to use this command")
        return
    print(f"unregistering {username} in {interaction.channel.name} {interaction.channel.id}")
    await interaction.response.defer()
    try:
        unregister_user(username, interaction.channel.id)
        print(f"{username} was unregistered from {interaction.channel.name}")
        await interaction.edit_original_response(content=
                                                 f"{username} has been unregistered from {interaction.channel.name}")
        return
    except UserNotRegisteredException:
        print(f"{username} is not registered in {interaction.channel.name}")
        await interaction.edit_original_response(content=f"{username} is not registered in {interaction.channel.name}")
        return
    except Exception as e:
        print(e)
        await interaction.edit_original_response(content="An error has occurred")
        return


@tree.command(name="get-post",
              description="Gets and posts an instagram post to this channel provided an post shortcode",
              guild=guild)
async def command_get_post(interaction: Interaction, shortcode: str):
    print(f"getting post {shortcode} in {interaction.channel.name} {interaction.channel.id}")
    await interaction.response.defer()
    try:
        post = instaHelper.get_post_from_shortcode(shortcode)
        files = get_post_files(post)
        await DiscordHelper.send_post(post, interaction.channel.id, files, client)
        await interaction.edit_original_response(content=f"Post {shortcode} has been posted")
    except Exception as e:
        print(f"There was an issue getting post {shortcode} in {interaction.channel.name}")
        print(e)
        await interaction.edit_original_response(content=f"There was an issue getting post {shortcode}")


@tree.command(name="get-stories",
              description="Gets and posts current instagram stories to this channel provided a username",
              guild=guild)
async def command_get_stories(interaction: Interaction, username: str):
    if not instaHelper.logged_in or not postgresDao.stories_are_enabled():
        await interaction.response.send_message("Stories are not enabled or are unavailable")
        return
    print(f"getting current stories for {username} in {interaction.channel.name} {interaction.channel.id}")
    await interaction.response.defer()
    try:
        userid = ""
        try:
            userid = postgresDao.get_userid_from_db(username)
        except:
            print(f"{username} not found in db, getting from instagram")
        if userid == "":
            profile = instaHelper.get_profile_from_username(username)
            userid = profile.userid
        storyitems = instaHelper.get_stories_for_user(userid, 0)
        await send_stories(storyitems, username, [interaction.channel.id], True)
        await interaction.edit_original_response(content=f"Stories for {username} have been sent")
    except Exception as exception:
        print(f"There was an issue getting stories for {username}")
        print(exception)
        await interaction.edit_original_response(content=f"There was an issue getting stories for {username}")


@tree.command(name="update-username",
              description="Updates a instagram users username, useful if a user changes their username",
              guild=guild)
async def command_update_username(interaction: Interaction, old_username: str, new_username: str):
    if not str(interaction.user.id) == os.getenv('BOT_OWNER_ID'):
        await interaction.response.send_message("You do not have permission to use this command")
        return
    if not len(postgresDao.get_channels_for_user(old_username)) > 0:
        await interaction.response.send_message(f"{old_username} is not registered in {interaction.channel.name}")
        return
    print(f"Updating user {old_username} to {new_username}")
    postgresDao.update_username(old_username, new_username)
    await interaction.response.send_message(f"Successfully updated {old_username} to {new_username}")


@tree.command(name="auto-refresh-stories",
              description="Enables/disables refreshing stories for auto refresh, /refresh, and /refresh-all",
              guild=guild)
async def command_disable_auto_refresh_stories(interaction: Interaction, enable: bool):
    if not str(interaction.user.id) == os.getenv('BOT_OWNER_ID'):
        await interaction.response.send_message("You do not have permission to use this command")
        return
    if enable:
        postgresDao.enabled_auto_refresh_stories()
        await interaction.response.send_message("Auto refresh stories has been enabled")
    else:
        postgresDao.disable_auto_refresh_stories()
        await interaction.response.send_message("Auto refresh stories has been disabled")


@client.event
async def on_ready():
    print('logged in as {0.user}'.format(client))
    await tree.sync(guild=guild)
    await post_bot_online_message()


async def post_bot_online_message():
    channel_id_string = os.getenv('REFRESH_ALL_CHANNEL')
    if '{channel_id}' not in channel_id_string and len(channel_id_string) > 0:
        try:
            channel_id = int(os.getenv('REFRESH_ALL_CHANNEL'))
            await DiscordHelper.send_message('Online', channel_id, client)
        except Exception as exception:
            print(exception)
            pass


async def refresh_users(users, refresh_all_users, channel_sent_from):
    start_time = datetime.datetime.now().timestamp()
    await refresh_posts(users, refresh_all_users, channel_sent_from)
    if instaHelper.logged_in and \
            postgresDao.stories_are_enabled() and \
            not postgresDao.get_disable_auto_refresh_stories():
        await refresh_stories(users, refresh_all_users, channel_sent_from)
    end_time = datetime.datetime.now().timestamp()
    # noinspection PyUnboundLocalVariable
    duration = round(end_time - start_time, 1)
    return duration


async def refresh_posts(users, refresh_all_users, channel_sent_from):
    for user in users:
        last_post_id = postgresDao.get_last_post_id_from_db(user)
        channels = postgresDao.get_channels_for_user(user)
        posts = instaHelper.get_posts(user, last_post_id)
        if len(posts) == 0 and not refresh_all_users:
            await DiscordHelper.send_message('no new posts for {0}'.format(user), channel_sent_from, client)
        await send_posts(posts, user, channels)


async def refresh_stories(users, refresh_all_users, channel_sent_from):
    for user in users:
        last_story_id = postgresDao.get_last_story_id_from_db(user)
        channels = postgresDao.get_channels_for_user(user)
        userid = postgresDao.get_userid_from_db(user)
        storyitems = instaHelper.get_stories_for_user(userid, last_story_id)
        if len(storyitems) == 0 and not refresh_all_users:
            await DiscordHelper.send_message('no new stories for {0}'.format(user), channel_sent_from, client)
        await send_stories(storyitems, user, channels, False)


def register_user(username, new_channel_id):
    # make sure user is not already registered in this channel
    for current_channel in postgresDao.get_channels_for_user(username):
        if new_channel_id == current_channel:
            raise UserAlreadyRegisteredException

    try:
        profile = instaHelper.get_profile_from_username(username)
    except Exception as e:
        # fail if user can't be found on instagram
        print(e)
        raise UserNotFoundException
    if profile is None:
        raise UserNotFoundException

    userid = profile.userid
    latest_post_id = instaHelper.get_latest_post_id_from_ig(profile)
    latest_story_id = instaHelper.get_latest_story_id_from_ig(userid)

    postgresDao.register_user(username, userid, latest_post_id, latest_story_id, new_channel_id)


def unregister_user(username, channel_id):
    users_in_channel = postgresDao.get_registered_users_in_channel(channel_id)
    if username not in users_in_channel:
        raise UserNotRegisteredException

    postgresDao.delete_user_channel_mapping(username, channel_id)

    # if this is the last channel this uer is registered in, delete last post id info
    if len(postgresDao.get_channels_for_user(username)) == 0:
        postgresDao.delete_user_info(username)


async def send_posts(posts, user, channels):
    for post in posts:
        try:
            files = get_post_files(post)
        except:
            print('There was an issue downloading {0}'.format(post.shortcode))
            traceback.print_exc()
            postgresDao.set_latest_post_id(user, post.mediaid)
            # this one is rough, if the download fails because an actual connection issue, it'll be skipped forever.
            # the other option is to not mark it as latest, but in any case that there is another post by this user,
            # that post will be set at the latest and this one will still be skipped forever
            # this is the most consistent way to handle this issue
            # this all came about because trying to download CNiXcG5nwpc was throwing
            # instaloader.exceptions.ConnectionException: download_pic(): HTTP error code 429
            # this post is an IGTV post and maybe that has something to do with it, but I don't see a way to
            # identify them before they fail to download.
            continue
        for channel in channels:
            print('{0} {1} in {2}'.format(post.mediaid, post.shortcode, channel))
            await DiscordHelper.send_post(post, channel, files, client)
        postgresDao.set_latest_post_id(user, post.mediaid)
        # sleep to hopefully make IG flag the account less often
        time.sleep(random.randint(1, 5))


async def send_stories(storyitems, user, channels, dont_update_last_story_id):
    for storyitem in storyitems:
        instaHelper.download_storyitem(storyitem)
        files = get_files(storyitem, ItemType.STORY)
        for channel in channels:
            print('{0} {1} in {2}'.format(storyitem.mediaid, storyitem.shortcode, channel))
            await DiscordHelper.send_story(storyitem, channel, files, client)
        if not dont_update_last_story_id:
            postgresDao.set_latest_story_id(user, storyitem.mediaid)
        # sleep to hopefully make IG flag the account less often
        time.sleep(random.randint(1, 5))


def get_post_files(post):
    try:
        files = get_files(post, ItemType.POST)
        if len(files) == post.mediacount:
            print('skipping download for {0}, files already exist'.format(post.shortcode))
            return files
        else:
            raise FilesNotFoundException
    except:
        print('downloading files for {0}'.format(post.shortcode))
        instaHelper.download_post(post)
        return get_files(post, ItemType.POST)


def get_files(item, item_type):
    files = []
    path = os.path.abspath("/downloads/{0}/{1}/{2}".format(item.owner_username, item_type.get_name(), item.shortcode))
    for (dirpath, dirnames, filenames) in os.walk(path):
        for file in filenames:
            if ".jpg" in file or ".mp4" in file:
                files.append(dirpath + "/" + file)
    files.sort()
    return files


def whitelist_user(server_id, user_id):
    if postgresDao.user_is_whitelisted(server_id, user_id):
        raise UserAlreadyWhitelistedException

    postgresDao.whitelist_user(server_id, user_id)


def unwhitelist_user(server_id, user_id):
    if not postgresDao.user_is_whitelisted(server_id, user_id):
        raise UserNotWhitelistedException

    postgresDao.un_whitelist_user(server_id, user_id)


def get_whitelisted_users(server_id):
    user_ids = postgresDao.get_whitelisted_user_ids_in_server(server_id)
    usernames = []
    for user_id in user_ids:
        try:
            user = client.get_user(user_id)
            usernames.append(user.name)
        except:
            continue
    return usernames


def strip_username_to_user_id(username):
    user_id = username
    for char in '<>@!':
        user_id = user_id.replace(char, '')
    return user_id


def get_users_string(users):
    users_string = ""
    for user in users:
        users_string = users_string + "\n" + user + ", disabled: {0}".format(postgresDao.is_user_disabled(user))
    return users_string


def get_channels_string(user, channels):
    channels_string = user + ":\n"
    for channel in channels:
        guild_name = client.get_channel(channel).guild.name
        channels_string = channels_string + "<#{0}> - {1}\n".format(channel, guild_name)
    return channels_string


def try_insta_login():
    username = os.getenv('INSTAGRAM_USERNAME')
    password = os.getenv('INSTAGRAM_PASSWORD')
    if not disable_insta_login and InstaHelper.login_info_is_valid(username, password):
        instaHelper.try_login(username, password)


async def print_auto_refresh_message(start, duration):
    channel_id = os.getenv('REFRESH_ALL_CHANNEL')
    if '{channel_id}' not in channel_id and len(channel_id) > 0:
        try:
            refresh_all_channel = int(os.getenv('REFRESH_ALL_CHANNEL'))
            if start:
                await DiscordHelper.send_message("refreshing all", refresh_all_channel, client)
            else:
                await DiscordHelper.send_message("done refreshing in {0}s".format(duration),
                                                 refresh_all_channel,
                                                 client)
        except Exception as e:
            print(e)
            pass


def get_refresh_interval():
    refresh_interval = os.getenv('REFRESH_INTERVAL')
    if len(refresh_interval) == 0:
        print('refresh interval not specified, defaulting to 60 minutes')
        return 60
    else:
        try:
            int_interval = int(refresh_interval)
            print('refresh interval set to {0} minutes'.format(refresh_interval))
            return int_interval
        except:
            print('refresh interval is invalid, defaulting to 60 minutes')
            return 60


def get_enabled_users(users):
    enabled_users = []
    for user in users:
        if not postgresDao.is_user_disabled(user):
            enabled_users.append(user)
    return enabled_users


@tasks.loop(minutes=get_refresh_interval())
async def auto_refresh():
    with contextlib.suppress(Exception):
        # it always tries to run this when first starting and fails because the bot hasn't started yet
        global first_refresh
        if first_refresh:
            first_refresh = False
            return
        all_users = postgresDao.get_all_enabled_users()
        print('auto refreshing all users')
        await print_auto_refresh_message(True, None)
        start_time = datetime.datetime.now().timestamp()
        await refresh_users(all_users, True, None)
        end_time = datetime.datetime.now().timestamp()
        duration = round(end_time - start_time, 1)
        print('done auto refreshing all users in {0}'.format(duration))
        await print_auto_refresh_message(False, duration)


async def start_bot():
    async with client:
        try:
            postgresDao.attempt_migrations()
            try:
                try_insta_login()
            except Exception as e:
                print('stories disabled due to login error')
                print(e)
            auto_refresh.start()
            await client.start(os.getenv('DISCORD_TOKEN'))
        finally:
            auto_refresh.stop()

if __name__ == "__main__":
    asyncio.run(start_bot())
