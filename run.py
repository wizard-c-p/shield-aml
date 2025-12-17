import uvicorn

if __name__ == "__main__":
    print("🚀 ShieldAML v1.0.0 Enterprise Edition Starting...")
    print("👉 Dashboard: http://127.0.0.1:8000")
    print("👉 Swagger API: http://127.0.0.1:8000/docs")
    
    # Run the FastAPI application served from app/main.py
    uvicorn.run("app.main:app", host="127.0.0.1", port=8000, reload=True)