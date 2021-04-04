import psycopg2
import os


class PostgresDao:

    def __init__(self):
        self.conn = psycopg2.connect(host=os.getenv('PGHOST'),
                                     dbname=os.getenv('POSTGRES_DB'),
                                     user=os.getenv('POSTGRES_USER'),
                                     password=os.getenv('POSTGRES_PASSWORD'))
        self.cursor = self.conn.cursor()

    def set_latest_story_id(self, username, last_story_id):
        self.cursor.execute("UPDATE user_info SET last_story_id = {0} WHERE username = '{1}';"
                            .format(last_story_id, username))
        self.conn.commit()

    def set_latest_post_id(self, username, last_post_id):
        self.cursor.execute("UPDATE user_info SET last_post_id = {0} WHERE username = '{1}';"
                            .format(last_post_id, username))
        self.conn.commit()

    def register_user(self, username, userid, latest_post_id, latest_story_id, new_channel_id):
        self.cursor.execute("INSERT INTO username_to_channel(username, channel) VALUES ('{0}', {1});"
                            .format(username, new_channel_id))
        self.cursor.execute("INSERT INTO user_info(username, userid, last_post_id, last_story_id) VALUES "
                            "('{0}', {1}, {2}, {3}) ON CONFLICT DO NOTHING;"
                            .format(username, userid, latest_post_id, latest_story_id))
        self.conn.commit()

    def get_registered_users_in_channel(self, channel_id):
        self.cursor.execute("SELECT username FROM username_to_channel WHERE channel = '{0}';".format(channel_id))
        rows = self.cursor.fetchall()
        users = []
        for row in rows:
            users.append(row[0])
        return users

    def delete_user_channel_mapping(self, username, channel_id):
        self.cursor.execute("DELETE FROM username_to_channel WHERE username = '{0}' AND channel = {1};"
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
        self.cursor.execute("SELECT DISTINCT username FROM  user_info;")
        rows = self.cursor.fetchall()
        users = []
        for row in rows:
            users.append(row[0])
        return users

    def get_channels_for_user(self, username):
        self.cursor.execute("SELECT channel FROM username_to_channel WHERE username = '{0}';".format(username))
        rows = self.cursor.fetchall()
        channels = []
        for row in rows:
            channels.append(row[0])
        return channels
