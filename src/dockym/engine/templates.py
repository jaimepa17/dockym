from __future__ import annotations

TEMPLATES: dict[str, dict] = {
    "mysql": {
        "name": "MySQL 8",
        "description": "Base de datos MySQL 8 con volumen persistente",
        "icon": "dolphin",
        "service": {
            "image": "mysql:8.0",
            "container_name": "${PROJECT_NAME}_mysql",
            "restart": "unless-stopped",
            "environment": {
                "MYSQL_ROOT_PASSWORD": "${DB_ROOT_PASSWORD:-root}",
                "MYSQL_DATABASE": "${DB_NAME:-app}",
                "MYSQL_USER": "${DB_USER:-app}",
                "MYSQL_PASSWORD": "${DB_PASSWORD:-secret}",
            },
            "ports": ["3306:3306"],
            "volumes": ["mysql_data:/var/lib/mysql"],
            "healthcheck": {
                "test": ["CMD", "mysqladmin", "ping", "-h", "localhost"],
                "interval": "10s",
                "timeout": "5s",
                "retries": 5,
            },
        },
        "volumes": {"mysql_data": {}},
    },
    "postgres": {
        "name": "PostgreSQL 16",
        "description": "Base de datos PostgreSQL 16 con volumen persistente",
        "icon": "elephant",
        "service": {
            "image": "postgres:16-alpine",
            "container_name": "${PROJECT_NAME}_postgres",
            "restart": "unless-stopped",
            "environment": {
                "POSTGRES_DB": "${DB_NAME:-app}",
                "POSTGRES_USER": "${DB_USER:-app}",
                "POSTGRES_PASSWORD": "${DB_PASSWORD:-secret}",
            },
            "ports": ["5432:5432"],
            "volumes": ["postgres_data:/var/lib/postgresql/data"],
            "healthcheck": {
                "test": ["CMD-SHELL", "pg_isready -U ${DB_USER:-app}"],
                "interval": "10s",
                "timeout": "5s",
                "retries": 5,
            },
        },
        "volumes": {"postgres_data": {}},
    },
    "redis": {
        "name": "Redis 7",
        "description": "Cache en memoria Redis 7 con persistencia AOF",
        "icon": "redis",
        "service": {
            "image": "redis:7-alpine",
            "container_name": "${PROJECT_NAME}_redis",
            "restart": "unless-stopped",
            "ports": ["6379:6379"],
            "volumes": ["redis_data:/data"],
            "command": ["redis-server", "--appendonly", "yes"],
            "healthcheck": {
                "test": ["CMD", "redis-cli", "ping"],
                "interval": "10s",
                "timeout": "5s",
                "retries": 5,
            },
        },
        "volumes": {"redis_data": {}},
    },
    "mongo": {
        "name": "MongoDB 7",
        "description": "Base de datos NoSQL MongoDB 7",
        "icon": "leaf",
        "service": {
            "image": "mongo:7",
            "container_name": "${PROJECT_NAME}_mongo",
            "restart": "unless-stopped",
            "environment": {
                "MONGO_INITDB_ROOT_USERNAME": "${MONGO_USER:-admin}",
                "MONGO_INITDB_ROOT_PASSWORD": "${MONGO_PASSWORD:-secret}",
            },
            "ports": ["27017:27017"],
            "volumes": ["mongo_data:/data/db"],
        },
        "volumes": {"mongo_data": {}},
    },
    "nginx": {
        "name": "Nginx",
        "description": "Servidor web Nginx con configuración personalizada",
        "icon": "globe",
        "service": {
            "image": "nginx:alpine",
            "container_name": "${PROJECT_NAME}_nginx",
            "restart": "unless-stopped",
            "ports": ["80:80", "443:443"],
            "volumes": [
                "./nginx.conf:/etc/nginx/nginx.conf:ro",
                "./public:/usr/share/nginx/html:ro",
            ],
        },
    },
    "node": {
        "name": "Node.js 20",
        "description": "Entorno Node.js 20 para desarrollo",
        "icon": "node",
        "service": {
            "image": "node:20-alpine",
            "container_name": "${PROJECT_NAME}_node",
            "working_dir": "/app",
            "volumes": ["./:/app"],
            "ports": ["3000:3000"],
            "command": "npm run dev",
            "environment": {
                "NODE_ENV": "${NODE_ENV:-development}",
            },
        },
    },
    "adminer": {
        "name": "Adminer",
        "description": "Gestor de bases de datos web (MySQL/PostgreSQL)",
        "icon": "database",
        "service": {
            "image": "adminer:latest",
            "container_name": "${PROJECT_NAME}_adminer",
            "restart": "unless-stopped",
            "ports": ["8080:8080"],
            "depends_on": ["db"],
        },
    },
    "mailpit": {
        "name": "Mailpit",
        "description": "Servidor SMTP de pruebas con UI web",
        "icon": "mail",
        "service": {
            "image": "axllent/mailpit:latest",
            "container_name": "${PROJECT_NAME}_mailpit",
            "restart": "unless-stopped",
            "ports": ["1025:1025", "8025:8025"],
            "environment": {
                "MP_SMTP_AUTH_ACCEPT_ANY": "true",
                "MP_SMTP_AUTH_ALLOW_INSECURE": "true",
            },
        },
    },
}
