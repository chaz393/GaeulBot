import psycopg2
import os
from DBMigrations import DBMigrations


class PostgresDao:

    db_version = 5
    dbMigrations = DBMigrations()

    def __init__(self):
        self.conn = psycopg2.connect(host=os.getenv('PGHOST'),
                                     dbname=os.getenv('POSTGRES_DB'),
                                     user=os.getenv('POSTGRES_USER'),
                                     password=os.getenv('POSTGRES_PASSWORD'))
        self.cursor = self.conn.cursor()

    def attempt_migrations(self):
        current_version = self.get_db_version()
        print("current db version: {0}, target db version {1}".format(current_version, self.db_version))
        if current_version < self.db_version:
            for migrate_from in range(current_version, self.db_version):
                print('migrating db from {0} to {1}'.format(migrate_from, migrate_from + 1))
                migration = self.dbMigrations.migrations.get(migrate_from)
                migration(self.conn)

    def get_db_version(self):
        try:
            self.cursor.execute("SELECT dbversion FROM app_info")
            rows = self.cursor.fetchall()
            return rows[0][0]
        except:
            self.conn.commit()
            return 1

    def set_latest_story_id(self, username, last_story_id):
        self.cursor.execute("UPDATE user_info SET last_story_id = {0} WHERE username = '{1}';"
                            .format(last_story_id, username))
        self.conn.commit()

    def set_latest_post_id(self, username, last_post_id):
        self.cursor.execute("UPDATE user_info SET last_post_id = {0} WHERE username = '{1}';"
                            .format(last_post_id, username))
        self.conn.commit()

    def register_user(self, username, userid, latest_post_id, latest_story_id, new_channel_id):
        self.cursor.execute("INSERT INTO registrations(username, channel) VALUES ('{0}', {1});"
                            .format(username, new_channel_id))
        self.cursor.execute("INSERT INTO user_info(username, userid, last_post_id, last_story_id) VALUES "
                            "('{0}', {1}, {2}, {3}) ON CONFLICT DO NOTHING;"
                            .format(username, userid, latest_post_id, latest_story_id))
        self.conn.commit()

    def get_registered_users_in_channel(self, channel_id):
        self.cursor.execute("SELECT username FROM registrations WHERE channel = '{0}' AND user_disabled = false;".format(channel_id))
        rows = self.cursor.fetchall()
        users = []
        for row in rows:
            users.append(row[0])
        return users

    def delete_user_channel_mapping(self, username, channel_id):
        self.cursor.execute("DELETE FROM registrations WHERE username = '{0}' AND channel = {1};"
                            .format(username, channel_id))
        self.conn.commit()

    def delete_user_info(self, username):
        self.cursor.execute("DELETE FROM user_info WHERE username = '{0}';"
                            .format(username))
        self.conn.commit()

    def get_userid_from_db(self, user):
        self.cursor.execute("SELECT userid FROM user_info WHERE username = '{0}';".format(user))
        rows = self.cursor.fetchall()
        return rows[0][0]

    def get_last_story_id_from_db(self, user):
        self.cursor.execute("SELECT last_story_id FROM user_info WHERE username = '{0}';".format(user))
        rows = self.cursor.fetchall()
        return rows[0][0]

    def get_last_post_id_from_db(self, user):
        self.cursor.execute("SELECT last_post_id FROM user_info WHERE username = '{0}';".format(user))
        rows = self.cursor.fetchall()
        return rows[0][0]

    def get_all_users(self):
        self.cursor.execute("SELECT DISTINCT username FROM user_info WHERE user_disabled = false;")
        rows = self.cursor.fetchall()
        users = []
        for row in rows:
            users.append(row[0])
        return users

    def get_channels_for_user(self, username):
        self.cursor.execute("SELECT channel FROM registrations WHERE username = '{0}';".format(username))
        rows = self.cursor.fetchall()
        channels = []
        for row in rows:
            channels.append(row[0])
        return channels

    def user_is_whitelisted(self, server_id, user_id):
        self.cursor.execute("SELECT * FROM whitelist WHERE server_id = {0} AND user_id = {1}"
                            .format(server_id, user_id))
        rows = self.cursor.fetchall()
        if len(rows) > 0:
            return True
        else:
            return False

    def whitelist_user(self, server_id, user_id):
        self.cursor.execute("INSERT INTO whitelist(server_id, user_id) VALUES({0}, {1})".format(server_id, user_id))
        self.conn.commit()

    def un_whitelist_user(self, server_id, user_id):
        self.cursor.execute("DELETE FROM whitelist WHERE server_id = {0} AND user_id = {1}".format(server_id, user_id))
        self.conn.commit()

    def get_whitelisted_user_ids_in_server(self, server_id):
        self.cursor.execute("SELECT user_id FROM whitelist WHERE server_id = {0}".format(server_id))
        rows = self.cursor.fetchall()
        user_ids = []
        for row in rows:
            user_ids.append(row[0])
        return user_ids

    def update_username(self, old_username, new_username):
        self.cursor.execute("UPDATE registrations SET username = \'{0}\' WHERE username = \'{1}\'"
                            .format(new_username, old_username))
        self.cursor.execute("UPDATE user_info SET username = \'{0}\' WHERE username = \'{1}\'"
                            .format(new_username, old_username))
        self.conn.commit()

    def stories_are_enabled(self):
        self.cursor.execute("SELECT stories_enabled FROM app_info")
        rows = self.cursor.fetchall()
        return rows[0][0]

    def enable_stories(self):
        self.cursor.execute("UPDATE app_info SET stories_enabled = true;")
        self.conn.commit()

    def disable_stories(self):
        self.cursor.execute("UPDATE app_info SET stories_enabled = false;")
        self.conn.commit()
