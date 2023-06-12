CREATE TABLE
    IS601_f1_drivers(
        id int PRIMARY KEY,
        name VARCHAR(60) not null,
        response TEXT not null,
        created TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP,
        modified TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP
    )