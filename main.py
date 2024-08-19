from flask import Flask, request, render_template, redirect, url_for, flash
from azure.storage.blob import BlobServiceClient, generate_blob_sas, BlobSasPermissions
from azure.core.exceptions import ResourceExistsError, ResourceNotFoundError
from datetime import datetime, timedelta, timezone
import os


app = Flask(__name__)

connect_str = "YOUR_AZURE_STORAGE_CONNECTION_STRING"
container_name = "YOUR_CONTAINER_NAME"

# Initialize BlobServiceClient
blob_service_client = BlobServiceClient.from_connection_string(connect_str)


@app.route('/')
def home():
    return render_template('index.html')


@app.route('/upload', methods=['POST'])
def upload_file():
    if 'file' not in request.files:
        flash("No file part")
        return redirect(url_for('home'))
    file = request.files['file']
    if file.filename == '':
        flash("No selected file")
        return redirect(url_for('home'))
    
    # Create a BlobClient for the specific file
    blob_client = blob_service_client.get_blob_client(container=container_name, blob=file.filename)
    
    # Check if the blob already exists
    try:
        # Check if the blob already exists by trying to fetch its properties
        blob_client.get_blob_properties()
        flash(f"A file with the name '{file.filename}' already exists.")
        return redirect(url_for('home'))
    except ResourceNotFoundError:
        # Blob doesn't exist, proceed with upload
        pass
    except Exception as e:
        flash(f"An error occurred while checking for the file: {str(e)}")
        return redirect(url_for('home'))

    try:
        # Upload the file to Azure Blob Storage
        blob_client.upload_blob(file, overwrite=False)  # Set overwrite to False to avoid accidental overwrites
    except ResourceExistsError:
        flash(f"A file with the name '{file.filename}' already exists.")
        return redirect(url_for('home'))
    except Exception as e:
        flash(f"An error occurred during file upload: {str(e)}")
        return redirect(url_for('home'))

    # Generate a time-limited access link (e.g., valid for 1 hour)
    sas_token = generate_blob_sas(
        account_name=blob_service_client.account_name,
        container_name=container_name,
        blob_name=file.filename,
        account_key=blob_service_client.credential.account_key,
        permission=BlobSasPermissions(read=True),
        expiry=datetime.now(timezone.utc) + timedelta(hours=1)  # Timezone-aware datetime
    )

    blob_url = f"https://{blob_service_client.account_name}.blob.core.windows.net/{container_name}/{file.filename}?{sas_token}"

    return redirect(url_for('success', url=blob_url))

@app.route('/success')
def success():
    url = request.args.get('url')
    return f"File uploaded successfully! Download link (valid for 1 hour):<br><br><a href='{url}'>{url}</a>"

if __name__ == '__main__':
    app.run(debug=True)
