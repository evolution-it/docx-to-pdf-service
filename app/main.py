from flask import Flask, request, send_file, jsonify
import os
import tempfile
import uuid
from pathlib import Path
import logging
import subprocess
 
app = Flask(__name__)
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)
 
TEMP_DIR = tempfile.gettempdir()
 
@app.route('/health', methods=['GET'])
def health_check():
    """Health check endpoint"""
    return jsonify({"status": "healthy", "service": "docx-to-pdf"}), 200
 
@app.route('/convert', methods=['POST'])
def convert_docx_to_pdf():
    """
    Convert DOCX to PDF using LibreOffice
    Expects: multipart/form-data with 'file' field containing .docx file
    Returns: PDF file
    """
    docx_path = None
    pdf_path = None
    
    try:
        if 'file' not in request.files:
            return jsonify({"error": "No file provided"}), 400
        
        file = request.files['file']
        
        if file.filename == '':
            return jsonify({"error": "No file selected"}), 400
        
        if not file.filename.lower().endswith('.docx'):
            return jsonify({"error": "File must be a .docx file"}), 400
        
        unique_id = str(uuid.uuid4())
        docx_filename = f"{unique_id}.docx"
        docx_path = os.path.join(TEMP_DIR, docx_filename)
        
        file.save(docx_path)
        logger.info(f"Saved DOCX file: {docx_path}")
        
        result = subprocess.run([
            'libreoffice',
            '--headless',
            '--convert-to', 'pdf',
            '--outdir', TEMP_DIR,
            docx_path
        ], capture_output=True, text=True, timeout=60)
        
        if result.returncode != 0:
            logger.error(f"LibreOffice error: {result.stderr}")
            raise Exception("Conversion failed")
        
        pdf_path = os.path.join(TEMP_DIR, f"{unique_id}.pdf")
        logger.info(f"Converted to PDF: {pdf_path}")
        
        if not os.path.exists(pdf_path):
            raise Exception("PDF file was not created")
        
        original_name = Path(file.filename).stem
        pdf_filename = f"{original_name}.pdf"
        
        response = send_file(
            pdf_path,
            mimetype='application/pdf',
            as_attachment=True,
            download_name=pdf_filename
        )
        
        @response.call_on_close
        def cleanup():
            try:
                if docx_path and os.path.exists(docx_path):
                    os.remove(docx_path)
                if pdf_path and os.path.exists(pdf_path):
                    os.remove(pdf_path)
                logger.info(f"Cleaned up files for {unique_id}")
            except Exception as e:
                logger.error(f"Error cleaning up files: {e}")
        
        return response
        
    except subprocess.TimeoutExpired:
        logger.error("Conversion timeout")
        if docx_path and os.path.exists(docx_path):
            os.remove(docx_path)
        if pdf_path and os.path.exists(pdf_path):
            os.remove(pdf_path)
        return jsonify({"error": "Conversion timeout"}), 500
        
    except Exception as e:
        logger.error(f"Error converting file: {str(e)}")
        if docx_path and os.path.exists(docx_path):
            try:
                os.remove(docx_path)
            except:
                pass
        if pdf_path and os.path.exists(pdf_path):
            try:
                os.remove(pdf_path)
            except:
                pass
        return jsonify({"error": f"Conversion failed: {str(e)}"}), 500
 
@app.route('/', methods=['GET'])
def index():
    """Root endpoint with API information"""
    return jsonify({
        "service": "DOCX to PDF Converter",
        "version": "1.0",
        "endpoints": {
            "/health": "GET - Health check",
            "/convert": "POST - Convert DOCX to PDF (multipart/form-data)"
        }
    }), 200
 
if __name__ == '__main__':
    port = int(os.environ.get('PORT', 8080))
    print(f"Starting Flask server on port {port}...")
    app.run(host='0.0.0.0', port=port, debug=False)
    