"""Extractive grounded answers. Source text is data, never instructions to tools."""
from pathlib import Path
import re
from backend.knowledge.retrieval import EngineeringIndex,tokens

STOP={'a','an','the','is','are','how','what','where','does','do','in','of','to','for','and','with','can','i','it','this','that','be','on','use','used'}

def answer(root:Path,question:str):
    index=EngineeringIndex(root,root/'knowledge/engineering-v3.json')
    hits=index.search(question,3)
    terms=set(tokens(question))-STOP
    matches=[]
    for hit in hits:
        lines=hit['excerpt'].splitlines()
        candidates=[(len(terms & set(tokens(line))),i,line.strip()) for i,line in enumerate(lines) if len(line.strip())>=12]
        candidates.sort(key=lambda x:(-x[0],x[1]))
        if not candidates or candidates[0][0]<min(2,len(terms)) or not terms:continue
        overlap,i,quote=candidates[0]
        citation={**hit['citation'],'start_line':hit['citation']['start_line']+i,'end_line':hit['citation']['start_line']+i}
        matches.append({'document_id':hit['document_id'],'quote':quote,'citation':citation,'query_term_overlap':overlap})
    return {'question':question,'mode':'extractive, no LLM generation','corpus_hash':index.corpus_hash,
            'abstained':not matches,'answer':'\n'.join(f"[{i+1}] {m['quote']}" for i,m in enumerate(matches)) if matches else 'No supported answer found in the versioned engineering corpus.',
            'sources':matches,'limitations':['Exact source excerpts; not a semantic or generative model.',
                                            'Citation correctness does not establish that an excerpt fully answers the question.']}
