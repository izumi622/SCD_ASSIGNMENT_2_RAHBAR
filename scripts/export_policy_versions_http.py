#!/usr/bin/env python3
"""Read-only paginated export of 2023 and 2026 RAHBAR policy passages from ChromaDB.

Use a temporary localhost port-forward to service/chroma. This makes bounded
HTTP requests rather than a single large, potentially stalled kubectl exec.
"""
from __future__ import annotations
import argparse
import json
from pathlib import Path
import sys
import time
from urllib.error import HTTPError, URLError
from urllib.request import Request, urlopen
from urllib.parse import quote

SOURCES = {
    '2023': 'undergraduate-academic-rules-aug-2023.pdf',
    '2026': 'academic-rules-handbook-jun-2026.pdf',
}
API_PREFIX = '/api/v2/tenants/default_tenant/databases/default_database/collections'


def call(base: str, path: str, payload: dict | None = None) -> dict:
    url = base.rstrip('/') + path
    body = json.dumps(payload).encode('utf-8') if payload is not None else None
    request = Request(url, data=body,
                      headers={'Content-Type': 'application/json'},
                      method='POST' if payload is not None else 'GET')
    for attempt in range(3):
        try:
            with urlopen(request, timeout=35) as response:
                result = json.loads(response.read().decode('utf-8'))
            if not isinstance(result, dict):
                raise RuntimeError(f'Unexpected response from {url}: {type(result).__name__}')
            return result
        except (HTTPError, URLError, TimeoutError, json.JSONDecodeError) as exc:
            if attempt == 2 or (isinstance(exc, HTTPError) and exc.code < 500):
                raise RuntimeError(f'{url}: {exc}') from exc
            print(f'HTTP attempt {attempt + 1} failed; retrying...', flush=True)
            time.sleep(attempt + 1)
    raise AssertionError('unreachable')


def export_year(base: str, collection_id: str, year: str, dest: Path, batch: int) -> int:
    source = SOURCES[year]
    records: list[tuple[dict, str]] = []
    offset = 0
    while True:
        result = call(base, f'{API_PREFIX}/{quote(collection_id)}/get',
                      {'where': {'source': source},
                       'include': ['documents', 'metadatas'],
                       'limit': batch, 'offset': offset})
        ids = result.get('ids') or []
        docs = result.get('documents') or []
        meta = result.get('metadatas') or []
        if not (len(ids) == len(docs) == len(meta)):
            raise RuntimeError(f'{year}: Chroma returned inconsistent lengths')
        for document, metadata in zip(docs, meta):
            metadata = metadata or {}
            if metadata.get('source') != source:
                raise RuntimeError(f'{year}: unexpected source metadata: {metadata.get("source")}')
            records.append((metadata, str(document or '')))
        offset += len(ids)
        print(f'  {year}: fetched {offset} chunks', flush=True)
        if len(ids) < batch:
            break
        if offset > 20000:
            raise RuntimeError('Unusually large export; check collection and filter')
    if not records:
        raise RuntimeError(f'No indexed passages found for {source}')
    records.sort(key=lambda x: (int(x[0].get('page') or 0),
                                str(x[0].get('section') or '')))
    lines = [f'SOURCE: {source}', f'CHUNKS: {len(records)}',
             'DATA: Indexed passages (verify against original PDFs)', '']
    for metadata, text in records:
        lines.extend([f'=== PAGE {metadata.get("page")} / SECTION {metadata.get("section")} ===',
                      text, ''])
    dest.write_text('\n'.join(lines), encoding='utf-8')
    return len(records)


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument('--base', default='http://127.0.0.1:8001')
    parser.add_argument('--out-dir', default='eval')
    parser.add_argument('--batch', type=int, default=12)
    args = parser.parse_args()
    if not 1 <= args.batch <= 50:
        parser.error('--batch must be in 1..50')
    output = Path(args.out_dir)
    output.mkdir(parents=True, exist_ok=True)
    try:
        collection = call(args.base, API_PREFIX + '/rahbar')
        collection_id = collection.get('id')
        if not collection_id:
            raise RuntimeError('RAHBAR collection missing from ChromaDB')
        print(f'Connected to ChromaDB collection: {collection_id}', flush=True)
        for year in ('2023', '2026'):
            path = output / f'version-{year}-extract.txt'
            print(f'Exporting {year} policy...', flush=True)
            count = export_year(args.base, collection_id, year, path, args.batch)
            print(f'  Saved {count} chunks: {path}', flush=True)
        print('DONE: source comparison files exported without modifying the index.')
        return 0
    except (RuntimeError, OSError) as exc:
        print(f'EXPORT ERROR: {exc}', file=sys.stderr)
        print('Verify the Chroma port-forward is still running on 8001.', file=sys.stderr)
        return 1


if __name__ == '__main__':
    sys.exit(main())
