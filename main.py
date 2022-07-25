import base64
import os
import uuid

import magic
from flask import Flask, render_template, request, redirect, url_for, current_app, abort
from flask_wtf import FlaskForm
from google.cloud import storage
from google.cloud.exceptions import NotFound
from werkzeug.utils import secure_filename
from wtforms import FileField

app = Flask(__name__)

app.config['SECRET_KEY'] = 'L3Bf4OXAizDL27ct0KRHV1rK0EcOCh0xY3CRdJaOgV4'
app.config['MAX_CONTENT_LENGTH'] = 20 * 1024 * 1024
app.config['UPLOAD_EXTENSIONS'] = ['.jpeg', '.jpg', '.png', '.gif']
app.config['SUPPORTED_MIME_TYPES'] = ['image/jpeg', 'image/png', 'image/gif']
app.config['BUCKET_NAME'] = "hive-parts-image-bucket"


class MyForm(FlaskForm):
    image = FileField('image')


@app.route("/upload", methods=['GET', 'POST'])
def upload():
    form = MyForm()
    if request.method == 'POST':
        uploaded_file = request.files['image']
        filename = secure_filename(uploaded_file.filename)
        if filename != '':
            file_ext = os.path.splitext(filename)[1]
            mime_type = check_file_type(uploaded_file.stream)
            if file_ext not in current_app.config['UPLOAD_EXTENSIONS'] or \
                    mime_type not in app.config['SUPPORTED_MIME_TYPES']:
                abort(400)
            upload_to_google_cloud(uploaded_file.stream, mime_type)
            return redirect(url_for('index'))

    return render_template('upload.html', form=form)


@app.route("/")
def index():
    storage_client = storage.Client()
    blobs = storage_client.list_blobs(app.config['BUCKET_NAME'])
    all_blobs = list(blobs)

    return render_template('index.html', all_blobs=all_blobs)


@app.route("/view/<string:blob_name>")
def view(blob_name):
    bucket = get_bucket()
    blob = bucket.get_blob(blob_name)
    content = blob.download_as_bytes()
    image = base64.b64encode(content).decode("utf-8")
    return render_template('view.html', content_type=blob.content_type, image=image)


def check_file_type(stream):
    header = stream.read(2048)
    stream.seek(0)
    return magic.from_buffer(header, mime=True)


def upload_to_google_cloud(contents, mime_type):
    storage_client = storage.Client()
    try:
        bucket = storage_client.get_bucket(app.config['BUCKET_NAME'])
    except NotFound:
        raise RuntimeError("Expected bucket in google cloud does not exist")

    name_exists = True
    while name_exists:
        blob_name = str(uuid.uuid4())
        name_exists = storage.Blob(bucket=bucket, name=blob_name).exists(storage_client)

    blob = bucket.blob(blob_name)
    blob.upload_from_file(contents, content_type=mime_type)


def get_bucket():
    storage_client = storage.Client()
    try:
        bucket = storage_client.get_bucket(app.config['BUCKET_NAME'])
    except NotFound:
        raise RuntimeError("Expected bucket in google cloud does not exist")
    return bucket


if __name__ == "__main__":
    app.run(debug=True, host="0.0.0.0", port=int(os.environ.get("PORT", 8080)))
