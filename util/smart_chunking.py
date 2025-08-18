"""
Smart chunking strategies for different document types with metadata preservation
"""

from typing import List, Dict, Any, Tuple
from langchain_text_splitters import RecursiveCharacterTextSplitter
from langchain_core.documents import Document
import re


class SmartDocumentChunker:
    def __init__(self, chunk_size: int = 1000, chunk_overlap: int = 200):
        self.chunk_size = chunk_size
        self.chunk_overlap = chunk_overlap
        self.default_splitter = RecursiveCharacterTextSplitter(
            chunk_size=chunk_size,
            chunk_overlap=chunk_overlap,
            add_start_index=True,
        )
    
    def chunk_document(self, text: str, file_path: str, images: List[Tuple[str, str]] = None, 
                      links: List[str] = None) -> List[Document]:
        """Main chunking method that determines document type and applies appropriate strategy"""
        file_ext = file_path.lower().split('.')[-1]
        
        if file_ext == 'pdf':
            return self._chunk_pdf(text, file_path, images, links)
        elif file_ext == 'docx':
            return self._chunk_docx(text, file_path, images, links)
        elif file_ext == 'pptx':
            return self._chunk_pptx(text, file_path, images, links)
        elif file_ext == 'txt':
            return self._chunk_txt(text, file_path)
        else:
            return self._chunk_default(text, file_path, images, links)
    
    def _chunk_pdf(self, text: str, file_path: str, images: List[Tuple[str, str]] = None, 
                   links: List[str] = None) -> List[Document]:
        """PDF-specific chunking that preserves page structure"""
        chunks = []
        
        # Split by pages first
        pages = text.split('--- Page ')
        
        for i, page_content in enumerate(pages):
            if not page_content.strip():
                continue
                
            page_num = i if i == 0 else int(page_content.split(' ---')[0])
            actual_content = page_content.split('---\n', 1)[-1] if '---\n' in page_content else page_content
            
            # Further split large pages
            if len(actual_content) > self.chunk_size:
                page_chunks = self.default_splitter.split_text(actual_content)
                for j, chunk in enumerate(page_chunks):
                    chunks.append(Document(
                        page_content=chunk,
                        metadata={
                            'source': file_path,
                            'page': page_num,
                            'chunk_id': f"page_{page_num}_chunk_{j}",
                            'document_type': 'pdf',
                            'total_pages': len(pages) - 1,
                            'images': [img for img in (images or []) if f"page{page_num}" in img[0]],
                            'links': links or []
                        }
                    ))
            else:
                chunks.append(Document(
                    page_content=actual_content,
                    metadata={
                        'source': file_path,
                        'page': page_num,
                        'chunk_id': f"page_{page_num}",
                        'document_type': 'pdf',
                        'total_pages': len(pages) - 1,
                        'images': [img for img in (images or []) if f"page{page_num}" in img[0]],
                        'links': links or []
                    }
                ))
        
        return chunks
    
    def _chunk_docx(self, text: str, file_path: str, images: List[Tuple[str, str]] = None, 
                    links: List[str] = None) -> List[Document]:
        """DOCX-specific chunking that preserves paragraph structure"""
        chunks = []
        
        # Split by paragraphs and group them
        paragraphs = [p.strip() for p in text.split('\n') if p.strip()]
        
        current_chunk = ""
        chunk_id = 0
        
        for para in paragraphs:
            # Check if adding this paragraph would exceed chunk size
            if len(current_chunk) + len(para) > self.chunk_size and current_chunk:
                chunks.append(Document(
                    page_content=current_chunk.strip(),
                    metadata={
                        'source': file_path,
                        'chunk_id': f"docx_chunk_{chunk_id}",
                        'document_type': 'docx',
                        'images': images or [],
                        'links': links or []
                    }
                ))
                current_chunk = para + "\n"
                chunk_id += 1
            else:
                current_chunk += para + "\n"
        
        # Add the last chunk
        if current_chunk.strip():
            chunks.append(Document(
                page_content=current_chunk.strip(),
                metadata={
                    'source': file_path,
                    'chunk_id': f"docx_chunk_{chunk_id}",
                    'document_type': 'docx',
                    'images': images or [],
                    'links': links or []
                }
            ))
        
        return chunks
    
    def _chunk_pptx(self, text: str, file_path: str, images: List[Tuple[str, str]] = None, 
                    links: List[str] = None) -> List[Document]:
        """PPTX-specific chunking that preserves slide structure"""
        chunks = []
        
        # Split by slides
        slides = text.split('--- Slide ')
        
        for i, slide_content in enumerate(slides):
            if not slide_content.strip():
                continue
                
            slide_num = i if i == 0 else int(slide_content.split(' ---')[0])
            actual_content = slide_content.split('---\n', 1)[-1] if '---\n' in slide_content else slide_content
            
            if actual_content.strip():
                chunks.append(Document(
                    page_content=actual_content.strip(),
                    metadata={
                        'source': file_path,
                        'slide': slide_num,
                        'chunk_id': f"slide_{slide_num}",
                        'document_type': 'pptx',
                        'total_slides': len(slides) - 1,
                        'images': [img for img in (images or []) if f"slide{slide_num}" in img[0]],
                        'links': links or []
                    }
                ))
        
        return chunks
    
    def _chunk_txt(self, text: str, file_path: str) -> List[Document]:
        """TXT-specific chunking with paragraph awareness"""
        # Use default splitter but preserve paragraph boundaries where possible
        text_chunks = self.default_splitter.split_text(text)
        
        chunks = []
        for i, chunk in enumerate(text_chunks):
            chunks.append(Document(
                page_content=chunk,
                metadata={
                    'source': file_path,
                    'chunk_id': f"txt_chunk_{i}",
                    'document_type': 'txt',
                    'total_chunks': len(text_chunks)
                }
            ))
        
        return chunks
    
    def _chunk_default(self, text: str, file_path: str, images: List[Tuple[str, str]] = None, 
                      links: List[str] = None) -> List[Document]:
        """Default chunking strategy for unknown document types"""
        text_chunks = self.default_splitter.split_text(text)
        
        chunks = []
        for i, chunk in enumerate(text_chunks):
            chunks.append(Document(
                page_content=chunk,
                metadata={
                    'source': file_path,
                    'chunk_id': f"chunk_{i}",
                    'document_type': 'unknown',
                    'total_chunks': len(text_chunks),
                    'images': images or [],
                    'links': links or []
                }
            ))
        
        return chunks
    
    def extract_headers_and_structure(self, text: str) -> Dict[str, Any]:
        """Extract document structure like headers, lists, tables"""
        structure = {
            'headers': [],
            'lists': [],
            'tables': [],
            'sections': []
        }
        
        lines = text.split('\n')
        
        for i, line in enumerate(lines):
            line = line.strip()
            
            # Detect headers (simple heuristic)
            if line and (line.isupper() or 
                        re.match(r'^#+\s', line) or  # Markdown headers
                        re.match(r'^\d+\.?\s+[A-Z]', line)):  # Numbered sections
                structure['headers'].append({
                    'text': line,
                    'line_number': i,
                    'level': self._estimate_header_level(line)
                })
            
            # Detect lists
            if re.match(r'^[\*\-\+]\s+', line) or re.match(r'^\d+\.?\s+', line):
                structure['lists'].append({
                    'text': line,
                    'line_number': i,
                    'type': 'bullet' if line.startswith(('*', '-', '+')) else 'numbered'
                })
        
        return structure
    
    def _estimate_header_level(self, text: str) -> int:
        """Estimate header level based on formatting"""
        if text.startswith('###'):
            return 3
        elif text.startswith('##'):
            return 2
        elif text.startswith('#'):
            return 1
        elif text.isupper():
            return 1
        elif re.match(r'^\d+\.?\s+', text):
            return 2
        else:
            return 3


# Usage example:
# chunker = SmartDocumentChunker(chunk_size=800, chunk_overlap=150)
# documents = chunker.chunk_document(text, file_path, images, links)