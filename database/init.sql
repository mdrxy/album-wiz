-- Switch to the vinyl_db database
\c vinyl_db;

-- Add an extension for vectorized queries (pgvector)
CREATE EXTENSION IF NOT EXISTS vector;

-- Create the artists table to store artist metadata
CREATE TABLE artists (
    id SERIAL PRIMARY KEY,               -- Unique identifier for the artist
    name VARCHAR(255) NOT NULL,          -- Artist name
    genre VARCHAR(100),                  -- Genre of the artist
    created_at TIMESTAMP DEFAULT NOW(),  -- Record creation timestamp
    updated_at TIMESTAMP DEFAULT NOW()   -- Last updated timestamp
);

-- Create the albums table to store album metadata
CREATE TABLE albums (
    id SERIAL PRIMARY KEY,               -- Unique identifier for the album (record ID)
    title VARCHAR(255) NOT NULL,         -- Album title
    artist_id INT NOT NULL,              -- Foreign key to the artist (from the artists table)
    release_date DATE,                   -- Release date of the album
    genre VARCHAR(100),                  -- Genre of the album
    cover_image_path TEXT,               -- URL for the album cover image
                                         -- Assuming all containers use /media as the root directory
    embedding VECTOR(256),               -- Vectorized representation for the album
    created_at TIMESTAMP DEFAULT NOW(),  -- Record creation timestamp
    updated_at TIMESTAMP DEFAULT NOW(),  -- Last updated timestamp
    FOREIGN KEY (artist_id) REFERENCES artists (id) ON DELETE CASCADE
);

-- Create the tracks table to store track details
CREATE TABLE tracks (
    id SERIAL PRIMARY KEY,               -- Unique identifier for the track
    album_id INT NOT NULL,               -- Foreign key to the album
    title VARCHAR(255) NOT NULL,         -- Track title
    duration_seconds INT,                -- Duration of the track in seconds
    explicit BOOLEAN,                    -- Indicates if the track contains explicit content
    created_at TIMESTAMP DEFAULT NOW(),  -- Record creation timestamp
    updated_at TIMESTAMP DEFAULT NOW(),  -- Last updated timestamp
    FOREIGN KEY (album_id) REFERENCES albums (id) ON DELETE CASCADE
);

-- Insert example data for testing
INSERT INTO artists (name, genre) VALUES
('Radiohead', 'Alternative Rock'),
('Kendrick Lamar', 'Hip-Hop'),
('Taylor Swift', 'Pop');

INSERT INTO albums (title, artist_id, release_date, genre, cover_image_path, embedding) VALUES
('OK Computer', 1, '1997-05-21', 'Alternative Rock', 'ok_computer.jpg', NULL),
('DAMN.', 2, '2017-04-14', 'Hip-Hop', 'damn.jpg', NULL),
('1989', 3, '2014-10-27', 'Pop', '1989.jpg', NULL);

INSERT INTO tracks (album_id, title, duration_seconds, explicit) VALUES
(1, 'Paranoid Android', 388, FALSE),
(2, 'HUMBLE.', 177, TRUE),
(3, 'Shake It Off', 242, FALSE);
