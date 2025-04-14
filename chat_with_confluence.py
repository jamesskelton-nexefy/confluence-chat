import os
from typing import List, Dict
from pinecone import Pinecone
from openai import OpenAI
from dotenv import load_dotenv
import re
from typing import Tuple

# Load environment variables
load_dotenv()

# Initialize OpenAI
client = OpenAI(api_key=os.getenv("OPENAI_API_KEY"))

# Initialize Pinecone
pc = Pinecone(api_key=os.getenv("PINECONE_API_KEY"))
index = pc.Index("pinecone")  # Your index name

def extract_keywords(text: str) -> List[str]:
    """
    Extract important keywords from the query using simple NLP techniques
    """
    # Remove special characters and convert to lowercase
    text = re.sub(r'[^\w\s]', ' ', text.lower())
    
    # Split into words
    words = text.split()
    
    # Remove common stop words (extend this list as needed)
    stop_words = {'a', 'an', 'and', 'are', 'as', 'at', 'be', 'by', 'for', 'from', 
                 'has', 'he', 'in', 'is', 'it', 'its', 'of', 'on', 'that', 'the', 
                 'to', 'was', 'were', 'will', 'with'}
    
    keywords = [word for word in words if word not in stop_words]
    return keywords

def keyword_match_score(text: str, keywords: List[str]) -> float:
    """
    Calculate a simple keyword match score for a text
    """
    if not text or not keywords:
        return 0.0
        
    text_lower = text.lower()
    matches = sum(1 for keyword in keywords if keyword in text_lower)
    return matches / len(keywords)

def hybrid_search(query: str, k: int = 5, debug: bool = False) -> List[Dict]:
    """
    Perform hybrid search combining vector similarity with keyword matching
    """
    # Get query embedding
    response = client.embeddings.create(
        model="text-embedding-3-large",
        input=query,
    )
    query_embedding = response.data[0].embedding
    
    # Extract keywords for keyword matching
    keywords = extract_keywords(query)
    
    # Get more results initially for hybrid reranking
    initial_k = k * 3
    
    try:
        # Try hybrid search if supported by your Pinecone index
        results = index.query(
            vector=query_embedding,
            top_k=initial_k,
            namespace="default",
            include_metadata=True,
            alpha=0.7,  # Blend between vector (1-alpha) and keyword (alpha) similarities
            filter={},  # Optional filters
        )
        
        if debug:
            print("\nDebug: First result metadata fields:")
            if results.matches:
                print(f"Available fields: {list(results.matches[0].metadata.keys())}")
                print(f"Sample metadata: {results.matches[0].metadata}")
            
    except Exception as e:
        print(f"Hybrid search not supported, falling back to vector search: {str(e)}")
        # Fallback to vector search and manual keyword scoring
        results = index.query(
            vector=query_embedding,
            top_k=initial_k,
            namespace="default",
            include_metadata=True
        )
        
        if debug and results.matches:
            print("\nDebug: First result metadata fields (fallback search):")
            print(f"Available fields: {list(results.matches[0].metadata.keys())}")
            print(f"Sample metadata: {results.matches[0].metadata}")
        
        # Add keyword matching scores
        for match in results.matches:
            text = match.metadata.get('text', '')
            title = match.metadata.get('title', '')
            space = match.metadata.get('space', '')
            combined_text = f"{title} {space} {text}"
            
            # Calculate keyword score
            keyword_score = keyword_match_score(combined_text, keywords)
            
            # Combine scores (70% vector similarity, 30% keyword matching)
            match.score = 0.7 * match.score + 0.3 * keyword_score
    
    return results.matches

def rerank_results(query: str, matches: List[Dict], debug: bool = False) -> List[Dict]:
    """
    Re-rank retrieved documents using GPT for better relevance scoring
    """
    if not matches:
        return matches

    # Extract texts and prepare for reranking
    texts = []
    for match in matches:
        text = match.metadata.get('text', '')
        title = match.metadata.get('title', '')
        space = match.metadata.get('space', '')
        context = f"Title: {title}\nSpace: {space}\nContent: {text}"
        texts.append(context)

    # Construct reranking prompt with clearer instructions
    rerank_prompt = (
        "Rate each document's relevance to the query on a scale of 0-10, where 10 is most relevant.\n"
        "Return ONLY a comma-separated list of ratings in document order.\n\n"
        f"Query: {query}\n\n"
        "Documents to rate:\n"
    )
    
    for i, text in enumerate(texts, 1):
        rerank_prompt += f"\nDocument {i}:\n{text}\n---"

    rerank_prompt += "\n\nOutput format example for 3 documents: 8,4,9\nYour ratings:"

    if debug:
        print("Reranking prompt:", rerank_prompt)

    # Get ratings from GPT
    try:
        response = client.chat.completions.create(
            model="gpt-3.5-turbo",
            messages=[{"role": "user", "content": rerank_prompt}],
            temperature=0,
        )

        ratings_str = response.choices[0].message.content.strip()
        if debug:
            print("Ratings response:", ratings_str)
        
        # Parse ratings and handle various formats
        # Remove any text that might surround the numbers
        ratings_str = re.search(r'[\d,\s]+', ratings_str).group(0)
        ratings = [float(r.strip()) for r in ratings_str.split(',') if r.strip()]
        
        # Validate we have the right number of ratings
        if len(ratings) != len(matches):
            print(f"Warning: Got {len(ratings)} ratings for {len(matches)} documents, using original order")
            return matches
            
        # Create (rating, index) pairs and sort by rating descending
        rated_indices = list(enumerate(ratings))
        rated_indices.sort(key=lambda x: x[1], reverse=True)
        
        # Extract the sorted indices
        sorted_indices = [idx for idx, _ in rated_indices]
        
        # Reorder matches based on ratings
        reranked = [matches[i] for i in sorted_indices]
        
        # Update scores based on ratings
        for match, (_, rating) in zip(reranked, rated_indices):
            match.score = rating / 10.0  # Normalize to 0-1 range
        
        return reranked
        
    except Exception as e:
        print(f"Reranking failed: {str(e)}, falling back to original order")
        return matches

def reformulate_query(query: str) -> List[str]:
    """
    Generate multiple query variations to improve search coverage
    """
    messages = [
        {
            "role": "system",
            "content": (
                "You are a helpful assistant that reformulates search queries to improve document retrieval. "
                "Generate 2-3 alternative phrasings of the user's query that might help find relevant documentation. "
                "Focus on using different technical terms, synonyms, and ways of asking for the same information. "
                "Return ONLY the reformulated queries, one per line."
            )
        },
        {
            "role": "user",
            "content": f"Original query: {query}"
        }
    ]
    
    response = client.chat.completions.create(
        model="gpt-3.5-turbo",
        messages=messages,
        temperature=0.7,
        max_tokens=200,
    )
    
    reformulations = response.choices[0].message.content.strip().split('\n')
    reformulations = [q.strip() for q in reformulations if q.strip()]
    reformulations.insert(0, query)  # Keep original query
    
    return reformulations

def get_relevant_context(query: str, k: int = 5) -> List[Dict]:
    """
    Get relevant documents using hybrid search with query reformulation
    """
    # Generate query variations
    query_variations = reformulate_query(query)
    
    # Get results for each query variation
    all_matches = []
    seen_ids = set()
    
    for variation in query_variations:
        # Get matches for this variation
        matches = hybrid_search(variation, k=k)
        
        # Add unique matches to results
        for match in matches:
            # Create unique ID from metadata (adjust based on your metadata structure)
            match_id = f"{match.metadata.get('title', '')}-{match.metadata.get('space', '')}"
            
            if match_id not in seen_ids:
                seen_ids.add(match_id)
                all_matches.append(match)
    
    # Sort combined results by score
    all_matches.sort(key=lambda x: x.score, reverse=True)
    
    # Take top k unique results
    top_matches = all_matches[:k]
    
    # Rerank final results
    reranked_matches = rerank_results(query, top_matches)
    
    return reranked_matches

def format_context_with_citations(matches: List[Dict]) -> Tuple[str, Dict]:
    """
    Format context with document IDs for citation and return citation mapping
    """
    context = "Here are the relevant sections:\n\n"
    citation_map = {}
    
    for i, match in enumerate(matches, 1):
        metadata = match.metadata
        doc_id = f"[{i}]"
        
        # Extract title from filename or first line of text
        text = metadata.get('text', '')
        title = text.split('\n')[0] if text else 'Untitled Document'
        
        # Get record ID for reference
        record_id = metadata.get('record_id', 'Unknown ID')
        
        # Store citation information
        citation_map[doc_id] = {
            "title": title,
            "record_id": record_id,
            "relevance": match.score
        }
        
        # Format context entry
        context += f"Document {doc_id}:\n"
        context += f"Title: {title}\n"
        context += f"Content: {text}\n"
        context += f"Relevance Score: {match.score:.2f}\n\n"
    
    return context, citation_map

def chat_with_context(query: str, context: str, citation_map: Dict = None, conversation_history: List[Dict] = None) -> str:
    """
    Generate a response with citations and additional context if needed
    """
    citation_instruction = ""
    if citation_map:
        citation_instruction = (
            "When referencing information, cite your sources using the document IDs provided "
            "(e.g., [1], [2], etc.). You can combine multiple citations [1,2] or cite ranges [1-3]. "
            "Make sure to cite ALL sources used in your response."
        )
    
    # Base system message
    system_message = {
        "role": "system",
        "content": (
            "You are a helpful assistant with access to documentation. "
            "Use the provided context to answer questions accurately and concisely. "
            "Maintain awareness of the conversation history and refer back to previous context when relevant. "
            "If the user asks follow-up questions, relate them to previous answers when appropriate. "
            f"{citation_instruction}\n"
            "If you're not confident about any part of your answer, say so explicitly."
        )
    }
    
    # Start with system message
    messages = [system_message]
    
    # Add conversation history if available
    if conversation_history:
        # Add relevant history but limit to last 4 exchanges to maintain context window
        for msg in conversation_history[-4:]:
            # Don't include the raw context in historical messages
            if msg["role"] == "user":
                messages.append({
                    "role": "user",
                    "content": msg["content"]  # Just the question
                })
            else:
                messages.append(msg)
    
    # Add current context and query as the final message
    messages.append({
        "role": "user",
        "content": (
            f"Previous conversation context is shown above. "
            f"Now answer this new question using the following reference material:\n\n"
            f"Context:\n{context}\n\n"
            f"Question: {query}"
        )
    })
    
    response = client.chat.completions.create(
        model="gpt-4-0125-preview",
        messages=messages,
        temperature=0.7,
    )
    
    response_text = response.choices[0].message.content
    
    # Add citation details at the end of the response if citations were used
    if citation_map:
        # Extract all citations from the response
        citations_used = set(re.findall(r'\[(\d+)\]', response_text))
        if citations_used:
            response_text += "\n\nSources:\n"
            for citation in sorted(citations_used, key=int):
                doc_id = f"[{citation}]"
                if doc_id in citation_map:
                    doc = citation_map[doc_id]
                    response_text += f"{doc_id} {doc['title']} (ID: {doc['record_id']})\n"
    
    return response_text

def clear_conversation_history() -> List[Dict]:
    """
    Clear conversation history and return a fresh empty list
    """
    return []

def trim_conversation_history(history: List[Dict], max_exchanges: int = 4) -> List[Dict]:
    """
    Trim conversation history to keep only the last N exchanges
    """
    if len(history) > max_exchanges * 2:  # Each exchange has 2 messages (user + assistant)
        return history[-(max_exchanges * 2):]
    return history

def main():
    print("Welcome to the Confluence Documentation Assistant!")
    print("Commands: 'quit' to exit, 'clear' to start new session")
    print("Loading knowledge base...")
    
    # Initialize conversation history
    conversation_history = clear_conversation_history()
    
    while True:
        query = input("\nYour question: ").strip().lower()
        
        if query == 'quit':
            break
        elif query == 'clear':
            conversation_history = clear_conversation_history()
            print("Started new conversation session")
            continue
            
        try:
            # Get relevant documents
            print("Searching documentation...")
            matches = hybrid_search(query, debug=True)  # Enable debug logging
            
            if not matches:
                print("No relevant documentation found.")
                continue
                
            # Format context with citations
            context, citation_map = format_context_with_citations(matches)
            
            # Generate response
            print("\nGenerating response...")
            response = chat_with_context(query, context, citation_map, conversation_history)
            
            # Update conversation history
            conversation_history.append({"role": "user", "content": query})
            conversation_history.append({"role": "assistant", "content": response})
            
            # Trim history to prevent excessive growth
            conversation_history = trim_conversation_history(conversation_history)
            
            print("\nResponse:", response)
            
        except Exception as e:
            print(f"An error occurred: {str(e)}")

if __name__ == "__main__":
    main() 