import discord
import os
import contextlib
from PostgresDao import PostgresDao
from InstaHelper import InstaHelper
from DiscordHelper import DiscordHelper
from GaeulBotExceptions import UserAlreadyRegisteredException
from GaeulBotExceptions import UserNotRegisteredException
from GaeulBotExceptions import UserNotFoundException
from discord.ext import tasks

postgresDao = PostgresDao()
instaHelper = InstaHelper()
client = discord.Client()
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


@client.event
async def on_message(message):
    if message.author == client.user:
        return

    if message.content.startswith('$ping'):
        await message.channel.send('pong')
        return

    if message.content.startswith('$help'):
        await message.channel.send(help_text)
        return

    if message.content.startswith('$refresh all') and str(message.author.id) == os.getenv('BOT_OWNER_ID'):
        print("refreshing all, called in {0} {1}".format(message.channel.name, str(message.channel.id)))
        all_users = postgresDao.get_all_users()
        if len(all_users) == 0:
            await message.channel.send("There are no registered users")
            return
        else:
            await refresh_users(all_users, True, message.channel.id)
            return

    if message.content.startswith('$refresh'):
        print("refreshing users in {0} {1}".format(message.channel.name, str(message.channel.id)))
        users = postgresDao.get_registered_users_in_channel(message.channel.id)
        if len(users) == 0:
            await message.channel.send("There are no registered users in {}".format(message.channel.name))
            return
        else:
            await refresh_users(users, False, message.channel.id)
            return

    if message.content.startswith('$register'):
        if len(message.content.split(' ')) == 2:  # if it has 2 args (command and username)
            username = message.content.split(' ')[1]
            print("registering {0} in {1} {2}".format(username, message.channel.name, str(message.channel.id)))
            try:
                register_user(username, message.channel.id)
                print("{0} has been registered".format(username))
                await message.channel.send('{0} has been registered'.format(username))
                return
            except UserAlreadyRegisteredException:
                print("{0} is already registered in {1}".format(username, message.channel.name))
                await message.channel.send("{0} is already registered in {1}".format(username, message.channel.name))
                return
            except UserNotFoundException:
                print("{0} was not found on instagram, check the spelling".format(username))
                await message.channel.send("{0} was not found on instagram, check the spelling".format(username))
                return
            except Exception as e:
                print(e)
                await message.channel.send("An error has occurred")
                return

    if message.content.startswith('$unregister'):
        if len(message.content.split(' ')) == 2:  # if it has 2 args (command and username)
            username = message.content.split(' ')[1]
            print("unregistering {0} in {1} {2}".format(username, message.channel.name, str(message.channel.id)))
            try:
                unregister_user(username, message.channel.id)
                print('{0} was unregistered from {1}'.format(username, message.channel.name))
                await message.channel.send('{0} was unregistered from {1}'.format(username, message.channel.name))
            except UserNotRegisteredException:
                print('{0} is not registered in {1}'.format(username, message.channel.name))
                await message.channel.send('{0} is not registered in {1}'.format(username, message.channel.name))
            return

    if message.content.startswith('$users'):
        users = postgresDao.get_registered_users_in_channel(message.channel.id)
        users_string = ""
        for user in users:
            users_string = users_string + " " + user
        if len(users) == 0:
            await message.channel.send("There are no registered users in {0}".format(message.channel.name))
        else:
            await message.channel.send("Currently registered users in {0}: {1}".format(message.channel.name, users_string))
        return

    if message.content.startswith('$getpost'):
        if len(message.content.split(' ')) == 2:  # if it has 2 args (command and username)
            shortcode = message.content.split(' ')[1]
            print("getting post {0} in {1} {2}".format(shortcode, message.channel.name, message.channel.id))
            post = instaHelper.get_post_from_shortcode(shortcode)
            instaHelper.download_post(post)
            files = get_files(post)
            await DiscordHelper.send_post(post, message.channel.id, files, client)
        return


async def refresh_users(users, refresh_all_users, channel_sent_from):
    await refresh_posts(users, refresh_all_users, channel_sent_from)
    if instaHelper.stories_enabled:
        await refresh_stories(users, refresh_all_users, channel_sent_from)


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
        postgresDao.set_latest_post_id(user, post.mediaid)
        files = get_files(post)
        for channel in channels:
            print(str(post.mediaid) + ' ' + post.shortcode + ' in ' + str(channel))
            await DiscordHelper.send_post(post, channel, files, client)


async def send_stories(storyitems, user, channels):
    for storyitem in storyitems:
        instaHelper.download_storyitem(storyitem)
        postgresDao.set_latest_story_id(user, storyitem.mediaid)
        files = get_files(storyitem)
        for channel in channels:
            print(str(storyitem.mediaid) + ' ' + storyitem.shortcode + ' in ' + str(channel))
            await DiscordHelper.send_story(storyitem, channel, files, client)


def get_files(item):
    files = []
    path = os.path.abspath("/downloads/" + item.owner_username + "/" + item.shortcode + "/")
    for (dirpath, dirnames, filenames) in os.walk(path):
        for file in filenames:
            if ".jpg" in file or ".mp4" in file:
                files.append(dirpath + "/" + file)
    return files


async def print_auto_refresh_message():
    if '{channel_id}' not in os.getenv('REFRESH_ALL_CHANNEL'):
        try:
            refresh_all_channel = int(os.getenv('REFRESH_ALL_CHANNEL'))
            await DiscordHelper.send_message("refreshing all", refresh_all_channel, client)
        except Exception as e:
            print(e)
            pass


@tasks.loop(minutes=20)
async def auto_refresh():
    with contextlib.suppress(Exception):
        all_users = postgresDao.get_all_users()
        print('auto refreshing all users')
        await print_auto_refresh_message()
        await refresh_users(all_users, True, None)


if __name__ == "__main__":
    try:
        auto_refresh.start()
        client.run(os.getenv('DISCORD_TOKEN'))
    finally:
        auto_refresh.stop()
