import instaloader
import discord
import os
import psycopg2
import contextlib
from discord.ext import tasks


class UserAlreadyRegisteredException(Exception):
    pass


class UserNotRegisteredException(Exception):
    pass


class UserNotFoundException(Exception):
    pass


client = discord.Client()
loader = instaloader.Instaloader(dirname_pattern='/downloads/{profile}/{shortcode}',
                                 filename_pattern='{date}',
                                 save_metadata=False,
                                 download_video_thumbnails=False,
                                 quiet=True)


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
        all_users = get_all_users()
        if len(all_users) == 0:
            await message.channel.send("There are no registered users")
            return
        else:
            await refresh_users(all_users, True, message.channel.id)
            return

    if message.content.startswith('$refresh'):
        print("refreshing users in {0} {1}".format(message.channel.name, str(message.channel.id)))
        users = get_registered_users_in_channel(message.channel.id)
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
        users = get_registered_users_in_channel(message.channel.id)
        print(users)
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
            post = get_post_from_shortcode(shortcode)
            download_post(post)
            files = get_files(post)
            await send_post(post, message.channel.id, files)
        return


def get_posts(user, last_id):
    profile = instaloader.Profile.from_username(loader.context, user)
    posts = []
    for post in profile.get_posts():
        if post.mediaid <= last_id:
            break
        posts.append(post)
    posts.sort(key=getMediaId)
    return posts


def get_post_from_shortcode(shortcode):
    return instaloader.Post.from_shortcode(loader.context, shortcode)


def get_latest_post_id_for_user(user):
    profile = instaloader.Profile.from_username(loader.context, user)
    for post in profile.get_posts():
        return post.mediaid


def download_post(post):
    loader.download_post(post, post.shortcode)


def get_files(post):
    files = []
    path = os.path.abspath("/downloads/" + post.owner_username + "/" + post.shortcode + "/")
    for (dirpath, dirnames, filenames) in os.walk(path):
        for file in filenames:
            if ".jpg" in file or ".mp4" in file:
                files.append(dirpath + "/" + file)
    return files


async def send_post(post, channel_id, files):
    date = post.date_local.strftime("%y%m%d")
    post_url = 'https://www.instagram.com/p/{0}/'.format(post.shortcode)
    channel = client.get_channel(channel_id)
    await channel.send('`{0} {1} {2} \n {3}`'.format(date, post.owner_username, post_url, post.caption))
    for file_on_disk in files:
        await channel.send(file=discord.File(file_on_disk))


async def send_message(message, channel_id):
    try:
        channel = client.get_channel(channel_id)
        await channel.send(message)
    except Exception as e:
        print(e)


def get_all_users():
    cursor.execute("SELECT DISTINCT username FROM  username_to_last_post_id;")
    rows = cursor.fetchall()
    users = []
    for row in rows:
        users.append(row[0])
    return users


def get_last_post_id(user):
    cursor.execute("SELECT last_post_id FROM username_to_last_post_id WHERE username = '{0}';".format(user))
    rows = cursor.fetchall()
    return rows[0][0]


def get_channels_for_user(user):
    cursor.execute("SELECT channel FROM username_to_channel WHERE username = '{0}';".format(user))
    rows = cursor.fetchall()
    channels = []
    for row in rows:
        channels.append(row[0])
    return channels


async def refresh_users(users, refresh_all_users, channel_sent_from):
    for user in users:
        last_post_id = get_last_post_id(user)
        channels = get_channels_for_user(user)
        posts = get_posts(user, last_post_id)
        if len(posts) == 0 and not refresh_all_users:
            await send_message('no update for {0}'.format(user), channel_sent_from)
        for post in posts:
            download_post(post)
            set_latest_post_id(user, post.mediaid)
            files = get_files(post)
            for channel in channels:
                print(str(post.mediaid) + ' ' + post.shortcode + ' in ' + str(channel))
                await send_post(post, channel, files)


def register_user(username, new_channel_id):
    # make sure user is not already registered in this channel
    for current_channel in get_channels_for_user(username):
        if new_channel_id == current_channel:
            raise UserAlreadyRegisteredException

    # fail if user can't be found on instagram
    latest_post_id = get_latest_post_id_for_user(username)
    if latest_post_id is None:
        raise UserNotFoundException

    cursor.execute("INSERT INTO username_to_channel(username, channel) VALUES ('{0}', {1});"
                   .format(username, new_channel_id))
    cursor.execute("INSERT INTO username_to_last_post_id(username, last_post_id) VALUES ('{0}', {1}) ON CONFLICT DO NOTHING;"
                   .format(username, latest_post_id))
    conn.commit()


def unregister_user(username, channel_id):
    users_in_channel = get_registered_users_in_channel(channel_id)
    if username not in users_in_channel:
        raise UserNotRegisteredException

    cursor.execute("DELETE FROM username_to_channel WHERE username = '{0}' AND channel = {1};"
                   .format(username, channel_id))
    conn.commit()

    # if this is the last channel this uer is registered in, delete last post id info
    if len(get_channels_for_user(username)) == 0:
        cursor.execute("DELETE FROM username_to_last_post_id WHERE username = '{0}';"
                       .format(username))
        conn.commit()


def set_latest_post_id(username, last_post_id):
    cursor.execute("UPDATE username_to_last_post_id SET last_post_id = {0} WHERE username = '{1}';"
                   .format(last_post_id, username))
    conn.commit()


def get_registered_users_in_channel(channel_id):
    cursor.execute("SELECT username FROM username_to_channel WHERE channel = '{0}';".format(channel_id))
    rows = cursor.fetchall()
    users = []
    for row in rows:
        users.append(row[0])
    return users


async def print_auto_refresh_message():
    if '{channel_id}' not in os.getenv('REFRESH_ALL_CHANNEL'):
        try:
            refresh_all_channel = int(os.getenv('REFRESH_ALL_CHANNEL'))
            await send_message("refreshing all", refresh_all_channel)
        except Exception as e:
            print(e)
            pass


def getMediaId(post):
    return post.mediaid


@tasks.loop(minutes=20)
async def auto_refresh():
    with contextlib.suppress(Exception):
        all_users = get_all_users()
        print('auto refreshing all users')
        await print_auto_refresh_message()
        await refresh_users(all_users, True, None)


if __name__ == "__main__":
    conn = psycopg2.connect(host=os.getenv('PGHOST'),
                            dbname=os.getenv('POSTGRES_DB'),
                            user=os.getenv('POSTGRES_USER'),
                            password=os.getenv('POSTGRES_PASSWORD'))
    cursor = conn.cursor()
    try:
        auto_refresh.start()
        client.run(os.getenv('DISCORD_TOKEN'))
    finally:
        auto_refresh.stop()
