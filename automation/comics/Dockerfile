FROM python:3.12-slim
ENV PYTHONDONTWRITEBYTECODE=1 PYTHONUNBUFFERED=1 DATA_DIR=/data PORT=8090
WORKDIR /app
COPY dialogue.py character_profiles.py app.py storage.py stories.py article_plan.py improvement.py sharing.py comfy.py engine.py editorial.py feedback.py learning.py local_llm.py telegram_trigger.py index.html character-editor.js speech-editor.js ./
RUN mkdir /data && chown 1000:1000 /data
USER 1000:1000
EXPOSE 8090
CMD ["python", "app.py"]
