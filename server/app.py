import os
import io
import zipfile
import tempfile
import argparse
from pathlib import Path
from flask import Flask, request, send_file, jsonify
from flask_cors import CORS

# Add parent directory to sys.path so we can import from animate.py
import sys
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from animate import run_pipeline

app = Flask(__name__)
CORS(app)  # Allow frontend to communicate

@app.route('/health', methods=['GET'])
def health_check():
    return jsonify({"status": "ok", "message": "PPTX Animator Backend is running!"})

@app.route('/api/animate', methods=['POST'])
def animate_upload():
    if 'files' not in request.files:
        return jsonify({"error": "No files part in the request"}), 400

    files = request.files.getlist('files')
    if not files or all(f.filename == '' for f in files):
        return jsonify({"error": "No files selected"}), 400

    profile = request.form.get('profile', 'balanced')

    # Create a temporary directory to process files
    with tempfile.TemporaryDirectory() as tmpdir:
        animated_files = []

        for f in files:
            if not f.filename.endswith('.pptx'):
                continue

            input_path = os.path.join(tmpdir, f.filename)
            f.save(input_path)

            output_filename = f.filename.replace('.pptx', '_animated.pptx')
            output_path = os.path.join(tmpdir, output_filename)

            # Mock CLI arguments
            class MockArgs:
                def __init__(self, in_p, out_p, prof):
                    self.input = in_p
                    self.output = out_p
                    self.profile = prof
                    self.dry_run = False
                    self.skip_slides = None
                    self.verbose = False
                    self.overwrite = True

            args = MockArgs(input_path, output_path, profile)
            
            try:
                # Run the exact same engine pipeline
                run_pipeline(args)
                if os.path.exists(output_path):
                    animated_files.append((output_filename, output_path))
            except Exception as e:
                print(f"Error animating {f.filename}: {e}")
                # We can continue with other files if one fails

        if not animated_files:
            return jsonify({"error": "Failed to animate any files."}), 500

        # If exactly one file was processed, send it directly
        if len(animated_files) == 1:
            with open(animated_files[0][1], 'rb') as f:
                file_data = io.BytesIO(f.read())
            return send_file(
                file_data,
                as_attachment=True,
                download_name=animated_files[0][0],
                mimetype='application/vnd.openxmlformats-officedocument.presentationml.presentation'
            )

        # If multiple files, zip them up
        zip_path = os.path.join(tmpdir, 'animated_presentations.zip')
        with zipfile.ZipFile(zip_path, 'w', zipfile.ZIP_DEFLATED) as zipf:
            for name, path in animated_files:
                zipf.write(path, arcname=name)

        with open(zip_path, 'rb') as f:
            zip_data = io.BytesIO(f.read())
            
        return send_file(
            zip_data,
            as_attachment=True,
            download_name='animated_presentations.zip',
            mimetype='application/zip'
        )

if __name__ == '__main__':
    # Run locally on port 5000
    app.run(host='0.0.0.0', port=5000, debug=True)
