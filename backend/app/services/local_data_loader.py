# Local data loader service for permanent VectorDB storage

import os
import glob
import asyncio
from typing import List, Dict, Any, Optional
from pathlib import Path
import hashlib
import re
from datetime import datetime

from backend.app.config.settings import settings
from backend.app.services.gemini_service import gemini_service
from backend.app.utils.logger import logger, log_error, log_function_call

class LocalDataLoaderService:
    """Service for loading scraped Adeona Technologies data into VectorDB permanently"""
    
    def __init__(self):
        self.scraped_data_paths = [
            "/Users/pasindumalinda/AI_projects/Agent_02/adeona-chatbot/scraped_data_20250928_135828/individual_pages/",
            "/Users/pasindumalinda/AI_projects/Agent_02/adeona-chatbot/scraped_data_20250928_135828/"
        ]
        self.chunk_size = 1000  # Optimal chunk size for embeddings
        self.chunk_overlap = 200  # Overlap between chunks
        
        # File patterns to include
        self.file_patterns = [
            "Adeona Technologies_*.txt",
            "CLEAN_TEXT_ONLY_*.txt",
            "COMPLETE_WEBSITE_CONTENT_*.txt"
        ]
    
    def find_scraped_files(self) -> List[str]:
        """Find all scraped data files"""
        found_files = []
        
        for base_path in self.scraped_data_paths:
            if os.path.exists(base_path):
                for pattern in self.file_patterns:
                    files = glob.glob(os.path.join(base_path, pattern))
                    found_files.extend(files)
        
        # Remove duplicates and sort
        found_files = list(set(found_files))
        found_files.sort()
        
        logger.info(f"Found {len(found_files)} scraped data files")
        return found_files
    
    def read_file_content(self, file_path: str) -> Optional[Dict[str, Any]]:
        """Read and process file content"""
        try:
            with open(file_path, 'r', encoding='utf-8') as file:
                content = file.read()
            
            if len(content.strip()) < 50:
                logger.warning(f"File too small, skipping: {file_path}")
                return None
            
            # Extract metadata from filename and content
            filename = os.path.basename(file_path)
            file_hash = hashlib.md5(file_path.encode()).hexdigest()[:8]
            
            # Determine page type from filename or content
            page_type = self._determine_page_type(filename, content)
            
            # Clean content
            cleaned_content = self._clean_content(content)
            
            return {
                'file_path': file_path,
                'filename': filename,
                'content': cleaned_content,
                'page_type': page_type,
                'file_hash': file_hash,
                'content_length': len(cleaned_content),
                'modification_time': os.path.getmtime(file_path)
            }
            
        except Exception as e:
            log_error(e, f"read_file_content: {file_path}")
            return None
    
    def _determine_page_type(self, filename: str, content: str) -> str:
        """Determine page type from filename and content"""
        filename_lower = filename.lower()
        content_lower = content.lower()
        
        # Check filename patterns
        if 'complete_website' in filename_lower or 'clean_text_only' in filename_lower:
            return 'complete_website'
        
        # Check content patterns
        if 'privacy policy' in content_lower or 'data protection' in content_lower:
            return 'privacy_policy'
        elif 'about us' in content_lower or 'company overview' in content_lower:
            return 'about'
        elif 'contact us' in content_lower or 'contact information' in content_lower:
            return 'contact'
        elif 'services' in content_lower or 'solutions' in content_lower:
            return 'services'
        elif 'projects' in content_lower or 'portfolio' in content_lower:
            return 'projects'
        else:
            return 'general'
    
    def _clean_content(self, content: str) -> str:
        """Clean and normalize content"""
        # Remove excessive whitespace
        content = re.sub(r'\n\s*\n\s*\n', '\n\n', content)
        content = re.sub(r'[ \t]+', ' ', content)
        
        # Remove navigation elements and common web artifacts
        unwanted_patterns = [
            r'Skip to.*?content',
            r'Menu\s*Toggle',
            r'Click here.*?more',
            r'Read more.*?$',
            r'\[.*?\]',
            r'JavaScript.*?enabled',
            r'Cookies.*?accept',
        ]
        
        for pattern in unwanted_patterns:
            content = re.sub(pattern, '', content, flags=re.IGNORECASE | re.MULTILINE)
        
        # Clean up spacing
        content = content.strip()
        
        return content
    
    def chunk_content(self, content: str, metadata: Dict[str, Any]) -> List[Dict[str, Any]]:
        """Split content into chunks with metadata"""
        chunks = []
        
        # Split content into sentences first
        sentences = re.split(r'[.!?]+\s+', content)
        
        current_chunk = ""
        sentence_count = 0
        chunk_index = 0
        
        for sentence in sentences:
            sentence = sentence.strip()
            if not sentence:
                continue
            
            # Check if adding this sentence would exceed chunk size
            if len(current_chunk + sentence) > self.chunk_size and current_chunk:
                # Save current chunk
                if len(current_chunk.strip()) > 100:  # Only save substantial chunks
                    chunks.append({
                        'text': current_chunk.strip(),
                        'metadata': {
                            **metadata,
                            'chunk_index': chunk_index,
                            'chunk_sentence_count': sentence_count,
                            'chunk_length': len(current_chunk.strip()),
                            'url': f"https://adeonatech.net/{metadata['page_type']}",
                            'source': 'local_scraped_data',
                            'timestamp': datetime.now().isoformat()
                        }
                    })
                    chunk_index += 1
                
                # Start new chunk with overlap
                if self.chunk_overlap > 0:
                    overlap_sentences = sentences[max(0, sentence_count - 2):sentence_count]
                    current_chunk = ' '.join(overlap_sentences) + ' ' + sentence
                else:
                    current_chunk = sentence
                sentence_count = 0
            else:
                current_chunk += ' ' + sentence if current_chunk else sentence
                sentence_count += 1
        
        # Add remaining chunk
        if len(current_chunk.strip()) > 100:
            chunks.append({
                'text': current_chunk.strip(),
                'metadata': {
                    **metadata,
                    'chunk_index': chunk_index,
                    'chunk_sentence_count': sentence_count,
                    'chunk_length': len(current_chunk.strip()),
                    'url': f"https://adeonatech.net/{metadata['page_type']}",
                    'source': 'local_scraped_data',
                    'timestamp': datetime.now().isoformat()
                }
            })
        
        logger.info(f"Generated {len(chunks)} chunks from {metadata['filename']}")
        return chunks
    
    async def load_all_files(self) -> List[Dict[str, Any]]:
        """Load and process all scraped files"""
        try:
            log_function_call("load_all_files")
            
            files = self.find_scraped_files()
            if not files:
                logger.error("No scraped data files found")
                return []
            
            all_chunks = []
            processed_files = 0
            
            for file_path in files:
                logger.info(f"Processing file: {os.path.basename(file_path)}")
                
                file_data = self.read_file_content(file_path)
                if not file_data:
                    continue
                
                # Generate chunks
                chunks = self.chunk_content(file_data['content'], file_data)
                all_chunks.extend(chunks)
                processed_files += 1
                
                logger.info(f"Processed {file_data['filename']}: {len(chunks)} chunks, {file_data['content_length']} chars")
            
            logger.info(f"Successfully processed {processed_files} files into {len(all_chunks)} chunks")
            return all_chunks
            
        except Exception as e:
            log_error(e, "load_all_files")
            return []
    
    async def check_data_freshness(self) -> Dict[str, Any]:
        """Check if local data needs to be reloaded"""
        try:
            files = self.find_scraped_files()
            
            file_stats = []
            total_size = 0
            latest_mod_time = 0
            
            for file_path in files:
                if os.path.exists(file_path):
                    stat = os.stat(file_path)
                    file_stats.append({
                        'path': file_path,
                        'size': stat.st_size,
                        'modified': stat.st_mtime,
                        'modified_readable': datetime.fromtimestamp(stat.st_mtime).isoformat()
                    })
                    total_size += stat.st_size
                    latest_mod_time = max(latest_mod_time, stat.st_mtime)
            
            return {
                'files_found': len(files),
                'total_files_size': total_size,
                'latest_modification': datetime.fromtimestamp(latest_mod_time).isoformat() if latest_mod_time > 0 else None,
                'file_details': file_stats[:10],  # Show first 10 files
                'data_fresh': True  # Always consider local data as fresh
            }
            
        except Exception as e:
            log_error(e, "check_data_freshness")
            return {'files_found': 0, 'data_fresh': False, 'error': str(e)}
    
    def get_file_preview(self, file_path: str, max_chars: int = 500) -> str:
        """Get preview of file content"""
        try:
            with open(file_path, 'r', encoding='utf-8') as file:
                content = file.read()
            
            preview = content[:max_chars]
            if len(content) > max_chars:
                preview += "..."
            
            return preview
            
        except Exception as e:
            log_error(e, f"get_file_preview: {file_path}")
            return f"Error reading file: {str(e)}"

# Create global instance
local_data_loader = LocalDataLoaderService()