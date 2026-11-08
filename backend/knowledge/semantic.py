"""Optional pinned Hugging Face / PyTorch semantic retrieval on CPU."""
import json
from pathlib import Path
import re
from backend.knowledge.retrieval import EngineeringIndex,sha

MODEL='sentence-transformers/all-MiniLM-L6-v2'
REVISION='1110a243fdf4706b3f48f1d95db1a4f5529b4d41'

def embed(texts,local_only=False):
    import torch
    from transformers import AutoTokenizer,AutoModel
    tokenizer=AutoTokenizer.from_pretrained(MODEL,revision=REVISION,trust_remote_code=False,local_files_only=local_only)
    model=AutoModel.from_pretrained(MODEL,revision=REVISION,trust_remote_code=False,use_safetensors=True,local_files_only=local_only).to('cpu').eval()
    outputs=[]
    torch.set_num_threads(2)
    with torch.inference_mode():
        for offset in range(0,len(texts),16):
            data=tokenizer(texts[offset:offset+16],padding=True,truncation=True,max_length=256,return_tensors='pt')
            hidden=model(**data).last_hidden_state
            mask=data['attention_mask'].unsqueeze(-1)
            pooled=(hidden*mask).sum(dim=1)/mask.sum(dim=1).clamp(min=1)
            outputs.append(torch.nn.functional.normalize(pooled,p=2,dim=1).numpy())
    import numpy as np
    return np.concatenate(outputs)

def chunks(index):
    rows=[]
    for doc in index.documents:
        lines=doc['excerpt'].splitlines()
        for start in range(0,len(lines),24):
            excerpt='\n'.join(lines[start:start+32])
            rows.append({'document_id':doc['id'],'text':doc['title']+'\n'+excerpt,'excerpt':excerpt,
               'citation':{'path':doc['path'],'source_sha256':doc['source_sha256'],
                           'start_line':doc['start_line']+start,'end_line':doc['start_line']+min(start+32,len(lines))-1}})
    return rows

def build(root,path):
    import numpy as np
    import importlib.metadata as meta
    corpus=EngineeringIndex(root,root/'knowledge/engineering-v3.json');rows=chunks(corpus)
    vectors=embed([r['text'] for r in rows])
    path.parent.mkdir(parents=True,exist_ok=True)
    np.savez_compressed(path,vectors=vectors)
    metadata={'model_id':MODEL,'revision':REVISION,'device':'cpu','corpus_hash':corpus.corpus_hash,'chunks':rows,
              'index_sha256':sha(path.read_bytes()),'versions':{p:meta.version(p) for p in ['torch','transformers','safetensors']},
              'max_tokens':256,'limitations':['Small source corpus; no domain-expert semantic benchmark.','Chunks longer than 256 model tokens are truncated for embedding only.']}
    path.with_suffix('.json').write_text(json.dumps(metadata,indent=2)+'\n');return metadata

def query(root,path,question,k=3):
    import numpy as np
    if not 1<=len(question)<=2000 or not 1<=k<=10:raise ValueError('Query outside bounds')
    corpus=EngineeringIndex(root,root/'knowledge/engineering-v3.json');metadata=json.loads(path.with_suffix('.json').read_text())
    if metadata['corpus_hash']!=corpus.corpus_hash or metadata['revision']!=REVISION or metadata['index_sha256']!=sha(path.read_bytes()):raise ValueError('Semantic index provenance changed')
    vectors=np.load(path,allow_pickle=False)['vectors'];q=embed([question],local_only=True)[0]
    scores=vectors@q;rows=[];seen=set()
    for i in np.argsort(-scores):
        hit=metadata['chunks'][int(i)]
        if hit['document_id'] in seen:continue
        seen.add(hit['document_id']);rows.append({**hit,'score':float(scores[i])})
        if len(rows)>=k:break
    return {'question':question,'mode':'Hugging Face MiniLM semantic source retrieval','model_id':MODEL,'revision':REVISION,
            'corpus_hash':corpus.corpus_hash,'sources':rows,'abstained':False,
            'limitations':['Similarity-ranked context, not an answer-generation model.','No calibrated out-of-domain abstention threshold.']}
