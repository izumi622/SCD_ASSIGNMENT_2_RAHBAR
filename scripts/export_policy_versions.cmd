@echo off
setlocal
cd /d "%~dp0.."
if not exist "eval" mkdir "eval"
echo Exporting indexed 2023 policy passages from the live ChromaDB collection...
minikube kubectl -- exec -n rahbar deployment/api -- python -c "import chromadb,sys; c=chromadb.HttpClient(host='chroma',port=8000).get_collection('rahbar'); r=c.get(where={'source':'undergraduate-academic-rules-aug-2023.pdf'},include=['documents','metadatas']); print('SOURCE: undergraduate-academic-rules-aug-2023.pdf'); print('CHUNKS:',len(r['ids'])); [print('\n=== PAGE '+str(m.get('page'))+' / SECTION '+str(m.get('section'))+' ===\n'+t) for m,t in sorted(zip(r['metadatas'],r['documents']),key=lambda x: int(x[0].get('page') or 0))]; sys.exit(2 if not r['ids'] else 0)" > "eval\version-2023-extract.txt"
if errorlevel 1 goto fail
echo Exporting indexed 2026 policy passages from the live ChromaDB collection...
minikube kubectl -- exec -n rahbar deployment/api -- python -c "import chromadb,sys; c=chromadb.HttpClient(host='chroma',port=8000).get_collection('rahbar'); r=c.get(where={'source':'academic-rules-handbook-jun-2026.pdf'},include=['documents','metadatas']); print('SOURCE: academic-rules-handbook-jun-2026.pdf'); print('CHUNKS:',len(r['ids'])); [print('\n=== PAGE '+str(m.get('page'))+' / SECTION '+str(m.get('section'))+' ===\n'+t) for m,t in sorted(zip(r['metadatas'],r['documents']),key=lambda x: int(x[0].get('page') or 0))]; sys.exit(2 if not r['ids'] else 0)" > "eval\version-2026-extract.txt"
if errorlevel 1 goto fail
echo.
echo Version evidence exported successfully:
echo   eval\version-2023-extract.txt
echo   eval\version-2026-extract.txt
echo Please upload both files for source-grounded q09/q10 verification.
exit /b 0
:fail
echo.
echo ERROR: Cannot export policy chunks. Check that Minikube is running and the source filenames match the indexed metadata.
exit /b 1
