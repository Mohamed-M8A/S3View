import os
import uuid
import duckdb
from core.models import TaskResponse, BatchResult
from core.execution.resolver import PathResolver
from core.execution.operations import BasicOps
from core.paths import Paths

FORMAT_BY_EXTENSION = {
    "csv": "CSV",
    "json": "JSON",
    "parquet": "PARQUET",
}

def _configure_s3_access(con, connection_manager, source_object):
    if not source_object.is_cloud:
        return

    access_key = connection_manager.s3_client._request_signer._credentials.access_key
    secret_key = connection_manager.s3_client._request_signer._credentials.secret_key
    endpoint = connection_manager.s3_client.meta.endpoint_url
    region = connection_manager.s3_client.meta.region_name
    provider = getattr(connection_manager, "provider", None)
    addressing_style = getattr(provider, "addressing_style", "path")

    con.execute("INSTALL httpfs; LOAD httpfs;")
    con.execute(f"SET s3_endpoint='{endpoint.replace('https://', '').replace('http://', '')}';")
    con.execute(f"SET s3_access_key_id='{access_key}';")
    con.execute(f"SET s3_secret_access_key='{secret_key}';")
    con.execute(f"SET s3_region='{region}';")
    con.execute(f"SET s3_url_style='{addressing_style}';")
    con.execute("SET s3_use_ssl=true;")

def execute_logic(connection_manager, command_model, plugin_instance=None):
    results = BatchResult()
    source_object = command_model.src
    destination_object = command_model.dst

    query = command_model.extra_metadata.get("query")
    if not query:
        results["errors"].append("SQL_ERROR: No query provided in directives (query: \"...\").")
        return results

    con = duckdb.connect(database=":memory:")
    temporary_output_path = None

    try:
        _configure_s3_access(con, connection_manager, source_object)

        db_path = source_object.get_full_identifier()
        con.execute(f"ATTACH '{db_path}' AS remote_db (TYPE SQLITE);")
        con.execute("USE remote_db;")

        if destination_object:
            destination_key = destination_object.payload
            extension = os.path.splitext(destination_key)[1].lstrip(".").lower()
            output_format = FORMAT_BY_EXTENSION.get(extension, "CSV")

            vault_path = Paths.resource_path("_sys/.vault")
            os.makedirs(vault_path, exist_ok=True)
            temporary_output_path = Paths.join(vault_path, f"sql_result_{uuid.uuid4().hex[:8]}.{extension or 'csv'}")

            con.execute(f"COPY ({query}) TO '{temporary_output_path}' (FORMAT {output_format});")
            result_row_count = con.execute(f"SELECT COUNT(*) FROM ({query})").fetchone()[0]
            result_size = os.path.getsize(temporary_output_path)

            if destination_object.is_cloud:
                s3_extra_arguments = BasicOps.build_s3_extra_args(command_model)
                BasicOps.l2s(connection_manager, temporary_output_path, destination_object.bucket, destination_object.prefix, extra_args=s3_extra_arguments)
                final_destination = f"s3://{destination_object.bucket}/{destination_object.prefix}"
            else:
                local_destination = Paths.get_full_physical_path(destination_object)
                BasicOps.l2l(temporary_output_path, local_destination, move_mode=False)
                final_destination = local_destination

            results["files"].append(TaskResponse(
                status="QUERY_EXECUTED",
                src=PathResolver.format_identifier(db_path, source_object),
                dst=final_destination,
                size=result_size,
                error="-"
            ))
            results["total_size"] = result_size
            results["count"] = result_row_count
        else:
            query_result = con.execute(query).fetchall()
            results["files"].append(TaskResponse(
                status="QUERY_EXECUTED",
                src=PathResolver.format_identifier(db_path, source_object),
                dst="-",
                size=0,
                error="-",
                metadata={"rows": query_result}
            ))
            results["count"] = len(query_result)

    except Exception as exc:
        results["errors"].append(f"SQL_EXECUTION_ERROR: {str(exc)}")
    finally:
        con.close()
        if temporary_output_path and os.path.exists(temporary_output_path):
            os.remove(temporary_output_path)

    return results

def simulate_logic(connection_manager, command_model, plugin_instance=None):
    results = BatchResult()
    db_path = command_model.src.get_full_identifier()

    results["files"].append(TaskResponse(
        status="WILL_QUERY",
        src=db_path,
        dst="-",
        size=0,
        error="-"
    ))
    return results
