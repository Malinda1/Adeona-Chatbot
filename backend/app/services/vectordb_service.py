# VectorDB operations

import pinecone
from pinecone import Pinecone, ServerlessSpec
from typing import List, Dict, Optional, Any
import asyncio
from backend.app.config.settings import settings
from backend.app.services.gemini_service import gemini_service
from backend.app.core.web_scraper import web_scraper
from backend.app.utils.logger import logger, log_error, log_function_call
from backend.app.models.chat_models import VectorSearchResult

class VectorDBService:
    """Service for managing Pinecone vector database operations"""
    
    def __init__(self):
        self.pc = Pinecone(api_key=settings.PINECONE_API_KEY)
        self.index_name = settings.PINECONE_INDEX_NAME
        self.dimension = settings.EMBEDDING_DIMENSION
        self.index = None
        self._initialized = False
    
    async def initialize(self):
        """Initialize Pinecone index"""
        try:
            log_function_call("initialize_vectordb")
            
            # Check if index exists
            existing_indexes = self.pc.list_indexes()
            index_names = [idx['name'] for idx in existing_indexes['indexes']]
            
            if self.index_name not in index_names:
                logger.info(f"Creating new Pinecone index: {self.index_name}")
                self.pc.create_index(
                    name=self.index_name,
                    dimension=self.dimension,
                    metric='cosine',
                    spec=ServerlessSpec(
                        cloud='aws',
                        region='us-east-1'
                    )
                )
                # Wait for index to be ready
                await asyncio.sleep(10)
            
            self.index = self.pc.Index(self.index_name)
            self._initialized = True
            logger.info(f"VectorDB initialized successfully")
            
        except Exception as e:
            log_error(e, "initialize_vectordb")
            raise e
    
    async def ensure_initialized(self):
        """Ensure the vector database is initialized"""
        if not self._initialized:
            await self.initialize()
    
    async def upsert_content(self, content_chunks: List[Dict[str, Any]]) -> bool:
        """Upsert content chunks into vector database"""
        try:
            await self.ensure_initialized()
            log_function_call("upsert_content", {"chunks_count": len(content_chunks)})
            
            vectors = []
            
            for i, chunk in enumerate(content_chunks):
                text = chunk['text']
                metadata = chunk['metadata']
                
                # Generate embedding
                embedding = await gemini_service.generate_embedding(text)
                
                # Create vector with unique ID
                vector_id = f"{metadata['page_type']}_{metadata['chunk_index']}_{i}"
                
                vectors.append({
                    'id': vector_id,
                    'values': embedding,
                    'metadata': {
                        **metadata,
                        'text': text[:1000]  # Store first 1000 chars in metadata
                    }
                })
            
            # Upsert in batches
            batch_size = 100
            for i in range(0, len(vectors), batch_size):
                batch = vectors[i:i + batch_size]
                self.index.upsert(vectors=batch)
                logger.info(f"Upserted batch {i//batch_size + 1}/{(len(vectors)-1)//batch_size + 1}")
            
            logger.info(f"Successfully upserted {len(vectors)} vectors")
            return True
            
        except Exception as e:
            log_error(e, "upsert_content")
            return False
    
    async def search_similar(self, query: str, top_k: int = 5, filter_dict: Optional[Dict] = None) -> List[VectorSearchResult]:
        """Search for similar content in vector database"""
        try:
            await self.ensure_initialized()
            log_function_call("search_similar", {"query_length": len(query), "top_k": top_k})
            
            # Generate query embedding
            query_embedding = await gemini_service.generate_embedding(query)
            
            # Perform search
            search_results = self.index.query(
                vector=query_embedding,
                top_k=top_k,
                include_metadata=True,
                filter=filter_dict
            )
            
            results = []
            for match in search_results['matches']:
                result = VectorSearchResult(
                    content=match['metadata'].get('text', ''),
                    score=match['score'],
                    metadata=match['metadata']
                )
                results.append(result)
            
            logger.info(f"Found {len(results)} similar results")
            return results
            
        except Exception as e:
            log_error(e, "search_similar")
            return []
    
    async def search_by_page_type(self, query: str, page_type: str, top_k: int = 3) -> List[VectorSearchResult]:
        """Search for content filtered by page type"""
        try:
            filter_dict = {"page_type": page_type}
            return await self.search_similar(query, top_k, filter_dict)
        except Exception as e:
            log_error(e, "search_by_page_type")
            return []
    
    async def get_page_content(self, page_type: str) -> List[VectorSearchResult]:
        """Get all content for a specific page type"""
        try:
            await self.ensure_initialized()
            log_function_call("get_page_content", {"page_type": page_type})
            
            # Use a generic query to get page content
            generic_query = f"information about {page_type}"
            return await self.search_by_page_type(generic_query, page_type, top_k=10)
            
        except Exception as e:
            log_error(e, "get_page_content")
            return []
    
    async def index_website_content(self) -> bool:
        """Index all website content (run once during startup)"""
        try:
            log_function_call("index_website_content")
            
            # Check if content already exists
            stats = self.index.describe_index_stats()
            if stats['total_vector_count'] > 0:
                logger.info("Website content already indexed, skipping...")
                return True
            
            logger.info("Starting website content indexing...")
            
            # Scrape website content
            async with web_scraper as scraper:
                scraped_content = await scraper.scrape_all_pages()
            
            if not scraped_content:
                logger.error("No content scraped from website")
                return False
            
            # Process and chunk content
            all_chunks = []
            for content in scraped_content:
                chunks = web_scraper.chunk_content(content)
                all_chunks.extend(chunks)
            
            logger.info(f"Generated {len(all_chunks)} content chunks")
            
            # Index content
            success = await self.upsert_content(all_chunks)
            
            if success:
                logger.info("Website content indexing completed successfully")
            else:
                logger.error("Website content indexing failed")
            
            return success
            
        except Exception as e:
            log_error(e, "index_website_content")
            return False
    
    async def delete_all_vectors(self):
        """Delete all vectors from index (use with caution)"""
        try:
            await self.ensure_initialized()
            log_function_call("delete_all_vectors")
            
            self.index.delete(delete_all=True)
            logger.info("All vectors deleted from index")
            
        except Exception as e:
            log_error(e, "delete_all_vectors")
            raise e
    
    async def get_index_stats(self) -> Dict[str, Any]:
        """Get index statistics"""
        try:
            await self.ensure_initialized()
            stats = self.index.describe_index_stats()
            return stats
        except Exception as e:
            log_error(e, "get_index_stats")
            return {}

# Create global instance
vectordb_service = VectorDBService()