# Cloud Tasks and Cloud Functions - Integration with Firebase - Demo

## Assumptions and pre-requisites

* gcloud CLI is installed in local environment.
* firebase CLI is installed in local environment.
* Python 3.10 and corresponding `pip` are installed in local environment.
* A GCP project already exists and has been already linked to Firebase (`firestore init` or via the Firebase UI).
* This sample uses the `us-central1` region. It can be changed by modifying the code and the variables set below.
* This sample uses the default Compute service account, for the sake of simplicity. You could (and should) create a dedicated service account for your functions.

## Project initialization

These commands enable the necessary APIs and configure the required permissions. Execute them from the root directory of this repository.

```bash
export GCP_PROJECT_ID="PROJECT_ID" # This is your Google Cloud project ID. Replace with your value.
export GCP_REGION="us-central1" # This is also hardcoded in the Python code, so you would need to change it there too.

gcloud auth login
gcloud auth application-default login

# Make sure we are working on the correct project.
gcloud config set project $GCP_PROJECT_ID

# This enables the necessary GCP APIs if they are not yet enabled, otherwise this command does nothing.
gcloud services enable \
    cloudresourcemanager.googleapis.com \
    compute.googleapis.com \
    cloudtasks.googleapis.com \
    cloudfunctions.googleapis.com \
    run.googleapis.com \
    eventarc.googleapis.com \
    pubsub.googleapis.com \
    cloudbuild.googleapis.com \
    artifactregistry.googleapis.com

gcloud auth application-default set-quota-project $GCP_PROJECT_ID

# Each GCP project has an ID and a number. We need the number in some steps. We get it here from the project ID.
export GCP_PROJECT_NUMBER=$(gcloud projects describe $GCP_PROJECT_ID --format="value(projectNumber)")

# This ensures that the Firebase CLI is configured to work with the appropriate project.
firebase projects:addfirebase $GCP_PROJECT_ID # If the project was already added to Firebase, this will fail.
firebase use --add $GCP_PROJECT_ID

# Ensure the default compute service account has the necessary permissions.
# For the sake of simplicity we are granting the Owner role, but in production you probably want to use a much more restrictive role.
export SERVICE_ACCOUNT_EMAIL="$GCP_PROJECT_NUMBER-compute@developer.gserviceaccount.com"
gcloud projects add-iam-policy-binding $GCP_PROJECT_ID --member=serviceAccount:$GCP_PROJECT_NUMBER-compute@developer.gserviceaccount.com --role=roles/owner
```

Now run the following to create a Python virtual environment and install the Python dependencies in your local environment. This is needed later by the Firebase CLI. (Again, start from this repo's root directory.)

```bash
cd functions && python3.10 -m venv venv && source venv/bin/activate
pip install -r requirements.txt
```

## Run locally to verify

This is a basic smoke test to verify that the Python code is not broken. (Again, start from this repo's root directory.)

```bash
# This will ask you to set environment variables. Use the service account email and project ID you used above.
firebase serve --only functions

# Run this in another tab. Ensure that GCP_PROJECT_ID is defined in the new tab.
curl -X POST -H 'Content-Type: application/json' -d '{"data": {"foo": "bar"}}' localhost:5000/{$GCP_PROJECT_ID}/us-central1/processtask

# Should return {"result":null} and print the following on the logs
# >  Processing task
# >  {'foo': 'bar'}

curl localhost:5000/{$GCP_PROJECT_ID}/us-central1/enqueue
# This should fail, as it's actually making request against the GCP environment which does not yet have any actual function created.
```

You can now stop the local emulator with CTRL+C.

## Deploy to Google Cloud

These commands will deploy the functions and create the Cloud Tasks queue on the fly.

```bash
# This will also ask you to set environment variables. Use the same values as above.
firebase deploy --only functions

# Invoke the function which enqueues jobs.
gcloud functions call enqueue --region=$GCP_REGION

# It can also be invoked with an HTTP request, but it requires the function to be open to the world.
# This is not very secure. If you want to follow this route, you should probably allow only some users
# to invoke the function (change the `member` parameter and ensure your call is authenticated properly).
gcloud functions add-invoker-policy-binding enqueue \
    --region="$GCP_REGION" \
    --member="allUsers"
curl $(gcloud functions describe enqueue --format="value(url)")

# In any case, the result should be:
# > Enqueued
```

## Verification

Check the logs of the worker function and see that it has received and processed the jobs successfully, as follows:

```bash
gcloud functions logs read processtask
```

The output should be similar to this:

```
LEVEL  NAME         EXECUTION_ID  TIME_UTC                 LOG
       processtask  VJFu7i7fL61v  2024-09-06 21:53:25.708  test_data
       processtask  VJFu7i7fL61v  2024-09-06 21:53:25.707  Processing task
I      processtask                2024-09-06 21:53:25.684
       processtask  SCVBxVidY0TO  2024-09-06 21:51:55.635  test_data
       processtask  SCVBxVidY0TO  2024-09-06 21:51:55.635  Processing task
I      processtask                2024-09-06 21:51:55.611
       processtask  f8NrRNu961PB  2024-09-06 21:50:27.854  test_data
       processtask  f8NrRNu961PB  2024-09-06 21:50:27.854  Processing task
I      processtask                2024-09-06 21:50:27.832
       processtask  7rdIvJToYJG9  2024-09-06 21:48:58.619  test_data
       processtask  7rdIvJToYJG9  2024-09-06 21:48:58.619  Processing task
```

If you visit the [Cloud Tasks UI](https://console.cloud.google.com/cloudtasks), click on the queue named `processtask` and:

1. Make sure there are no running tasks in the `TASKS` tab.
2. The `Completed in last minute` tab is greater than 0.
