from g_runtime import create_fastapi_app

if __name__ == "__main__":
    import uvicorn

    app = create_fastapi_app()
    uvicorn.run(app, host="0.0.0.0", port=8300)
