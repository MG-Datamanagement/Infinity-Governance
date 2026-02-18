# Swagger API Request Examples

## 📊 Current Data Summary
- **MongoDB Tables/Views:** 17
- **MongoDB Columns:** 87
- **PostgreSQL Tables/Views:** 218
- **PostgreSQL Columns:** 2,105

---

## 1️⃣ MongoDB Source - Register New Source

**Endpoint:** `POST /sources`

```json
{
  "name": "mongodb-patient360",
  "source_type": "mongodb",
  "description": "MongoDB Patient360 Database",
  "connection_details": {
    "connect_uri": "mongodb://localhost:27017/?authSource=admin",
    "username": "admin",
    "password": "admin"
  },
  "include_views": false,
  "include_tables": true
}
```

---

## 2️⃣ PostgreSQL Source - Register New Source

**Endpoint:** `POST /sources`

```json
{
  "name": "Cust_warehouse",
  "source_type": "postgres",
  "description": "PostgreSQL Customer Warehouse",
  "connection_details": {
    "host_port": "host.docker.internal:5432",
    "database": "Cust_warehouse",
    "username": "postgres",
    "password": "root"
  },
  "include_views": true,
  "include_tables": true
}
```

---

## 3️⃣ Trigger MongoDB Ingestion

**Endpoint:** `POST /ingest`

```json
{
  "source_id": "755d2c11-e455-4fdf-9205-6b9431b93f4c",
  "include_profiling": true,
  "include_lineage": true,
  "incremental": false
}
```

**Response Example:**
```json
{
  "job_id": "d83e3e0d-215f-448a-8951-b9fd3ef27656",
  "source_id": "755d2c11-e455-4fdf-9205-6b9431b93f4c",
  "source_name": "mongodb-patient360",
  "status": "started",
  "message": "Ingestion job started successfully"
}
```

---

## 4️⃣ Trigger PostgreSQL Ingestion

**Endpoint:** `POST /ingest`

```json
{
  "source_id": "4a336741-306b-4844-9c9d-7933186a167c",
  "include_profiling": true,
  "include_lineage": true,
  "incremental": false
}
```

**Response Example:**
```json
{
  "job_id": "92dd5f8a-6d68-4d30-90fe-faf452f9ca25",
  "source_id": "4a336741-306b-4844-9c9d-7933186a167c",
  "source_name": "Cust_warehouse_v2",
  "status": "started",
  "message": "Ingestion job started successfully"
}
```

---

## 5️⃣ Get All Sources

**Endpoint:** `GET /sources`

**Response Example:**
```json
[
  {
    "id": "755d2c11-e455-4fdf-9205-6b9431b93f4c",
    "name": "mongodb-patient360",
    "source_type": "mongodb",
    "description": "MongoDB Patient360 Database",
    "status": "active",
    "created_at": "2026-02-18T04:48:00+00:00",
    "updated_at": "2026-02-18T04:48:00+00:00",
    "last_ingested_at": "2026-02-18T10:25:00+00:00"
  },
  {
    "id": "4a336741-306b-4844-9c9d-7933186a167c",
    "name": "Cust_warehouse_v2",
    "source_type": "postgres",
    "description": "PostgreSQL Customer Warehouse with Lineage",
    "status": "active",
    "created_at": "2026-02-18T04:49:19+00:00",
    "updated_at": "2026-02-18T04:49:19+00:00",
    "last_ingested_at": "2026-02-18T10:26:00+00:00"
  }
]
```

---

## 6️⃣ Get Source by ID

**Endpoint:** `GET /sources/{id}`

Example with MongoDB source ID:
```
GET /sources/755d2c11-e455-4fdf-9205-6b9431b93f4c
```

---

## 7️⃣ Search Catalogs (Tables)

**Endpoint:** `POST /search`

```json
{
  "query": "customers",
  "source_type": "postgres",
  "limit": 50
}
```

**Response Example:**
```json
{
  "results": [
    {
      "id": "uuid-here",
      "database_name": "Cust_warehouse",
      "schema_name": "customer_analytics",
      "table_name": "customers",
      "source_type": "postgres",
      "column_count": 5,
      "columns": [
        {
          "name": "customer_id",
          "data_type": "integer",
          "is_nullable": false
        },
        {
          "name": "customer_name",
          "data_type": "character varying",
          "is_nullable": true
        },
        {
          "name": "email",
          "data_type": "character varying",
          "is_nullable": true
        }
      ]
    }
  ],
  "total": 1
}
```

---

## 8️⃣ Get Statistics

**Endpoint:** `GET /statistics`

**Response Example:**
```json
{
  "total_sources": 2,
  "active_sources": 2,
  "total_datasets": 235,
  "total_columns": 2192,
  "successful_jobs": 2,
  "failed_jobs": 0,
  "source_types_count": 2,
  "sources_by_type": {
    "mongodb": 1,
    "postgres": 1
  },
  "last_ingestion": "2026-02-18T10:26:00+00:00"
}
```

---

## 📝 Notes

- **MongoDB Source ID:** `755d2c11-e455-4fdf-9205-6b9431b93f4c`
- **PostgreSQL Source ID:** `4a336741-306b-4844-9c9d-7933186a167c`
- **API Base URL:** `http://localhost:8005`
- **Swagger UI:** `http://localhost:8005/docs`

### Connection Details
**MongoDB:**
- URI: `mongodb://localhost:27017/?authSource=admin`
- Username: `admin`
- Password: `admin`

**PostgreSQL:**
- Host: `host.docker.internal:5432`
- Database: `Cust_warehouse`
- Username: `postgres`
- Password: `root`

### Features
✅ Direct SQL extraction for PostgreSQL (avoids threading issues)  
✅ DataHub integration for MongoDB  
✅ Automatic metadata persistence to postgres_ig  
✅ Column-level lineage tracking  
✅ Table/View type detection  
✅ Profiling support  

---

## 🔍 Testing in Swagger UI

1. Navigate to `http://localhost:8005/docs`
2. Click on any endpoint
3. Click "Try it out"
4. Paste the JSON request body
5. Click "Execute"
6. View the response

