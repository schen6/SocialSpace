DROP TABLE IF EXISTS weibo_post;

CREATE TABLE weibo_post (
	id BIGINT NOT NULL,
	user_id BIGINT NOT NULL,
	text TEXT,
	source NVARCHAR(128) NOT NULL,
	favorited TINYINT DEFAULT NULL,
	truncated TINYINT DEFAULT NULL,
	in_reply_to_status_id VARCHAR(64) DEFAULT NULL,
	in_reply_to_user_id VARCHAR(64) DEFAULT NULL,
	in_reply_to_screen_name NVARCHAR(128) DEFAULT NULL,
	geo VARCHAR(64) DEFAULT NULL,
	mid VARCHAR(64) NOT NULL,
	reposts_count INT(64) DEFAULT NULL,
	comments_count INT(64) DEFAULT NULL,
	annotations VARCHAR(128) DEFAULT NULL,
	created_at DATETIME NOT NULL,
	created_time TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP,
	updated_time TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP,
	PRIMARY KEY (id),
	UNIQUE KEY (mid),
	INDEX INX_WEIBO_POST_CREATED_AT (created_at),
	INDEX INX_WEIBO_POST_USER_ID (user_id)
	/*,FOREIGN KEY FK_WEIBO_POST_USER_ID (user_id) REFERENCES weibo_user(id)
	*/
) ENGINE=InnoDB DEFAULT CHARSET=utf8;