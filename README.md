# Vinyl Record Recognition System

This project is a companion tool for radio DJs to explore and discover vinyl records from a physical collection. By leveraging computer vision, deep learning, and metadata aggregation, this tool strives to make music exploration easier and more enjoyable.

## Project Structure

The project is containerized with Docker to simplify setup and deployment. The services include:

- **Frontend**: React app for user interaction.
- **Backend**: Python (FastAPI) service for image recognition and metadata aggregation.
- **Database**: PostgreSQL with `pgvector` for vectorized queries. pgAdmin is available for browsing the database in the browser.
- **Cache**: Redis for high-performance data caching.
- **Vector Search**: Service for latent vector encoding and similarity search.
- **Nginx**: Reverse proxy for routing traffic between services.

The vector search service is separated into its own service for modularity, scalability, and maintainability:

- Separation keeps the backend lightweight and focused
- Also, we could theoretically run this on the HPC to allocate more GPU

**Example Vector Search Workflow:**

1. Backend receives an image from the frontend and sends it to the vector search service via an internal API.
2. Vector search encodes the image, queries the database (or Redis), and returns results to the backend.
3. Backend combines these results with metadata from other sources (e.g., Spotify, Last.fm) and returns a response to the frontend.

---

## Getting Started

### Prerequisites

Ensure you install the following locally first:

- [Docker Desktop](https://docs.docker.com/desktop/setup/install/mac-install/)
- [Node.js and npm](https://nodejs.org/en)
- Python 3.10+

### Installation

1. Clone the repository:

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

3. Build and start the containers:

    ```bash
    docker compose up -d --build
    ```

    Note: if you omit `-d`, the app will still launch and logs will be output to your terminal. However, upon pressing `CTRL-C`, the containers will stop. The `-d` flag detaches the containers and runs them in the background.

    Omit `--build` if there are no container changes needing to be made (e.g. you only changed `backend` or `frontend` code).

4. Access the services:
   - Frontend: <http://localhost/>
   - Backend: <http://localhost/api/>
   - pgAdmin: <http://localhost/pga/>
     - User/pass: `admin@vinyl.com`/`admin`
     - PostgreSQL: `postgres`/`postgres`

5. Stop all services:

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

Changes made in `/backend` are automatically reflected in the running backend service. However, if you need to rebuild the backend service for any reason:

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

## Troubleshooting

WIP

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

- Show artist images on library page
