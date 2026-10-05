# Validate A4: hello-world container approximating a free Hugging Face Space (CPU basic).
FROM python:3.11-slim
RUN pip install --no-cache-dir onnxruntime==1.30.0 tokenizers huggingface_hub numpy fastapi uvicorn
ENV HF_HOME=/models
RUN python -c "from huggingface_hub import snapshot_download; snapshot_download('protectai/deberta-v3-base-prompt-injection-v2', allow_patterns=['onnx/*','*.json'])"
COPY app.py /app/app.py
WORKDIR /app
EXPOSE 7860
CMD ["uvicorn", "app:app", "--host", "0.0.0.0", "--port", "7860"]
