FROM python:3.12-slim
ENV PYTHONDONTWRITEBYTECODE=1 PYTHONUNBUFFERED=1 DATA_DIR=/data PORT=8090
WORKDIR /app
RUN pip install --no-cache-dir --only-binary=:all: Pillow==13.0.0 reportlab==5.1.0 fonttools==4.67.0
COPY --from=comic-design design.py editorial_layout.py /app/comic-design/
COPY --from=comic-fonts manrope.ttf manrope-OFL.txt /app/dgx-invitations/fonts/
COPY narrative_profiles.py experiments.py experiments.js series.py series-editor.js source_generator.py source-generator.js books.py book-export.js panel_correction.py panel-correction.js lettering.py bubble-positioner.js dialogue.py character_profiles.py app.py storage.py stories.py article_plan.py improvement.py sharing.py comfy.py engine.py editorial.py feedback.py learning.py local_llm.py telegram_trigger.py index.html character-editor.js speech-editor.js ./
RUN chmod -R a+rX /app/comic-design /app/dgx-invitations && mkdir /data && chown 1000:1000 /data
USER 1000:1000
EXPOSE 8090
CMD ["python", "app.py"]
