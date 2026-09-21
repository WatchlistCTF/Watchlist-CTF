# Create venv in the r300 folder
python3 -m venv venv

# Activate it
source venv/bin/activate

# Install boto3
pip install boto3

# Set AWS credentials
export AWS_ACCESS_KEY_ID=your_key
export AWS_SECRET_ACCESS_KEY=your_secret
export AWS_DEFAULT_REGION=us-east-2

# Run the script
python3 step2-populate_s3.py
