CREATE TABLE
    IS601_f1_story(
        id int auto_increment PRIMARY KEY,
        short_desc VARCHAR(200),
        long_desc TEXT,
        imagestr TEXT,
        created_by int not null,
        created TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP,
        modified TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP,
        Foreign Key (created_by) REFERENCES IS601_sr2484_Users(id)
    )


ALTER TABLE IS601_f1_story
ADD COLUMN imagestr TEXT Comment 'url for the image';