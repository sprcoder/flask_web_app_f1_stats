CREATE TABLE
    IS601_f1_driver_stats(
        driver_id int not null,
        seasons int not null,
        teams VARCHAR(50),
        logo TEXT,
        points int,
        PRIMARY KEY(driver_id, seasons),
        FOREIGN KEY (driver_id) REFERENCES IS601_f1_drivers(id),
        created TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP,
        modified TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP
    )