FROM postgres:15

# Add the PostgreSQL apt repository and install pgvector
RUN apt-get update && apt-get install -y wget gnupg && \
    wget -qO - https://www.postgresql.org/media/keys/ACCC4CF8.asc | apt-key add - && \
    echo "deb http://apt.postgresql.org/pub/repos/apt bullseye-pgdg main" > /etc/apt/sources.list.d/pgdg.list && \
    apt-get update && apt-get install -y postgresql-15-pgvector && \
    rm -rf /var/lib/apt/lists/*

# Copy initialization scripts
COPY ./init.sql /docker-entrypoint-initdb.d/