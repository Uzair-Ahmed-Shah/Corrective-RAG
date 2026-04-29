import arxiv 
import time

def search_arxiv(query: str, max_retries=3):
    search = arxiv.Search(
        query= query,
        max_results = 3,
        sort_by = arxiv.SortCriterion.Relevance
    )
    
    for attempt in range(max_retries):
        try:
            combined_summary = ""
            for result in search.results():
                paper_url = result.entry_id
                published_date = result.published.strftime("%Y-%m-%d") if result.published else "Unknown"
                
                combined_summary += f"\n---\nTitle: {result.title}\nPublished: {published_date}\nURL: {paper_url}\nSummary: {result.summary}\n"
            return combined_summary
        except arxiv.HTTPError as e:
            if attempt == max_retries - 1:
                print(f"arXiv Error: {e}")
                return "No arXiv results found due to rate limiting."
            
            wait_time = 5 * (2 ** attempt)
            print(f"arXiv rate limit hit. Retrying in {wait_time} seconds (Attempt {attempt + 1}/{max_retries})...")
            time.sleep(wait_time)
            
    return ""