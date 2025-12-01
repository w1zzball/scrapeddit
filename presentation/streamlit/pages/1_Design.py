import streamlit as st

st.header("Design")

st.markdown(
    """
    As the PRAW API exposes the full comment thread from a submission 
    object by means of a `replace_more()` method, which populates a comment tree
    scraping entire threads becomes a matter of getting a submission and following along the comments.
    As PRAW also allows for getting the top **N** submissions from a subreddit this could easily be extended
    to scraping entire subreddits.
    """
)
