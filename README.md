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

- [Install Docker and Docker Compose on your system.](https://docs.docker.com/compose/install/)

### Installation

1. Clone the repository:

   ```bash
   git clone https://github.com/mdrxy/album-wiz.git
   cd album-wiz
   ```

2. Setup a `.env`:

    ```bash
    cp .sample.env .env
    ```

    Enter values for `DISCOGS_TOKEN`, `SPOTIFY_CLIENT_ID`, `SPOTIFY_CLIENT_SECRET`

3. Build and start the containers:

    ```bash
    docker compose up -d --build
    ```

    Note: if you omit `-d`, the app will still launch and logs will be output to your terminal. However, upon pressing `CTRL-C`, the containers will stop. The `-d` flag detaches the containers and runs them in the background.

4. Access the services:
   - Frontend: <http://localhost/>
   - Backend: <http://localhost/api/>
   - pgAdmin: <http://localhost/pga/>

5. Stop services

    ```bash
    docker compose down
    ```

## Development / Contributing

### Debugging

To debug a specific container, view its logs, e.g.

```bash
docker logs -f vinyl-backend
```

Note that you need to use the *container* name instead of the *service* name. Service names come from `docker-compose.yml` to refer to a component of the app's architecture. Container names are actual instances of that service. Thus, to view service logs, we want to peek into the *container* actually running the service.

It's also important to note that `-f` attaches the logs to your terminal window and will update in real-time. Detach using `CTRL-C`. If `-f` is ommitted, then you will see the logs up to the point of the command being run (and nothing after).

### Executing commands inside a running container

To access a running container, run the following, replacing `vinyl-backend` with the name of the container (found in `docker compose.yml` or by running `docker ps`).

```bash
docker exec -it vinyl-backend /bin/bash
```

#### Shortcut: update Nginx

To update the Nginx config inside the running container, make the necessary changes locally and then run:

```bash
docker exec vinyl-nginx nginx -s reload
```

### Building a container following changes

If you've made changes to a service, rebuild and restart it:

```bash
docker compose up --build backend
```

### Running tests

To run tests,
TODO

### Frontend

Note: if changing `package.json`, don't forget to run `npm install` from the `frontend/` folder so that `package-lock.json` is updated.

```sh
export BUILD_TARGET=development
docker-compose up --build
```

```sh
export BUILD_TARGET=production
docker-compose up --build
```

### Backend

### Database

If you need to make changes to the database schema, edit `database/init.sql`.

### Vector Search

## Troubleshooting

## TODO

Use a Makefile?
