CREATE TABLE
    IS601_f1_driverstory(
        driver_id int not null,
        story_id int not null,
        PRIMARY KEY(driver_id, story_id),
        Foreign Key (driver_id) REFERENCES IS601_f1_drivers(id),
        Foreign Key (story_id) REFERENCES IS601_f1_story(id)
    )