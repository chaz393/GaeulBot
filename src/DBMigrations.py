class DBMigrations:

    migrations = {}

    def __init__(self):
        self.migrations[1] = self.one_to_two

    def one_to_two(self, conn):
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
