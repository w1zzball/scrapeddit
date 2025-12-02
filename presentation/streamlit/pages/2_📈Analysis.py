import streamlit as st

st.header("Analysis")

st.markdown(
    """
    After gathering a substantial amount of data, 1.3million comments from 33,000 subreddits.
    I set out to analyse the structure of the communities I had scraped.
"""
)

st.markdown(
    """
    ## Methodology-
    I opted to use the number of shared commenters (i.e. redditors who had commented in both subreddits) 
    as a measure of connectedness between communities.
"""
)

st.warning(
    """as the original ETL processes only took vertical slices of a single comment/thread/subreddit and not at commenters.
    The data may have been sparse in terms of commenter overlap"""
)

st.success(
    """
    To flesh out the data I wrote a script which given a redditor/list of redditors, 
    would fetch the top *n* posts from that redditor.

    To specifically find connections I wrote a script which would recursively follow subreddits,
    taking the top redditors from the subreddit, examining their comments, 
    scraping them and then applying the same function to the subreddits those comments were posted to.
"""
)

st.warning(
    """
    the recursive expansion of the dataset did work although two main problems were encountered
    
"""
)
