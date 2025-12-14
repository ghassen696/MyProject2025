from pathlib import Path
from bs4 import BeautifulSoup
import json
import hashlib

def find_all_html_files(root_dir):
    """Find all HTML files recursively."""
    return list(Path(root_dir).rglob("*.html"))


def extract_metadata(soup, filepath):
    """Extract rich metadata for better citations."""
    metadata = {}
    
    # Title
    metadata['title'] = soup.title.string.strip() if soup.title and soup.title.string else "Untitled"
    
    # DC metadata (Dublin Core - common in documentation)
    for meta in soup.find_all('meta'):
        name = meta.get('name', '')
        if name.startswith('DC.'):
            key = name.replace('DC.', '').lower()
            metadata[f'dc_{key}'] = meta.get('content', '')
    
    # Product/version info
    metadata['product'] = soup.find('meta', {'name': 'prodname'})
    metadata['product'] = metadata['product'].get('content', 'Unknown') if metadata['product'] else 'Unknown'
    
    metadata['version'] = soup.find('meta', {'name': 'version'})
    metadata['version'] = metadata['version'].get('content', 'Unknown') if metadata['version'] else 'Unknown'
    
    # Extract hierarchical path from filepath
    path_parts = Path(filepath).parts
    metadata['doc_path'] = ' > '.join(path_parts[-3:])  # Last 3 parts of path
    
    # Generate stable doc_id
    metadata['doc_id'] = hashlib.md5(str(filepath).encode()).hexdigest()[:12]
    
    return metadata


def extract_content(filepath):
    """Extract content with rich metadata."""
    try:
        with open(filepath, "r", encoding="utf-8") as f:
            soup = BeautifulSoup(f, "html.parser")
        
        # Remove script and style elements
        for script in soup(["script", "style", "nav", "header", "footer"]):
            script.decompose()
        
        # Extract metadata
        metadata = extract_metadata(soup, filepath)
        
        # Get main content
        body = soup.get_text(separator=" ", strip=True)
        
        # Clean up excessive whitespace
        body = " ".join(body.split())
        
        return {
            "filepath": str(filepath),
            "content": body,
            **metadata  # Unpack all metadata
        }
    
    except Exception as e:
        print(f"❌ Error processing {filepath}: {e}")
        return None


def ingest_all_documents(root_dir, output_json="html_docs.json"):
    """
    Ingest ALL HTML files - let semantic search handle relevance.
    """
    html_files = find_all_html_files(root_dir)
    documents = []
    
    print(f"📄 Found {len(html_files)} HTML files")
    
    for file in html_files:
        doc = extract_content(file)
        if doc and len(doc['content']) > 50:  # Minimal filter: at least 50 chars
            documents.append(doc)
    
    with open(output_json, "w", encoding="utf-8") as f:
        json.dump(documents, f, indent=2, ensure_ascii=False)
    
    print(f"✅ Saved {len(documents)} documents")
    return documents
