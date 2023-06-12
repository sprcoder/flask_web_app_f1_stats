ALTER TABLE IS601_f1_drivers
ADD COLUMN country varchar(30) COMMENT 'Birth country of the driver',
ADD COLUMN birthdate DATE COMMENT 'Date of birth',
ADD COLUMN podiums INT COMMENT 'Podium wins achieved',
ADD COLUMN championships INT COMMENT 'No. of World Championships';

ALTER TABLE IS601_f1_drivers
ADD COLUMN image TEXT Comment 'url for the image';