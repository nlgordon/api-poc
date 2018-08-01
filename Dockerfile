FROM python:3.6

COPY requirements.txt /
RUN pip install -Ur /requirements.txt
COPY api_poc /api_poc/
EXPOSE 8001

CMD ["python", "api_poc/app.py"]
