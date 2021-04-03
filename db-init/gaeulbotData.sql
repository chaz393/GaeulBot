CREATE TABLE username_to_channel (
  key serial PRIMARY KEY,
  username VARCHAR ( 30 ) UNIQUE NOT NULL,
  channel BIGINT NOT NULL
);

CREATE TABLE username_to_last_post_id (
  key serial PRIMARY KEY,
  username VARCHAR ( 30 ) UNIQUE NOT NULL,
  last_post_id BIGINT NOT NULL
);
