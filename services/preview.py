import os
import time
import json
import boto3
from fastapi import APIRouter, HTTPException, Query

router = APIRouter(tags=["Data Preview"])


@router.get("/api/v1/catalogs/{catalog_id}/preview")
async def get_table_preview(
    catalog_id: str,
    limit: int = Query(default=5, ge=1, le=100),
):
    """
    Preview rows from an Athena table.
    - total_row_count  : pulled from catalogs table (set during ingestion)
    - rows             : live SELECT * LIMIT {limit} from Athena
    """
    from app import db, logger

    try:
        # ── 1. Get table info + total row count + credentials from DB ─────
        record = await db.fetch_one(
            """
            SELECT
                c.table_name,
                c.schema_name,
                c.row_count        AS total_row_count,
                d.connection_details
            FROM   catalogs     c
            JOIN   data_sources d ON d.id = c.source_id
            WHERE  c.id = $1
            """,
            catalog_id,
        )

        if not record:
            raise HTTPException(status_code=404, detail="Catalog not found")

        table_name      = record["table_name"]
        schema_name     = record["schema_name"]
        total_row_count = record["total_row_count"] or 0

        # ── 2. Parse credentials ──────────────────────────────────────────
        conn_details = (
            json.loads(record["connection_details"])
            if isinstance(record["connection_details"], str)
            else record["connection_details"]
        )

        aws_access_key_id = (
            conn_details.get("aws_access_key_id")
            or conn_details.get("username")
        )
        aws_secret_access_key = (
            conn_details.get("aws_secret_access_key")
            or conn_details.get("password")
        )
        aws_region     = conn_details.get("aws_region") or os.environ.get("AWS_DEFAULT_REGION", "us-east-1")
        s3_staging_dir = conn_details.get("s3_staging_dir")

        if not aws_access_key_id or not aws_secret_access_key:
            raise HTTPException(status_code=422, detail="AWS credentials not found for this datasource.")
        if not s3_staging_dir:
            raise HTTPException(status_code=422, detail="s3_staging_dir not configured for this datasource.")

        # ── 3. Run Athena SELECT * LIMIT ──────────────────────────────────
        athena = boto3.client(
            "athena",
            region_name=aws_region,
            aws_access_key_id=aws_access_key_id,
            aws_secret_access_key=aws_secret_access_key,
        )

        query = f'SELECT * FROM "{schema_name}"."{table_name}" LIMIT {limit}'

        response = athena.start_query_execution(
            QueryString=query,
            QueryExecutionContext={"Database": schema_name},
            ResultConfiguration={"OutputLocation": s3_staging_dir},
        )
        query_execution_id = response["QueryExecutionId"]

        # ── 4. Poll until complete (max 30s) ──────────────────────────────
        for _ in range(30):
            status_resp = athena.get_query_execution(QueryExecutionId=query_execution_id)
            state = status_resp["QueryExecution"]["Status"]["State"]

            if state == "SUCCEEDED":
                break
            if state in ("FAILED", "CANCELLED"):
                reason = status_resp["QueryExecution"]["Status"].get(
                    "StateChangeReason", "Unknown error"
                )
                raise HTTPException(status_code=500, detail=f"Athena query failed: {reason}")
            time.sleep(1)
        else:
            raise HTTPException(status_code=408, detail="Athena query timed out after 30s")

        # ── 5. Parse results into rows only ───────────────────────────────
        results     = athena.get_query_results(QueryExecutionId=query_execution_id)
        rows        = results["ResultSet"]["Rows"]
        column_info = results["ResultSet"]["ResultSetMetadata"]["ColumnInfo"]

        headers = [col["Name"] for col in column_info]

        # rows[0] is Athena's header row — skip it
        data = []
        for row in rows[1:]:
            values = [col.get("VarCharValue", "") for col in row["Data"]]
            data.append(dict(zip(headers, values)))

        # ── 6. Return ─────────────────────────────────────────────────────
        return {
            "catalog_id":      catalog_id,
            "table_name":      table_name,
            "schema_name":     schema_name,
            "total_row_count": total_row_count,   
            "showing":         len(data),          
            "rows":            data,               
        }

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error previewing catalog {catalog_id}: {e}")
        raise HTTPException(status_code=500, detail=str(e))