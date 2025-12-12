# APK Builder Template (Python + Flask) 

This repository is a template to implement a web backend + worker that automatically customizes
an Android template project and builds signed APKs. It is designed to be pushed to GitHub and
deployed on Render (or any Docker-capable host).

**What's included**
- `template/` (placeholder): copy your Android `MyWebviewApp_Fixed3` project here.
- `backend/`: Flask web server (upload form + enqueue).
- `scripts/`: replacement & icon generation utilities.
- `Dockerfile`: container image that installs JDK & Android commandline tools (reference).
- `render.yaml`: (example) Render infra config.

**How to use**
1. Replace `template/` with your Android project (copy contents of your MyWebviewApp_Fixed3).
2. Customize `scripts/replace_vars.py` to match the exact locations in your template (package names, MainActivity path, etc).
3. Build and test locally (you'll need Android SDK locally for actual builds) OR deploy to Render.
4. Store sensitive data (keystore, passwords, S3 keys) as Render/environment secrets — DO NOT commit them.

**Important notes**
- This template avoids embedding any keystore or passwords.
- Container images with Android SDK are large; consider using a prebuilt base image or caching layers.
- For production, use a robust queue system (Redis + RQ/Celery) and limit concurrent builds.

