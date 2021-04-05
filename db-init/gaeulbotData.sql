CREATE TABLE username_to_channel (
  key serial PRIMARY KEY,
  username VARCHAR ( 30 ) UNIQUE NOT NULL,
  channel BIGINT NOT NULL
);

CREATE TABLE user_info (
  key serial PRIMARY KEY,
  username VARCHAR ( 30 ) UNIQUE NOT NULL,
  userid BIGINT UNIQUE NOT NULL,
  last_post_id BIGINT NOT NULL,
  last_story_id BIGINT NOT NULL
);
