import json, time
from pathlib import Path
import numpy as np, onnxruntime as ort
from fastapi import FastAPI
from huggingface_hub import snapshot_download
from tokenizers import Tokenizer
t0 = time.time()
p = Path(snapshot_download('protectai/deberta-v3-base-prompt-injection-v2', allow_patterns=['onnx/*','*.json']))
tf = p / 'onnx' / 'tokenizer.json'
tok = Tokenizer.from_file(str(tf if tf.exists() else p / 'tokenizer.json'))
so = ort.SessionOptions(); so.intra_op_num_threads = 2
sess = ort.InferenceSession(str(p / 'onnx' / 'model.onnx'), so, providers=['CPUExecutionProvider'])
names = {i.name for i in sess.get_inputs()}
LOAD_S = time.time() - t0
app = FastAPI()
@app.get('/healthz')
def health(): return {'ok': True, 'load_s': round(LOAD_S, 1)}
@app.post('/score')
def score(body: dict):
    ids = tok.encode(body['text'], add_special_tokens=False).ids[:510]
    ids = [tok.token_to_id('[CLS]')] + ids + [tok.token_to_id('[SEP]')]
    feed = {'input_ids': np.array([ids], dtype=np.int64), 'attention_mask': np.ones((1, len(ids)), dtype=np.int64)}
    if 'token_type_ids' in names: feed['token_type_ids'] = np.zeros((1, len(ids)), dtype=np.int64)
    t = time.perf_counter(); out = sess.run(None, feed)[0][0]
    return {'ms': round((time.perf_counter() - t) * 1000, 1), 'tokens': len(ids)}
