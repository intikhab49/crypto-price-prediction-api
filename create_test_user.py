import requests
import logging

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

def create_test_user():
    try:
        # Register new test user
        register_response = requests.post(
            "http://localhost:8000/auth/register",
            json={
                "username": "test_user",
                "password": "test_password",
                "email": "test_user@example.com"
            }
        )
        
        if register_response.status_code == 201:
            logger.info("Test user created successfully")
        else:
            logger.info("Test user might already exist, trying to log in")
        
        # Try logging in
        login_response = requests.post(
            "http://localhost:8000/auth/login",
            json={
                "username": "test_user",
                "password": "test_password",
                "email": "test_user@example.com"
            }
        )
        
        if login_response.status_code == 200:
            logger.info("Test user login successful")
            return True
        else:
            logger.error(f"Test user login failed: {login_response.text}")
            return False
            
    except Exception as e:
        logger.error(f"Error setting up test user: {str(e)}")
        return False

if __name__ == "__main__":
    create_test_user()