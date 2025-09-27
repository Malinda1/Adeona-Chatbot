# VectorDB operations

# VectorDB operations - SerpAPI only integration

from pinecone import Pinecone, ServerlessSpec
from typing import List, Dict, Optional, Any
import asyncio
from backend.app.config.settings import settings
from backend.app.services.gemini_service import gemini_service
from backend.app.services.serpapi_service import serpapi_service  # Only SerpAPI, no web scraping
from backend.app.utils.logger import logger, log_error, log_function_call
from backend.app.models.chat_models import VectorSearchResult

class VectorDBService:
    """Service for managing Pinecone vector database operations with SerpAPI-only integration"""
    
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
            index_names = [idx.name for idx in existing_indexes.indexes]
            
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
            
            if not content_chunks:
                logger.warning("No content chunks provided for upserting")
                return False
            
            vectors = []
            successful_embeddings = 0
            
            for i, chunk in enumerate(content_chunks):
                text = chunk['text']
                metadata = chunk['metadata']
                
                if not text or len(text.strip()) < 20:
                    logger.warning(f"Skipping chunk {i} - insufficient text content (length: {len(text)})")
                    continue
                
                # Generate embedding
                try:
                    embedding = await gemini_service.generate_embedding(text)
                    if not embedding or len(embedding) != self.dimension:
                        logger.warning(f"Invalid embedding for chunk {i} - dimension: {len(embedding) if embedding else 0}")
                        continue
                    
                    successful_embeddings += 1
                    
                except Exception as e:
                    logger.error(f"Failed to generate embedding for chunk {i}: {e}")
                    continue
                
                # Create vector with unique ID based on URL and chunk index
                url_hash = str(hash(metadata['url']))[-8:]
                vector_id = f"{metadata['page_type']}_{url_hash}_{metadata['chunk_index']}_serpapi"
                
                vectors.append({
                    'id': vector_id,
                    'values': embedding,
                    'metadata': {
                        **metadata,
                        'text': text[:4000],  # Store substantial text for better context
                        'content_length': len(text),
                        'extraction_source': 'serpapi'
                    }
                })
                
                logger.debug(f"Prepared vector {vector_id} for {metadata['page_type']} page")
            
            if not vectors:
                logger.error(f"No valid vectors created from {len(content_chunks)} content chunks")
                return False
            
            logger.info(f"Successfully prepared {len(vectors)} vectors from {successful_embeddings} successful embeddings")
            
            # Upsert in batches to avoid rate limits
            batch_size = 50
            success_count = 0
            
            for i in range(0, len(vectors), batch_size):
                batch = vectors[i:i + batch_size]
                try:
                    self.index.upsert(vectors=batch)
                    success_count += len(batch)
                    logger.info(f"Upserted batch {i//batch_size + 1}/{(len(vectors)-1)//batch_size + 1} - {len(batch)} vectors")
                    await asyncio.sleep(1)  # Delay between batches
                except Exception as e:
                    logger.error(f"Failed to upsert batch {i//batch_size + 1}: {e}")
                    continue
            
            logger.info(f"Successfully upserted {success_count}/{len(vectors)} vectors to Pinecone")
            return success_count > 0
            
        except Exception as e:
            log_error(e, "upsert_content")
            return False
    
    async def search_similar(self, query: str, top_k: int = 15, filter_dict: Optional[Dict] = None) -> List[VectorSearchResult]:
        """Search for similar content in vector database with enhanced results"""
        try:
            await self.ensure_initialized()
            log_function_call("search_similar", {"query_length": len(query), "top_k": top_k})
            
            # Generate query embedding
            query_embedding = await gemini_service.generate_embedding(query)
            
            # Perform search with higher top_k for better results
            search_results = self.index.query(
                vector=query_embedding,
                top_k=min(top_k, 25),  # Increased limit for better recall
                include_metadata=True,
                filter=filter_dict
            )
            
            results = []
            for match in search_results['matches']:
                # Lower threshold for better recall, especially for privacy policy queries
                score_threshold = 0.5 if 'privacy' in query.lower() else 0.6
                
                if match['score'] > score_threshold:
                    result = VectorSearchResult(
                        content=match['metadata'].get('text', ''),
                        score=match['score'],
                        metadata=match['metadata']
                    )
                    results.append(result)
            
            logger.info(f"Found {len(results)} similar results for query: '{query[:50]}...'")
            
            # Log the best matches for debugging
            if results:
                best_match = results[0]
                logger.info(f"Best match: {best_match.metadata.get('page_type', 'unknown')} page, score: {best_match.score:.3f}")
            
            return results
            
        except Exception as e:
            log_error(e, "search_similar")
            return []
    
    async def search_by_page_type(self, query: str, page_type: str, top_k: int = 10) -> List[VectorSearchResult]:
        """Search for content filtered by page type"""
        try:
            filter_dict = {"page_type": page_type}
            results = await self.search_similar(query, top_k, filter_dict)
            logger.info(f"Found {len(results)} results for page type '{page_type}'")
            return results
        except Exception as e:
            log_error(e, "search_by_page_type")
            return []
    
    async def search_privacy_policy(self, query: str) -> List[VectorSearchResult]:
        """Specific search for privacy policy content with enhanced matching"""
        try:
            log_function_call("search_privacy_policy", {"query": query})
            
            # Search specifically for privacy-related content
            privacy_results = await self.search_by_page_type(query, "privacy", top_k=8)
            
            # Also search generally for privacy terms with lower threshold
            privacy_keywords = ["privacy policy", "data protection", "privacy practices", "data security"]
            general_results = []
            
            for keyword in privacy_keywords:
                combined_query = f"{query} {keyword}"
                keyword_results = await self.search_similar(combined_query, top_k=5)
                general_results.extend(keyword_results)
            
            # Combine and deduplicate results
            all_results = privacy_results + general_results
            seen_ids = set()
            unique_results = []
            
            for result in all_results:
                result_id = f"{result.metadata.get('url', '')}_{result.metadata.get('chunk_index', 0)}"
                if result_id not in seen_ids:
                    seen_ids.add(result_id)
                    unique_results.append(result)
            
            # Sort by relevance score
            unique_results.sort(key=lambda x: x.score, reverse=True)
            
            logger.info(f"Found {len(unique_results)} privacy policy results")
            return unique_results[:10]  # Return top 10 results
            
        except Exception as e:
            log_error(e, "search_privacy_policy")
            return []
    
    async def get_page_content(self, page_type: str) -> List[VectorSearchResult]:
        """Get all content for a specific page type"""
        try:
            await self.ensure_initialized()
            log_function_call("get_page_content", {"page_type": page_type})
            
            # Use a generic query to get page content
            generic_query = f"information about {page_type} Adeona Technologies"
            return await self.search_by_page_type(generic_query, page_type, top_k=15)
            
        except Exception as e:
            log_error(e, "get_page_content")
            return []
    
    async def force_reindex_website_content(self) -> bool:
        """Force complete reindexing of website content using SerpAPI ONLY"""
        try:
            log_function_call("force_reindex_website_content")
            
            logger.info("Starting FORCED website content reindexing with SerpAPI ONLY...")
            
            # Step 1: Delete all existing vectors first
            await self.delete_all_vectors()
            logger.info("Deleted all existing vectors - fresh start")
            
            # Wait for deletion to complete
            await asyncio.sleep(5)
            
            # Step 2: Extract comprehensive content using SerpAPI ONLY
            logger.info("Extracting content using SerpAPI ONLY...")
            scraped_content = await serpapi_service.scrape_all_company_pages()
            
            if not scraped_content:
                logger.error("No content extracted using SerpAPI")
                return False
            
            logger.info(f"SerpAPI extracted content from {len(scraped_content)} pages")
            
            # Log content details for verification
            total_chars = 0
            for content in scraped_content:
                chars = len(content.content)
                total_chars += chars
                logger.info(f"Page: {content.page_type} | URL: {content.url} | Content: {chars} chars")
                
                # Show preview of content for debugging
                preview = content.content[:200].replace('\n', ' ')
                logger.info(f"Preview: {preview}...")
                
                if chars < 100:
                    logger.warning(f"Limited content for {content.url}")
            
            logger.info(f"Total content extracted: {total_chars} characters")
            
            if total_chars < 1000:
                logger.warning("Total extracted content is less than expected, but proceeding...")
            
            # Step 3: Process and chunk content
            all_chunks = []
            for content in scraped_content:
                if len(content.content) > 50:  # Only process if we have substantial content
                    chunks = serpapi_service.chunk_content(content)
                    all_chunks.extend(chunks)
                    logger.info(f"Generated {len(chunks)} chunks for {content.page_type} page")
                else:
                    logger.warning(f"Skipping {content.page_type} - insufficient content ({len(content.content)} chars)")
            
            if not all_chunks:
                logger.error("No valid content chunks generated")
                return False
            
            logger.info(f"Generated total of {len(all_chunks)} content chunks")
            
            # Step 4: Index content in vector database
            success = await self.upsert_content(all_chunks)
            
            if success:
                # Verify indexing
                await asyncio.sleep(3)  # Wait for indexing to complete
                stats = await self.get_index_stats()
                vector_count = stats.get('total_vector_count', 0)
                logger.info(f"FORCED website content reindexing completed successfully - {vector_count} vectors indexed")
                
                # Test search to verify content is accessible
                test_results = await self.search_similar("privacy policy", top_k=3)
                logger.info(f"Test search for 'privacy policy' returned {len(test_results)} results")
                
                if test_results:
                    best_result = test_results[0]
                    logger.info(f"Best result: {best_result.metadata.get('page_type', 'unknown')} page, score: {best_result.score:.3f}")
                
                return vector_count > 0
            else:
                logger.error("FORCED website content reindexing failed during vector insertion")
                return False
            
        except Exception as e:
            log_error(e, "force_reindex_website_content")
            return False
    
    async def index_website_content(self) -> bool:
        """Index website content using SerpAPI (always force reindex for better content)"""
        try:
            log_function_call("index_website_content")
            
            logger.info("Starting website content indexing with SerpAPI (forcing complete reindex)...")
            return await self.force_reindex_website_content()
            
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
            
            # Wait for deletion to propagate
            await asyncio.sleep(3)
            
        except Exception as e:
            log_error(e, "delete_all_vectors")
            raise e
    
    async def get_index_stats(self) -> Dict[str, Any]:
        """Get index statistics"""
        try:
            await self.ensure_initialized()
            stats = self.index.describe_index_stats()
            
            # Handle the case where stats might be None or not have expected structure
            if stats is None:
                logger.warning("Index stats returned None")
                return {"total_vector_count": 0, "namespaces": {}}
            
            # Convert to dict safely
            if hasattr(stats, '__dict__'):
                stats_dict = stats.__dict__
            elif hasattr(stats, 'to_dict'):
                stats_dict = stats.to_dict()
            elif isinstance(stats, dict):
                stats_dict = stats
            else:
                # If we can't convert, create a basic structure
                logger.warning(f"Unexpected stats type: {type(stats)}")
                stats_dict = {"total_vector_count": 0, "namespaces": {}}
            
            # Ensure we have the expected keys
            if 'total_vector_count' not in stats_dict:
                stats_dict['total_vector_count'] = 0
            if 'namespaces' not in stats_dict:
                stats_dict['namespaces'] = {}
            
            return stats_dict
            
        except Exception as e:
            log_error(e, "get_index_stats")
            return {"total_vector_count": 0, "namespaces": {}, "error": str(e)}

# Create global instance
vectordb_service = VectorDBService()