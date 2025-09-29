# VectorDB operations



from pinecone import Pinecone, ServerlessSpec
from typing import List, Dict, Optional, Any
import asyncio
from datetime import datetime
import hashlib

from backend.app.config.settings import settings
from backend.app.services.gemini_service import gemini_service
from backend.app.services.local_data_loader import local_data_loader
from backend.app.services.serpapi_service import serpapi_service
from backend.app.utils.logger import logger, log_error, log_function_call
from backend.app.models.chat_models import VectorSearchResult

class EnhancedVectorDBService:
    """managing Pinecone vector database with improved search logic"""
    
    def __init__(self):
        self.pc = Pinecone(api_key=settings.PINECONE_API_KEY)
        self.index_name = settings.PINECONE_INDEX_NAME
        self.dimension = settings.EMBEDDING_DIMENSION
        self.index = None
        self._initialized = False
        self._local_data_loaded = False
        
        # Namespace for different data sources
        self.LOCAL_DATA_NAMESPACE = "adeona_local_scraped"
        self.SERPAPI_NAMESPACE = "adeona_serpapi"
        
        #  More lenient search thresholds
        self.MIN_SEARCH_SCORE = 0.6  # Lowered from 0.8
        self.GOOD_RESULT_THRESHOLD = 0.75  # Lowered from 0.8
        self.EXCELLENT_RESULT_THRESHOLD = 0.85
    
    async def initialize(self):
        """Initialize Pinecone index and load local data permanently"""
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
            
            # Load local scraped data permanently on initialization
            await self.ensure_local_data_loaded()
            
            logger.info(f"VectorDB initialized successfully with permanent local data")
            
        except Exception as e:
            log_error(e, "initialize_vectordb")
            raise e
    
    async def ensure_initialized(self):
        """Ensure the vector database is initialized"""
        if not self._initialized:
            await self.initialize()
    
    async def ensure_local_data_loaded(self):
        """Ensure local scraped data is loaded into VectorDB (permanent storage)"""
        try:
            if self._local_data_loaded:
                logger.info("Local data already loaded, skipping...")
                return True
            
            # Check if local data already exists in VectorDB
            stats = await self.get_namespace_stats(self.LOCAL_DATA_NAMESPACE)
            local_vector_count = stats.get('vector_count', 0)
            
            if local_vector_count > 0:
                logger.info(f"Found {local_vector_count} existing local vectors in VectorDB")
                self._local_data_loaded = True
                return True
            
            # Load local data for the first time
            logger.info("Loading local scraped data into VectorDB permanently...")
            success = await self.load_local_data_to_vectordb()
            
            if success:
                self._local_data_loaded = True
                logger.info("Local data successfully loaded and stored permanently")
            
            return success
            
        except Exception as e:
            log_error(e, "ensure_local_data_loaded")
            return False
    
    async def load_local_data_to_vectordb(self) -> bool:
        """Load local scraped data into VectorDB permanently"""
        try:
            log_function_call("load_local_data_to_vectordb")
            
            # Load all local files
            all_chunks = await local_data_loader.load_all_files()
            
            if not all_chunks:
                logger.error("No chunks loaded from local files")
                return False
            
            logger.info(f"Processing {len(all_chunks)} chunks from local files...")
            
            # Process chunks and create vectors
            vectors = []
            successful_embeddings = 0
            
            for i, chunk in enumerate(all_chunks):
                try:
                    text = chunk['text']
                    metadata = chunk['metadata']
                    
                    # Generate embedding
                    embedding = await gemini_service.generate_embedding(text)
                    
                    if not embedding or len(embedding) != self.dimension:
                        logger.warning(f"Invalid embedding for chunk {i}")
                        continue
                    
                    successful_embeddings += 1
                    
                    # Create unique vector ID for local data
                    chunk_hash = hashlib.md5(text.encode()).hexdigest()[:8]
                    vector_id = f"local_{metadata['page_type']}_{metadata['chunk_index']}_{chunk_hash}"
                    
                    vectors.append({
                        'id': vector_id,
                        'values': embedding,
                        'metadata': {
                            **metadata,
                            'text': text[:4000],  # Store text for context
                            'data_source': 'local_scraped',
                            'loaded_at': datetime.now().isoformat()
                        }
                    })
                    
                    if len(vectors) >= 50:  # Batch processing
                        await self._upsert_batch(vectors, self.LOCAL_DATA_NAMESPACE)
                        vectors = []
                        await asyncio.sleep(1)  # Rate limiting
                    
                except Exception as e:
                    logger.error(f"Error processing chunk {i}: {e}")
                    continue
            
            # Process remaining vectors
            if vectors:
                await self._upsert_batch(vectors, self.LOCAL_DATA_NAMESPACE)
            
            logger.info(f"Successfully loaded {successful_embeddings} local data vectors into VectorDB")
            return successful_embeddings > 0
            
        except Exception as e:
            log_error(e, "load_local_data_to_vectordb")
            return False
    
    async def _upsert_batch(self, vectors: List[Dict], namespace: str = ""):
        """Upsert a batch of vectors to specific namespace"""
        try:
            if namespace:
                self.index.upsert(vectors=vectors, namespace=namespace)
            else:
                self.index.upsert(vectors=vectors)
            logger.debug(f"Upserted {len(vectors)} vectors to namespace: {namespace or 'default'}")
        except Exception as e:
            log_error(e, f"_upsert_batch to namespace {namespace}")
            raise e
    
    async def search_adeona_knowledge(self, query: str, top_k: int = 15, include_serpapi: bool = False) -> List[VectorSearchResult]:
        """Search Adeona knowledge base with better scoring and expanded search"""
        try:
            await self.ensure_initialized()
            log_function_call("search_adeona_knowledge", {"query": query[:50], "top_k": top_k})
            
            # Expand query for better matching
            expanded_query = self._expand_query_for_adeona(query)
            
            # Generate query embedding
            query_embedding = await gemini_service.generate_embedding(expanded_query)
            
            # Search with more results initially to have better selection
            local_results = await self._search_namespace(
                query_embedding, 
                self.LOCAL_DATA_NAMESPACE, 
                top_k=top_k * 2,  # Get more results initially
                min_score=self.MIN_SEARCH_SCORE  # Use more lenient threshold
            )
            
            logger.info(f"Local search returned {len(local_results)} results with expanded query")
            
            # Check for different quality levels
            excellent_results = [r for r in local_results if r.score >= self.EXCELLENT_RESULT_THRESHOLD]
            good_results = [r for r in local_results if r.score >= self.GOOD_RESULT_THRESHOLD]
            decent_results = [r for r in local_results if r.score >= self.MIN_SEARCH_SCORE]
            
            logger.info(f"Result quality breakdown: {len(excellent_results)} excellent, {len(good_results)} good, {len(decent_results)} decent")
            
            # If we have excellent results, use them
            if excellent_results:
                logger.info("Using excellent local results")
                return excellent_results[:top_k]
            
            # If we have good results, use them
            if good_results:
                logger.info("Using good local results")
                return good_results[:top_k]
            
            # If we have decent results and don't need SerpAPI, use them
            if decent_results and not include_serpapi:
                logger.info("Using decent local results")
                return decent_results[:top_k]
            
            # If include_serpapi is True and we need more/better results
            if include_serpapi:
                logger.info("Including SerpAPI results due to limited local results")
                serpapi_results = await self._search_namespace(
                    query_embedding,
                    self.SERPAPI_NAMESPACE,
                    top_k=top_k//2,
                    min_score=self.MIN_SEARCH_SCORE
                )
                
                all_results = decent_results + serpapi_results
                all_results.sort(key=lambda x: x.score, reverse=True)
                return all_results[:top_k]
            
            # Return whatever we found, even if scores are low
            return decent_results[:top_k] if decent_results else []
            
        except Exception as e:
            log_error(e, "search_adeona_knowledge")
            return []
    
    def _expand_query_for_adeona(self, query: str) -> str:
        """Expand query to improve search matching"""
        query_lower = query.lower().strip()
        
        # Handle context awareness - "this company" means "Adeona Technologies"
        if any(phrase in query_lower for phrase in ['this company', 'the company', 'your company']):
            query = query.replace('this company', 'Adeona Technologies')
            query = query.replace('the company', 'Adeona Technologies')
            query = query.replace('your company', 'Adeona Technologies')
        
        # Expand service-related queries
        if any(word in query_lower for word in ['service', 'services', 'solution', 'solutions']):
            query += " Adeona Technologies services software development CRM mobile web applications"
        
        # Expand company-related queries
        if any(word in query_lower for word in ['company', 'about', 'information', 'details']):
            query += " Adeona Technologies company information"
        
        # Add Adeona context if not present
        if 'adeona' not in query_lower:
            query += " Adeona Technologies"
        
        logger.info(f"Expanded query: {query}")
        return query
    
    async def _search_namespace(self, query_embedding: List[float], namespace: str, top_k: int = 15, min_score: float = 0.6) -> List[VectorSearchResult]:
        """Search specific namespace with more lenient scoring"""
        try:
            search_results = self.index.query(
                vector=query_embedding,
                top_k=top_k,
                include_metadata=True,
                namespace=namespace
            )
            
            results = []
            for match in search_results['matches']:
                # Use more lenient threshold and include more results
                if match['score'] >= min_score:
                    result = VectorSearchResult(
                        content=match['metadata'].get('text', ''),
                        score=match['score'],
                        metadata=match['metadata']
                    )
                    results.append(result)
            
            logger.info(f"Namespace {namespace}: Found {len(results)} results above threshold {min_score}")
            return results
            
        except Exception as e:
            log_error(e, f"_search_namespace: {namespace}")
            return []
    
    async def search_with_fallback(self, query: str, top_k: int = 12) -> tuple[List[VectorSearchResult], bool]:
        """Enhanced search with more intelligent fallback logic"""
        try:
            log_function_call("search_with_fallback", {"query": query[:50]})
            
            # First search local knowledge base with expanded results
            local_results = await self.search_adeona_knowledge(query, top_k=top_k, include_serpapi=False)
            
            logger.info(f"Local search found {len(local_results)} results")
            
            # More intelligent fallback decision
            needs_fallback = self._should_use_serpapi_fallback(local_results, query)
            
            if not needs_fallback:
                logger.info("Local results sufficient, no fallback needed")
                return local_results, False
            
            # Use SerpAPI fallback
            logger.info("Using SerpAPI fallback for additional context")
            serpapi_results = await self._search_serpapi_fallback(query)
            
            # IMPROVED: Better result combination
            combined_results = self._combine_search_results(local_results, serpapi_results)
            
            return combined_results[:top_k], True
            
        except Exception as e:
            log_error(e, "search_with_fallback")
            return [], False
    
    def _should_use_serpapi_fallback(self, local_results: List[VectorSearchResult], query: str) -> bool:
        """More intelligent decision on when to use SerpAPI fallback"""
        
        # If no local results at all
        if not local_results:
            logger.info("No local results - using fallback")
            return True
        
        # If we have high-quality results (score > 0.85), don't use fallback
        high_quality_count = sum(1 for r in local_results if r.score >= 0.85)
        if high_quality_count >= 2:
            logger.info(f"Have {high_quality_count} high-quality results - no fallback needed")
            return False
        
        # If we have moderate results but enough of them
        moderate_quality_count = sum(1 for r in local_results if r.score >= 0.75)
        if moderate_quality_count >= 3:
            logger.info(f"Have {moderate_quality_count} moderate-quality results - no fallback needed")
            return False
        
        # If query is service-related and we have few results, use fallback
        query_lower = query.lower()
        if any(word in query_lower for word in ['service', 'services', 'what do', 'what are']) and len(local_results) < 3:
            logger.info("Service-related query with few results - using fallback")
            return True
        
        # If all results have low scores, use fallback
        if all(r.score < 0.7 for r in local_results):
            logger.info("All results have low scores - using fallback")
            return True
        
        return False
    
    def _combine_search_results(self, local_results: List[VectorSearchResult], serpapi_results: List[VectorSearchResult]) -> List[VectorSearchResult]:
        """Better combination of local and SerpAPI results"""
        
        # Prioritize local results by boosting their scores slightly
        boosted_local = []
        for result in local_results:
            boosted_result = VectorSearchResult(
                content=result.content,
                score=min(result.score + 0.1, 1.0),  # Slight boost for local results
                metadata={**result.metadata, 'source_boost': 'local_prioritized'}
            )
            boosted_local.append(boosted_result)
        
        # Combine and sort
        all_results = boosted_local + serpapi_results
        all_results.sort(key=lambda x: x.score, reverse=True)
        
        # Remove duplicates based on content similarity
        deduplicated_results = self._remove_duplicate_results(all_results)
        
        logger.info(f"Combined results: {len(local_results)} local + {len(serpapi_results)} SerpAPI = {len(deduplicated_results)} final")
        return deduplicated_results
    
    def _remove_duplicate_results(self, results: List[VectorSearchResult]) -> List[VectorSearchResult]:
        """Remove duplicate or very similar results"""
        if not results:
            return results
        
        unique_results = []
        seen_content = set()
        
        for result in results:
            # Create a simplified version of content for comparison
            content_key = result.content[:100].lower().replace(' ', '').replace('\n', '')
            
            if content_key not in seen_content:
                seen_content.add(content_key)
                unique_results.append(result)
        
        return unique_results
    
    async def _search_serpapi_fallback(self, query: str) -> List[VectorSearchResult]:
        """Search SerpAPI as fallback with better result processing"""
        try:
            # Use SerpAPI to search for additional information
            serpapi_results = await serpapi_service.search_adeona_specific(query, max_results=5)
            
            # Convert SerpAPI results to VectorSearchResult format
            fallback_results = []
            for i, result in enumerate(serpapi_results):
                #Better scoring for SerpAPI results
                base_score = 0.75 - (i * 0.05)  # Start higher, decrease by position
                relevance_score = result.get('relevance_score', 0)
                
                # Combine base score with relevance score
                final_score = min(base_score + (relevance_score * 0.1), 0.85)
                
                fallback_results.append(VectorSearchResult(
                    content=result.get('snippet', ''),
                    score=final_score,
                    metadata={
                        'title': result.get('title', ''),
                        'url': result.get('link', ''),
                        'page_type': 'serpapi_fallback',
                        'source': 'serpapi_realtime',
                        'relevance_score': relevance_score,
                        'timestamp': datetime.now().isoformat()
                    }
                ))
            
            logger.info(f"SerpAPI fallback returned {len(fallback_results)} results")
            return fallback_results
            
        except Exception as e:
            log_error(e, "_search_serpapi_fallback")
            return []
    
    # Continue with other existing methods...
    async def search_privacy_policy(self, query: str) -> List[VectorSearchResult]:
        """privacy policy search using local data"""
        try:
            log_function_call("search_privacy_policy", {"query": query})
            
            # Create privacy-focused query
            privacy_query = f"privacy policy data protection {query}"
            
            # Search with emphasis on privacy content
            results = await self.search_adeona_knowledge(privacy_query, top_k=10, include_serpapi=True)
            
            # Filter for privacy-related content
            privacy_results = []
            for result in results:
                metadata = result.metadata
                content_lower = result.content.lower()
                
                is_privacy_related = (
                    metadata.get('page_type') == 'privacy_policy' or
                    'privacy' in content_lower or
                    'data protection' in content_lower or
                    'personal information' in content_lower
                )
                
                if is_privacy_related:
                    privacy_results.append(result)
            
            logger.info(f"Found {len(privacy_results)} privacy-related results")
            return privacy_results[:5]  # Return top 5 privacy results
            
        except Exception as e:
            log_error(e, "search_privacy_policy")
            return []
    
    async def get_namespace_stats(self, namespace: str) -> Dict[str, Any]:
        """Get statistics for specific namespace"""
        try:
            await self.ensure_initialized()
            stats = self.index.describe_index_stats()
            
            namespace_stats = {}
            if hasattr(stats, 'namespaces') and stats.namespaces:
                namespace_info = stats.namespaces.get(namespace, {})
                if hasattr(namespace_info, 'vector_count'):
                    namespace_stats['vector_count'] = namespace_info.vector_count
                else:
                    namespace_stats['vector_count'] = 0
            else:
                namespace_stats['vector_count'] = 0
            
            return namespace_stats
            
        except Exception as e:
            log_error(e, f"get_namespace_stats: {namespace}")
            return {'vector_count': 0, 'error': str(e)}
    
    async def get_comprehensive_stats(self) -> Dict[str, Any]:
        """Get comprehensive statistics for all data sources"""
        try:
            await self.ensure_initialized()
            
            # Get overall stats
            overall_stats = self.index.describe_index_stats()
            
            # Get namespace-specific stats
            local_stats = await self.get_namespace_stats(self.LOCAL_DATA_NAMESPACE)
            serpapi_stats = await self.get_namespace_stats(self.SERPAPI_NAMESPACE)
            
            # Get local file information
            local_data_info = await local_data_loader.check_data_freshness()
            
            return {
                'total_vectors': getattr(overall_stats, 'total_vector_count', 0),
                'local_data_vectors': local_stats.get('vector_count', 0),
                'serpapi_vectors': serpapi_stats.get('vector_count', 0),
                'local_files_count': local_data_info.get('files_found', 0),
                'local_data_size': local_data_info.get('total_files_size', 0),
                'local_data_loaded': self._local_data_loaded,
                'last_updated': datetime.now().isoformat()
            }
            
        except Exception as e:
            log_error(e, "get_comprehensive_stats")
            return {'error': str(e)}
    
    async def reload_local_data(self) -> bool:
        """Force reload of local data (for admin use)"""
        try:
            log_function_call("reload_local_data")
            
            # Clear local data namespace
            await self.clear_namespace(self.LOCAL_DATA_NAMESPACE)
            
            # Reset flags
            self._local_data_loaded = False
            
            # Reload data
            success = await self.load_local_data_to_vectordb()
            
            if success:
                self._local_data_loaded = True
                logger.info("Local data successfully reloaded")
            
            return success
            
        except Exception as e:
            log_error(e, "reload_local_data")
            return False
    
    async def clear_namespace(self, namespace: str):
        """Clear all vectors from specific namespace"""
        try:
            await self.ensure_initialized()
            self.index.delete(delete_all=True, namespace=namespace)
            logger.info(f"Cleared namespace: {namespace}")
            await asyncio.sleep(2)  # Wait for deletion to propagate
        except Exception as e:
            log_error(e, f"clear_namespace: {namespace}")
            raise e
    
    # Legacy methods for compatibility
    async def search_similar(self, query: str, top_k: int = 15, filter_dict: Optional[Dict] = None) -> List[VectorSearchResult]:
        """Legacy search method - now uses enhanced Adeona knowledge search"""
        return await self.search_adeona_knowledge(query, top_k)
    
    async def search_by_page_type(self, query: str, page_type: str, top_k: int = 10) -> List[VectorSearchResult]:
        """Search for content filtered by page type"""
        try:
            results = await self.search_adeona_knowledge(f"{query} {page_type}", top_k)
            # Filter by page type
            filtered_results = [r for r in results if r.metadata.get('page_type') == page_type]
            return filtered_results[:top_k]
        except Exception as e:
            log_error(e, "search_by_page_type")
            return []

# Create global instance
vectordb_service = EnhancedVectorDBService()