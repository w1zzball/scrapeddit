import streamlit as st

st.header("Takeaways")

st.markdown(
    """
    ### Lessons
    were I to start the project over, knowing what I know now. Here are some things I would do differently
    - ##### Do not refactor too late
        - As the project grew in scope and new features were added, refactoring some code
        earlier (e.g. the code surrounding scraping subreddits) would have been refactored before
        new features (e.g. the detailed progress information) were added to keep the function simpler.
    - ##### Don't try and re-invent the wheel
        - Many modules imported in the final version were being written from scratch before the scale and complexity of
        the features necessitated outside tools. Both the reddit API and prompt logic were originally
        going to be bespoke before better alternatives presented themselves.
    - ##### Don't be too precious about individual graphs
        - Network analysis is both art and science and as the underlying graph data produces similar results among a
        number of different simulations, one doesn't have to be too concerned about getting a setting wrong and ruining
        *the perfect graph*
    - ##### Write tests sooner
        - Testing certain aspects like components using context managers is quite complicated and writing tests either before
        or immediately after the function was implemented would have saved some headaches.
"""
)

st.markdown(
    """
    ### Features to be added
    - Either by way of VPN or age confirmation a bot can scrape 18+ subreddits. So a toggle for allowing/disallowing
    content from communities flagged 18+ would be useful.
    - Changing the reddit API from PRAW to its asynchronous variant may give some slight speed increases.
    - Outputting to files from the prompt.
    - flags for censoring words / information.
    - flags for obsfucation
    ### Other analysis
    - A large corpus of text lends itself to natural language processing and in future I would like to try both topic 
    extraction and model training on the data.
    """
)

st.markdown(
    """
    ### Thanks
    - ##### Huge thanks to Ed and Ryan for their instruction and guidance.
    - ##### Thanks to the rest of the DF Team, including but not limited to Lisa, Bassmah, Ruth, Alex and Tim.
    - ##### Shoutout to the rest of my cohort for the fun collaborations and banter.
"""
)

st.markdown(
    """
    ### Acknowledgements
    -  [Vicent Gilabert's](https://github.com/vgilabert94) amazing [streamlit plugin](https://github.com/vgilabert94/streamlit-image-zoom) allowing for zoomable images was a lifesaver
"""
)
