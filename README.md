# Vinyl Record Recognition System

This project is a companion tool for radio DJs to explore and discover vinyl records from a physical collection. By leveraging computer vision, deep learning, and metadata aggregation, this tool strives to make music exploration easier and more enjoyable.

## Project Structure

The project is containerized with Docker to simplify setup and deployment. The services include:

- **Frontend**: React app for user interaction.
- **Backend**: Python (Flask/FastAPI) service for image recognition and metadata aggregation.
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

2. Set up environment variables

    Copy `.sample.env` as `.env` in the root directory of the project and input any missing values.

3. Build and start the containers:

    ```bash
    docker compose up --build
    ```

4. Access the services:
   - Frontend: <http://localhost:3000>
   - Backend: <http://localhost:8000>
   - pgAdmin: <http://localhost:5050>
   - Nginx: <http://localhost>
     - Home page: `/` (root)
     - API: `/api`

5. Stop services

    ```bash
    docker compose down
    ```

## Development / Contributing

If you're only working on a specific service, run just the necessary containers. For instance:

```bash
docker compose up backend
```

If you've made changes to a service, rebuild and restart it:

```bash
docker compose up --build backend
```

To debug a specific container, view its logs:

```bash
docker logs -f vinyl-backend
```

`-f` attaches the logs to your terminal window and will update in real-time. Detach using `CTRL-C`.

To access a running container, run the following, replacing `vinyl-backend` with the name of the container (found in `docker compose.yml` or by running `docker ps`).

```bash
docker exec -it vinyl-backend /bin/bash
```

To update the Nginx config inside the running container, make the necessary changes locally and then run:

```bash
docker exec vinyl-nginx nginx -s reload
```

To run tests,
TODO

### Frontend

If changing `package.json`, don't forget to run `npm install` from the `frontend/` folder so that `package-lock.json` is updated.

### Backend

### Database

If you need to make changes to the database schema, edit `database/init.sql`.

### Vector Search

## Troubleshooting

## TODO

Use a Makefile?
