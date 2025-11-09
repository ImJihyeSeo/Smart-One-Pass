CREATE TABLE students (

    sid TEXT PRIMARY KEY, 

    face BLOB,

    name TEXT

);

CREATE TABLE log (

    log_id INTEGER PRIMARY KEY, 

    sid TEXT, enter TEXT NOT NULL, 

    exit TEXT, 

    FOREIGN KEY (sid) REFERENCES students(sid)

);

CREATE TABLE study_room (

    room_id TEXT PRIMARY KEY, 

    room_name TEXT NOT NULL, 

    location TEXT

);

CREATE TABLE study_room_seat (

    room_id TEXT NOT NULL, 

    seat_number INTEGER NOT NULL, 

    PRIMARY KEY (room_id, seat_number), 

    FOREIGN KEY (room_id) REFERENCES study_room(room_id)

);

CREATE TABLE seat_reservation (

    reservation_id INTEGER PRIMARY KEY,

    sid TEXT NOT NULL, 

    room_id TEXT NOT NULL, 

    seat_number INTEGER NOT NULL, 

    date TEXT NOT NULL, 

    start_time TEXT NOT NULL, 

    end_time TEXT NOT NULL, 

    return_time TEXT,

    FOREIGN KEY (sid) REFERENCES students(sid), 

    FOREIGN KEY (room_id, seat_number) REFERENCES study_room_seat(room_id, seat_number)

);

CREATE TABLE study_room_status (

    status_id INTEGER PRIMARY KEY, 

    room_id TEXT NOT NULL, 

    record_time TEXT NOT NULL, 

    total_seat INTEGER NOT NULL, 

    used_seat INTEGER NOT NULL, 

    FOREIGN KEY (room_id) REFERENCES study_room(room_id)

);