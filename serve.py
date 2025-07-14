
from app.main import INAIApplication


# serve.py (bottom of the file)
inai = INAIApplication()
sio_app = inai.asgi_app  # This line is required for uvicorn
