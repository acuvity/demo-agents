from g_runtime import create_fastapi_app_google_adk

app = create_fastapi_app_google_adk()

if __name__ == "__main__":
    import uvicorn

    uvicorn.run(app, host="0.0.0.0", port=8300)
