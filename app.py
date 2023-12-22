from flask import Flask, render_template, request, redirect, url_for
from werkzeug.utils import secure_filename
from azure.storage.blob import BlobServiceClient
import requests
import pyodbc
import os

app = Flask(__name__)
app.config['UPLOAD_FOLDER'] = 'uploads'
app.config['MAX_CONTENT_LENGTH'] = 16 * 1024 * 1024  # 16 MB upload limit
ALLOWED_EXTENSIONS = {'png', 'jpg', 'jpeg', 'gif'}

# Azure Custom Vision API Details
custom_vision_endpoint = "https://myproject-prediction.cognitiveservices.azure.com/"
custom_vision_key = "c55049dc99fe4f7a89fa2e540a0fc83c"
custom_vision_project_id = "afd4338b-876c-49fb-9aa9-b9799de41a31"
custom_vision_iteration_name = "Iteration1"

# Azure Blob Storage Details
storage_account_name = "myprojectt"
storage_account_key = "45Fu9frFiFQxgNiugPqfTuKPIuktXzuxV90mi6JOVR5A7gk5wZ6Rf8iYB7hztjd0ncty86iJoZfW+AStInzv5Q=="
blob_container_name = "images"

# Azure SQL Database Connection Details
server = 'myglasses.database.windows.net'
database = 'glasses'
username = 'brahex'
password = 'Elahbib1970@@'
driver = '{ODBC Driver 18 for SQL Server}'

blob_service_client = BlobServiceClient(account_url=f"https://{storage_account_name}.blob.core.windows.net", credential=storage_account_key)

def allowed_file(filename):
    return '.' in filename and filename.rsplit('.', 1)[1].lower() in ALLOWED_EXTENSIONS

@app.route('/upload', methods=['GET', 'POST'])
def upload():
    if request.method == 'POST':
        if 'file' not in request.files:
            return redirect(request.url)
        file = request.files['file']
        if file.filename == '':
            return redirect(request.url)
        if file and allowed_file(file.filename):
            filename = secure_filename(file.filename)
            file_path = os.path.join(app.config['UPLOAD_FOLDER'], filename)
            file.save(file_path)

            # Upload to Azure Blob Storage
            blob_client = blob_service_client.get_blob_client(container=blob_container_name, blob=filename)
            with open(file_path, 'rb') as data:
                blob_client.upload_blob(data)

            return redirect(url_for('show_image', filename=filename))
    return render_template('upload.html')

@app.route('/show_image')
def show_image():
    filename = request.args.get('filename')
    blob_client = blob_service_client.get_blob_client(container=blob_container_name, blob=filename)
    image_url = blob_client.url

    # Azure Custom Vision Prediction
    prediction_api_url = f"{custom_vision_endpoint}customvision/v3.0/Prediction/{custom_vision_project_id}/classify/iterations/{custom_vision_iteration_name}/url"
    headers = {"Prediction-Key": custom_vision_key, "Content-Type": "application/json"}
    response = requests.post(prediction_api_url, headers=headers, json={"Url": image_url})

    if response.status_code == 200:
        result = response.json()
        highest_prediction = max(result["predictions"], key=lambda x: x["probability"])
        face_type = highest_prediction["tagName"]

        # Query SQL Database for Glasses Recommendation
        conn = pyodbc.connect(f'DRIVER={driver};SERVER={server};DATABASE={database};UID={username};PWD={password}')
        cursor = conn.cursor()
        query = f"SELECT glasses_image FROM Glasses WHERE face_shape = '{face_type}'"
        cursor.execute(query)
        row = cursor.fetchone()
        conn.close()

        if row:
            glasses_image_url = row[0]
            return render_template('image.html', image_url=glasses_image_url, face_type=face_type)
    return "No recommendations available for this face type."

if __name__ == '__main__':
    os.makedirs(app.config['UPLOAD_FOLDER'], exist_ok=True)
    app.run(debug=True)
