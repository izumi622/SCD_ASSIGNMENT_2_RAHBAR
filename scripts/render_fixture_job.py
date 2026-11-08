"""Render the *real* indexer Job for a CI ConfigMap fixture corpus.

CI changes only the corpus volume and image, not the indexing arguments.
The production Job continues to use its persistent corpus-data PVC.
"""
from __future__ import annotations

import argparse
from pathlib import Path
import yaml


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument('--image', required=True)
    parser.add_argument('--out', type=Path, required=True)
    args=parser.parse_args()
    root=Path(__file__).resolve().parents[1]
    obj=yaml.safe_load((root/'k8s/base/indexer-job.yaml').read_text())
    obj['metadata']['name']='indexer-fixture'
    obj['metadata']['namespace']='rahbar'
    spec=obj['spec']['template']['spec']
    indexer=next(x for x in spec['containers'] if x['name']=='indexer')
    indexer['image']=args.image
    indexer['args']=[]
    for v in spec['volumes']:
        if v['name']=='corpus':
            v.pop('persistentVolumeClaim',None)
            v['configMap']={'name':'fixture-corpus'}
    args.out.parent.mkdir(parents=True,exist_ok=True)
    args.out.write_text(yaml.safe_dump(obj,sort_keys=False),encoding='utf-8')
    print(f'Wrote real CI indexing Job to {args.out}')


if __name__=='__main__':main()
