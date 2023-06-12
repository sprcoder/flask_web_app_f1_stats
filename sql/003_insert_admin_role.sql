INSERT INTO
    IS601_sr2484_Roles (
        id,
        name,
        description,
        is_active
    )
VALUES (-1, 'Admin', 'A super user', 1) ON DUPLICATE KEY
UPDATE name = name;