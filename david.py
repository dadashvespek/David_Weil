from flask import Flask, request, jsonify
import pandas as pd
import os

app = Flask(__name__)

# Directory where uploaded files will be saved
UPLOAD_FOLDER = 'uploads'
os.makedirs(UPLOAD_FOLDER, exist_ok=True)  # Ensure the upload folder exists

@app.route('/upload-dataframe', methods=['POST'])
def upload_dataframe():
    # Check if there is a JSON payload
    if not request.json:
        return 'Missing JSON in request', 400

    try:
        # Convert JSON to pandas DataFrame
        dataframe = pd.DataFrame(request.json)
        
        # Generate a filename (you could make this more sophisticated)
        filename = 'uploaded_dataframe.csv'
        filepath = os.path.join(UPLOAD_FOLDER, filename)
        
        # Determine if the file already exists to handle the header accordingly
        file_exists = os.path.isfile(filepath)
        
        # Save the DataFrame as a CSV file, appending if file exists
        dataframe.to_csv(filepath, mode='a', index=False, header=not file_exists)
        
        return jsonify({'message': f'DataFrame appended to {filename}'} if file_exists else {'message': f'DataFrame saved as {filename}'}), 200
    except Exception as e:
        return jsonify({'error': str(e)}), 500
    
@app.route('/upload-dataframes', methods=['POST'])
def upload_dataframes():
    if not request.json:
        return 'Missing JSON in request', 400

    filename = 'uploaded_dataframe.csv'
    filepath = os.path.join(UPLOAD_FOLDER, filename)
    file_exists = os.path.isfile(filepath)

    try:
        for df_json in request.json:
            dataframe = pd.DataFrame(df_json)
            dataframe.to_csv(filepath, mode='a', index=False, header=not file_exists)
            # Update header flag to False after the first write operation
            if file_exists is False:
                file_exists = True

        return jsonify({'message': f'DataFrames appended to {filename}'}), 200
    except Exception as e:
        return jsonify({'error': str(e)}), 500


if __name__ == '__main__':
    app.run(debug=True,port=8080)
