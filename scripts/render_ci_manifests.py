"""Render normal manifests with CI-only stub LLM and fixture embed server.

Must never be used to configure production or the real university corpus.
"""
from __future__ import annotations

import argparse
from pathlib import Path
import subprocess
import yaml


def main() -> None:
    parser=argparse.ArgumentParser()
    parser.add_argument('--api-image',required=True)
    parser.add_argument('--ui-image',required=True)
    parser.add_argument('--indexer-image',required=True)
    parser.add_argument('--out',required=True,type=Path)
    args=parser.parse_args()
    root=Path(__file__).resolve().parents[1]
    rendered=subprocess.check_output(['kubectl','kustomize',str(root/'k8s/overlays/prod')],text=True)
    docs=list(yaml.safe_load_all(rendered))
    for o in docs:
        if not o: continue
        kind=o.get('kind'); name=o.get('metadata',{}).get('name')
        if kind=='ConfigMap' and name=='rahbar-config':
            data=o['data']
            data.update({'LLM_PROVIDER':'stub', 'EMBED_MODEL':'fixture-bow-768',
                         'OLLAMA_URL':'http://fixture-embed:11434',
                         'RELEVANCE_FLOOR':'0.20','CHUNK_SIZE':'90','CHUNK_OVERLAP':'15',
                         'CACHE_THRESHOLD':'0.95','TOP_K':'5'})
        if kind=='Deployment' and name in ('api','ui'):
            for c in o['spec']['template']['spec']['containers']:
                if c['name']==name:
                    c['image']=args.api_image if name=='api' else args.ui_image
                    c['imagePullPolicy']='IfNotPresent'
        if kind=='CronJob' and name=='reindex':
            for c in o['spec']['jobTemplate']['spec']['template']['spec']['containers']:
                if c['name']=='indexer':
                    c['image']=args.indexer_image
                    c['imagePullPolicy']='IfNotPresent'
            # Do not let a weekly CronJob run against the fixture corpus's empty PVC.
            o['spec']['suspend']=True
    args.out.parent.mkdir(parents=True,exist_ok=True)
    args.out.write_text(yaml.safe_dump_all(docs,sort_keys=False),encoding='utf-8')
    print('Rendered fixture-only manifests for ephemeral cluster.')

if __name__=='__main__':main()
