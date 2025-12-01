import streamlit as st

st.header("Design")

st.markdown(
    """
    As the PRAW API exposes the full comment thread from a submission
    object by means of a `replace_more()` method, which populates a
    comment tree scraping entire threads becomes a matter of getting
      a submission and following along the comments. As PRAW also allows
    for getting the top **N** submissions from a subreddit this
    could easily be extended to scraping entire subreddits.
    """
)

st.markdown(
    """
    Given the breath of choice available in terms of both the granularity and
    sheer amount of data available on reddit. I opted to build a tool
    which gave the user control over what to extract.
    To this end I created a command line interface employing the
    `prompt_toolkit` library,
    """
)

st.success(
    """this library also allows for nice
    quality of life features like history and autocomplete
    for free.
    """
)

with st.container(horizontal_alignment="center"):
    st.image("presentation/assets/prompt_toolkit_features.png")

st.warning(
    """initially the reddit API was called sequentially,
         each Get request having to wait for the previous to complete
        this resulted in long extraction times"""
)

st.markdown(
    """
    The sequential extraction was replaced by a multithreaded approach
    where a number of requests were dispatched at once. The number of 'workers'
    being supplied by the user (defaulting to 5)
    """
)
