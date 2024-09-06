# Dependencies for task queue functions.
from google.cloud import tasks_v2
from firebase_functions.options import RetryConfig, RateLimits, SupportedRegion

# Dependencies for image backup.
import json
from firebase_admin import initialize_app, functions
from firebase_functions import https_fn, tasks_fn, params
import google.auth
from google.auth.transport.requests import AuthorizedSession

app = initialize_app()

PROJECT_ID = params.StringParam("PROJECT_ID").value
SERVICE_ACCOUNT_EMAIL = params.StringParam("SERVICE_ACCOUNT_EMAIL").value


@tasks_fn.on_task_dispatched(
    retry_config=RetryConfig(max_attempts=5, min_backoff_seconds=60),
    rate_limits=RateLimits(max_concurrent_dispatches=10),
)
def processtask(req: tasks_fn.CallableRequest) -> str:
    print("Processing task")
    print(req.data)


@https_fn.on_request()
def enqueue(_: https_fn.Request) -> https_fn.Response:
    """Adds backup tasks to a Cloud Tasks queue."""
    tasks_client = tasks_v2.CloudTasksClient()
    task_queue = tasks_client.queue_path(
        PROJECT_ID, SupportedRegion.US_CENTRAL1.value, "processtask"
    )

    target_uri = get_function_url("processtask")
    body = {"data": "test_data"}

    http_request = tasks_v2.HttpRequest(
        http_method=tasks_v2.HttpMethod.POST,
        url=target_uri,
        headers={"Content-type": "application/json"},
        oidc_token=tasks_v2.OidcToken(service_account_email=SERVICE_ACCOUNT_EMAIL),
        body=json.dumps(body).encode(),
    )
    task = tasks_v2.Task(http_request=http_request)
    tasks_client.create_task(parent=task_queue, task=task)

    return https_fn.Response(status=200, response=f"Enqueued")


def get_function_url(
    name: str, location: str = SupportedRegion.US_CENTRAL1.value
) -> str:
    credentials, project_id = google.auth.default(
        scopes=["https://www.googleapis.com/auth/cloud-platform"]
    )
    authed_session = AuthorizedSession(credentials)
    url = (
        "https://cloudfunctions.googleapis.com/v2beta/"
        + f"projects/{project_id}/locations/{location}/functions/{name}"
    )
    response = authed_session.get(url)
    data = response.json()
    function_url = data["serviceConfig"]["uri"]
    return function_url
