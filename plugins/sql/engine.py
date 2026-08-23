import duckdb
from core.models import TaskResponse
from core.execution.resolver import PathResolver

def worker(connection_manager, execution_context, command_model):
    return True

def execute_logic(connection_manager, command_model, plugin_instance):
    results = {"files": [], "errors": [], "total_size": 0, "count": 0}
    source_object = command_model.src
    
    query = command_model.extra_metadata.get("query")
    if not query:
        results["errors"].append("SQL_ERROR: No query provided in directives (query: \"...\").")
        return results

    try:
        con = duckdb.connect(database=':memory:')
        
        if source_object.is_cloud:
            access_key = connection_manager.s3_client._request_signer._credentials.access_key
            secret_key = connection_manager.s3_client._request_signer._credentials.secret_key
            endpoint = connection_manager.s3_client.meta.endpoint_url
            
            con.execute(f"INSTALL httpfs; LOAD httpfs;")
            con.execute(f"SET s3_endpoint='{endpoint.replace('https://', '').replace('http://', '')}';")
            con.execute(f"SET s3_access_key_id='{access_key}';")
            con.execute(f"SET s3_secret_access_key='{secret_key}';")
            con.execute(f"SET s3_url_style='path';")
            con.execute(f"SET s3_use_ssl=true;")

        db_path = source_object.get_full_identifier()
        
        con.execute(f"ATTACH '{db_path}' AS remote_db (TYPE SQLITE);")
        con.execute(f"USE remote_db;")
        
        query_result = con.execute(query).fetchall()
        
        results["files"].append(TaskResponse(
            status="QUERY_SUCCESS",
            src=PathResolver.format_identifier(db_path, source_object),
            dst="-",
            size=0,
            error="-"
        ))
        
        results["count"] = 1
        
    except Exception as exc:
        results["errors"].append(f"SQL_EXECUTION_ERROR: {str(exc)}")

    return results

def simulate_logic(connection_manager, command_model, plugin_instance):
    results = {"files": [], "errors": [], "total_size": 0, "count": 0}
    db_path = command_model.src.get_full_identifier()
    
    results["files"].append(TaskResponse(
        status="WILL_QUERY",
        src=db_path,
        dst="-",
        size=0,
        error="-"
    ))
    return results