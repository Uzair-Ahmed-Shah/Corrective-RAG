import arxiv 
import time

def search_arxiv(query: str, max_retries=3):
    """
    Returns a LIST of dictionary objects (papers) instead of a single string.
    This allows us to chunk and index each paper separately into ChromaDB.
    """
    search = arxiv.Search(
        query= query,
        max_results = 5,
        sort_by = arxiv.SortCriterion.Relevance
    )
    
    for attempt in range(max_retries):
        try:
            results_list = []
            for result in search.results():
                paper_url = result.entry_id
                published_date = result.published.strftime("%Y-%m-%d") if result.published else "Unknown"
                
                content_string = f"Title: {result.title}\nPublished: {published_date}\nURL: {paper_url}\nSummary: {result.summary}"
                results_list.append({
                    "id": paper_url,
                    "content": content_string
                })
            return results_list
        except arxiv.HTTPError as e:
            if attempt == max_retries - 1:
                print(f"arXiv Error: {e}")
                return []
            
            wait_time = 5 * (2 ** attempt)
            print(f"arXiv rate limit hit. Retrying in {wait_time} seconds (Attempt {attempt + 1}/{max_retries})...")
            time.sleep(wait_time)
            
    return []