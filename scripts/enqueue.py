#!/usr/bin/env python
import argparse

# Dependencies for task queue functions.
from google.cloud import tasks_v2
from firebase_functions.options import RetryConfig, RateLimits, SupportedRegion

# Dependencies for image backup.
import json
from firebase_admin import initialize_app, functions
from firebase_functions import https_fn, tasks_fn, params
import google.auth
from google.auth.transport.requests import AuthorizedSession


def enqueue(project_id, service_account_email):
    """Adds backup tasks to a Cloud Tasks queue."""
    tasks_client = tasks_v2.CloudTasksClient()
    task_queue = tasks_client.queue_path(
        project_id, SupportedRegion.US_CENTRAL1.value, "processtask"
    )

    target_uri = get_function_url("processtask")
    body = {"data": "test_data"}

    http_request = tasks_v2.HttpRequest(
        http_method=tasks_v2.HttpMethod.POST,
        url=target_uri,
        headers={"Content-type": "application/json"},
        oidc_token=tasks_v2.OidcToken(service_account_email=service_account_email),
        body=json.dumps(body).encode(),
    )
    task = tasks_v2.Task(http_request=http_request)
    tasks_client.create_task(parent=task_queue, task=task)

    print("Enqueued")


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


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument('project_id')
    parser.add_argument('service_account_email')
    args = parser.parse_args()
    enqueue(args.project_id, args.service_account_email)
