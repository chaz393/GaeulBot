CREATE TABLE registrations (
  key serial PRIMARY KEY,
  username VARCHAR ( 30 ) NOT NULL,
  channel BIGINT NOT NULL
);

CREATE TABLE user_info (
  key serial PRIMARY KEY,
  username VARCHAR ( 30 ) UNIQUE NOT NULL,
  userid BIGINT UNIQUE NOT NULL,
  last_post_id BIGINT NOT NULL,
  last_story_id BIGINT NOT NULL
);

CREATE TABLE app_info (
  key serial PRIMARY KEY,
  dbversion INT
);

CREATE TABLE whitelist (
  key serial PRIMARY KEY,
  server_id BIGINT NOT NULL,
  user_id BIGINT NOT NULL
);

INSERT INTO app_info(dbversion) VALUES(3);
