class DBMigrations:

    migrations = {}

    def __init__(self):
        self.migrations[1] = self.one_to_two
        self.migrations[2] = self.two_to_three
        self.migrations[3] = self.three_to_four
        self.migrations[4] = self.four_to_five

    @staticmethod
    def one_to_two(conn):
        cursor = conn.cursor()
        cursor.execute("CREATE TABLE app_info (key serial PRIMARY KEY, dbversion INT);")
        cursor.execute("CREATE TABLE registrations (key serial PRIMARY KEY, username VARCHAR (30) NOT NULL, channel BIGINT NOT NULL);")
        conn.commit()
        cursor.execute("INSERT INTO app_info(dbversion) VALUES(2);")
        conn.commit()
        cursor.execute("SELECT (username, channel) FROM username_to_channel;")
        rows = cursor.fetchall()
        for row in rows:
            username = row[0].split(',')[0][1:]
            channel = row[0].split(',')[1][:-1]
            cursor.execute("INSERT INTO registrations(username, channel) VALUES('{0}', {1});".format(username, channel))
        cursor.execute("DROP TABLE username_to_channel")
        conn.commit()

    @staticmethod
    def two_to_three(conn):
        cursor = conn.cursor()
        cursor.execute("CREATE TABLE whitelist (key serial PRIMARY KEY, server_id BIGINT NOT NULL, user_id BIGINT NOT NULL)")
        cursor.execute("UPDATE app_info SET dbversion = 3")
        conn.commit()

    @staticmethod
    def three_to_four(conn):
        cursor = conn.cursor()
        cursor.execute("ALTER TABLE app_info ADD COLUMN stories_enabled BOOLEAN;")
        cursor.execute("UPDATE app_info SET stories_enabled = true")
        cursor.execute("UPDATE app_info SET dbversion = 4")
        conn.commit()

    @staticmethod
    def four_to_five(conn):
        cursor = conn.cursor()
        cursor.execute("ALTER TABLE user_info ADD COLUMN user_disabled BOOLEAN DEFAULT FALSE")
        conn.commit()
