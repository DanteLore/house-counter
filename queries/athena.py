import time
import boto3

AWS_PROFILE = "dantelore"
AWS_REGION = "eu-west-1"
ATHENA_DB = "incoming"
RESULTS_BUCKET = "s3://dantelore.queryresults/"


def _client():
    session = boto3.Session(profile_name=AWS_PROFILE)
    return session.client("athena", region_name=AWS_REGION)


def _wait(client, execution_id):
    while True:
        status = client.get_query_execution(QueryExecutionId=execution_id)
        state = status["QueryExecution"]["Status"]["State"]
        if state == "SUCCEEDED":
            return
        if state in ("FAILED", "CANCELLED"):
            reason = status["QueryExecution"]["Status"].get("StateChangeReason", state)
            raise RuntimeError(f"Athena query {state}: {reason}")
        time.sleep(1)


def _fetch_rows(client, execution_id):
    rows = []
    kwargs = {"QueryExecutionId": execution_id}
    while True:
        resp = client.get_query_results(**kwargs)
        rows.extend(resp["ResultSet"]["Rows"])
        token = resp.get("NextToken")
        if not token:
            break
        kwargs["NextToken"] = token
    return rows


def _execute(sql):
    client = _client()
    resp = client.start_query_execution(
        QueryString=sql,
        QueryExecutionContext={"Database": ATHENA_DB},
        ResultConfiguration={"OutputLocation": RESULTS_BUCKET},
    )
    execution_id = resp["QueryExecutionId"]
    _wait(client, execution_id)
    return _fetch_rows(client, execution_id)


def run_query(sql) -> list[dict]:
    """Execute SQL and return results as a list of dicts (header row used as keys)."""
    rows = _execute(sql)
    if not rows:
        return []
    headers = [c["VarCharValue"] for c in rows[0]["Data"]]
    return [
        {headers[i]: col.get("VarCharValue", "") for i, col in enumerate(row["Data"])}
        for row in rows[1:]
    ]


def run_query_rows(sql) -> list:
    """Execute SQL and return raw Athena rows (including header row at index 0)."""
    return _execute(sql)
