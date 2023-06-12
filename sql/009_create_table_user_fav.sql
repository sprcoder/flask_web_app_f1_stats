CREATE TABLE
    IS601_f1_userfavs(
        user_id int not null,
        driver_id int not null,
        PRIMARY KEY(user_id, driver_id),
        Foreign Key (user_id) REFERENCES IS601_sr2484_Users(id),
        Foreign Key (driver_id) REFERENCES IS601_f1_drivers(id)
    )