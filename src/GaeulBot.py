import discord
import os
import contextlib
import datetime
import time
from discord.ext import tasks
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

postgresDao = PostgresDao()
instaHelper = InstaHelper()
intents = discord.Intents.default()
intents.members = True
intents.guilds = True
client = discord.Client(intents=intents)
first_refresh = True
help_text = 'Use $register {username} to register a user. ($register p_fall99) \n' \
            'Use $refresh to refresh the current users. \n' \
            'Use $users to see current users. \n' \
            'Use $unregister {username} to unregister a user. ($unregister p_fall99) \n' \
            'If you have any questions DM fanchazstic#6151 or join the ' \
            'GaeulBot server for help https://discord.gg/63fdDSzdrr'


@client.event
async def on_ready():
    print('logged in as {0.user}'.format(client))
    await client.change_presence(activity=discord.Game(name="$help"))
    channel_id = os.getenv('REFRESH_ALL_CHANNEL')
    if '{channel_id}' not in channel_id and len(channel_id) > 0:
        try:
            refresh_all_channel = int(os.getenv('REFRESH_ALL_CHANNEL'))
            await DiscordHelper.send_message('Online', refresh_all_channel, client)
        except:
            pass


@client.event
async def on_message(message):
    msg = message.content
    channel_name = message.channel.name
    channel_id = message.channel.id

    if message.author == client.user:
        return

    if msg.startswith('$ping'):
        await DiscordHelper.send_message('pong', channel_id, client)
        return

    if msg.startswith('$help'):
        await DiscordHelper.send_message(help_text, channel_id, client)
        return

    if msg.startswith('$refresh all') and str(message.author.id) == os.getenv('BOT_OWNER_ID'):
        print("refreshing all, called in {0} {1}".format(channel_name, str(channel_id)))
        all_users = postgresDao.get_all_users()
        if len(all_users) == 0:
            await DiscordHelper.send_message('There are no registered users', channel_id, client)
            return
        else:
            await refresh_users(all_users, True, channel_id)
            return

    if msg.startswith('$refresh'):
        print("refreshing users in {0} {1}".format(channel_name, str(channel_id)))
        users = postgresDao.get_registered_users_in_channel(channel_id)
        if len(users) == 0:
            await DiscordHelper.send_message('There are no registered users in {0}'.format(channel_name),
                                             channel_id,
                                             client)
            return
        else:
            await refresh_users(users, False, channel_id)
            return

    if msg.startswith('$register') and \
            DiscordHelper.user_is_allowed_to_register(message.author,
                                                      postgresDao.user_is_whitelisted(message.guild.id,
                                                                                      message.author.id),
                                                      message.guild):
        if len(msg.split(' ')) == 2:  # if it has 2 args (command and username)
            username = msg.split(' ')[1]
            print("registering {0} in {1} {2}".format(username, channel_name, str(channel_id)))
            try:
                register_user(username, channel_id)
                print("{0} has been registered".format(username))
                await DiscordHelper.send_message('{0} has been registered'.format(username), channel_id, client)
                return
            except UserAlreadyRegisteredException:
                print("{0} is already registered in {1}".format(username, channel_name))
                await DiscordHelper.send_message("{0} is already registered in {1}".format(username, channel_name),
                                                 channel_id,
                                                 client)
                return
            except UserNotFoundException:
                print("{0} was not found on instagram, check the spelling".format(username))
                await DiscordHelper.send_message("{0} was not found on instagram, check the spelling".format(username),
                                                 channel_id,
                                                 client)
                return
            except Exception as e:
                print(e)
                await DiscordHelper.send_message("An error has occurred", channel_id, client)
                return

    if msg.startswith('$unregister') and \
            DiscordHelper.user_is_allowed_to_register(message.author,
                                                      postgresDao.user_is_whitelisted(message.guild.id,
                                                                                      message.author.id),
                                                      message.guild):
        if len(msg.split(' ')) == 2:  # if it has 2 args (command and username)
            username = msg.split(' ')[1]
            print("unregistering {0} in {1} {2}".format(username, channel_name, str(channel_id)))
            try:
                unregister_user(username, channel_id)
                print('{0} was unregistered from {1}'.format(username, channel_name))
                await DiscordHelper.send_message('{0} was unregistered from {1}'.format(username, channel_name),
                                                 channel_id,
                                                 client)
            except UserNotRegisteredException:
                print('{0} is not registered in {1}'.format(username, channel_name))
                await DiscordHelper.send_message('{0} is not registered in {1}'.format(username, channel_name),
                                                 channel_id,
                                                 client)
            return

    if msg.startswith('$users all') and str(message.author.id) == os.getenv('BOT_OWNER_ID'):
        users = postgresDao.get_all_users()
        users_string = ""
        for user in users:
            users_string = users_string + " " + user
        if len(users) == 0:
            await DiscordHelper.send_message("There are no registered users", channel_id, client)
        else:
            await DiscordHelper.send_message("Currently registered users: {0}".format(users_string), channel_id, client)
        return

    if msg.startswith('$users'):
        users = postgresDao.get_registered_users_in_channel(channel_id)
        users_string = ""
        for user in users:
            users_string = users_string + " " + user
        if len(users) == 0:
            await DiscordHelper.send_message("There are no registered users in {0}".format(channel_name),
                                             channel_id,
                                             client)
        else:
            await DiscordHelper.send_message("Currently registered users in {0}: {1}"
                                             .format(channel_name, users_string),
                                             channel_id,
                                             client)
        return

    if msg.startswith('$getpost'):
        if len(msg.split(' ')) == 2:  # if it has 2 args (command and shortcode)
            shortcode = msg.split(' ')[1]
            print("getting post {0} in {1} {2}".format(shortcode, channel_name, channel_id))
            post = instaHelper.get_post_from_shortcode(shortcode)
            files = get_post_files(post)
            await DiscordHelper.send_post(post, channel_id, files, client)
        return

    if msg.startswith('$whitelist') and \
            DiscordHelper.user_is_mod(message.author, message.guild) and \
            len(msg.split(' ')) == 2:  # if it has 2 args (command and username)
        username = msg.split(' ')[1]
        user_id = strip_username_to_user_id(username)
        try:
            whitelist_user(message.guild.id, user_id)
            await DiscordHelper.send_message('{0} has been whitelisted in this server'.format(username),
                                             channel_id,
                                             client)
            return
        except UserAlreadyWhitelistedException:
            await DiscordHelper.send_message('{0} is already whitelisted in this server'.format(username),
                                             channel_id,
                                             client)
            return
        except:
            await DiscordHelper.send_message('An error has occurred', channel_id, client)
            return

    if msg.startswith('$unwhitelist') and DiscordHelper.user_is_mod(message.author, message.guild):
        if len(msg.split(' ')) == 2:  # if it has 2 args (command and username)
            username = msg.split(' ')[1]
            user_id = strip_username_to_user_id(username)
            try:
                unwhitelist_user(message.guild.id, user_id)
                await DiscordHelper.send_message('{0} has been unwhitelisted in this server'.format(username),
                                                 channel_id,
                                                 client)
                return
            except UserNotWhitelistedException:
                await DiscordHelper.send_message('{0} is not whitelisted in this server'.format(username),
                                                 channel_id,
                                                 client)
                return
            except:
                await DiscordHelper.send_message('An error has occurred', channel_id, client)
                return

    if msg.startswith('$whitelist') and \
            DiscordHelper.user_is_mod(message.author, message.guild) and \
            len(msg.split(' ')) == 1:  # if it is only the whitelist command
        try:
            users = get_whitelisted_users(message.guild.id)
            users_string = ""
            for user in users:
                users_string = users_string + " " + user
            if len(users) == 0:
                await DiscordHelper.send_message("There are no whitelisted users in this server.",
                                                 channel_id,
                                                 client)
                return
            else:
                await DiscordHelper.send_message("Currently whitelisted users in this server: {0}"
                                                 .format(users_string),
                                                 channel_id,
                                                 client)
                return
        except:
            await DiscordHelper.send_message('An error has occurred', channel_id, client)
            return

    if msg.startswith('$stories'):
        if instaHelper.stories_enabled:
            await DiscordHelper.send_message('stories are currently disabled')
        else:
            await DiscordHelper.send_message('stories are currently enabled')


async def refresh_users(users, refresh_all_users, channel_sent_from):
    if refresh_all_users:
        await DiscordHelper.send_message("refreshing all", channel_sent_from, client)
        start_time = datetime.datetime.now().timestamp()
    await refresh_posts(users, refresh_all_users, channel_sent_from)
    if instaHelper.stories_enabled:
        await refresh_stories(users, refresh_all_users, channel_sent_from)
    if refresh_all_users:
        end_time = datetime.datetime.now().timestamp()
        duration = round(end_time - start_time, 1)
        await DiscordHelper.send_message("done refreshing in {0}s".format(duration), channel_sent_from, client)


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
        await send_stories(storyitems, user, channels)


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
        instaHelper.download_post(post)
        files = get_post_files(post)
        for channel in channels:
            print('{0} {1} in {2}'.format(post.mediaid, post.shortcode, channel))
            await DiscordHelper.send_post(post, channel, files, client)
        postgresDao.set_latest_post_id(user, post.mediaid)


async def send_stories(storyitems, user, channels):
    for storyitem in storyitems:
        instaHelper.download_storyitem(storyitem)
        files = get_files(storyitem)
        for channel in channels:
            print('{0} {1} in {2}'.format(storyitem.mediaid, storyitem.shortcode, channel))
            await DiscordHelper.send_story(storyitem, channel, files, client)
        postgresDao.set_latest_story_id(user, storyitem.mediaid)


def get_post_files(post):
    try:
        files = get_files(post)
        if len(files) == post.mediacount:
            print('skipping download for {0}, files already exist'.format(post.shortcode))
            return files
        else:
            raise FilesNotFoundException
    except:
        print('downloading files for {0}'.format(post.shortcode))
        instaHelper.download_post(post)
        return get_files(post)


def get_files(item):
    files = []
    path = os.path.abspath("/downloads/" + item.owner_username + "/" + item.shortcode + "/")
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
            print('refresh interval set to {0} minutes'.format(refresh_interval))
            return int(refresh_interval)
        except:
            print('refresh interval is invalid, defaulting to 60 minutes')
            return 60


@tasks.loop(minutes=get_refresh_interval())
async def auto_refresh():
    with contextlib.suppress(Exception):
        global first_refresh
        # it always tries to run this when first starting and fails because the bot hasn't started yet
        if not first_refresh:
            all_users = postgresDao.get_all_users()
            print('auto refreshing all users')
            await print_auto_refresh_message(True, None)
            start_time = datetime.datetime.now().timestamp()
            await refresh_users(all_users, True, None)
            end_time = datetime.datetime.now().timestamp()
            duration = round(end_time - start_time, 1)
            await print_auto_refresh_message(False, duration)
        else:
            first_refresh = False


if __name__ == "__main__":
    try:
        postgresDao.attempt_migrations()
        auto_refresh.start()
        client.run(os.getenv('DISCORD_TOKEN'))
    finally:
        auto_refresh.stop()
