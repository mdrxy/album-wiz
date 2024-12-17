# Vinyl Record Recognition System

This project is a companion tool for radio DJs to help facilitate exploration and discovery with physical collections of vinyl records. By leveraging computer vision, deep learning, and metadata aggregation, this tool aims to reduce the amount of time needed to retrieve relevant information about a given release.

## Project Structure

The project is containerized with Docker to increase compatibility across platforms and to simplify setup and deployment. The key services include:

- **Frontend**: React app for user interaction.
- **Backend**: Python (FastAPI) service for API endpoints, image recognition and metadata aggregation.
- **Database**: PostgreSQL with `pgvector` for vectorized queries. pgAdmin is available for browsing the database in a web browser.
- **Cache**: Redis for high-performance data caching.
- **Nginx**: Reverse proxy for routing traffic between services.

## Getting Started

### Prerequisites

Ensure you install the following locally first:

#### For Deployment

- [Docker Desktop](https://docs.docker.com/desktop/setup/install/mac-install/)

#### For Development

- [Node.js and npm](https://nodejs.org/en)
- Python 3.10+

### Installation

1. Clone this repository:

   ```bash
   git clone https://github.com/mdrxy/album-wiz.git
   cd album-wiz
   ```

2. Setup a `.env`:

    ```bash
    cp .sample.env .env
    nano .env
    ```

    Enter values for `DISCOGS_TOKEN`, `SPOTIFY_CLIENT_ID`, `SPOTIFY_CLIENT_SECRET`.

    - Get a Discogs token by making a Discogs account and then [generating a personal access token](discogs.com/settings/developers).
    - Get Spotify Client ID and secrets by making an app in their [developer dashboard](https://developer.spotify.com/).

3. Build and start the app:

    ```bash
    docker compose up -d --build
    ```

    Note: if you omit `-d`, the app will still launch and logs will be output to your terminal. Upon pressing `CTRL-C`, the app will stop. The `-d` flag is used to run the app in the background.

    Omit `--build` if there are no container changes needing to be made (e.g. you only changed `backend` or `frontend` code).

4. Access the services:
   - Frontend: <http://localhost/>
   - Backend: <http://localhost/api/>
   - pgAdmin: <http://localhost/pga/>
     - User/pass: `admin@vinyl.com`/`admin`
     - PostgreSQL: `postgres`/`postgres`

5. Stop the app:

    ```bash
    docker compose down
    ```

    Note: this command must be ran from the project's top level directory (`/album-wiz`).

## Development

### Debugging

To debug a specific container, you can view its logs using:

```bash
docker logs -f vinyl-backend
```

Note that you need to use the *container* name instead of the *service* name. Service names come from `docker compose.yml` to refer to a component of the app's architecture. *Container names* are actual instances of that service. Thus, to view service logs, we want to peek into the *container* actually running the service.

It's also important to note that `-f` attaches the logs to your terminal window and will update in real-time. Detach using `CTRL-C`. If `-f` is ommitted, then you will see the logs up to the point of the command being run (and nothing after).

### Frontend (React)

1. Navigate to the frontend directory:

    ```sh
    cd frontend
    ```

2. Install dependencies:

    ```sh
    npm install
    ```

3. Rebuild the frontend in Docker (if needed):

    For instances where you modify the Dockerfile for the frontend or update any configuration in docker-compose.yml that impacts the frontend service (e.g., ports, environment variables, volumes, or build context).

    If you update `package.json` (e.g., add, remove, or update npm packages), Docker needs to re-install dependencies, which requires rebuilding the container.

    ```sh
    cd frontend
    npm install
    docker compose up -d --build frontend
    ```

### Backend

Changes made in `/backend` are automatically reflected in the running backend service (after detecting a change in any backend file - remember to save!). If you need to rebuild the backend service for any reason:

```bash
docker compose up -d --build backend
```

### Executing commands inside a running container

To access a running container, run the following, replacing `vinyl-backend` with the name of the container (found in `docker compose.yml` or by running `docker ps`).

```bash
docker exec -it vinyl-backend /bin/bash
```

### Database

To modify the database schema:

1. Edit `database/init.sql`

2. Drop the local `postgres_data` Docker volume:

    ```sh
    docker compose down
    docker volume rm album-wiz_postgres_data
    ```

3. Rebuild the database container:

    ```sh
    docker compose up -d --build database
    ```

### Update Nginx config without rebuilding

To update the Nginx config, make the necessary changes locally and then run:

```bash
docker exec vinyl-nginx nginx -s reload
```

## Contributing Guidelins

1. Always create feature branches for new work:

    ```sh
    git checkout -b feature/new-feature-name
    ```

2. Commit changes with descriptive messages:

    ```sh
    git commit -m "Fix: Add health check for backend service"
    ```

3. Submit pull requests for review. Include:

      - A clear summary of changes
      - Testing instructions

4. Run code formatters (e.g., black for Python, Prettier for JS) before committing.

## TODO

### Immediate

- Add Records endpoint
  - Interface for selecting just one DB
  - Resolve

### Long-term

- Caching
- Detailed error messages
  - Debugging view - present the debugging image stages
- Batch detection? Instance segmentation.
- Show artist images on library page.
- On-the-fly (live) classification.
- If no classification above a certain threshold is found, return the three closest, and present them to the user. The user chooses the ground truth and the model is updated via reinforcement learning.
- Add to playlist/queue in streaming apps (Spotify)
