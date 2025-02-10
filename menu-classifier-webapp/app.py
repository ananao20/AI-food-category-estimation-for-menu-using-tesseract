import os
import pytesseract
from flask import Flask, request, render_template, jsonify
import cv2
import openpyxl
from PIL import Image
import re

# Initialize Flask app
app = Flask(__name__)

# Set the folder where the uploaded files will be saved
UPLOAD_FOLDER = 'static/uploads'
app.config['UPLOAD_FOLDER'] = UPLOAD_FOLDER

# Define path to Tesseract executable
pytesseract.pytesseract.tesseract_cmd = r'C:\Program Files\Tesseract-OCR\tesseract.exe'  # Change this if needed

# Load the Excel file with dish names, categories, and calories
def load_excel():
    wb = openpyxl.load_workbook(r'dish_categories.xlsx')
    return wb.active

sheet = load_excel()

# Helper function to clean up extracted text
def clean_text(extracted_text):
    # Remove non-alphanumeric characters except spaces and digits
    cleaned_text = re.sub(r'[^a-zA-Z0-9\s]', '', extracted_text)
    # Remove multiple spaces
    cleaned_text = re.sub(r'\s+', ' ', cleaned_text).strip()
    return cleaned_text

# Helper function to classify dishes
def classify_dishes(extracted_text):
    dishes = []
    cleaned_text = clean_text(extracted_text)
    print("Cleaned Text:", cleaned_text)

    # Convert to lowercase for case-insensitive matching
    cleaned_text = cleaned_text.lower()

    # Loop through the rows in the Excel sheet to check for dish matches
    for row in sheet.iter_rows(min_row=2, values_only=True):
        category = row[0].lower()  # Category (e.g., 'healthy', 'unhealthy')
        dish_name = clean_text(row[1]).lower()  # Cleaned and lowercased dish name
        calories = row[2]

        print(f"Checking: {dish_name}, Found in Extracted Text: {'Yes' if dish_name in cleaned_text else 'No'}")

        # Check if the dish name is in the cleaned text
        if dish_name in cleaned_text:
            dishes.append((dish_name, category, calories))

    return dishes


# Route to home page and image upload form
@app.route('/')
def index():
    return render_template('index.html')

# Route to handle the uploaded image and classify dishes
@app.route('/upload', methods=['POST'])
def upload_image():
    if 'file' not in request.files:
        return 'No file part'
    
    file = request.files['file']
    
    if file.filename == '':
        return 'No selected file'

    # Validate that the file is an image
    if not file.filename.lower().endswith(('png', 'jpg', 'jpeg')):
        return 'Invalid file type. Please upload an image.'

    # Save the uploaded image
    image_path = os.path.join(app.config['UPLOAD_FOLDER'], file.filename)
    file.save(image_path)

    # Read the image using OpenCV
    img = cv2.imread(image_path)

    # Convert the image to grayscale and apply thresholding (improve OCR accuracy)
    gray = cv2.cvtColor(img, cv2.COLOR_BGR2GRAY)
    _, thresh = cv2.threshold(gray, 150, 255, cv2.THRESH_BINARY)

    # Extract text using Tesseract
    text = pytesseract.image_to_string(thresh)
    print("Extracted Text:", text)  # Extracted text will also be shown on the terminal

    # Classify the dishes from extracted text
    dishes = classify_dishes(text)

    if not dishes:
        # If no dishes detected, include the extracted text in the response for debugging
        return jsonify({"message": "No dishes detected or classified", "status": "error", "extracted_text": text})
    
    # Return the classified dishes as a JSON response with category and calories
    return jsonify({
        "dishes": [{"dish_name": dish[0], "category": dish[1], "calories": dish[2]} for dish in dishes],
        "status": "success",
        "extracted_text": text  # Include the extracted text in the response for debugging
    })


if __name__ == '__main__':
    app.run(debug=True)
