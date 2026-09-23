FROM python:3.12-slim
WORKDIR /app
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt gunicorn
COPY voorraadwacht ./voorraadwacht
ENV DATABASE_URL=sqlite:////data/voorraadwacht.db
VOLUME /data
EXPOSE 8000
# Eén worker: anders draait de automatische controle meerdere keren
CMD ["gunicorn", "-w", "1", "--threads", "4", "-b", "0.0.0.0:8000", "voorraadwacht:create_app()"]
