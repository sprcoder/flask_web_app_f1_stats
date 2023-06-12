CREATE TABLE
    IS601_f1_config(
        id int PRIMARY KEY,
        api_url VARCHAR(200) not NULL,
        create_prefix int DEFAULT 1000,
        perday_limit int DEFAULT 100,
        permin_limit int DEFAULT 10,
        created TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP,
        modified TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP
    )