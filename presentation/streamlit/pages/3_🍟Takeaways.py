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
    - ##### Don't try and reinvent the wheel
        - Many modules imported in the final version were being written from scratch before the scale and complexity of
        the features necessitated outside tools. Both the reddit API and prompt logic were originally
        going to be bespoke before better alternatives presented themselves.
    - ##### Don't be too precious about individual graphs
        - Network analysis is both art and science and as the underlying graph data produces similar results among a
        number of different simulations, one doesn't have to be too concerned about getting a setting wrong and ruining
        *the perfect graph*
"""
)
