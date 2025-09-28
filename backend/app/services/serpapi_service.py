# Fixed SerpAPI service with SSL certificate handling

# Enhanced SerpAPI service with improved search accuracy and SSL handling

import aiohttp
import ssl
from typing import List, Dict, Optional, Any
import asyncio
from urllib.parse import quote
import json

from backend.app.config.settings import settings
from backend.app.utils.logger import logger, log_error, log_function_call

class EnhancedSerpAPIService:
    """Enhanced service for real-time Adeona Technologies information via Google Search"""
    
    def __init__(self):
        self.serpapi_key = settings.SERPAPI_API_KEY
        self.serpapi_url = "https://serpapi.com/search"
        self.adeona_domain = settings.ADEONA_DOMAIN
        
        # Rate limiting
        self._last_request_time = 0
        self._min_request_interval = 1.2  # Slightly increased interval
        
        # Enhanced search configuration
        self.search_config = {
            'timeout': 20,
            'max_retries': 2,
            'min_content_length': 30
        }
    
    async def _rate_limited_request(self):
        """Implement rate limiting for API requests"""
        import time
        current_time = time.time()
        time_since_last = current_time - self._last_request_time
        
        if time_since_last < self._min_request_interval:
            wait_time = self._min_request_interval - time_since_last
            await asyncio.sleep(wait_time)
        
        self._last_request_time = time.time()
    
    async def search_adeona_specific(self, query: str, max_results: int = 8) -> List[Dict[str, Any]]:
        """IMPROVED: Search for Adeona Technologies specific information with better accuracy"""
        try:
            log_function_call("search_adeona_specific", {"query": query[:50], "max_results": max_results})
            
            if not self.serpapi_key:
                logger.warning("SerpAPI key not configured")
                return []
            
            # Rate limiting
            await self._rate_limited_request()
            
            # IMPROVED: Create multiple search strategies for better coverage
            search_strategies = self._create_search_strategies(query)
            
            all_results = []
            
            # Try different search approaches
            for strategy in search_strategies:
                try:
                    results = await self._execute_search_strategy(strategy, max_results)
                    if results:
                        all_results.extend(results)
                        
                    # Don't overload with too many requests
                    if len(all_results) >= max_results * 2:
                        break
                        
                except Exception as e:
                    logger.warning(f"Search strategy failed: {e}")
                    continue
            
            # Process and deduplicate results
            processed_results = self._process_and_deduplicate_results(all_results, max_results)
            
            logger.info(f"SerpAPI search completed: {len(processed_results)} final results")
            return processed_results
            
        except Exception as e:
            log_error(e, "search_adeona_specific")
            return []
    
    def _create_search_strategies(self, query: str) -> List[Dict[str, str]]:
        """IMPROVED: Create multiple search strategies for comprehensive coverage"""
        
        strategies = []
        
        # Strategy 1: Direct Adeona site search
        strategies.append({
            'type': 'site_specific',
            'query': f'site:{self.adeona_domain} {query}',
            'priority': 'high'
        })
        
        # Strategy 2: Adeona Technologies specific search
        strategies.append({
            'type': 'company_specific', 
            'query': f'"Adeona Technologies" {query}',
            'priority': 'high'
        })
        
        # Strategy 3: Combined approach for services
        if any(word in query.lower() for word in ['service', 'solution', 'software', 'development']):
            strategies.append({
                'type': 'services_focused',
                'query': f'site:{self.adeona_domain} "Adeona Technologies" services solutions {query}',
                'priority': 'medium'
            })
        
        # Strategy 4: Privacy policy specific if relevant
        if any(word in query.lower() for word in ['privacy', 'data', 'policy', 'protection']):
            strategies.append({
                'type': 'privacy_focused',
                'query': f'site:{self.adeona_domain} privacy policy {query}',
                'priority': 'high'
            })
        
        return strategies
    
    async def _execute_search_strategy(self, strategy: Dict[str, str], max_results: int) -> List[Dict[str, Any]]:
        """Execute a specific search strategy"""
        try:
            # Create SSL context with proper settings
            ssl_context = ssl.create_default_context()
            ssl_context.check_hostname = False
            ssl_context.verify_mode = ssl.CERT_NONE
            
            connector = aiohttp.TCPConnector(
                ssl=ssl_context,
                limit=10,
                limit_per_host=5
            )
            
            timeout = aiohttp.ClientTimeout(total=self.search_config['timeout'])
            
            async with aiohttp.ClientSession(connector=connector, timeout=timeout) as session:
                params = {
                    'api_key': self.serpapi_key,
                    'engine': 'google',
                    'q': strategy['query'],
                    'num': min(max_results, 10),  # Limit per strategy
                    'hl': 'en',
                    'gl': 'lk'  # Sri Lanka location for more relevant results
                }
                
                logger.info(f"Executing {strategy['type']} strategy: {strategy['query']}")
                
                async with session.get(self.serpapi_url, params=params) as response:
                    if response.status == 200:
                        data = await response.json()
                        organic_results = data.get('organic_results', [])
                        
                        if organic_results:
                            logger.info(f"{strategy['type']} strategy found {len(organic_results)} results")
                            return self._process_strategy_results(organic_results, strategy['type'])
                        else:
                            logger.warning(f"{strategy['type']} strategy returned no results")
                            return []
                    else:
                        logger.error(f"SerpAPI request failed with status: {response.status}")
                        return []
        
        except asyncio.TimeoutError:
            logger.warning(f"Search strategy {strategy['type']} timed out")
            return []
        except Exception as e:
            logger.error(f"Search strategy {strategy['type']} failed: {e}")
            return []
    
    def _process_strategy_results(self, results: List[Dict], strategy_type: str) -> List[Dict[str, Any]]:
        """Process results from a specific search strategy"""
        processed_results = []
        
        for result in results:
            link = result.get('link', '')
            title = result.get('title', '')
            snippet = result.get('snippet', '')
            
            # IMPROVED: Better validation for Adeona content
            if not self._is_valid_adeona_result(link, title, snippet):
                continue
            
            # Calculate relevance score based on strategy and content
            relevance_score = self._calculate_enhanced_relevance_score(
                title, snippet, strategy_type
            )
            
            processed_results.append({
                'title': title,
                'link': link,
                'snippet': snippet,
                'source': 'serpapi_realtime',
                'strategy_type': strategy_type,
                'relevance_score': relevance_score
            })
        
        return processed_results
    
    def _is_valid_adeona_result(self, link: str, title: str, snippet: str) -> bool:
        """IMPROVED: Better validation for Adeona-specific results"""
        
        # Must be from Adeona domain
        if not self.adeona_domain.lower() in link.lower():
            return False
        
        # Must have substantial content
        if len(snippet.strip()) < self.search_config['min_content_length']:
            return False
        
        # Should mention Adeona or related terms
        content = f"{title} {snippet}".lower()
        adeona_indicators = [
            'adeona', 'technologies', 'software development', 
            'crm', 'mobile app', 'web development', 'sri lanka'
        ]
        
        if not any(indicator in content for indicator in adeona_indicators):
            return False
        
        # Exclude unwanted content
        excluded_terms = ['error', '404', 'not found', 'under construction']
        if any(term in content for term in excluded_terms):
            return False
        
        return True
    
    def _calculate_enhanced_relevance_score(self, title: str, snippet: str, strategy_type: str) -> float:
        """IMPROVED: Calculate relevance score with strategy weighting"""
        score = 0.0
        content = f"{title} {snippet}".lower()
        
        # Strategy-based base score
        strategy_scores = {
            'site_specific': 2.0,
            'company_specific': 1.8,
            'services_focused': 1.5,
            'privacy_focused': 1.7
        }
        score += strategy_scores.get(strategy_type, 1.0)
        
        # High value terms
        high_value_terms = [
            ('adeona technologies', 3.0),
            ('adeona foresight', 2.5),
            ('custom software', 2.0),
            ('mobile app development', 2.0),
            ('crm system', 2.0),
            ('web development', 1.5)
        ]
        
        for term, weight in high_value_terms:
            if term in content:
                score += weight
        
        # Medium value terms
        medium_value_terms = [
            ('software development', 1.0),
            ('it solutions', 1.0),
            ('digital transformation', 1.0),
            ('colombo', 0.8),
            ('sri lanka', 0.8),
            ('privacy policy', 1.2),
            ('services', 0.5)
        ]
        
        for term, weight in medium_value_terms:
            if term in content:
                score += weight
        
        # Title boost
        if 'adeona' in title.lower():
            score += 1.0
        
        # Content length bonus
        if len(snippet) > 100:
            score += 0.5
        
        # Normalize score to 0-10 range
        normalized_score = min(score / 2.0, 5.0)  # Max 5.0 for SerpAPI results
        
        return round(normalized_score, 2)
    
    def _process_and_deduplicate_results(self, all_results: List[Dict], max_results: int) -> List[Dict[str, Any]]:
        """IMPROVED: Process and deduplicate results with better ranking"""
        
        if not all_results:
            return []
        
        # Remove exact duplicates based on URL
        seen_urls = set()
        unique_results = []
        
        for result in all_results:
            url = result.get('link', '')
            if url not in seen_urls:
                seen_urls.add(url)
                unique_results.append(result)
        
        # Sort by relevance score
        unique_results.sort(key=lambda x: x.get('relevance_score', 0), reverse=True)
        
        # Remove similar content (based on snippet similarity)
        final_results = []
        seen_snippets = set()
        
        for result in unique_results:
            snippet = result.get('snippet', '')
            snippet_key = snippet[:50].lower().replace(' ', '')
            
            if snippet_key not in seen_snippets:
                seen_snippets.add(snippet_key)
                final_results.append(result)
                
                if len(final_results) >= max_results:
                    break
        
        logger.info(f"Deduplication: {len(all_results)} -> {len(unique_results)} -> {len(final_results)}")
        return final_results
    
    async def search_privacy_policy(self, query: str) -> List[Dict[str, Any]]:
        """Specific search for Adeona privacy policy information"""
        try:
            log_function_call("search_privacy_policy", {"query": query})
            
            privacy_query = f"privacy policy data protection {query}"
            return await self.search_adeona_specific(privacy_query, max_results=3)
            
        except Exception as e:
            log_error(e, "search_privacy_policy")
            return []
    
    async def search_services(self, query: str) -> List[Dict[str, Any]]:
        """Specific search for Adeona services information"""
        try:
            log_function_call("search_services", {"query": query})
            
            services_query = f"services solutions software development {query}"
            return await self.search_adeona_specific(services_query, max_results=5)
            
        except Exception as e:
            log_error(e, "search_services")
            return []
    
    async def search_company_info(self, query: str) -> List[Dict[str, Any]]:
        """Specific search for general company information"""
        try:
            log_function_call("search_company_info", {"query": query})
            
            company_query = f"about company information {query}"
            return await self.search_adeona_specific(company_query, max_results=4)
            
        except Exception as e:
            log_error(e, "search_company_info")
            return []
    
    async def comprehensive_adeona_search(self, query: str) -> Dict[str, List[Dict[str, Any]]]:
        """Perform comprehensive search across different Adeona content types"""
        try:
            log_function_call("comprehensive_adeona_search", {"query": query})
            
            # Perform multiple targeted searches concurrently
            search_tasks = [
                self.search_adeona_specific(query, max_results=5),
                self.search_services(query),
                self.search_company_info(query)
            ]
            
            # Add privacy search if query is privacy-related
            if any(term in query.lower() for term in ['privacy', 'data', 'policy', 'protection']):
                search_tasks.append(self.search_privacy_policy(query))
            
            results = await asyncio.gather(*search_tasks, return_exceptions=True)
            
            # Organize results
            comprehensive_results = {
                'general': results[0] if len(results) > 0 and not isinstance(results[0], Exception) else [],
                'services': results[1] if len(results) > 1 and not isinstance(results[1], Exception) else [],
                'company_info': results[2] if len(results) > 2 and not isinstance(results[2], Exception) else [],
                'privacy': results[3] if len(results) > 3 and not isinstance(results[3], Exception) else []
            }
            
            total_results = sum(len(v) for v in comprehensive_results.values())
            logger.info(f"Comprehensive search completed: {total_results} total results")
            return comprehensive_results
            
        except Exception as e:
            log_error(e, "comprehensive_adeona_search")
            return {'general': [], 'services': [], 'company_info': [], 'privacy': []}
    
    async def get_best_answer_snippet(self, query: str) -> Optional[str]:
        """Get the best answer snippet for a specific query"""
        try:
            results = await self.search_adeona_specific(query, max_results=3)
            
            if not results:
                return None
            
            # Return the snippet from the highest scoring result
            best_result = max(results, key=lambda x: x.get('relevance_score', 0))
            return best_result['snippet']
            
        except Exception as e:
            log_error(e, "get_best_answer_snippet")
            return None
    
    def is_available(self) -> bool:
        """Check if SerpAPI service is available"""
        return bool(self.serpapi_key)
    
    async def test_connection(self) -> Dict[str, Any]:
        """Test SerpAPI connection and functionality"""
        try:
            log_function_call("test_serpapi_connection")
            
            if not self.serpapi_key:
                return {
                    "success": False,
                    "error": "SerpAPI key not configured",
                    "suggestion": "Add SERPAPI_API_KEY to environment variables"
                }
            
            # Test with simple Adeona query
            test_query = "Adeona Technologies"
            results = await self.search_adeona_specific(test_query, max_results=2)
            
            return {
                "success": len(results) > 0,
                "results_count": len(results),
                "test_query": test_query,
                "first_result": results[0] if results else None,
                "api_status": "connected",
                "search_strategies": len(self._create_search_strategies(test_query))
            }
            
        except Exception as e:
            log_error(e, "test_serpapi_connection")
            return {
                "success": False,
                "error": str(e),
                "api_status": "error"
            }

# Create global instance
serpapi_service = EnhancedSerpAPIService()