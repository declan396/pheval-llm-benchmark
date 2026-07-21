python -c "
import sys
sys.argv = ['run_llm_rag_disease.py']
import run_llm_rag_disease as r
r.RESULTS_DIR.mkdir(exist_ok=True)

import json
from pathlib import Path
from sentence_transformers import SentenceTransformer
import chromadb

embed_model = SentenceTransformer(r.EMBEDDING_MODEL)
collection = r.load_index()
id_to_label = r.parse_hpo_labels()

for ppath in sorted(Path('phenopackets').glob('patient_*.json'))[:5]:
    patient_id = ppath.stem
    print(f'Testing {patient_id}...', end=' ')
    hpo_ids, hpo_labels = r.load_patient(ppath, id_to_label)
    retrieved = r.retrieve_diseases(hpo_labels, collection, embed_model)
    prompt = r.build_prompt(hpo_labels, retrieved)
    response = r.client.messages.create(model=r.MODEL, max_tokens=r.MAX_TOKENS, system=r.SYSTEM_PROMPT, messages=[{'role': 'user', 'content': prompt}])
    text = response.content[0].text.strip()
    result = r._parse_json(text)
    if result:
        result['top_diseases'] = r._pad_diseases(result.get('top_diseases', []), retrieved)
        print(f'ok  top: {result[\"top_diseases\"][0][\"disease_id\"]}  diseases: {len(result[\"top_diseases\"])}')
    else:
        print(f'failed to parse JSON')
"